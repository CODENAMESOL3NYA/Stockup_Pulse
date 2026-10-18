"""
StockUp Pulse - Deterministic Restocking Optimizer for Spaza Retail Realities
Incorporates Pack Integrality, Supplier Fixed Costs, and Key-Value Item (KVI) Guarantees.
"""

import json
import math
import logging
from typing import List, Dict, Any, Optional
from stockup_pulse.core.db import query_live_market_substitute

logger = logging.getLogger(__name__)

# Brand elasticity: High stickiness means township customers refuse off-brands
BRAND_STICKINESS = {
    "coca-cola": 0.85,
    "coke": 0.85,
    "white star": 0.90,
    "albany": 0.70,
    "sunbake": 0.70,
    "sunfoil": 0.40,
}

DEFAULT_FIXED_SUPPLIER_TRIP_COST = 150.0  # Avanza / bakkie transport share per supplier


def get_brand_stickiness(product_name: str) -> float:
    """Matches product names using substring rules (e.g. 'Coca-Cola Original' -> 0.85)."""
    prod = str(product_name).lower()
    for brand, score in BRAND_STICKINESS.items():
        if brand in prod:
            return score
    return 0.30


class RestockingPlanOptimizer:
    def __init__(self, seed: int = 42, fixed_trip_cost: float = DEFAULT_FIXED_SUPPLIER_TRIP_COST):
        self.seed = seed
        self.fixed_trip_cost = fixed_trip_cost

    def optimize_plan(
        self,
        candidate_items: List[Dict[str, Any]],
        budget: float,
        planning_horizon_days: int = 14,
        allow_substitutions: bool = True
    ) -> Dict[str, Any]:
        if budget <= 0 or not math.isfinite(budget):
            raise ValueError("Budget must be a finite positive amount.")

        budget_cents = int(round(budget * 100))
        trip_cost_cents = int(round(self.fixed_trip_cost * 100))

        # 1. Clean & Normalize Candidate Items
        candidates = []
        for idx, item in enumerate(candidate_items):
            product = str(item.get("product", "")).strip()
            
            # Robust pack units extraction
            units_per_pack = int(item.get("units_per_pack", 0))
            if units_per_pack <= 0:
                pack_str = str(item.get("pack_size", "1")).lower()
                units_per_pack = 24 if "24" in pack_str else 1
            
            # Robust pack price
            supplier_price = float(item.get("supplier_price", item.get("price", 10.0)))
            pack_price = float(item.get("pack_price", supplier_price))
            unit_price = float(item.get("unit_price", pack_price / units_per_pack))
            our_price = float(item.get("our_price", unit_price * 1.35))
            
            # Support both recommended_packs and recommended_qty
            if "recommended_packs" in item:
                packs_needed = int(item["recommended_packs"])
            else:
                raw_qty = float(item.get("recommended_qty", item.get("qty", 10)))
                packs_needed = max(1, int(math.ceil(raw_qty / units_per_pack)))

            category = str(item.get("category", "General")).lower()
            is_kvi = bool(item.get("is_kvi", category in ["staples", "bakery", "dairy"]))
            at_risk = bool(item.get("at_risk", False))
            
            pack_margin = (our_price * units_per_pack) - pack_price
            kvi_weight = 3.5 if is_kvi else 1.0
            urgency_weight = 2.0 if at_risk else 1.0
            roi_ratio = pack_margin / max(1.0, pack_price)
            composite_score = roi_ratio * kvi_weight * urgency_weight

            candidates.append({
                "product": product,
                "pack_size": item.get("pack_size", f"{units_per_pack} ea"),
                "supplier": item.get("supplier", "Makro"),
                "units_per_pack": units_per_pack,
                "pack_price": pack_price,
                "pack_price_cents": int(round(pack_price * 100)),
                "unit_price": round(unit_price, 2),
                "our_price": round(our_price, 2),
                "pack_margin": round(pack_margin, 2),
                "recommended_packs": packs_needed,
                "composite_score": composite_score,
                "is_kvi": is_kvi,
                "at_risk": at_risk,
                "category": category,
                "is_out_of_stock": bool(item.get("is_out_of_stock", False))
            })

        # Deterministic sort
        candidates.sort(key=lambda x: (-x["composite_score"], x["product"]))

        allocated_items: List[Dict[str, Any]] = []
        substitutions_applied: List[Dict[str, Any]] = []
        unfunded_items: List[Dict[str, Any]] = []
        visited_suppliers = set()
        current_spend_cents = 0

        def supplier_inc_cost(supplier: str) -> int:
            return 0 if supplier in visited_suppliers else trip_cost_cents

        # Pass 1: Guarantee KVI staples
        for cand in candidates:
            if not cand["is_kvi"] or cand["is_out_of_stock"]:
                continue
            
            inc_trip = supplier_inc_cost(cand["supplier"])
            cost_one_pack = cand["pack_price_cents"] + inc_trip
            
            if current_spend_cents + cost_one_pack <= budget_cents:
                current_spend_cents += cost_one_pack
                visited_suppliers.add(cand["supplier"])
                cand["recommended_packs"] -= 1
                
                allocated_items.append({
                    "product": cand["product"],
                    "qty": cand["units_per_pack"],
                    "unit_price": cand["unit_price"],
                    "packs_ordered": 1,
                    "units_per_pack": cand["units_per_pack"],
                    "total_units": cand["units_per_pack"],
                    "supplier": cand["supplier"],
                    "pack_price": cand["pack_price"],
                    "total_cost": cand["pack_price"],
                    "status": "Within budget (KVI Protection)",
                    "is_substituted": False,
                    "is_kvi": True,
                    "at_risk": cand["at_risk"]
                })

        # Pass 2: Remaining allocation
        for cand in candidates:
            packs_still_needed = cand["recommended_packs"]
            if packs_still_needed <= 0 or cand["is_out_of_stock"]:
                continue

            supplier = cand["supplier"]
            pack_cost_cents = cand["pack_price_cents"]
            packs_allocated_for_cand = 0

            for _ in range(packs_still_needed):
                inc_trip = supplier_inc_cost(supplier)
                total_step_cost = pack_cost_cents + inc_trip
                
                if current_spend_cents + total_step_cost <= budget_cents:
                    current_spend_cents += total_step_cost
                    visited_suppliers.add(supplier)
                    packs_allocated_for_cand += 1
                    
                    existing = next((i for i in allocated_items if i["product"] == cand["product"]), None)
                    if existing:
                        existing["packs_ordered"] += 1
                        existing["total_units"] += cand["units_per_pack"]
                        existing["qty"] = existing["total_units"]
                        existing["total_cost"] = round(existing["packs_ordered"] * cand["pack_price"], 2)
                    else:
                        allocated_items.append({
                            "product": cand["product"],
                            "qty": cand["units_per_pack"],
                            "unit_price": cand["unit_price"],
                            "packs_ordered": 1,
                            "units_per_pack": cand["units_per_pack"],
                            "total_units": cand["units_per_pack"],
                            "supplier": supplier,
                            "pack_price": cand["pack_price"],
                            "total_cost": cand["pack_price"],
                            "status": "Within budget",
                            "is_substituted": False,
                            "is_kvi": cand["is_kvi"],
                            "at_risk": cand["at_risk"]
                        })
                else:
                    unfunded_packs = packs_still_needed - packs_allocated_for_cand
                    stickiness = get_brand_stickiness(cand["product"])
                    
                    if allow_substitutions and stickiness >= 0.80:
                        reason = f"High customer brand loyalty ({int(stickiness*100)}%). Substitution avoided."
                    else:
                        reason = "Exceeds remaining cash budget (pack-integral constraint)"

                    unfunded_items.append({
                        "product": cand["product"],
                        "unfunded_packs": unfunded_packs,
                        "unfunded_qty": unfunded_packs * cand["units_per_pack"],
                        "reason": reason
                    })
                    break

        allocated_items.sort(key=lambda x: x["product"])

        # Build supplier breakdown
        supplier_breakdown: Dict[str, Dict[str, Any]] = {}
        for sup in visited_suppliers:
            sup_items = [i for i in allocated_items if i["supplier"] == sup]
            sup_spend = sum(i["total_cost"] for i in sup_items)
            sup_units = sum(i["qty"] for i in sup_items)
            
            supplier_breakdown[sup] = {
                "supplier": sup,
                "total_spend": round(sup_spend, 2),
                "items_count": sup_units,
                "stock_spend": round(sup_spend, 2),
                "transport_allowance": self.fixed_trip_cost,
                "total_commitment": round(sup_spend + self.fixed_trip_cost, 2),
                "items": sup_items
            }

        total_stock_spend = sum(item["total_cost"] for item in allocated_items)
        total_transport = len(visited_suppliers) * self.fixed_trip_cost
        total_outlay = round(total_stock_spend + total_transport, 2)
        total_items_to_reorder = sum(i["qty"] for i in allocated_items)

        plan = {
            "plan_version": "2.0-spaza-realistic",
            "seed": self.seed,
            "approved": False,
            "budget": round(budget, 2),
            "total_spend": round(total_stock_spend, 2),
            "stock_spend": round(total_stock_spend, 2),
            "transport_provision": round(total_transport, 2),
            "total_outlay": total_outlay,
            "remaining_budget": round(budget - total_outlay, 2),
            "budget_utilization_pct": round((total_outlay / budget) * 100, 1) if budget > 0 else 0.0,
            "total_items_to_reorder": total_items_to_reorder,
            "active_suppliers_count": len(visited_suppliers),
            "at_risk_items_count": sum(1 for i in allocated_items if i.get("at_risk")),
            "unfunded_items_count": len(unfunded_items),
            "allocated_items": allocated_items,
            "substitutions_applied": substitutions_applied,
            "unfunded_items": unfunded_items,
            "supplier_breakdown": supplier_breakdown
        }
        return plan

    def serialize_plan_to_deterministic_json(self, plan: Dict[str, Any]) -> str:
        """Byte-identical JSON serialization using sorted keys."""
        return json.dumps(plan, sort_keys=True, indent=2)


# Export both names to satisfy all imports across the codebase
SpazaRestockingOptimizer = RestockingPlanOptimizer
optimizer = RestockingPlanOptimizer(seed=42)