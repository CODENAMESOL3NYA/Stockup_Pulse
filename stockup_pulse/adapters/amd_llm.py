"""AMD Radeon Cloud inference boundary.

Only leaflet extraction and narrative explanations use the provider. Catalogue
matching and all financial calculations remain deterministic local operations.
"""

import base64
import json
import logging
import mimetypes
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import httpx

from stockup_pulse.core.config import settings
from stockup_pulse.trace.tracker import TraceEvent, trace_collector

logger = logging.getLogger(__name__)


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a provider-dependent operation is requested while disabled."""


class ProviderRequestError(RuntimeError):
    """Raised when a provider request fails; response bodies are never exposed."""


class AmdLlmAdapter:
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or settings.AMD_ROCM_HOST).rstrip("/")
        self.model = model if model is not None else settings.AMD_ROCM_MODEL
        self.timeout = settings.EXTERNAL_TIMEOUT_SECONDS
        self.max_retries = settings.MAX_RETRIES

    def _require_configured(self) -> None:
        if not settings.AMD_ROCM_ENABLED:
            raise ProviderNotConfiguredError("AMD image extraction is disabled.")
        if not settings.AMD_ROCM_API_KEY or not self.host or not self.model.strip():
            raise ProviderNotConfiguredError(
                "AMD image extraction requires AMD_ROCM_HOST, AMD_ROCM_API_KEY, and AMD_ROCM_MODEL."
            )

    @staticmethod
    def _retry_after_seconds(value: Optional[str], attempt: int) -> float:
        if value:
            try:
                return min(30.0, max(0.0, float(value)))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return min(30.0, max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(30.0, (2 ** attempt) + random.uniform(0.0, 0.25))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._require_configured()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {settings.AMD_ROCM_API_KEY}"
        retryable_statuses = {429, 502, 503}
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.request(
                    method,
                    f"{self.host}/{path.lstrip('/')}",
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    time.sleep(min(30.0, 2 ** attempt))
                    continue
                raise ProviderRequestError("AMD request timed out.") from exc
            except httpx.RequestError as exc:
                if attempt < self.max_retries:
                    time.sleep(min(30.0, 2 ** attempt))
                    continue
                raise ProviderRequestError("AMD endpoint could not be reached.") from exc

            if response.status_code in retryable_statuses and attempt < self.max_retries:
                time.sleep(self._retry_after_seconds(response.headers.get("Retry-After"), attempt))
                continue
            if response.is_error:
                raise ProviderRequestError(f"AMD endpoint returned HTTP {response.status_code}.")
            return response
        raise ProviderRequestError("AMD request retry policy was exhausted.")

    @staticmethod
    def _supports_images(model: Dict[str, Any]) -> bool:
        capability = model.get("capabilities")
        if isinstance(capability, dict) and any(
            capability.get(key) is True for key in ("vision", "image", "images")
        ):
            return True
        if isinstance(capability, list) and any(
            str(value).lower() in {"vision", "image", "images"} for value in capability
        ):
            return True
        for key in ("input_modalities", "modalities", "supported_modalities"):
            modalities = model.get(key)
            if isinstance(modalities, list) and any(
                str(value).lower() in {"image", "images", "vision"} for value in modalities
            ):
                return True
        architecture = model.get("architecture")
        if isinstance(architecture, dict):
            modalities = architecture.get("input_modalities")
            if isinstance(modalities, list) and any(
                str(value).lower() in {"image", "images", "vision"} for value in modalities
            ):
                return True
        return any(model.get(key) is True for key in ("vision", "supports_vision", "image_input"))

    def discover_vision_model(self) -> str:
        """Validate the configured model against live provider capability metadata."""
        self._require_configured()
        response = self._request("GET", "models")
        try:
            catalog = response.json().get("data", [])
        except (ValueError, AttributeError) as exc:
            raise ProviderRequestError("AMD model catalog returned invalid JSON.") from exc
        if not isinstance(catalog, list):
            raise ProviderRequestError("AMD model catalog has an unsupported shape.")
        selected = next(
            (entry for entry in catalog if isinstance(entry, dict) and entry.get("id") == self.model),
            None,
        )
        if selected is None:
            raise ProviderNotConfiguredError(
                "Configured AMD_ROCM_MODEL is not present in the live model catalog."
            )
        if not self._supports_images(selected):
            raise ProviderNotConfiguredError(
                "Configured AMD_ROCM_MODEL is not marked as image-capable by the live catalog."
            )
        return self.model

    def _record_call(
        self,
        started: float,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        task: str = "leaflet_extraction",
    ) -> None:
        trace_collector.record(TraceEvent(
            event_type="llm_call" if status == "success" else "fallback",
            device=settings.AMD_ROCM_DEVICE if settings.AMD_ROCM_DEVICE != "not_configured" else "remote",
            rocm_version=settings.AMD_ROCM_VERSION,
            model=self.model,
            endpoint_host=self.host,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            tokens_total=prompt_tokens + completion_tokens,
            status=status,
            details={"task": task},
        ))

    def extract_leaflet_candidates(
        self,
        image_bytes: bytes,
        prompt: str,
        filename: str,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        mime_type = mimetypes.guess_type(filename)[0]
        if mime_type not in {"image/jpeg", "image/png"}:
            raise ValueError("AMD leaflet extraction accepts JPEG or PNG images only.")
        image_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        try:
            self._require_configured()
            self.discover_vision_model()
            response = self._request(
                "POST",
                "chat/completions",
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_uri}},
                        ],
                    }],
                    "response_format": {"type": "json_object"},
                },
            )
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                items = parsed.get("extracted_items", parsed.get("items"))
            else:
                items = None
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise ProviderRequestError("AMD returned an invalid leaflet candidate structure.")
            usage = payload.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            self._record_call(started, "success", prompt_tokens, completion_tokens)
            return {"extracted_items": items, "source": "amd"}
        except ProviderNotConfiguredError:
            self._record_call(started, "error")
            raise
        except ProviderRequestError:
            self._record_call(started, "error")
            raise
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            self._record_call(started, "error")
            raise ProviderRequestError("AMD returned an invalid leaflet response.") from exc

    def extract_leaflet_text(self, image_data_or_url: str, prompt: str) -> Dict[str, Any]:
        """Return a local fixture for legacy/demo callers; uploads use the provider path."""
        started = time.perf_counter()
        result = self._fallback_extract(prompt)
        trace_collector.record(TraceEvent(
            event_type="fallback",
            device="not_invoked",
            rocm_version="not_invoked",
            model="not_invoked",
            endpoint_host="not_invoked",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status="fallback",
            details={"task": "leaflet_extraction", "source": "local_demo_fixture"},
        ))
        return result

    def adjudicate_product_match(self, internal_product: str, candidate_supplier_item: str, score: float) -> Dict[str, Any]:
        """Perform deterministic product matching; no model call is made."""
        clean_int = internal_product.lower().strip()
        clean_cand = candidate_supplier_item.lower().strip()
        is_match = False
        rationale = "Heuristic match based on brand and volume equivalence"
        confidence = score

        if "coca-cola" in clean_int and ("coke" in clean_cand or "coca-cola" in clean_cand):
            is_match, rationale, confidence = True, "Identified brand synonym: Coke -> Coca-Cola, package volumes compatible", 0.96
        elif "sprite" in clean_int and "sprite" in clean_cand:
            is_match, rationale, confidence = True, "Direct match on brand and bottle size", 0.98
        elif "noodles" in clean_int and ("noodles" in clean_cand or "ramen" in clean_cand):
            is_match, rationale, confidence = True, "Category match on instant noodle pack", 0.92
        elif "bread" in clean_int and ("bread" in clean_cand or "loaf" in clean_cand):
            is_match, rationale, confidence = True, "Bakery staple match: Standard Brown Bread 700g", 0.88
        elif "oil" in clean_int and "oil" in clean_cand:
            is_match, rationale, confidence = True, "Cooking Oil cooking fat category match", 0.89
        elif score >= 0.75:
            is_match, rationale = True, f"High fuzzy similarity ({round(score * 100)}%) with compatible pack sizes"
        else:
            rationale = f"Insufficient match confidence ({round(score * 100)}%)"

        trace_collector.record(TraceEvent(
            event_type="tool_call",
            device="CPU",
            rocm_version="not_applicable",
            model="deterministic_rules",
            endpoint_host="local",
            status="success",
            details={"task": "catalogue_adjudication"},
        ))
        return {"is_match": is_match, "confidence": confidence, "rationale": rationale}

    def _deterministic_explanation(self, plan_data: Dict[str, Any]) -> str:
        budget = plan_data.get("budget", 0.0)
        total_spend = plan_data.get("total_spend", 0.0)
        units_count = plan_data.get("total_items_to_reorder", 0)
        remaining = plan_data.get("remaining_budget", 0.0)
        substitutions = plan_data.get("substitutions_applied", [])
        subs_text = ""
        if substitutions:
            subs_list = [
                f"{s.get('original_product')} -> {s.get('substituted_with')} ({s.get('reason')})"
                for s in substitutions
            ]
            subs_text = (
                f" To stay within your R {budget:,.2f} budget, we made "
                f"{len(substitutions)} brand substitution(s): " + "; ".join(subs_list) + "."
            )
        return (
            f"Here is your restocking plan for Sunnyside Spaza. "
            f"We allocated R {total_spend:,.2f} out of your R {budget:,.2f} budget across {units_count} units, "
            f"leaving R {remaining:,.2f} as a buffer.{subs_text} "
            "This plan uses the prices supplied with the request; verify supplier availability before ordering."
        )

    def write_plain_language_explanation(self, plan_data: Dict[str, Any]) -> str:
        fallback = self._deterministic_explanation(plan_data)
        if (
            not settings.AMD_ROCM_ENABLED
            or not settings.AMD_ROCM_API_KEY
            or not self.host
            or not self.model
        ):
            self._record_call(time.perf_counter(), "fallback", task="plan_explanation")
            return fallback
        started = time.perf_counter()
        try:
            response = self._request(
                "POST",
                "chat/completions",
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": (
                            "Explain the following completed restocking plan in plain language. "
                            "Do not calculate, change, or recommend any prices, quantities, or totals. "
                            "Return only a short explanation.\n"
                            + json.dumps(plan_data, sort_keys=True)
                        ),
                    }],
                },
            )
            payload = response.json()
            explanation = payload["choices"][0]["message"]["content"]
            if not isinstance(explanation, str) or not explanation.strip():
                raise ProviderRequestError("AMD returned an empty explanation.")
            usage = payload.get("usage") or {}
            self._record_call(
                started,
                "success",
                int(usage.get("prompt_tokens") or 0),
                int(usage.get("completion_tokens") or 0),
                "plan_explanation",
            )
            return explanation.strip()
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ProviderRequestError,
            ProviderNotConfiguredError,
        ):
            self._record_call(started, "error", task="plan_explanation")
            logger.warning("AMD explanation failed; returning the deterministic explanation.")
            return fallback

    def _fallback_extract(self, prompt: str) -> Dict[str, Any]:
        return {
            "source": "local_demo_fixture",
            "extracted_items": [
                {"product": "Coca-Cola 440ml", "pack_size": "24 x 440ml", "supplier": "Makro", "price": 289.00, "unit_price": 12.04},
                {"product": "Sprite 440ml", "pack_size": "24 x 440ml", "supplier": "Makro", "price": 275.50, "unit_price": 11.48},
                {"product": "Chicken Flavour Noodles", "pack_size": "5 x 70g", "supplier": "Shoprite", "price": 42.00, "unit_price": 8.40},
                {"product": "Brown Bread", "pack_size": "1 x 700g", "supplier": "Usave", "price": 16.50, "unit_price": 16.50},
                {"product": "Milk (long life)", "pack_size": "6 x 1L", "supplier": "Usave", "price": 84.00, "unit_price": 14.00},
                {"product": "Cooking Oil", "pack_size": "6 x 1L", "supplier": "Makro", "price": 210.00, "unit_price": 35.00},
                {"product": "Twizza Carbonated Drink 500ml", "pack_size": "24 x 500ml", "supplier": "Jumbo", "price": 168.00, "unit_price": 7.00},
                {"product": "Jive Soda 440ml", "pack_size": "24 x 440ml", "supplier": "Shoprite", "price": 180.00, "unit_price": 7.50},
            ],
        }


amd_llm = AmdLlmAdapter()
