"""
StockUp Pulse - Leaflet & Price List Document Extractor
Extracts promotional pricing and pack sizes from real wholesale leaflets (Makro, Jumbo, Shoprite, Usave).
Uses AMD ROCm Qwen2.5-VL-7B-Instruct adapter with Evolus document extraction workflow.
"""

from typing import Any, Dict, List

from stockup_pulse.adapters.amd_llm import amd_llm
from stockup_pulse.adapters.evolus import evolus_adapter


class LeafletExtractor:
    def extract_from_leaflet(self, image_data_or_bytes: bytes, filename: str = "flyer.jpg") -> List[Dict[str, Any]]:
        prompt = self._extraction_prompt()
        result = self.extract_structured_from_leaflet(image_data_or_bytes, filename, prompt)
        return result["extracted_items"]

    @staticmethod
    def _extraction_prompt() -> str:
        return (
            "Read this wholesale promotional leaflet and extract every clearly visible offer. "
            "Return only a JSON object with an extracted_items array. Each item may contain "
            "product, pack_size, pack_count, pack_price, supplier, currency, availability, "
            "evidence, and confidence. Use null for information that is not clearly shown. "
            "pack_price is the observed price for the whole offered pack, not a calculated "
            "unit price. Only report pack_count when it is explicitly stated. Do not estimate "
            "prices, pack counts, retail prices, sales, stock, demand, or order quantities. "
            "Preserve the currency shown and quote a short evidence phrase when possible. "
            "confidence must be between 0 and 1."
        )

    def extract_structured_from_leaflet(
        self,
        content: bytes,
        filename: str,
        prompt: str | None = None,
    ) -> Dict[str, Any]:
        if filename.lower().endswith(".pdf"):
            return evolus_adapter.extract_document(content, filename, prompt or self._extraction_prompt())
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            request_prompt = prompt or self._extraction_prompt()
            return amd_llm.extract_leaflet_candidates(content, request_prompt, filename)
        raise ValueError("Leaflet inputs must be PDF, JPG, JPEG, or PNG files.")

leaflet_extractor = LeafletExtractor()
