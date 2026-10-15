import base64
import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import stockup_pulse.core.db as database
from stockup_pulse.api import main as api


@pytest.fixture
def client(monkeypatch, tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'api-test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", test_engine)
    SQLModel.metadata.create_all(test_engine)

    async def no_scrape(**kwargs):
        return []

    monkeypatch.setattr(api.live_retail_scraper, "scrape_staples_and_sync", no_scrape)
    with TestClient(api.app) as test_client:
        yield test_client
    test_engine.dispose()


def register(client: TestClient, phone: str) -> tuple[str, int]:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Owner",
            "shop_name": "Test Shop",
            "whatsapp_number": phone,
            "password": "a-strong-test-password",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    user = database.authenticate_user(phone, "a-strong-test-password")
    return payload["access_token"], user.id


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_registration_hashes_password_and_rejects_duplicate(client):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Owner",
            "shop_name": "Test Shop",
            "whatsapp_number": "+27820000001",
            "password": "a-strong-test-password",
        },
    )
    assert response.status_code == 200
    user = database.authenticate_user("+27820000001", "a-strong-test-password")
    assert user is not None
    assert user.password_hash != "a-strong-test-password"

    duplicate = client.post(
        "/api/auth/register",
        json={
            "full_name": "Other Owner",
            "shop_name": "Other Shop",
            "whatsapp_number": "+27820000001",
            "password": "another-strong-password",
        },
    )
    assert duplicate.status_code == 409
    assert database.authenticate_user("+27820000001", "a-strong-test-password") is not None


def test_legacy_password_is_upgraded_only_after_valid_login(client):
    with Session(database.engine) as session:
        session.add(database.User(
            whatsapp_number="+27820000006",
            full_name="Legacy Owner",
            shop_name="Legacy Shop",
            password_hash="legacy-password",
        ))
        session.commit()

    assert database.authenticate_user("+27820000006", "incorrect-password") is None
    with Session(database.engine) as session:
        stored = session.exec(
            database.select(database.User).where(database.User.whatsapp_number == "+27820000006")
        ).first()
        assert stored.password_hash == "legacy-password"

    response = client.post("/api/auth/login", json={
        "whatsapp_number": "+27820000006",
        "password": "legacy-password",
    })
    assert response.status_code == 200
    with Session(database.engine) as session:
        stored = session.exec(
            database.select(database.User).where(database.User.whatsapp_number == "+27820000006")
        ).first()
        assert stored.password_hash.startswith("pbkdf2_sha256$")


def test_existing_demo_account_is_removed(client):
    with Session(database.engine) as session:
        session.add(database.User(
            whatsapp_number="+27821234567",
            full_name="Mpho Khumalo",
            shop_name="Sunnyside Spaza",
            password_hash="spaza123",
        ))
        session.commit()

    database.seed_users_if_empty()
    assert database.authenticate_user("+27821234567", "spaza123") is None


def test_plan_approval_and_orders_are_owner_scoped_and_persistent(client):
    owner_token, _ = register(client, "+27820000002")
    other_token, _ = register(client, "+27820000003")
    plan_body = {
        "budget": 1000,
        "items": [{"product": "Brown Bread", "recommended_qty": 2, "unit_price": 16.5}],
    }

    assert client.post("/api/plan", json=plan_body).status_code == 401
    plan_response = client.post("/api/plan", json=plan_body, headers=auth(owner_token))
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["plan_id"]

    assert client.post(
        "/api/plan/approve",
        json={"approved": True, "plan_id": plan_id},
        headers=auth(other_token),
    ).status_code == 404
    assert client.post(
        "/api/orders",
        json={"approved": True, "plan_id": plan_id},
        headers=auth(owner_token),
    ).status_code == 409

    approved = client.post(
        "/api/plan/approve",
        json={"approved": True, "plan_id": plan_id},
        headers=auth(owner_token),
    )
    assert approved.status_code == 200
    created = client.post(
        "/api/orders",
        json={"approved": True, "plan_id": plan_id, "store_name": "Test Shop"},
        headers=auth(owner_token),
    )
    assert created.status_code == 200
    order_numbers = [order["order_number"] for order in created.json()["orders"]]
    repeated = client.post(
        "/api/orders",
        json={"approved": True, "plan_id": plan_id, "store_name": "Test Shop"},
        headers=auth(owner_token),
    )
    assert [order["order_number"] for order in repeated.json()["orders"]] == order_numbers
    assert client.get("/api/orders", headers=auth(other_token)).json() == []


def test_plan_rejects_invalid_financial_inputs(client):
    token, _ = register(client, "+27820000004")
    response = client.post(
        "/api/plan",
        headers=auth(token),
        json={
            "budget": 1000,
            "items": [{"product": "Rice", "recommended_qty": -2, "unit_price": 5}],
        },
    )
    assert response.status_code == 422


def test_file_import_plan_requires_verified_zar_currency_and_integer_lead_time(client):
    token, _ = register(client, "+27820000016")
    item = {
        "product": "Rice",
        "recommended_qty": 2,
        "unit_price": 10,
        "supplier_price": 60,
        "our_price": 15,
        "supplier": "Makro",
        "source": "file_import",
        "reviewed": True,
        "retail_price_verified": True,
        "currency": "ZAR",
        "currency_verified": True,
        "lead_time_days": 2,
    }
    valid = client.post(
        "/api/plan",
        headers=auth(token),
        json={"budget": 100, "items": [item]},
    )
    assert valid.status_code == 200

    fractional_lead_time = {**item, "lead_time_days": 2.5}
    invalid = client.post(
        "/api/plan",
        headers=auth(token),
        json={"budget": 100, "items": [fractional_lead_time]},
    )
    assert invalid.status_code == 422

    unverified_currency = {**item, "currency_verified": False}
    invalid = client.post(
        "/api/plan",
        headers=auth(token),
        json={"budget": 100, "items": [unverified_currency]},
    )
    assert invalid.status_code == 422


def test_sensitive_read_and_scrape_routes_require_auth(client):
    assert client.get("/api/trace").status_code == 401
    assert client.get("/api/market-prices").status_code == 401
    assert client.post("/api/scraper/sync").status_code == 401


def test_logout_revokes_session(client):
    token, _ = register(client, "+27820000005")
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200
    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def _twilio_signature(url: str, fields: dict[str, str], token: str) -> str:
    payload = url + "".join(key + fields[key] for key in sorted(fields))
    digest = hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def test_twilio_signature_sender_isolation_and_repeated_approval_are_safe(client, monkeypatch):
    public_url = "https://stockup.example/api/whatsapp/webhook"
    auth_token = "test-twilio-token"
    monkeypatch.setattr(api.settings, "TWILIO_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(api.settings, "TWILIO_ACCOUNT_SID", "test-account")
    monkeypatch.setattr(api.settings, "TWILIO_AUTH_TOKEN", auth_token)
    monkeypatch.setattr(api.settings, "TWILIO_WEBHOOK_PUBLIC_URL", public_url)
    owner_token, _ = register(client, "+27820000011")
    register(client, "+27820000012")
    plan = client.post(
        "/api/plan",
        json={"budget": 1000, "items": [{"product": "Rice", "recommended_qty": 2, "unit_price": 10}]},
        headers=auth(owner_token),
    ).json()
    fields = {
        "From": "whatsapp:+27820000011",
        "Body": "APPROVE",
        "MessageSid": "SM-test-1",
    }

    valid = client.post(
        "/api/whatsapp/webhook",
        data=fields,
        headers={"X-Twilio-Signature": _twilio_signature(public_url, fields, auth_token)},
    )
    assert valid.status_code == 200
    assert "Approval confirmed" in valid.text
    initial_orders = client.get("/api/orders", headers=auth(owner_token)).json()
    assert len(initial_orders) == 1

    repeated = client.post(
        "/api/whatsapp/webhook",
        data=fields,
        headers={"X-Twilio-Signature": _twilio_signature(public_url, fields, auth_token)},
    )
    assert repeated.status_code == 200
    assert "Plan already approved" in repeated.text
    assert [order["order_number"] for order in client.get(
        "/api/orders", headers=auth(owner_token)
    ).json()] == [initial_orders[0]["order_number"]]

    attacker_fields = {**fields, "From": "whatsapp:+27820000012"}
    attacker = client.post(
        "/api/whatsapp/webhook",
        data=attacker_fields,
        headers={"X-Twilio-Signature": _twilio_signature(public_url, attacker_fields, auth_token)},
    )
    assert attacker.status_code == 200
    assert "No pending" in attacker.text
    assert client.post(
        "/api/whatsapp/webhook",
        data=fields,
        headers={"X-Twilio-Signature": "invalid"},
    ).status_code == 403


def test_file_import_requires_auth_and_provider_status_does_not_expose_credentials(client, monkeypatch):
    monkeypatch.setattr(api.settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(api.settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(api.settings, "AMD_ROCM_API_KEY", "never-return-this")
    monkeypatch.setattr(api.settings, "AMD_ROCM_MODEL", "vision-model")
    status = client.get("/api/providers")
    assert status.status_code == 200
    assert "never-return-this" not in status.text
    assert status.json()["amd_image_extraction"]["enabled"] is True

    assert client.post(
        "/api/plan/from-files",
        files=[("files", ("sales.csv", b"date,product,quantity_sold", "text/csv"))],
    ).status_code == 401


def test_file_import_rejects_oversized_file(client):
    token, _ = register(client, "+27820000013")
    response = client.post(
        "/api/plan/from-files",
        headers=auth(token),
        files=[("files", ("too-large.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv"))],
    )
    assert response.status_code == 413


def test_file_import_returns_review_candidates_without_saving_a_plan(client, monkeypatch):
    token, user_id = register(client, "+27820000014")
    monkeypatch.setattr(api.settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(api.settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(api.settings, "AMD_ROCM_API_KEY", "test-key")
    monkeypatch.setattr(api.settings, "AMD_ROCM_MODEL", "vision-model")
    monkeypatch.setattr(
        api.leaflet_extractor,
        "extract_structured_from_leaflet",
        lambda content, filename: {
            "source": "amd",
            "extracted_items": [{
                "product": "Milk 1L",
                "pack_size": "6 x 1L",
                "pack_price": 60,
                "supplier": "Makro",
                "currency": "ZAR",
                "evidence": "6 for R60",
                "confidence": 0.9,
            }],
        },
    )

    response = client.post(
        "/api/plan/from-files",
        headers=auth(token),
        data={"supplier_lead_times_json": '{"Makro": 2}', "planning_horizon_days": "14"},
        files=[
            ("files", ("sales.csv", b"date,product,quantity_sold\n2025-03-01,Milk 1L,4\n", "text/csv")),
            ("files", ("stock.csv", b"product,current_stock\nMilk 1L,2\n", "text/csv")),
            ("files", ("offer.jpg", b"fake image bytes", "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    candidate = response.json()["candidates"][0]
    assert candidate["unit_price"] == 10
    assert candidate["sales_history"] == [4]
    assert candidate["lead_time_days"] == 2
    assert candidate["currency_verified"] is False
    assert database.get_plan_for_user(user_id) is None


def test_file_import_provider_failure_returns_no_partial_review(client, monkeypatch):
    token, user_id = register(client, "+27820000015")
    monkeypatch.setattr(api.settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(api.settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(api.settings, "AMD_ROCM_API_KEY", "test-key")
    monkeypatch.setattr(api.settings, "AMD_ROCM_MODEL", "vision-model")

    def fail_extraction(content, filename):
        raise api.ProviderRequestError("sensitive provider detail")

    monkeypatch.setattr(api.leaflet_extractor, "extract_structured_from_leaflet", fail_extraction)
    response = client.post(
        "/api/plan/from-files",
        headers=auth(token),
        files=[
            ("files", ("sales.csv", b"date,product,quantity_sold\n2025-03-01,Milk 1L,4\n", "text/csv")),
            ("files", ("stock.csv", b"product,current_stock\nMilk 1L,2\n", "text/csv")),
            ("files", ("offer.jpg", b"fake image bytes", "image/jpeg")),
        ],
    )

    assert response.status_code == 502
    assert "sensitive provider detail" not in response.text
    assert database.get_plan_for_user(user_id) is None