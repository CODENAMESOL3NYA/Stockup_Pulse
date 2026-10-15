"""
StockUp Pulse - Leaflet & Price List Document Extractor
Extracts promotional pricing and pack sizes from real wholesale leaflets (Makro, Jumbo, Shoprite, Usave).
Uses AMD ROCm Qwen2.5-VL-7B-Instruct adapter with Evolus document extraction workflow.
"""

from typing import List, Dict, Any
from stockup_pulse.adapters.amd_llm import amd_llm
from stockup_pulse.adapters.evolus import evolus_adapter

class LeafletExtractor:
    def extract_from_leaflet(self, image_data_or_bytes: bytes, filename: str = "flyer.jpg") -> List[Dict[str, Any]]:
        # 1. Trigger Evolus document extraction workflow event
        evolus_adapter.extract_document(image_data_or_bytes, filename)
        
        # 2. Call AMD ROCm LLM Vision Adapter
        prompt = (
            "Analyze this wholesale promotional leaflet from Makro / Jumbo / Shoprite / Usave. "
            "Extract: product name, pack size, wholesale pack price, unit price, and supplier name. "
            "Return valid JSON array of items."
        )
        extraction_res = amd_llm.extract_leaflet_text(str(image_data_or_bytes[:100]), prompt)
        return extraction_res.get("extracted_items", [])

leaflet_extractor = LeafletExtractor()
