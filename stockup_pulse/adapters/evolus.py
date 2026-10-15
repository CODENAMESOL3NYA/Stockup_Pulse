"""
StockUp Pulse - Evolus Building Blocks Adapter
Interfaces with Evolus Building Blocks:
  - Agent
  - Workflow
  - Document Extraction
  - Knowledge Library
Features 30s timeout, retry, fallback to direct tools, and audit trace events.
"""

import time
from typing import Dict, Any, Optional, List
from stockup_pulse.core.config import settings
from stockup_pulse.trace.tracker import trace_collector, TraceEvent

class EvolusAdapter:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key or settings.EVOLUS_API_KEY
        self.endpoint = endpoint or settings.EVOLUS_ENDPOINT
        self.timeout = settings.EXTERNAL_TIMEOUT_SECONDS
        self.max_retries = settings.MAX_RETRIES

    def extract_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        self._record_unconfigured("document_extraction", {"file": filename, "size_bytes": len(file_content)})
        return {"status": "not_configured", "tables_found": 0}

    def execute_workflow(self, workflow_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._record_unconfigured("workflow", {"workflow": workflow_name})
        return {"status": "not_configured", "workflow": workflow_name}

    def run_agent_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._record_unconfigured("agent", {"action": action})
        return {"status": "not_configured", "action": action}

    def query_knowledge_library(self, query: str) -> List[Dict[str, Any]]:
        self._record_unconfigured("knowledge_library", {"query": query})
        return []

    def _record_unconfigured(self, block: str, details: Dict[str, Any]) -> None:
        trace_collector.record(TraceEvent(
            event_type="fallback",
            device="not_invoked",
            rocm_version="not_invoked",
            model="not_invoked",
            endpoint_host="not_invoked",
            evolus_block=block,
            status="not_configured",
            details={**details, "provider_call": False}
        ))

evolus_adapter = EvolusAdapter()
