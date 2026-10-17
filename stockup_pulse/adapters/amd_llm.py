"""AMD Radeon Cloud inference boundary.

Only leaflet extraction and narrative explanations use the provider. Catalogue
matching and all financial calculations remain deterministic local operations.
"""

import base64
import io
import json
import logging
import mimetypes
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image

from stockup_pulse.core.config import settings
from stockup_pulse.trace.tracker import TraceEvent, trace_collector

logger = logging.getLogger(__name__)


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a provider-dependent operation is requested while disabled."""


class ProviderRequestError(RuntimeError):
    """Raised when a provider request fails; response bodies are never exposed."""


_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b", re.IGNORECASE)
_VARIANT_WORDS = {"zero", "diet", "light", "lite", "white", "brown", "whole", "wholewheat"}
_SUGAR_VARIANTS = {"zero", "diet", "light", "lite"}


def _first_size(text: str) -> Optional[Tuple[float, str]]:
    """Return the first pack size in the text, normalised to (amount, 'ml' | 'g')."""
    match = _SIZE_RE.search(text)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "l":
        return amount * 1000.0, "ml"
    if unit == "kg":
        return amount * 1000.0, "g"
    return amount, unit


def _variants(text: str) -> set:
    return set(re.findall(r"\b[a-z]+\b", text)) & _VARIANT_WORDS


def _has_word(word: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _prepare_image_for_vlm(image_bytes: bytes, max_dim: int = 1536) -> Tuple[bytes, str]:
    """Resize high-res scans to fit within max_dim to avoid ROCm token explosion & gateway timeouts."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_format = img.format if img.format in {"JPEG", "PNG"} else "JPEG"
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            out_buf = io.BytesIO()
            img.save(out_buf, format=img_format, quality=85, optimize=True)
            mime = "image/jpeg" if img_format == "JPEG" else "image/png"
            return out_buf.getvalue(), mime
    except Exception:
        # Fallback to original bytes if PIL fails
        return image_bytes, "image/jpeg"


class AmdLlmAdapter:
    _CAPABILITY_KEYS = (
        "capabilities",
        "input_modalities",
        "modalities",
        "supported_modalities",
        "architecture",
        "vision",
        "supports_vision",
        "image_input",
    )

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or settings.AMD_ROCM_HOST or "").rstrip("/")
        self.model = (model if model is not None else settings.AMD_ROCM_MODEL) or ""
        self.timeout = settings.EXTERNAL_TIMEOUT_SECONDS
        self.max_retries = settings.MAX_RETRIES
        self._vision_validated = False

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
                return min(65.0, max(0.0, float(value)))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return min(65.0, max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(30.0, (2 ** attempt) + random.uniform(0.0, 0.25))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        self._require_configured()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {settings.AMD_ROCM_API_KEY}"
        
        # Include 504 Gateway Timeout in retryable statuses
        retryable_statuses = {429, 502, 503, 504}
        
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

            # Retry if status code is in retryable_statuses or is a 500 wrapping an upstream 504
            is_upstream_timeout_500 = (
                response.status_code == 500 and "504" in response.text
            )
            if (response.status_code in retryable_statuses or is_upstream_timeout_500) and attempt < self.max_retries:
                time.sleep(self._retry_after_seconds(response.headers.get("Retry-After"), attempt))
                continue

            if response.is_error:
                logger.warning(
                    "AMD endpoint returned HTTP %s (%s).",
                    response.status_code,
                    self._error_summary(response),
                )
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
        self._require_configured()
        if self._vision_validated:
            return self.model
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
        advertises = any(key in selected for key in self._CAPABILITY_KEYS)
        if advertises and not self._supports_images(selected):
            logger.warning(
                "Model %s does not advertise image input in the live catalog; attempting anyway.",
                self.model,
            )
        self._vision_validated = True
        return self.model

    @staticmethod
    def _parse_json_content(content: Any) -> Any:
        """Parse model output as JSON, tolerating thinking tags, text preamble, and code fences."""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise ValueError("Model content was not text.")
        text = content.strip()
        # Remove <think>...</think> tags if present
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        
        # Extract content from markdown code fences if wrapped
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        else:
            first_brace = text.find("{")
            first_bracket = text.find("[")
            start = -1
            if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
                start = first_brace
                end = text.rfind("}")
            elif first_bracket != -1:
                start = first_bracket
                end = text.rfind("]")
            if start != -1 and end != -1:
                text = text[start:end + 1]

        return json.loads(text.strip())

    @staticmethod
    def _chat_options(max_tokens: int) -> Dict[str, Any]:
        options: Dict[str, Any] = {"max_tokens": max_tokens}
        effort = getattr(settings, "AMD_ROCM_REASONING_EFFORT", "low")
        if effort:
            options["reasoning_effort"] = effort
        return options

    @staticmethod
    def _error_summary(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return "unparseable error body"
        error = body.get("detail", body) if isinstance(body, dict) else None
        if isinstance(error, dict):
            error = error.get("error", error)
        if isinstance(error, dict):
            return f"{error.get('code') or error.get('type') or 'unknown'}: {str(error.get('message') or '')[:200]}"
        return "unrecognised error body"

    def _record_call(
        self,
        started: float,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        task: str = "leaflet_extraction",
    ) -> None:
        if status == "success":
            event_type = "llm_call"
        elif status == "error":
            event_type = "error"
        else:
            event_type = "fallback"
        trace_collector.record(TraceEvent(
            event_type=event_type,
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
        
        # Prepare & resize image to prevent ROCm GPU memory overload and gateway timeouts
        processed_bytes, mime_type = _prepare_image_for_vlm(image_bytes, max_dim=1536)
        image_uri = f"data:{mime_type};base64,{base64.b64encode(processed_bytes).decode('ascii')}"

        try:
            self._require_configured()
            self.discover_vision_model()
            
            # Using 3072 max_tokens ensures quick response without memory starvation
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
                    **self._chat_options(3072),
                },
            )
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = self._parse_json_content(content) 

            # Extract list of items
            items = None
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                items = (
                    parsed.get("extracted_items")
                    or parsed.get("items")
                    or parsed.get("offers")
                    or parsed.get("products")
                )
                if items is None:
                    # Check nested objects if wrapped under a document/leaflet key
                    for val in parsed.values():
                        if isinstance(val, dict) and "extracted_items" in val:
                            items = val["extracted_items"]
                            break
                        if isinstance(val, list) and val and isinstance(val[0], dict):
                            items = val
                            break

            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise ProviderRequestError("AMD returned an invalid leaflet candidate structure.")

            # Sanitize LLM values so they satisfy the schema
            cleaned_items = []
            for item in items:
                curr = str(item.get("currency") or "").strip().upper()
                if curr in {"R", "RAND", "RANDS"}:
                    curr = "ZAR"

                raw_price = item.get("pack_price", item.get("supplier_price", item.get("price")))
                if isinstance(raw_price, str):
                    clean_price = re.sub(r"[^\d.]", "", raw_price.replace(",", ""))
                    try:
                        raw_price = float(clean_price) if clean_price else None
                    except ValueError:
                        raw_price = None

                conf = item.get("confidence")
                if isinstance(conf, (int, float)) and conf > 1.0:
                    conf = min(1.0, conf / 100.0)

                cleaned_item = dict(item)
                if curr:
                    cleaned_item["currency"] = curr
                if raw_price is not None:
                    cleaned_item["pack_price"] = raw_price
                if conf is not None:
                    cleaned_item["confidence"] = conf
                cleaned_items.append(cleaned_item)

            usage = payload.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            self._record_call(started, "success", prompt_tokens, completion_tokens)
            return {"status": "completed", "extracted_items": cleaned_items, "source": "amd"}
            
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
        clean_int = internal_product.lower().strip()
        clean_cand = candidate_supplier_item.lower().strip()
        is_match = False
        rationale = "Heuristic match based on brand and volume equivalence"
        confidence = score

        int_size = _first_size(clean_int)
        cand_size = _first_size(clean_cand)
        int_variants = _variants(clean_int)
        cand_variants = _variants(clean_cand)

        if int_size and cand_size and int_size != cand_size:
            rationale = "Pack sizes differ, so these are not the same product"
        elif (int_variants ^ cand_variants) & _SUGAR_VARIANTS or (
            int_variants and cand_variants and int_variants != cand_variants
        ):
            rationale = "Product variants differ (e.g. zero/diet or white/brown)"
        elif _has_word("coca-cola", clean_int) and (_has_word("coke", clean_cand) or _has_word("coca-cola", clean_cand)):
            is_match, rationale, confidence = True, "Identified brand synonym: Coke -> Coca-Cola", min(score, 0.96) if score else 0.96
        elif _has_word("sprite", clean_int) and _has_word("sprite", clean_cand):
            is_match, rationale, confidence = True, "Direct match on brand", min(score, 0.98) if score else 0.98
        elif _has_word("noodles", clean_int) and (_has_word("noodles", clean_cand) or _has_word("ramen", clean_cand)):
            is_match, rationale, confidence = True, "Category match on instant noodle pack", min(score, 0.92) if score else 0.92
        elif _has_word("bread", clean_int) and (_has_word("bread", clean_cand) or _has_word("loaf", clean_cand)):
            is_match, rationale, confidence = True, "Bakery staple category match", min(score, 0.88) if score else 0.88
        elif _has_word("oil", clean_int) and _has_word("oil", clean_cand):
            is_match, rationale, confidence = True, "Cooking oil category match", min(score, 0.89) if score else 0.89
        elif score >= 0.75:
            is_match, rationale = True, f"High fuzzy similarity ({round(score * 100)}%)"
        else:
            rationale = f"Insufficient match confidence ({round(score * 100)}%)"

        if is_match and not (int_size and cand_size):
            rationale += "; pack size not confirmed, verify before ordering"

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
                    **self._chat_options(2048),
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
        def item(product: str, pack_size: str, supplier: str, price: float, unit_price: float) -> Dict[str, Any]:
            return {
                "product": product,
                "pack_size": pack_size,
                "supplier": supplier,
                "price": price,
                "pack_price": price,
                "unit_price": unit_price,
            }

        return {
            "status": "completed",
            "source": "local_demo_fixture",
            "extracted_items": [
                item("Coca-Cola 440ml", "24 x 440ml", "Makro", 289.00, 12.04),
                item("Sprite 440ml", "24 x 440ml", "Makro", 275.50, 11.48),
                item("Chicken Flavour Noodles", "5 x 70g", "Shoprite", 42.00, 8.40),
                item("Brown Bread", "1 x 700g", "Usave", 16.50, 16.50),
                item("Milk (long life)", "6 x 1L", "Usave", 84.00, 14.00),
                item("Cooking Oil", "6 x 1L", "Makro", 210.00, 35.00),
                item("Twizza Carbonated Drink 500ml", "24 x 500ml", "Jumbo", 168.00, 7.00),
                item("Jive Soda 440ml", "24 x 440ml", "Shoprite", 180.00, 7.50),
            ],
        }


amd_llm = AmdLlmAdapter()