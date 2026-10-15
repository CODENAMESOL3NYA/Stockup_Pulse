"""
StockUp Pulse - Audit Trace & Hardware Evidence Recorder
AMD Hackathon ACT III
Records device, model, endpoint host, latency, tokens, Evolus building block + status.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import threading
import uuid

class TraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str # "llm_call", "evolus_call", "fallback", "retry", "device_check", "tool_call", "approval"
    device: str = "not_reported"
    rocm_version: str = "not_reported"
    model: str = "not_reported"
    endpoint_host: str = "not_reported"
    evolus_block: Optional[str] = None # "document_extraction", "agent", "workflow", "knowledge_library"
    latency_ms: float = 0.0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    status: str = "success" # "success", "retry", "fallback", "error"
    details: Dict[str, Any] = Field(default_factory=dict)

class TraceCollector:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TraceCollector, cls).__new__(cls)
                cls._instance._events: List[TraceEvent] = []
        return cls._instance

    def record(self, event: TraceEvent) -> TraceEvent:
        with self._lock:
            self._events.append(event)
        return event

    def get_events(self) -> List[TraceEvent]:
        with self._lock:
            return list(self._events)

    def clear(self):
        with self._lock:
            self._events.clear()

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            events = list(self._events)
        
        llm_events = [e for e in events if e.event_type == "llm_call"]
        evolus_events = [e for e in events if e.event_type == "evolus_call"]
        latest_external_event = next(
            (event for event in reversed(events) if event.event_type in ("llm_call", "evolus_call")),
            None,
        )
        
        avg_latency = (
            sum(e.latency_ms for e in llm_events) / len(llm_events)
            if llm_events else 0.0
        )
        total_tokens = sum(e.tokens_total for e in llm_events)
        
        evolus_blocks = {}
        for e in evolus_events:
            block = e.evolus_block or "unknown"
            evolus_blocks[block] = evolus_blocks.get(block, 0) + 1

        return {
            "device": latest_external_event.device if latest_external_event else "not_reported",
            "rocm_version": latest_external_event.rocm_version if latest_external_event else "not_reported",
            "model": latest_external_event.model if latest_external_event else "not_reported",
            "endpoint_host": latest_external_event.endpoint_host if latest_external_event else "not_reported",
            "total_events": len(events),
            "llm_calls": len(llm_events),
            "evolus_calls": len(evolus_events),
            "evolus_breakdown": evolus_blocks,
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": total_tokens,
            "fallback_count": sum(1 for e in events if e.event_type == "fallback"),
            "retry_count": sum(1 for e in events if e.status == "retry"),
        }

trace_collector = TraceCollector()
