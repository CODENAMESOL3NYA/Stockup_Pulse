"""
StockUp Pulse - Catalogue Matching & Product Adjudication
Matches extracted messy wholesale price lists against the shop's product catalogue.
Uses RapidFuzz string distance + LLM Adjudication adapter on borderline items.
"""

from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz
from stockup_pulse.adapters.amd_llm import amd_llm

class CatalogueMatcher:
    def __init__(self, high_threshold: float = 0.85, review_threshold: float = 0.60):
        self.high_threshold = high_threshold
        self.review_threshold = review_threshold

    def match_catalogue(
        self,
        internal_catalogue: List[Dict[str, Any]],
        supplier_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        for item in internal_catalogue:
            item_name = item.get("name", "")
            pack_size = item.get("pack_size", "")
            our_price = float(item.get("our_price", 0.0))
            
            best_match: Optional[Dict[str, Any]] = None
            best_score = 0.0
            
            for sup_item in supplier_items:
                sup_name = sup_item.get("product", "")
                score = fuzz.token_sort_ratio(item_name.lower(), sup_name.lower()) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = sup_item

            if best_match and best_score >= self.high_threshold:
                status = "Confirmed"
                confidence = round(best_score, 2)
                matched_item = best_match
            elif best_match and best_score >= self.review_threshold:
                # Borderline match: call AMD LLM adjudication adapter
                adj = amd_llm.adjudicate_product_match(
                    internal_product=item_name,
                    candidate_supplier_item=best_match.get("product", ""),
                    score=best_score
                )
                status = "Confirmed" if adj.get("is_match") else "Needs review"
                confidence = round(adj.get("confidence", best_score), 2)
                matched_item = best_match
            elif best_match and best_score > 0.35:
                status = "Needs review"
                confidence = round(best_score, 2)
                matched_item = best_match
            else:
                status = "Unmatched"
                confidence = round(best_score, 2)
                matched_item = None

            supplier_price = matched_item.get("price", our_price * 0.82) if matched_item else our_price
            supplier_name = matched_item.get("supplier", "Unknown") if matched_item else "-"
            
            results.append({
                "product": item_name,
                "pack_size": pack_size,
                "supplier_price": round(supplier_price, 2),
                "our_price": round(our_price, 2),
                "supplier": supplier_name,
                "status": status,
                "confidence": confidence,
                "matched_supplier_item": matched_item.get("product") if matched_item else None
            })
            
        return results

matcher = CatalogueMatcher()
