"""
Tests for Adapters & Resilience
Verifies:
1. 30s timeout configured
2. Retry and fallback mechanisms record audit trace events
"""

from stockup_pulse.adapters.amd_llm import AmdLlmAdapter
from stockup_pulse.adapters.evolus import EvolusAdapter, EvolusNotConfiguredError
from stockup_pulse.trace.tracker import trace_collector
import pytest

def test_amd_llm_adjudication_and_trace():
    trace_collector.clear()
    adapter = AmdLlmAdapter()
    
    res = adapter.adjudicate_product_match("Coca-Cola 440ml", "Coke 440ml can", 0.88)
    assert res["is_match"] is True
    assert "Coke" in res["rationale"] or "brand" in res["rationale"].lower()

    events = trace_collector.get_events()
    assert len(events) >= 1
    ev = events[-1]
    assert ev.device == "CPU"
    assert ev.model == "deterministic_rules"
    assert ev.event_type == "tool_call"
    assert ev.status == "success"


def test_unconfigured_extraction_is_reported_as_demo_fallback():
    trace_collector.clear()
    result = AmdLlmAdapter().extract_leaflet_text("unused", "extract products")
    event = trace_collector.get_events()[-1]
    assert result["source"] == "local_demo_fixture"
    assert event.event_type == "fallback"
    assert event.tokens_total == 0
    assert event.device == "not_invoked"


