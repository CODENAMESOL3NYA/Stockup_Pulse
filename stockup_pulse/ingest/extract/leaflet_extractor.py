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
            "Return only a valid JSON object with the exact key 'extracted_items' containing a list of objects. "
            "Each item object must conform to this schema:\n"
            "- product: string (the product name and brand, never null)\n"
            "- pack_size: string or null (e.g. '24 x 440ml', '500g', '6 x 1L')\n"
            "- pack_count: integer or null (total unit count; e.g. for '24 x 440ml', use 24. Do not output 1 for multipacks)\n"
            "- pack_price: float or null (numeric amount only, e.g. 149.99; DO NOT include 'R', currency symbols, or commas)\n"
            "- supplier: string or null (e.g. 'Makro', 'Jumbo', 'Shoprite', 'Usave')\n"
            "- currency: string or null (standard 3-letter ISO code like 'ZAR'; use 'ZAR' for South African Rand, never 'R')\n"
            "- availability: string or null\n"
            "- evidence: string or null (short observed text quote)\n"
            "- confidence: float between 0.0 and 1.0 (e.g. 0.95)\n"
            "Do not calculate retail prices, demand, or order quantities. Output only raw JSON."
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
