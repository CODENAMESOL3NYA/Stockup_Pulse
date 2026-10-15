import base64
import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from stockup_pulse.adapters.amd_llm import (
    AmdLlmAdapter,
    ProviderNotConfiguredError,
    ProviderRequestError,
)
from stockup_pulse.adapters.evolus import EvolusAdapter, EvolusRequestError
from stockup_pulse.api.main import PlanRequest, _parse_lead_times
from stockup_pulse.core.config import settings
from fastapi import HTTPException
from stockup_pulse.trace.tracker import trace_collector


def test_amd_discovers_vision_model_and_sends_base64_image(monkeypatch):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "Qwen3.8-27B")
    adapter = AmdLlmAdapter(model="Qwen3.8-27B")
    requests = []

    def request(method, path, **kwargs):
        requests.append((method, path, kwargs))
        if path == "models":
            return httpx.Response(200, json={
                "data": [{"id": "Qwen3.8-27B", "capabilities": {"vision": True}}],
            })
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps({"extracted_items": []})}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        })

    monkeypatch.setattr(adapter, "_request", request)
    trace_collector.clear()
    result = adapter.extract_leaflet_candidates(b"image-bytes", "extract offers", "leaflet.jpg")

    assert result == {"extracted_items": [], "source": "amd"}
    assert requests[0][:2] == ("GET", "models")
    call = requests[1][2]["json"]
    image_url = call["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url == f"data:image/jpeg;base64,{base64.b64encode(b'image-bytes').decode()}"
    event = trace_collector.get_events()[-1]
    assert event.event_type == "llm_call"
    assert event.tokens_total == 15


def test_amd_model_discovery_failure_is_traced(monkeypatch):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "text-only")
    adapter = AmdLlmAdapter(model="text-only")
    monkeypatch.setattr(
        adapter,
        "_request",
        lambda method, path, **kwargs: httpx.Response(
            200,
            json={"data": [{"id": "text-only", "capabilities": {"vision": False}}]},
        ),
    )
    trace_collector.clear()

    with pytest.raises(ProviderNotConfiguredError, match="not marked as image-capable"):
        adapter.extract_leaflet_candidates(b"image", "extract", "leaflet.png")

    event = trace_collector.get_events()[-1]
    assert event.event_type == "fallback"
    assert event.status == "error"


def test_amd_retries_rate_limit_using_retry_after(monkeypatch):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "vision-model")
    adapter = AmdLlmAdapter(model="vision-model")
    adapter.max_retries = 1
    responses = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"data": []}),
    ]
    calls = []
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: calls.append(kwargs) or responses.pop(0))
    monkeypatch.setattr("stockup_pulse.adapters.amd_llm.time.sleep", lambda _: None)

    assert adapter._request("GET", "models").status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize("status_code", [502, 503])
def test_amd_retries_transient_gateway_errors(monkeypatch, status_code):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "vision-model")
    adapter = AmdLlmAdapter(model="vision-model")
    adapter.max_retries = 1
    responses = [httpx.Response(status_code), httpx.Response(200, json={"data": []})]
    calls = []
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: calls.append(1) or responses.pop(0))
    monkeypatch.setattr("stockup_pulse.adapters.amd_llm.time.sleep", lambda _: None)

    assert adapter._request("GET", "models").status_code == 200
    assert len(calls) == 2


def test_amd_retries_request_timeout_once(monkeypatch):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "vision-model")
    adapter = AmdLlmAdapter(model="vision-model")
    adapter.max_retries = 1
    calls = []

    def request(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.TimeoutException("request timed out")
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr(httpx, "request", request)
    monkeypatch.setattr("stockup_pulse.adapters.amd_llm.time.sleep", lambda _: None)

    assert adapter._request("GET", "models").status_code == 200
    assert len(calls) == 2


def test_evolus_submits_and_polls_configured_workflow(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUS_ENABLED", True)
    monkeypatch.setattr(settings, "EVOLUS_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUS_APPLICATION_ID", "test-app")
    monkeypatch.setattr(settings, "EVOLUS_WORKFLOW_ID", "leaflet-workflow")
    monkeypatch.setattr(settings, "EVOLUS_EXECUTION_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(settings, "EVOLUS_POLL_INTERVAL_SECONDS", 0.01)
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.poll = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs))
            return SimpleNamespace(
                status_code=202,
                headers={},
                json=lambda: {"executionId": "execution-1"},
            )

        def get(self, url, **kwargs):
            calls.append(("GET", url, kwargs))
            self.poll += 1
            state = ["Pending", "Running", "Completed"][self.poll - 1]
            result = {"items": [{"product": "Rice", "pack_price": 20, "supplier": "Makro"}]}
            return SimpleNamespace(
                is_error=False,
                status_code=200,
                json=lambda: {"status": state, "result": result},
            )

    monkeypatch.setattr("stockup_pulse.adapters.evolus.httpx.Client", FakeClient)
    monkeypatch.setattr("stockup_pulse.adapters.evolus.time.sleep", lambda _: None)

    result = EvolusAdapter().extract_document(b"%PDF-fixture", "leaflet.pdf")

    assert result["status"] == "completed"
    assert result["extracted_items"][0]["product"] == "Rice"
    assert len(calls) == 4
    assert "workflows/leaflet-workflow/execute" in calls[0][1]
    assert calls[0][2]["headers"]["X-Application-Id"] == "test-app"
    assert calls[0][2]["files"]["file"][1] == b"%PDF-fixture"


def test_evolus_failed_execution_is_reported_without_result(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUS_ENABLED", True)
    monkeypatch.setattr(settings, "EVOLUS_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUS_APPLICATION_ID", "test-app")
    monkeypatch.setattr(settings, "EVOLUS_WORKFLOW_ID", "leaflet-workflow")
    monkeypatch.setattr(settings, "EVOLUS_EXECUTION_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(settings, "EVOLUS_POLL_INTERVAL_SECONDS", 0.01)

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return SimpleNamespace(status_code=202, headers={}, json=lambda: {"executionId": "execution-1"})

        def get(self, *args, **kwargs):
            return SimpleNamespace(is_error=False, status_code=200, json=lambda: {"status": "Failed"})

    monkeypatch.setattr("stockup_pulse.adapters.evolus.httpx.Client", FakeClient)
    monkeypatch.setattr("stockup_pulse.adapters.evolus.time.sleep", lambda _: None)

    with pytest.raises(EvolusRequestError, match="workflow failed"):
        EvolusAdapter().extract_document(b"%PDF-fixture", "leaflet.pdf")


def test_evolus_malformed_completed_result_fails_validation(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUS_ENABLED", True)
    monkeypatch.setattr(settings, "EVOLUS_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUS_APPLICATION_ID", "test-app")
    monkeypatch.setattr(settings, "EVOLUS_WORKFLOW_ID", "leaflet-workflow")
    monkeypatch.setattr(settings, "EVOLUS_EXECUTION_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(settings, "EVOLUS_POLL_INTERVAL_SECONDS", 0.01)

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return SimpleNamespace(status_code=202, headers={}, json=lambda: {"executionId": "execution-1"})

        def get(self, *args, **kwargs):
            return SimpleNamespace(
                is_error=False,
                status_code=200,
                json=lambda: {"status": "Completed", "result": {"items": "not-an-array"}},
            )

    monkeypatch.setattr("stockup_pulse.adapters.evolus.httpx.Client", FakeClient)
    monkeypatch.setattr("stockup_pulse.adapters.evolus.time.sleep", lambda _: None)

    with pytest.raises(EvolusRequestError, match="invalid candidate structure"):
        EvolusAdapter().extract_document(b"%PDF-fixture", "leaflet.pdf")


def test_evolus_pending_execution_respects_deadline(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUS_ENABLED", True)
    monkeypatch.setattr(settings, "EVOLUS_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "EVOLUS_APPLICATION_ID", "test-app")
    monkeypatch.setattr(settings, "EVOLUS_WORKFLOW_ID", "leaflet-workflow")
    monkeypatch.setattr(settings, "EVOLUS_EXECUTION_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(settings, "EVOLUS_POLL_INTERVAL_SECONDS", 0.001)

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            return SimpleNamespace(status_code=202, headers={}, json=lambda: {"executionId": "execution-1"})

        def get(self, *args, **kwargs):
            return SimpleNamespace(is_error=False, status_code=200, json=lambda: {"status": "Pending"})

    monkeypatch.setattr("stockup_pulse.adapters.evolus.httpx.Client", FakeClient)
    monkeypatch.setattr("stockup_pulse.adapters.evolus.time.sleep", lambda _: None)

    with pytest.raises(EvolusRequestError, match="exceeded its configured deadline"):
        EvolusAdapter().extract_document(b"%PDF-fixture", "leaflet.pdf")


@pytest.mark.parametrize("value", ['{"Makro": 1.5}', '{"Makro": true}', '{"Makro": 0}'])
def test_supplier_lead_time_rejects_non_whole_or_out_of_range_days(value):
    with pytest.raises(HTTPException):
        _parse_lead_times(value)


def test_imported_plan_rejects_fractional_lead_time():
    with pytest.raises(ValidationError):
        PlanRequest(
            budget=100,
            items=[{
                "product": "Rice",
                "recommended_qty": 1,
                "unit_price": 2,
                "supplier_price": 2,
                "our_price": 3,
                "supplier": "Makro",
                "currency": "ZAR",
                "currency_verified": True,
                "lead_time_days": 1.5,
                "source": "file_import",
                "reviewed": True,
                "retail_price_verified": True,
            }],
        )


@pytest.mark.parametrize("status_code", [401, 403])
def test_amd_http_errors_are_not_retried_without_policy(monkeypatch, status_code):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "https://amd.example/v1")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "vision-model")
    adapter = AmdLlmAdapter(model="vision-model")
    adapter.max_retries = 3
    calls = []
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: calls.append(1) or httpx.Response(status_code))

    with pytest.raises(ProviderRequestError, match=f"HTTP {status_code}"):
        adapter._request("GET", "models")

    assert len(calls) == 1


def test_amd_explanation_uses_local_fallback_when_configuration_is_incomplete(monkeypatch):
    monkeypatch.setattr(settings, "AMD_ROCM_ENABLED", True)
    monkeypatch.setattr(settings, "AMD_ROCM_HOST", "")
    monkeypatch.setattr(settings, "AMD_ROCM_API_KEY", "test-token")
    monkeypatch.setattr(settings, "AMD_ROCM_MODEL", "vision-model")
    trace_collector.clear()

    explanation = AmdLlmAdapter().write_plain_language_explanation({
        "budget": 100,
        "total_spend": 80,
        "total_items_to_reorder": 4,
        "remaining_budget": 20,
    })

    assert "R 80.00" in explanation
    event = trace_collector.get_events()[-1]
    assert event.event_type == "fallback"
    assert event.status == "fallback"
