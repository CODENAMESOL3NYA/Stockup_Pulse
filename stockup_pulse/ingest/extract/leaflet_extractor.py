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
        prompt = (
            "Analyze this wholesale promotional leaflet from Makro / Jumbo / Shoprite / Usave. "
            "Extract every offer as JSON with product, pack_size, pack_price, supplier, and confidence. "
            "Do not estimate missing prices or pack counts. Return an object with extracted_items."
        )
        result = self.extract_structured_from_leaflet(image_data_or_bytes, filename, prompt)
        return result["extracted_items"]

    def extract_structured_from_leaflet(
        self,
        content: bytes,
        filename: str,
        prompt: str | None = None,
    ) -> Dict[str, Any]:
        if filename.lower().endswith(".pdf"):
            return evolus_adapter.extract_document(content, filename)
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            request_prompt = prompt or (
                "Extract each wholesale offer as JSON with product, pack_size, pack_price, supplier, "
                "and confidence. Do not estimate missing values. Return an object with extracted_items."
            )
            return amd_llm.extract_leaflet_candidates(content, request_prompt, filename)
        raise ValueError("Leaflet inputs must be PDF, JPG, JPEG, or PNG files.")

leaflet_extractor = LeafletExtractor()
