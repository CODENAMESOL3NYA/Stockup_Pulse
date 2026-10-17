"""Evolus document-extraction workflow adapter with bounded polling."""

import json
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from stockup_pulse.core.config import settings
from stockup_pulse.trace.tracker import TraceEvent, trace_collector


class EvolusNotConfiguredError(RuntimeError):
    """Raised when PDF extraction is requested while the Evolus integration is disabled."""


class EvolusRequestError(RuntimeError):
    """Raised for sanitized Evolus workflow failures."""


class EvolusAdapter:
    _SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b", re.IGNORECASE)
    _COUNT_RE = re.compile(r"\b(\d+)\s*s\b", re.IGNORECASE)

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        application_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.EVOLUS_API_KEY
        self.endpoint = (endpoint or settings.EVOLUS_ENDPOINT).rstrip("/")
        self.application_id = application_id if application_id is not None else settings.EVOLUS_APPLICATION_ID
        self.workflow_id = workflow_id if workflow_id is not None else settings.EVOLUS_WORKFLOW_ID
        self.timeout = settings.EVOLUS_EXECUTION_TIMEOUT_SECONDS
        self.poll_interval = settings.EVOLUS_POLL_INTERVAL_SECONDS

    def _require_configured(self) -> None:
        if not settings.EVOLUS_ENABLED:
            raise EvolusNotConfiguredError("Evolus PDF extraction is disabled.")
        if not all((self.api_key, self.application_id, self.workflow_id, self.endpoint)):
            raise EvolusNotConfiguredError(
                "Evolus PDF extraction requires API key, application ID, workflow ID, and endpoint."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "X-ApiKey": self.api_key,
            "X-Application-Id": self.application_id,
            "Accept": "application/json",
        }

    def _record(self, status: str, started: float) -> None:
        trace_collector.record(TraceEvent(
            event_type="evolus_call" if status == "success" else "fallback",
            device="not_reported",
            rocm_version="not_reported",
            model="not_invoked",
            endpoint_host=self.endpoint,
            evolus_block="document_extraction",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status=status,
            details={"task": "pdf_extraction"},
        ))

    @staticmethod
    def _normalise_lines(document: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        lines = document.get("lines")
        if not isinstance(lines, list) or not all(isinstance(line, dict) for line in lines):
            return None
        terms = document.get("terms") if isinstance(document.get("terms"), dict) else {}
        items: List[Dict[str, Any]] = []
        for line in lines:
            raw_name = line.get("raw_name") or line.get("product_name")
            price = line.get("pack_price")
            if not raw_name or not isinstance(price, (int, float)):
                continue  # or collect these as rejected lines for review
            promo = line.get("promo") if isinstance(line.get("promo"), dict) else {}
            conf = line.get("confidence")
            conf_vals = (
                [v for v in conf.values() if isinstance(v, (int, float))]
                if isinstance(conf, dict) else []
            )
            size_match = EvolusAdapter._SIZE_RE.search(raw_name)
            count_match = EvolusAdapter._COUNT_RE.search(raw_name)
            if size_match:
                pack_size = f"{size_match.group(1)}{size_match.group(2).lower()}"
            else:
                pack_size = f"{line.get('pack_size')}{line.get('pack_unit') or ''}"
            items.append({
                "product": line.get("product_name") or raw_name,
                "pack_size": pack_size,
                "pack_count": int(count_match.group(1)) if count_match else None,
                "pack_price": float(price),
                "supplier": document.get("supplier"),
                "currency": document.get("currency"),
                "availability": None,
                "evidence": " | ".join(filter(None, [raw_name, promo.get("promo_note")])),
                "confidence": min(conf_vals) if conf_vals else None,
                "was_price": promo.get("was_price"),
                "valid_to": document.get("valid_to"),
                "minimum_order": terms.get("minimum_order"),
                "prices_include_vat": document.get("prices_include_vat"),
                "needs_review": bool(line.get("needs_review")),
            })
        return items

    def extract_document(
        self,
        file_content: bytes,
        filename: str,
        prompt: str = (
            "Extract the leaflet's clearly observed products, pack sizes, pack prices, "
            "supplier, currency, availability, and short evidence as JSON. Do not estimate "
            "missing values or calculate retail prices, demand, or order quantities."
        ),
    ) -> Dict[str, Any]:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Evolus document extraction accepts PDF files only.")
        started = time.perf_counter()
        if self.timeout <= 0 or self.poll_interval <= 0:
            self._record("not_configured", started)
            raise EvolusNotConfiguredError("Evolus timeout and poll interval must be positive.")
        deadline = time.monotonic() + self.timeout
        workflow = quote(self.workflow_id, safe="")
        execute_url = f"{self.endpoint}/workflows/{workflow}/execute"
        try:
            self._require_configured()
            with httpx.Client(timeout=min(30.0, self.timeout), follow_redirects=False) as client:
                submitted = client.post(
                    execute_url,
                    headers=self._headers(),
                    data={"input": None},
                    files={"file": (filename, file_content, "application/pdf")},
                )
                if submitted.status_code != 202:
                    raise EvolusRequestError(f"Evolus workflow submission returned HTTP {submitted.status_code}.")
                execution_id = submitted.headers.get("X-Workflow-Execution-Id")
                if not execution_id:
                    try:
                        submission = submitted.json()
                    except ValueError as exc:
                        raise EvolusRequestError("Evolus workflow submission returned invalid JSON.") from exc
                    if not isinstance(submission, dict):
                        raise EvolusRequestError("Evolus workflow submission returned an invalid response.")
                    execution_id = submission.get("executionId")
                if not isinstance(execution_id, str) or not execution_id:
                    raise EvolusRequestError("Evolus response did not include an execution ID.")

                status_url = (
                    f"{self.endpoint}/workflows/{workflow}/executions/"
                    f"{quote(execution_id, safe='')}"
                )
                while time.monotonic() < deadline:
                    remaining = deadline - time.monotonic()
                    time.sleep(min(self.poll_interval, max(0.0, remaining)))
                    if time.monotonic() >= deadline:
                        break
                    response = client.get(
                        status_url,
                        headers=self._headers(),
                        timeout=min(30.0, max(0.1, deadline - time.monotonic())),
                    )
                    if response.status_code != 200:
                        raise EvolusRequestError(
                            f"Evolus workflow polling returned HTTP {response.status_code}."
                        )
                    try:
                        execution = response.json()
                    except ValueError as exc:
                        raise EvolusRequestError("Evolus workflow status returned invalid JSON.") from exc
                    if not isinstance(execution, dict):
                        raise EvolusRequestError("Evolus workflow status returned an invalid response.")
                    state = str(execution.get("status", "")).lower()
                    if state in {"pending", "running"}:
                        continue
                    if state == "failed":
                        raise EvolusRequestError("Evolus document-extraction workflow failed.")
                    if state == "completed":
                        result = execution.get("output")
                        if result is None:
                            result = execution.get("result")
                        # 1) Decode a JSON string first (it may hold the "lines" document).
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except ValueError as exc:
                                raise EvolusRequestError("Evolus workflow result was not valid JSON.") from exc
                        # 2) Then unwrap/normalise whichever dict shape arrived.
                        if isinstance(result, dict) and "lines" in result:
                            result = self._normalise_lines(result)
                        elif isinstance(result, dict):
                            result = result.get("extracted_items", result.get("items"))
                        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
                            raise EvolusRequestError("Evolus workflow result has an invalid candidate structure.")
                        self._record("success", started)
                        return {"status": "completed", "extracted_items": result, "source": "evolus"}
                    raise EvolusRequestError("Evolus workflow returned an unknown execution status.")
            raise EvolusRequestError("Evolus document extraction exceeded its configured deadline.")
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            self._record("error", started)
            raise EvolusRequestError("Evolus document-extraction request failed or timed out.") from exc
        except EvolusNotConfiguredError:
            self._record("not_configured", started)
            raise
        except EvolusRequestError:
            self._record("error", started)
            raise

    def execute_workflow(self, workflow_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise EvolusNotConfiguredError("Only the configured PDF document-extraction workflow is supported.")

    def run_agent_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        raise EvolusNotConfiguredError("Evolus agent/chat APIs are outside the configured integration scope.")

    def query_knowledge_library(self, query: str) -> List[Dict[str, Any]]:
        raise EvolusNotConfiguredError("Evolus knowledge-library APIs are outside the configured integration scope.")


evolus_adapter = EvolusAdapter()