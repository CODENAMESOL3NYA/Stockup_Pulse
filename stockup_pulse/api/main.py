"""
StockUp Pulse - FastAPI Restocking API

Features:
    - Owner-authenticated plans and purchase orders
    - Strict HTTP 409 approval gate
    - Deterministic budget allocation and fixture-labeled metrics
    - Explicitly disabled provider webhook until signature verification is configured
"""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
import math

from stockup_pulse.core.config import settings
from stockup_pulse.planning.optimizer import optimizer
from stockup_pulse.orders.manager import order_manager, PlanNotApprovedError
from stockup_pulse.forecast.forecaster import forecaster
from stockup_pulse.catalogue.matcher import matcher
from stockup_pulse.trace.tracker import trace_collector, TraceEvent
from stockup_pulse.adapters.amd_llm import amd_llm

from stockup_pulse.core.db import (
    init_db,
    LiveMarketPrice,
    engine,
    authenticate_user,
    register_user,
    User,
    create_auth_session,
    get_user_for_token,
    revoke_auth_session,
    save_plan_for_user,
    get_plan_for_user,
    set_plan_approval,
    save_orders_for_plan,
    list_orders_for_user,
    get_order_for_user,
)
from stockup_pulse.app.ingest.live_scraper import live_retail_scraper
from sqlmodel import Session, select

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="StockUp Pulse API",
    description="AI Restocking Agent for South African Spaza Shops",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_auth = HTTPBearer(auto_error=False)


def require_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_auth)) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    user = get_user_for_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session", headers={"WWW-Authenticate": "Bearer"})
    return user

class PlanRequest(BaseModel):
    budget: float = Field(default=3000.0, gt=0, allow_inf_nan=False)
    planning_horizon_days: int = Field(default=14, gt=0, le=365)
    items: List[Dict[str, Any]]
    allow_substitutions: bool = True

    @field_validator("items")
    @classmethod
    def validate_items(cls, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            raise ValueError("At least one candidate item is required.")
        for index, item in enumerate(items):
            product = str(item.get("product", "")).strip()
            quantity = item.get("recommended_qty", item.get("qty", 10))
            price = item.get("unit_price", item.get("price", item.get("supplier_price", 10.0)))
            try:
                quantity_value = float(quantity)
                price_value = float(price)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Item {index + 1} must have a numeric quantity and unit price.") from exc
            if not product:
                raise ValueError(f"Item {index + 1} must have a product name.")
            if not math.isfinite(quantity_value) or quantity_value <= 0 or not quantity_value.is_integer():
                raise ValueError(f"Item {index + 1} quantity must be a positive integer.")
            if not math.isfinite(price_value) or price_value <= 0:
                raise ValueError(f"Item {index + 1} unit price must be a finite positive amount.")
            for field_name in ("supplier_price", "our_price"):
                if field_name in item:
                    try:
                        optional_price = float(item[field_name])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"Item {index + 1} {field_name} must be numeric.") from exc
                    if not math.isfinite(optional_price) or optional_price <= 0:
                        raise ValueError(f"Item {index + 1} {field_name} must be a finite positive amount.")
        return items

class ApprovalRequest(BaseModel):
    approved: bool = True
    owner_notes: Optional[str] = None
    plan_id: Optional[str] = None

class CreateOrderRequest(BaseModel):
    approved: bool
    store_name: str = Field(default="Sunnyside Spaza", min_length=1, max_length=120)
    plan_id: Optional[str] = None

class LoginRequest(BaseModel):
    whatsapp_number: str = Field(min_length=8, max_length=32)
    password: str = Field(min_length=1, max_length=128)

class RegisterRequest(BaseModel):
    full_name: str
    shop_name: str = "Sunnyside Spaza"
    whatsapp_number: str
    password: str = Field(min_length=8, max_length=128)


class WhatsAppSimulationRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

@app.post("/api/auth/login")
def api_login(req: LoginRequest):
    user = authenticate_user(req.whatsapp_number, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid WhatsApp number or password")
    return {
        "status": "success",
        "access_token": create_auth_session(user.id),
        "token_type": "bearer",
        "user": {
            "phone": user.whatsapp_number,
            "full_name": user.full_name,
            "shop_name": user.shop_name
        }
    }

@app.post("/api/auth/register")
def api_register(req: RegisterRequest):
    try:
        user = register_user(
            full_name=req.full_name,
            shop_name=req.shop_name,
            whatsapp_number=req.whatsapp_number,
            password=req.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "status": "success",
        "access_token": create_auth_session(user.id),
        "token_type": "bearer",
        "user": {
            "phone": user.whatsapp_number,
            "full_name": user.full_name,
            "shop_name": user.shop_name
        }
    }


@app.get("/api/auth/me")
def api_current_user(user: User = Depends(require_user)):
    return {"user": {"phone": user.whatsapp_number, "full_name": user.full_name, "shop_name": user.shop_name}}


@app.post("/api/auth/logout")
def api_logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_auth),
    user: User = Depends(require_user)
):
    del user
    revoke_auth_session(credentials.credentials)
    return {"status": "signed_out"}

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": settings.APP_NAME,
        "device": settings.AMD_ROCM_DEVICE,
        "rocm": settings.AMD_ROCM_VERSION
    }

@app.post("/api/plan")
def create_restocking_plan(req: PlanRequest, user: User = Depends(require_user)):
    """
    Generate deterministic restocking plan.
    Strictly sets approved=False until user explicitly approves.
    """
    plan = optimizer.optimize_plan(
        candidate_items=req.items,
        budget=req.budget,
        planning_horizon_days=req.planning_horizon_days,
        allow_substitutions=req.allow_substitutions
    )
    plan["plain_language_explanation"] = amd_llm.write_plain_language_explanation(plan)
    return save_plan_for_user(user.id, plan)

@app.post("/api/plan/approve")
def approve_restocking_plan(req: ApprovalRequest, user: User = Depends(require_user)):
    """Explicit owner approval gate."""
    plan = set_plan_approval(user.id, req.approved, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found to approve.")
    
    trace_collector.record(TraceEvent(
        event_type="approval",
        status="success",
        details={"approved": req.approved, "notes": req.owner_notes, "plan_id": plan["plan_id"], "owner_id": user.id}
    ))
    return {
        "message": "Restocking plan approved successfully.",
        "plan_approved": plan["approved"],
        "plan_id": plan["plan_id"]
    }

@app.post("/api/orders")
def generate_purchase_orders(req: CreateOrderRequest, user: User = Depends(require_user)):
    """
    Generate Purchase Orders.
    NON-NEGOTIABLE PRINCIPLE: Enforce HTTP 409 if not approved!
    """
    plan = get_plan_for_user(user.id, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No restocking plan found. Generate a plan first.")

    # Strict approval gate check in API
    if not req.approved or not plan.get("approved", False):
        raise HTTPException(
            status_code=409,
            detail="Conflict (409): No purchase order exists until the owner explicitly approves the restocking plan. Approval gate enforced."
        )

    try:
        orders = order_manager.create_orders_from_plan(
            plan=plan,
            approved=True,
            store_name=req.store_name
        )
        orders = save_orders_for_plan(user.id, plan["plan_id"], orders)
        return {
            "status": "success",
            "message": "Purchase orders created successfully",
            "orders": orders
        }
    except PlanNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.get("/api/orders")
def get_all_orders(user: User = Depends(require_user)):
    return list_orders_for_user(user.id)

@app.get("/api/orders/{order_id}")
def get_order_by_id(order_id: str, user: User = Depends(require_user)):
    order = get_order_for_user(user.id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order

@app.post("/api/whatsapp/simulate")
def simulate_whatsapp_message(req: WhatsAppSimulationRequest, user: User = Depends(require_user)):
    text_content = req.body.strip()
    if text_content.upper() not in ("APPROVE", "CONFIRM", "YES"):
        return {"reply": "Leaflet ingestion is not configured. Generate a plan in the dashboard before approving it here."}

    plan = set_plan_approval(user.id, True)
    if not plan:
        return {"reply": "No pending restocking plan was found for this account."}

    orders = order_manager.create_orders_from_plan(plan, approved=True, store_name=user.shop_name)
    orders = save_orders_for_plan(user.id, plan["plan_id"], orders)
    total_spend = sum(order["total_spend"] for order in orders)
    order_numbers = ", ".join(order["order_number"] for order in orders)
    return {
        "reply": f"Approval confirmed. Purchase orders: {order_numbers}. Total spend: R {total_spend:,.2f}.",
        "orders": orders,
    }


@app.post("/api/whatsapp/webhook")
def whatsapp_webhook_not_configured():
    raise HTTPException(
        status_code=501,
        detail="Provider webhook is disabled until request-signature verification is configured. Use /api/whatsapp/simulate in the authenticated dashboard."
    )

@app.get("/api/trace")
def get_trace_events(user: User = Depends(require_user)):
    """Retrieve full audit trace log for AMD ROCm MI300X and Evolus building blocks."""
    del user
    return {
        "summary": trace_collector.get_summary(),
        "events": [e.dict() for e in trace_collector.get_events()]
    }

@app.get("/api/metrics")
def get_wape_metrics(user: User = Depends(require_user)):
    """Return explicitly labeled illustrative fixture metrics."""
    del user
    return forecaster.evaluate_wape()

@app.get("/api/market-prices")
def get_live_market_prices(limit: int = Query(default=50, ge=1, le=500), user: User = Depends(require_user)):
    """Retrieve live scraped market prices from the SQLite database."""
    del user
    with Session(engine) as session:
        statement = select(LiveMarketPrice).limit(limit)
        results = session.exec(statement).all()
        return [r.dict() for r in results]

@app.post("/api/scraper/sync")
async def trigger_live_scraper_sync(user: User = Depends(require_user)):
    """Trigger an on-demand async scrape of SA retail staple queries."""
    del user
    records = await live_retail_scraper.scrape_staples_and_sync()
    return {
        "status": "completed",
        "newly_scraped_count": len(records),
        "message": "Live retail scraper sync completed. Database updated."
    }
