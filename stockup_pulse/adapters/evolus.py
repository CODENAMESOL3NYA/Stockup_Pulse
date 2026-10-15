"""Evolus document-extraction workflow adapter with bounded polling."""

import json
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

    def extract_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
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
                    data={"input": "Extract the leaflet's product, pack size, pack price, and supplier as JSON."},
                    files={"file": (filename, file_content, "application/pdf")},
                )
                if submitted.status_code != 202:
                    raise EvolusRequestError(f"Evolus workflow submission returned HTTP {submitted.status_code}.")
                try:
                    submission = submitted.json()
                except ValueError as exc:
                    raise EvolusRequestError("Evolus workflow submission returned invalid JSON.") from exc
                if not isinstance(submission, dict):
                    raise EvolusRequestError("Evolus workflow submission returned an invalid response.")
                execution_id = submission.get("executionId") or submitted.headers.get("X-Workflow-Execution-Id")
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
                    if response.is_error:
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
                        result = execution.get("result", execution.get("output"))
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except ValueError as exc:
                                raise EvolusRequestError("Evolus workflow result was not valid JSON.") from exc
                        if isinstance(result, dict):
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
