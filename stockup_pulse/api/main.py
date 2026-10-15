"""
StockUp Pulse - FastAPI Restocking API

Features:
    - Owner-authenticated plans and purchase orders
    - Strict HTTP 409 approval gate
    - Deterministic budget allocation and fixture-labeled metrics
    - Explicitly disabled provider webhook until signature verification is configured
"""

from contextlib import asynccontextmanager
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
import re
from xml.sax.saxutils import escape

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional

from stockup_pulse.core.config import settings
from stockup_pulse.planning.optimizer import optimizer
from stockup_pulse.orders.manager import order_manager, PlanNotApprovedError
from stockup_pulse.forecast.forecaster import forecaster
from stockup_pulse.catalogue.matcher import matcher
from stockup_pulse.trace.tracker import trace_collector, TraceEvent
from stockup_pulse.adapters.amd_llm import (
    AmdLlmAdapter,
    ProviderNotConfiguredError,
    ProviderRequestError,
    amd_llm,
)
from stockup_pulse.adapters.evolus import EvolusNotConfiguredError, EvolusRequestError
from stockup_pulse.ingest.extract.leaflet_extractor import leaflet_extractor
from stockup_pulse.ingest.importer import (
    ImportValidationError,
    normalize_leaflet_candidates,
    normalize_product_name,
    parse_sales_stock_files,
)

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
    get_orders_for_plan,
    get_latest_pending_plan_for_user,
    get_user_for_whatsapp_number,
    create_file_import_job,
    get_file_import_job,
    update_file_import_job,
)
from stockup_pulse.app.ingest.live_scraper import live_retail_scraper
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

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
            if item.get("source") == "file_import":
                required_fields = ("supplier_price", "unit_price", "our_price", "supplier", "lead_time_days")
                if (
                    item.get("reviewed") is not True
                    or item.get("retail_price_verified") is not True
                    or item.get("currency_verified") is not True
                    or str(item.get("currency") or "").upper() != "ZAR"
                    or any(item.get(name) in (None, "") for name in required_fields)
                ):
                    raise ValueError(
                        f"Item {index + 1} from an uploaded file must be reviewed with supplier, pack/unit price, "
                        "ZAR currency, retail price, and lead time."
                    )
                try:
                    raw_lead_time = item["lead_time_days"]
                    lead_time_number = float(raw_lead_time)
                    unit_price = float(item["unit_price"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Item {index + 1} has invalid reviewed price or lead time.") from exc
                if (
                    isinstance(raw_lead_time, bool)
                    or not math.isfinite(lead_time_number)
                    or not lead_time_number.is_integer()
                    or lead_time_number <= 0
                    or lead_time_number > 365
                    or not math.isfinite(unit_price)
                    or unit_price <= 0
                ):
                    raise ValueError(f"Item {index + 1} has invalid reviewed price or lead time.")
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


class ImportForecastRequest(BaseModel):
    sales_history: List[float] = Field(min_length=1)
    current_stock: float = Field(ge=0, allow_inf_nan=False)
    lead_time_days: int = Field(gt=0, le=365)
    planning_horizon_days: int = Field(gt=0, le=365)

    @field_validator("sales_history")
    @classmethod
    def validate_sales_history(cls, history: List[float]) -> List[float]:
        if any(not math.isfinite(value) or value < 0 for value in history):
            raise ValueError("Sales history must contain only finite nonnegative quantities.")
        return history


def _provider_capabilities() -> Dict[str, Any]:
    return {
        "amd_image_extraction": {
            "enabled": bool(
                settings.AMD_ROCM_ENABLED
                and settings.AMD_ROCM_HOST
                and settings.AMD_ROCM_API_KEY
                and settings.AMD_ROCM_MODEL
            ),
        },
        "evolus_pdf_extraction": {
            "enabled": bool(
                settings.EVOLUS_ENABLED
                and settings.EVOLUS_ENDPOINT
                and settings.EVOLUS_API_KEY
                and settings.EVOLUS_APPLICATION_ID
                and settings.EVOLUS_WORKFLOW_ID
            ),
        },
        "twilio_inbound_webhook": {
            "enabled": bool(
                settings.TWILIO_WEBHOOK_ENABLED
                and settings.TWILIO_ACCOUNT_SID
                and settings.TWILIO_AUTH_TOKEN
                and settings.TWILIO_WEBHOOK_PUBLIC_URL.startswith(("https://", "http://"))
            ),
        },
        "supplier_dispatch": {"enabled": False},
    }


def _parse_lead_times(raw_value: str) -> Dict[str, int]:
    try:
        supplied = json.loads(raw_value or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Supplier lead times must be a JSON object.") from exc
    if not isinstance(supplied, dict):
        raise HTTPException(status_code=422, detail="Supplier lead times must be a JSON object.")
    result: Dict[str, int] = {}
    for supplier, days in supplied.items():
        try:
            numeric_days = float(days)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Supplier lead times must be positive whole days.") from exc
        if (
            isinstance(days, bool)
            or not math.isfinite(numeric_days)
            or not numeric_days.is_integer()
            or not str(supplier).strip()
            or numeric_days <= 0
            or numeric_days > 365
        ):
            raise HTTPException(status_code=422, detail="Supplier lead times must be positive whole days.")
        parsed_days = int(numeric_days)
        result[str(supplier).casefold().strip()] = parsed_days
    return result


def _approved_orders_for_plan(user: User, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    existing = get_orders_for_plan(user.id, plan["plan_id"])
    if existing:
        return existing
    generated = order_manager.create_orders_from_plan(
        plan=plan,
        approved=True,
        store_name=user.shop_name,
    )
    return save_orders_for_plan(user.id, plan["plan_id"], generated)


def _twilio_signature_is_valid(canonical_url: str, params: Dict[str, List[str]], signature: str) -> bool:
    if not settings.TWILIO_AUTH_TOKEN or not signature:
        return False
    payload = canonical_url + "".join(
        key + value
        for key in sorted(params)
        for value in sorted(params[key])
    )
    expected = base64.b64encode(
        hmac.new(
            settings.TWILIO_AUTH_TOKEN.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")
    return hmac.compare_digest(expected, signature)


def _twiml_reply(message: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(message)}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")

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
        "rocm": settings.AMD_ROCM_VERSION,
        "providers": _provider_capabilities(),
    }


@app.get("/api/providers")
def provider_status():
    """Expose provider availability without returning credentials or endpoints."""
    return _provider_capabilities()


async def _build_import_review(
    file_contents: List[tuple[str, str, bytes]],
    tabular_files: List[tuple[str, bytes]],
    leaflet_files: List[tuple[str, str, bytes]],
    imported: Dict[str, Any],
    lead_times: Dict[str, int],
    planning_horizon_days: int,
) -> Dict[str, Any]:
    provider_limit = asyncio.Semaphore(2)

    async def extract_one(filename: str, content: bytes) -> tuple[str, Dict[str, Any]]:
        async with provider_limit:
            try:
                result = await asyncio.to_thread(
                    leaflet_extractor.extract_structured_from_leaflet,
                    content,
                    filename,
                )
                return filename, result
            except (ProviderNotConfiguredError, EvolusNotConfiguredError) as exc:
                raise HTTPException(status_code=503, detail=f"{filename}: provider is not configured.") from exc
            except EvolusRequestError as exc:
                raise HTTPException(status_code=502, detail=f"{filename}: {exc}") from exc
            except ProviderRequestError as exc:
                raise HTTPException(status_code=502, detail=f"{filename}: provider extraction failed.") from exc
            except ValueError as exc:
                raise HTTPException(status_code=502, detail=f"{filename}: extracted data failed validation.") from exc

    tasks = [
        asyncio.create_task(extract_one(filename, content))
        for filename, _, content in leaflet_files
    ]
    try:
        extracted_files = await asyncio.gather(*tasks)
    except Exception:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    available_products = []
    for key in sorted(imported["product_names"]):
        names = imported["product_names"][key]
        available_products.append({
            "normalized_key": key,
            "name": names[0],
            "ambiguous": len(names) > 1,
            "sales_history": list(imported["sales"].get(key, {}).values()),
            "current_stock": imported["stock"].get(key),
        })

    review_candidates: List[Dict[str, Any]] = []
    for file_index, (filename, response_data) in enumerate(extracted_files, start=1):
        source = response_data.get("source", "provider")
        try:
            source_candidates = normalize_leaflet_candidates(
                response_data.get("extracted_items", []),
                source=source,
                source_filename=filename,
            )
        except ImportValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"{filename}: provider output did not meet the leaflet schema.",
            ) from exc
        for candidate_index, candidate in enumerate(source_candidates, start=1):
            key = normalize_product_name(candidate["product"])
            names = imported["product_names"].get(key, [])
            matched = names[0] if len(names) == 1 else ""
            issues = ["Enter a verified store retail price before planning."]
            if not candidate["pack_count"]:
                issues.append("Enter or verify the pack count; unit price was not inferred.")
            if not candidate["supplier"]:
                issues.append("Enter and verify the supplier.")
            if candidate["supplier_price"] is None:
                issues.append("Enter the observed supplier pack price.")
            if candidate["currency"] != "ZAR":
                issues.append("Verify that the supplier price is denominated in ZAR.")
            if len(names) > 1:
                issues.append("Product match is ambiguous; select a store product.")
            elif not names:
                issues.append("No exact product match in sales or current-stock data.")
            if key not in imported["sales"]:
                issues.append("Sales history is missing; add sales or exclude this candidate.")
            if key not in imported["stock"]:
                issues.append("Current stock is missing; map this candidate to a stock item.")
            lead_time = lead_times.get(candidate["supplier"].casefold().strip())
            if lead_time is None:
                issues.append("Enter a verified supplier lead time.")
            matched_key = normalize_product_name(matched) if matched else ""
            history = imported["sales"].get(matched_key)
            stock = imported["stock"].get(matched_key)
            forecast = None
            if matched and len(names) == 1 and history and stock is not None and lead_time:
                forecast = forecaster.forecast_item(
                    sales_history=list(history.values()),
                    lead_time_days=lead_time,
                    planning_horizon_days=planning_horizon_days,
                    current_stock=stock,
                )
            review_candidates.append({
                **candidate,
                "id": f"{file_index}-{candidate_index}",
                "currency_verified": False,
                "matched_product": matched,
                "lead_time_days": lead_time,
                "current_stock": stock,
                "sales_history": list(history.values()) if history else None,
                "forecast": forecast,
                "recommended_qty": forecast["recommended_qty"] if forecast else None,
                "at_risk": forecast["at_risk_before_delivery"] if forecast else False,
                "issues": issues,
                "status": "Needs review",
            })

    return {
        "status": "review_required",
        "sales_interval": imported["sales_interval"],
        "candidates": review_candidates,
        "available_products": available_products,
        "source_files": [
            {"filename": name, "kind": "tabular" if suffix in {"csv", "xlsx"} else suffix}
            for name, suffix, _ in file_contents
        ],
        "providers": _provider_capabilities(),
    }


async def _run_import_review_job(
    job_id: str,
    file_contents: List[tuple[str, str, bytes]],
    tabular_files: List[tuple[str, bytes]],
    leaflet_files: List[tuple[str, str, bytes]],
    imported: Dict[str, Any],
    lead_times: Dict[str, int],
    planning_horizon_days: int,
) -> None:
    try:
        result = await _build_import_review(
            file_contents,
            tabular_files,
            leaflet_files,
            imported,
            lead_times,
            planning_horizon_days,
        )
        update_file_import_job(job_id, status="completed", result=result)
    except HTTPException as exc:
        update_file_import_job(job_id, status="failed", error=str(exc.detail))
    except Exception:
        logger.exception("File import review job %s failed unexpectedly.", job_id)
        update_file_import_job(
            job_id,
            status="failed",
            error="File extraction failed unexpectedly. Please retry the upload.",
        )


@app.post("/api/plan/from-files", status_code=202)
async def create_import_review(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    supplier_lead_times_json: str = Form(default="{}"),
    planning_horizon_days: int = Form(default=14, ge=1, le=365),
    user: User = Depends(require_user),
):
    """Queue file parsing and extraction for asynchronous owner review."""
    if not files or len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload between 1 and {settings.MAX_UPLOAD_FILES} files.",
        )

    lead_times = {
        str(supplier).casefold().strip(): days
        for supplier, days in settings.SUPPLIER_LEAD_TIMES.items()
    }
    lead_times.update(_parse_lead_times(supplier_lead_times_json))
    file_contents: List[tuple[str, str, bytes]] = []
    total_bytes = 0
    tabular_files: List[tuple[str, bytes]] = []
    leaflet_files: List[tuple[str, str, bytes]] = []

    for index, upload in enumerate(files, start=1):
        original_name = upload.filename or f"upload-{index}"
        filename = re.split(r"[/\\]", original_name)[-1][:255]
        suffix = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
        if suffix not in {"csv", "xlsx", "pdf", "jpg", "jpeg", "png"}:
            raise HTTPException(status_code=415, detail=f"{filename}: unsupported file type.")
        content = await upload.read(settings.MAX_UPLOAD_FILE_BYTES + 1)
        if len(content) > settings.MAX_UPLOAD_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"{filename}: file exceeds the 10 MB limit.")
        total_bytes += len(content)
        if total_bytes > settings.MAX_UPLOAD_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="Combined upload exceeds the 25 MB limit.")
        file_contents.append((filename, suffix, content))
        if suffix in {"csv", "xlsx"}:
            tabular_files.append((filename, content))
        else:
            leaflet_files.append((filename, suffix, content))

    if not tabular_files or not leaflet_files:
        raise HTTPException(
            status_code=422,
            detail="Upload sales data, current stock data, and at least one PDF or image leaflet.",
        )

    try:
        imported = parse_sales_stock_files(tabular_files)
    except ImportValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if any(suffix in {"jpg", "jpeg", "png"} for _, suffix, _ in leaflet_files):
        if not _provider_capabilities()["amd_image_extraction"]["enabled"]:
            raise HTTPException(status_code=503, detail="AMD image extraction is disabled or not configured.")
    if any(suffix == "pdf" for _, suffix, _ in leaflet_files):
        if not _provider_capabilities()["evolus_pdf_extraction"]["enabled"]:
            raise HTTPException(status_code=503, detail="Evolus PDF extraction is disabled or not configured.")

    if user.id is None:
        raise HTTPException(status_code=401, detail="Authenticated user record is unavailable.")
    job_id = create_file_import_job(user.id)
    background_tasks.add_task(
        _run_import_review_job,
        job_id,
        file_contents,
        tabular_files,
        leaflet_files,
        imported,
        lead_times,
        planning_horizon_days,
    )
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/plan/from-files/{job_id}")
def get_import_review_job(job_id: str, user: User = Depends(require_user)):
    """Return the authenticated owner's file-import job state."""
    job = get_file_import_job(user.id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="File import job not found.")
    if job["status"] == "completed":
        return {"job_id": job_id, "status": job["status"], "result": job["result"]}
    if job["status"] == "failed":
        return {"job_id": job_id, "status": job["status"], "error": job["error"]}
    return {"job_id": job_id, "status": job["status"]}


@app.post("/api/plan/from-files/forecast")
def forecast_import_candidate(req: ImportForecastRequest, user: User = Depends(require_user)):
    """Recalculate a reviewed candidate's recommendation after mapping/lead-time edits."""
    del user
    return forecaster.forecast_item(
        sales_history=req.sales_history,
        lead_time_days=req.lead_time_days,
        planning_horizon_days=req.planning_horizon_days,
        current_stock=req.current_stock,
    )


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
        orders = get_orders_for_plan(user.id, plan["plan_id"])
        if not orders:
            generated = order_manager.create_orders_from_plan(
                plan=plan,
                approved=True,
                store_name=req.store_name
            )
            orders = save_orders_for_plan(user.id, plan["plan_id"], generated)
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
        return {
            "channel": "simulator",
            "delivery_status": "not_sent",
            "reply": "This authenticated local simulator accepts APPROVE, CONFIRM, or YES for a pending plan.",
        }

    plan = get_latest_pending_plan_for_user(user.id)
    if plan:
        plan = set_plan_approval(user.id, True, plan["plan_id"])
    else:
        plan = get_plan_for_user(user.id)
    if not plan:
        return {
            "channel": "simulator",
            "delivery_status": "not_sent",
            "reply": "No pending restocking plan was found for this account.",
        }

    if not plan.get("approved", False):
        return {
            "channel": "simulator",
            "delivery_status": "not_sent",
            "reply": "No pending restocking plan was found for this account.",
        }
    orders = _approved_orders_for_plan(user, plan)
    total_spend = sum(order["total_spend"] for order in orders)
    order_numbers = ", ".join(order["order_number"] for order in orders)
    return {
        "channel": "simulator",
        "delivery_status": "not_sent",
        "reply": f"Approval confirmed. Purchase orders: {order_numbers}. Total spend: R {total_spend:,.2f}.",
        "orders": orders,
    }


@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    capabilities = _provider_capabilities()["twilio_inbound_webhook"]["enabled"]
    if not capabilities:
        raise HTTPException(status_code=503, detail="Twilio inbound webhook is disabled or not configured.")
    canonical_url = settings.TWILIO_WEBHOOK_PUBLIC_URL
    if not canonical_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=503, detail="Twilio canonical webhook URL is not configured.")
    signature = request.headers.get("x-twilio-signature", "")
    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Twilio form request.") from exc
    params: Dict[str, List[str]] = {}
    for key, value in form.multi_items():
        if isinstance(value, str):
            params.setdefault(key, []).append(value)
    if not _twilio_signature_is_valid(canonical_url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio request signature.")

    sender = str(form.get("From") or "")
    if not sender.startswith("whatsapp:"):
        raise HTTPException(status_code=403, detail="Unrecognized Twilio WhatsApp sender.")
    phone = sender.removeprefix("whatsapp:")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise HTTPException(status_code=403, detail="Unrecognized Twilio WhatsApp sender.")
    user = get_user_for_whatsapp_number(phone)
    if not user:
        raise HTTPException(status_code=403, detail="Sender is not registered.")

    body = str(form.get("Body") or "").strip()
    if body.upper() not in {"APPROVE", "CONFIRM", "YES"}:
        return _twiml_reply("This channel accepts APPROVE, CONFIRM, or YES for a pending restocking plan.")

    plan = get_latest_pending_plan_for_user(user.id)
    if plan is None:
        latest = get_plan_for_user(user.id)
        if latest and latest.get("approved"):
            orders = get_orders_for_plan(user.id, latest["plan_id"])
            if orders:
                return _twiml_reply(
                    f"Plan already approved. Existing purchase orders: "
                    f"{', '.join(order['order_number'] for order in orders)}."
                )
        return _twiml_reply("No pending restocking plan was found for this account.")

    approved_plan = set_plan_approval(user.id, True, plan["plan_id"])
    if approved_plan is None:
        return _twiml_reply("No pending restocking plan was found for this account.")
    orders = _approved_orders_for_plan(user, approved_plan)
    order_numbers = ", ".join(order["order_number"] for order in orders) or "none"
    return _twiml_reply(f"Approval confirmed. Purchase orders: {order_numbers}.")

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
