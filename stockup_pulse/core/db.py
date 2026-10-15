"""
StockUp Pulse - Database Integration (SQLModel + SQLite)
Manages the `live_market_prices` table and connections for live retail scraper data.
"""

from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import os
import re
import base64
import hashlib
import hmac
import json
import math
import secrets
import uuid

# SQLite Database setup
DB_PATH = os.environ.get("SQLITE_DB_PATH", "stockup_pulse.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

class LiveMarketPrice(SQLModel, table=True):
    __tablename__ = "live_market_prices"

    id: Optional[int] = Field(default=None, primary_key=True)
    retailer: str = Field(index=True) # "makro", "shoprite", "checkers", "picknpay", "woolworths"
    query: str = Field(index=True) # "maize meal", "cooking oil", "sugar", "rice", "soft drink"
    product_name: str = Field(index=True)
    price_zar: float
    currency: str = Field(default="ZAR")
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    sku_or_gtin: Optional[str] = None
    availability: str = Field(default="InStock")
    source_type: str = Field(default="live_scraper") # "json-ld", "html-selector", "demo_fixture"
    scraped_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    whatsapp_number: str = Field(index=True, unique=True)
    full_name: str
    shop_name: str = Field(default="Sunnyside Spaza")
    password_hash: str
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuthSessionRecord(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at_utc: str
    revoked_at_utc: Optional[str] = None
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RestockingPlanRecord(SQLModel, table=True):
    __tablename__ = "restocking_plans"

    plan_id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    owner_id: int = Field(foreign_key="users.id", index=True)
    plan_json: str
    approved: bool = Field(default=False)
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ApiOrderRecord(SQLModel, table=True):
    __tablename__ = "api_orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    plan_id: str = Field(foreign_key="restocking_plans.plan_id", index=True)
    order_number: str = Field(unique=True, index=True)
    order_json: str
    created_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def init_db():
    """Initialize tables, fixture prices, and legacy demo-account cleanup."""
    SQLModel.metadata.create_all(engine)
    seed_baseline_if_empty()
    mark_fixture_prices()
    seed_users_if_empty()

def normalize_phone(phone: str) -> str:
    """Normalize South African phone formats to digits-only."""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if cleaned.startswith("0") and len(cleaned) == 10:
        cleaned = "+27" + cleaned[1:]
    return cleaned

def seed_users_if_empty():
    """Remove the former hard-coded demo account from existing local databases."""
    with Session(engine) as session:
        demo_user = session.exec(
            select(User).where(
                User.whatsapp_number == "+27821234567",
                User.full_name == "Mpho Khumalo",
                User.shop_name == "Sunnyside Spaza",
            )
        ).first()
        if demo_user:
            session.delete(demo_user)
            session.commit()


_PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{_PASSWORD_HASH_PREFIX}${_PASSWORD_HASH_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Return (matches, needs_upgrade); legacy plaintext is upgraded after successful login."""
    if not stored_hash.startswith(f"{_PASSWORD_HASH_PREFIX}$"):
        return hmac.compare_digest(stored_hash, password), True

    try:
        algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split("$", 3)
        if algorithm != _PASSWORD_HASH_PREFIX:
            return False, False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False, False

    return hmac.compare_digest(actual, expected), int(iterations) < _PASSWORD_HASH_ITERATIONS

def authenticate_user(whatsapp_number: str, password: str) -> Optional[User]:
    """Authenticates against the users table in SQLite."""
    clean_phone = normalize_phone(whatsapp_number)
    with Session(engine) as session:
        statement = select(User).where(User.whatsapp_number == clean_phone)
        user = session.exec(statement).first()
        if user:
            matches, needs_upgrade = verify_password(password, user.password_hash)
            if not matches:
                return None
            if needs_upgrade:
                user.password_hash = hash_password(password)
                session.add(user)
                session.commit()
                session.refresh(user)
            return user
    return None


def create_auth_session(user_id: int, lifetime_hours: int = 12) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=lifetime_hours)
    with Session(engine) as session:
        session.add(AuthSessionRecord(
            owner_id=user_id,
            token_hash=token_hash,
            expires_at_utc=expires_at.isoformat()
        ))
        session.commit()
    return token


def get_user_for_token(token: str) -> Optional[User]:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        auth_session = session.exec(
            select(AuthSessionRecord).where(
                AuthSessionRecord.token_hash == token_hash,
                AuthSessionRecord.revoked_at_utc.is_(None)
            )
        ).first()
        if not auth_session or datetime.fromisoformat(auth_session.expires_at_utc) <= now:
            return None
        return session.get(User, auth_session.owner_id)


def revoke_auth_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with Session(engine) as session:
        auth_session = session.exec(
            select(AuthSessionRecord).where(AuthSessionRecord.token_hash == token_hash)
        ).first()
        if auth_session and auth_session.revoked_at_utc is None:
            auth_session.revoked_at_utc = datetime.now(timezone.utc).isoformat()
            session.add(auth_session)
            session.commit()


def save_plan_for_user(owner_id: int, plan: dict) -> dict:
    plan_id = str(uuid.uuid4())
    plan_data = {**plan, "plan_id": plan_id}
    with Session(engine) as session:
        session.add(RestockingPlanRecord(
            plan_id=plan_id,
            owner_id=owner_id,
            plan_json=json.dumps(plan_data, sort_keys=True),
            approved=False
        ))
        session.commit()
    return plan_data


def get_plan_for_user(owner_id: int, plan_id: Optional[str] = None) -> Optional[dict]:
    with Session(engine) as session:
        statement = select(RestockingPlanRecord).where(RestockingPlanRecord.owner_id == owner_id)
        if plan_id:
            statement = statement.where(RestockingPlanRecord.plan_id == plan_id)
        else:
            statement = statement.order_by(RestockingPlanRecord.created_at_utc.desc())
        record = session.exec(statement).first()
        return json.loads(record.plan_json) if record else None


def set_plan_approval(owner_id: int, approved: bool, plan_id: Optional[str] = None) -> Optional[dict]:
    with Session(engine) as session:
        statement = select(RestockingPlanRecord).where(RestockingPlanRecord.owner_id == owner_id)
        if plan_id:
            statement = statement.where(RestockingPlanRecord.plan_id == plan_id)
        else:
            statement = statement.order_by(RestockingPlanRecord.created_at_utc.desc())
        record = session.exec(statement).first()
        if not record:
            return None
        data = json.loads(record.plan_json)
        data["approved"] = approved
        record.approved = approved
        record.plan_json = json.dumps(data, sort_keys=True)
        session.add(record)
        session.commit()
        return data


def save_orders_for_plan(owner_id: int, plan_id: str, orders: list[dict]) -> list[dict]:
    from stockup_pulse.orders.manager import PurchaseOrderManager

    with Session(engine) as session:
        plan = session.get(RestockingPlanRecord, plan_id)
        if not plan or plan.owner_id != owner_id or not plan.approved:
            raise ValueError("Orders can only be persisted for an approved plan owned by this account.")
        existing = session.exec(
            select(ApiOrderRecord).where(
                ApiOrderRecord.owner_id == owner_id,
                ApiOrderRecord.plan_id == plan_id
            ).order_by(ApiOrderRecord.id)
        ).all()
        if existing:
            return [json.loads(record.order_json) for record in existing]

        manager = PurchaseOrderManager()
        saved_orders = []
        order_year = datetime.now(timezone.utc).year
        for order in orders:
            record = ApiOrderRecord(
                owner_id=owner_id,
                plan_id=plan_id,
                order_number=f"pending-{uuid.uuid4()}",
                order_json="{}"
            )
            session.add(record)
            session.flush()
            order_number = f"PO-{order_year}-{record.id:06d}"
            order["order_number"] = order_number
            order["whatsapp_message"] = manager.format_whatsapp_message(
                order_number,
                order["supplier"],
                order["store_name"],
                {
                    "items": order["items"],
                    "total_spend": order["total_spend"],
                }
            )
            record.order_number = order_number
            record.order_json = json.dumps(order, sort_keys=True)
            session.add(record)
            saved_orders.append(order)
        session.commit()
        return saved_orders


def list_orders_for_user(owner_id: int) -> list[dict]:
    with Session(engine) as session:
        records = session.exec(
            select(ApiOrderRecord).where(ApiOrderRecord.owner_id == owner_id).order_by(ApiOrderRecord.id)
        ).all()
        return [json.loads(record.order_json) for record in records]


def get_order_for_user(owner_id: int, order_number: str) -> Optional[dict]:
    with Session(engine) as session:
        record = session.exec(
            select(ApiOrderRecord).where(
                ApiOrderRecord.owner_id == owner_id,
                ApiOrderRecord.order_number == order_number
            )
        ).first()
        return json.loads(record.order_json) if record else None

def register_user(full_name: str, shop_name: str, whatsapp_number: str, password: str) -> User:
    """Creates a new shopkeeper account in the SQLite users table."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters.")
    clean_phone = normalize_phone(whatsapp_number)
    if not re.fullmatch(r"\+\d{8,15}", clean_phone):
        raise ValueError("Enter a valid WhatsApp number with country code.")
    if not full_name.strip():
        raise ValueError("Full name is required.")
    with Session(engine) as session:
        statement = select(User).where(User.whatsapp_number == clean_phone)
        existing = session.exec(statement).first()
        if existing:
            raise ValueError("An account with this WhatsApp number already exists.")

        new_user = User(
            whatsapp_number=clean_phone,
            full_name=full_name,
            shop_name=shop_name or "Sunnyside Spaza",
            password_hash=hash_password(password)
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user

def seed_baseline_if_empty():
    """
    Inserts illustrative staple prices when the local database is empty.
    """
    with Session(engine) as session:
        existing = session.exec(select(LiveMarketPrice)).first()
        if existing:
            return

        baseline_records = [
            # Soft drinks (Substitution for Coca-Cola stockouts / budget limits)
            LiveMarketPrice(
                retailer="Shoprite",
                query="soft drink",
                product_name="Jive Carbonated Soda 440ml",
                price_zar=7.50,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Checkers",
                query="soft drink",
                product_name="Twizza Carbonated Soft Drink 500ml",
                price_zar=7.00,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Makro",
                query="soft drink",
                product_name="Sparletta Creme Soda 440ml",
                price_zar=8.20,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Cooking Oil
            LiveMarketPrice(
                retailer="Shoprite",
                query="cooking oil",
                product_name="Sunfoil Sunflower Cooking Oil 750ml",
                price_zar=24.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Makro",
                query="cooking oil",
                product_name="D'lite Cooking Oil 6x1L",
                price_zar=149.00,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Checkers",
                query="cooking oil",
                product_name="Housebrand Pure Sunflower Oil 1L",
                price_zar=29.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Maize Meal
            LiveMarketPrice(
                retailer="Shoprite",
                query="maize meal",
                product_name="White Star Super Maize Meal 2.5kg",
                price_zar=36.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Makro",
                query="maize meal",
                product_name="Ace Super Maize Meal 5kg",
                price_zar=59.00,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Sugar
            LiveMarketPrice(
                retailer="Shoprite",
                query="sugar",
                product_name="Huletts White Sugar 2.5kg",
                price_zar=54.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Checkers",
                query="sugar",
                product_name="Housebrand White Sugar 2.5kg",
                price_zar=48.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Rice
            LiveMarketPrice(
                retailer="Shoprite",
                query="rice",
                product_name="Tastic Long Grain Parboiled Rice 2kg",
                price_zar=42.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Makro",
                query="rice",
                product_name="Spekko Long Grain Parboiled Rice 2kg",
                price_zar=36.50,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Bakery / Brown Bread
            LiveMarketPrice(
                retailer="Shoprite",
                query="brown bread",
                product_name="Sunbake Sliced Brown Bread 700g",
                price_zar=15.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Pick n Pay",
                query="brown bread",
                product_name="Sasko Premium Brown Bread 700g",
                price_zar=16.49,
                availability="InStock",
                source_type="verified_seed"
            ),
            # Milk
            LiveMarketPrice(
                retailer="Shoprite",
                query="long-life milk",
                product_name="Crystal Valley Long Life Milk 6x1L",
                price_zar=79.99,
                availability="InStock",
                source_type="verified_seed"
            ),
            LiveMarketPrice(
                retailer="Checkers",
                query="long-life milk",
                product_name="First Choice Full Cream UHT Milk 6x1L",
                price_zar=89.99,
                availability="InStock",
                source_type="verified_seed"
            )
        ]

        for rec in baseline_records:
            session.add(rec)
        session.commit()


def mark_fixture_prices() -> None:
    with Session(engine) as session:
        fixture_prices = session.exec(
            select(LiveMarketPrice).where(LiveMarketPrice.source_type == "verified_seed")
        ).all()
        for record in fixture_prices:
            record.source_type = "demo_fixture"
            session.add(record)
        if fixture_prices:
            session.commit()

def upsert_scraped_product(record: dict) -> None:
    """Upserts a scraped ProductRecord into live_market_prices table."""
    with Session(engine) as session:
        statement = select(LiveMarketPrice).where(
            LiveMarketPrice.retailer == record.get("retailer"),
            LiveMarketPrice.product_name == record.get("product_name")
        )
        existing = session.exec(statement).first()

        price = record.get("price_zar")
        try:
            price_value = float(price)
        except (TypeError, ValueError):
            return
        if not math.isfinite(price_value) or price_value <= 0:
            return

        if existing:
            existing.price_zar = price_value
            existing.availability = record.get("availability") or "InStock"
            existing.product_url = record.get("product_url")
            existing.image_url = record.get("image_url")
            existing.sku_or_gtin = record.get("sku_or_gtin")
            existing.scraped_at_utc = record.get("scraped_at_utc") or datetime.now(timezone.utc).isoformat()
            existing.source_type = record.get("source_type") or "live_scraper"
            session.add(existing)
        else:
            new_item = LiveMarketPrice(
                retailer=record.get("retailer", "Unknown"),
                query=record.get("query", "staples"),
                product_name=record.get("product_name"),
                price_zar=price_value,
                currency=record.get("currency", "ZAR"),
                product_url=record.get("product_url"),
                image_url=record.get("image_url"),
                sku_or_gtin=record.get("sku_or_gtin"),
                availability=record.get("availability") or "InStock",
                source_type=record.get("source_type") or "live_scraper",
                scraped_at_utc=record.get("scraped_at_utc") or datetime.now(timezone.utc).isoformat()
            )
            session.add(new_item)
        session.commit()

def query_live_market_substitute(
    product_name: str,
    original_unit_price: float,
    prefer_lower_price: bool = True
) -> Optional[LiveMarketPrice]:
    """
    Queries live_market_prices SQLite table for a brand substitution.
    Deterministic: Orders by lowest price_zar, then alphabetically by product_name.
    """
    clean_target = product_name.lower()

    # Determine query domain
    domain = None
    if any(k in clean_target for k in ["coca-cola", "coke", "sprite", "drink", "soda"]):
        domain = "soft drink"
    elif any(k in clean_target for k in ["oil", "cooking oil", "sunflower"]):
        domain = "cooking oil"
    elif any(k in clean_target for k in ["bread", "loaf"]):
        domain = "brown bread"
    elif any(k in clean_target for k in ["milk", "dairy", "uht"]):
        domain = "long-life milk"
    elif any(k in clean_target for k in ["maize", "meal", "pap"]):
        domain = "maize meal"
    elif any(k in clean_target for k in ["rice"]):
        domain = "rice"
    elif any(k in clean_target for k in ["sugar"]):
        domain = "sugar"

    with Session(engine) as session:
        # 1. Search by domain if recognized
        if domain:
            statement = select(LiveMarketPrice).where(
                LiveMarketPrice.query == domain,
                LiveMarketPrice.availability != "OutOfStock"
            )
            candidates = list(session.exec(statement).all())
            # Exclude the exact original product name
            candidates = [c for c in candidates if clean_target not in c.product_name.lower()]
            if candidates:
                # Deterministic sort: lowest price_zar first, then product_name
                candidates.sort(key=lambda x: (x.price_zar, x.product_name))
                # Check if cheaper
                for cand in candidates:
                    if not prefer_lower_price or cand.price_zar <= original_unit_price:
                        return cand
                # If no strictly cheaper one, return the cheapest available in domain
                return candidates[0]

        # 2. Fallback search across all live market prices
        statement = select(LiveMarketPrice).where(
            LiveMarketPrice.availability != "OutOfStock"
        )
        all_candidates = list(session.exec(statement).all())
        all_candidates.sort(key=lambda x: (x.price_zar, x.product_name))
        for cand in all_candidates:
            if cand.price_zar < original_unit_price:
                return cand

    return None
