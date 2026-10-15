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


def test_sensitive_read_and_scrape_routes_require_auth(client):
    assert client.get("/api/trace").status_code == 401
    assert client.get("/api/market-prices").status_code == 401
    assert client.post("/api/scraper/sync").status_code == 401


def test_logout_revokes_session(client):
    token, _ = register(client, "+27820000005")
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200
    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401