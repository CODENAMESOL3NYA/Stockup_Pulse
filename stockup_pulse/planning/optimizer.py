"""
StockUp Pulse - Deterministic Restocking Optimizer & Brand Substitution Engine
AMD Hackathon ACT III (Reinvent Commerce)

Non-Negotiables:
1. LLM NEVER calculates money, quantities, or prices. Pure deterministic code only.
2. Identical input + seed => byte-identical plan JSON (sorted keys, fixed seed, zero wall-clock).
3. Deterministic Brand Substitution: if an item breaches budget or has a stockout,
   the optimizer queries the `live_market_prices` SQLite table for a cheaper or available equivalent.
   Strictly respects the Rand budget limit.
"""

import json
import logging
import math
from typing import List, Dict, Any, Optional
from stockup_pulse.core.db import query_live_market_substitute

logger = logging.getLogger(__name__)

# Fallback substitutions knowledge graph for Spaza retail staples
FALLBACK_SUBSTITUTION_RULES: Dict[str, Dict[str, Any]] = {
    "coca-cola": {
        "alternatives": ["Jive Carbonated Soda 440ml", "Twizza Carbonated Soft Drink 500ml", "Sparletta Creme Soda 440ml"],
        "category": "Soft Drinks",
        "supplier": "Shoprite",
        "savings_expected_pct": 38.0,
        "reason": "Lower unit wholesale cost allows meeting customer drink demand within budget"
    },
    "coke": {
        "alternatives": ["Twizza Carbonated Soft Drink 500ml", "Jive Carbonated Soda 440ml"],
        "category": "Soft Drinks",
        "supplier": "Checkers",
        "savings_expected_pct": 38.0,
        "reason": "Wholesale brand substitution preserves profit margin"
    },
    "cooking oil": {
        "alternatives": ["Sunfoil Sunflower Cooking Oil 750ml", "D'lite Cooking Oil 6x1L"],
        "category": "Cooking Oil",
        "supplier": "Shoprite",
        "savings_expected_pct": 14.0,
        "reason": "Alternative oil brand available at Shoprite/Makro with equivalent volume"
    },
    "brown bread": {
        "alternatives": ["Sunbake Sliced Brown Bread 700g", "Sasko Premium Brown Bread 700g"],
        "category": "Bakery",
        "supplier": "Shoprite",
        "savings_expected_pct": 8.0,
        "reason": "Fresh regional bakery substitution maintains daily delivery schedule"
    }
}

class RestockingPlanOptimizer:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def optimize_plan(
        self,
        candidate_items: List[Dict[str, Any]],
        budget: float,
        planning_horizon_days: int = 14,
        allow_substitutions: bool = True
    ) -> Dict[str, Any]:
        """
        Deterministic integer budget allocation algorithm.
        Maximizes expected margin and stockout prevention within budget constraint.
        Applies deterministic brand substitution querying `live_market_prices` if items exceed budget or stockout.
        """
        try:
            budget = float(budget)
        except (TypeError, ValueError) as exc:
            raise ValueError("Budget must be a finite positive amount.") from exc
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError("Budget must be a finite positive amount.")
        if not isinstance(planning_horizon_days, int) or planning_horizon_days <= 0:
            raise ValueError("Planning horizon must be a positive integer.")

        budget_cents = int(round(budget * 100))
        budget = budget_cents / 100

        # 1. Deterministic sorting by profitability score / urgency to ensure identical results
        # Score = (our_price - supplier_price) / max(0.01, supplier_price) * urgency_multiplier
        processed_candidates = []
        for index, item in enumerate(candidate_items):
            if not isinstance(item, dict):
                raise ValueError(f"Item {index + 1} must be an object.")
            product = str(item.get("product", "")).strip()
            if not product:
                raise ValueError(f"Item {index + 1} must have a product name.")

            raw_qty = item.get("recommended_qty", item.get("qty", 10))
            try:
                qty_value = float(raw_qty)
                supplier_price = round(float(item.get("supplier_price", item.get("price", 10.0))), 2)
                unit_price = round(float(item.get("unit_price", supplier_price)), 2)
                our_price = round(float(item.get("our_price", unit_price * 1.35)), 2)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Item {index + 1} quantity and prices must be numeric.") from exc
            if not math.isfinite(qty_value) or qty_value <= 0 or not qty_value.is_integer():
                raise ValueError(f"Item {index + 1} quantity must be a positive integer.")
            if any(not math.isfinite(value) or value <= 0 for value in (supplier_price, unit_price, our_price)):
                raise ValueError(f"Item {index + 1} prices must be finite positive amounts.")
            qty_needed = int(qty_value)
            margin = our_price - unit_price
            at_risk = bool(item.get("at_risk", False))
            
            # Urgency weight: at-risk items receive 2.0x priority
            urgency = 2.0 if at_risk else 1.0
            roi_score = (margin / max(0.01, unit_price)) * urgency
            
            processed_candidates.append({
                "product": product,
                "pack_size": item.get("pack_size", "1 ea"),
                "supplier": item.get("supplier", "Makro"),
                "recommended_qty": qty_needed,
                "unit_price": unit_price,
                "pack_price": supplier_price,
                "our_price": our_price,
                "margin": margin,
                "roi_score": roi_score,
                "at_risk": at_risk,
                "category": item.get("category", "General"),
                "is_out_of_stock": bool(item.get("is_out_of_stock", False))
            })

        # Sort strictly deterministically: descending roi_score, then ascending product name
        processed_candidates.sort(key=lambda x: (-x["roi_score"], x["product"]))

        allocated_items: List[Dict[str, Any]] = []
        substitutions_applied: List[Dict[str, Any]] = []
        unfunded_items: List[Dict[str, Any]] = []
        
        current_spend_cents = 0

        for cand in processed_candidates:
            product = cand["product"]
            req_qty = cand["recommended_qty"]
            unit_price = cand["unit_price"]
            unit_price_cents = int(round(unit_price * 100))
            item_total_cents = req_qty * unit_price_cents
            item_total = item_total_cents / 100
            
            # Check if out of stock or breaches budget
            needs_sub = False
            sub_reason = ""
            
            if cand["is_out_of_stock"]:
                needs_sub = True
                sub_reason = "Original supplier out of stock"
            elif (current_spend_cents + item_total_cents) > budget_cents:
                needs_sub = True
                sub_reason = "Budget limit constraint reached"

            # Check if brand substitution via live_market_prices or fallback rules can resolve
            if needs_sub and allow_substitutions:
                substitute_found = self._find_substitute(product, cand, current_spend_cents / 100, budget)
                if substitute_found:
                    sub_item, sub_qty, sub_cost = substitute_found
                    sub_cost_cents = int(round(sub_cost * 100))
                    if current_spend_cents + sub_cost_cents <= budget_cents:
                        current_spend_cents += sub_cost_cents
                        allocated_items.append({
                            "product": sub_item["product"],
                            "original_requested": product,
                            "qty": sub_qty,
                            "supplier": sub_item["supplier"],
                            "unit_price": round(sub_item["unit_price"], 2),
                            "total_cost": sub_cost_cents / 100,
                            "status": "Within budget (Substituted)",
                            "is_substituted": True,
                            "swapped_via_live_market_prices": sub_item.get("swapped_via_live_market_prices", False),
                            "live_market_retailer": sub_item.get("live_market_retailer", None),
                            "at_risk": cand["at_risk"]
                        })
                        substitutions_applied.append({
                            "original_product": product,
                            "substituted_with": sub_item["product"],
                            "original_cost": item_total_cents / 100,
                            "substituted_cost": sub_cost_cents / 100,
                            "savings": (item_total_cents - sub_cost_cents) / 100,
                            "reason": sub_item.get("sub_reason", sub_reason),
                            "swapped_via_live_market_prices": sub_item.get("swapped_via_live_market_prices", False),
                            "live_market_retailer": sub_item.get("live_market_retailer", None)
                        })
                        continue

            # Standard allocation if within budget
            if current_spend_cents + item_total_cents <= budget_cents and not cand["is_out_of_stock"]:
                current_spend_cents += item_total_cents
                allocated_items.append({
                    "product": product,
                    "qty": req_qty,
                    "supplier": cand["supplier"],
                    "unit_price": round(unit_price, 2),
                    "total_cost": item_total_cents / 100,
                    "status": "Within budget",
                    "is_substituted": False,
                    "swapped_via_live_market_prices": False,
                    "at_risk": cand["at_risk"]
                })
            else:
                # Can partial quantity fit within budget?
                remaining_cents = budget_cents - current_spend_cents
                partial_qty = remaining_cents // unit_price_cents
                if partial_qty > 0 and not cand["is_out_of_stock"]:
                    cost_cents = partial_qty * unit_price_cents
                    current_spend_cents += cost_cents
                    allocated_items.append({
                        "product": product,
                        "qty": partial_qty,
                        "supplier": cand["supplier"],
                        "unit_price": round(unit_price, 2),
                        "total_cost": cost_cents / 100,
                        "status": "Within budget (Partial)",
                        "is_substituted": False,
                        "swapped_via_live_market_prices": False,
                        "at_risk": cand["at_risk"]
                    })
                    unfunded_items.append({
                        "product": product,
                        "unfunded_qty": req_qty - partial_qty,
                        "reason": "Partial funding due to budget limit"
                    })
                else:
                    unfunded_items.append({
                        "product": product,
                        "unfunded_qty": req_qty,
                        "reason": sub_reason or "Exceeds remaining budget"
                    })

        # Calculate KPIs
        current_spend = current_spend_cents / 100
        remaining_budget = (budget_cents - current_spend_cents) / 100
        total_items_to_reorder = sum(i["qty"] for i in allocated_items)
        at_risk_count = sum(1 for i in allocated_items if i.get("at_risk"))

        # Sort allocated items deterministically by product name
        allocated_items.sort(key=lambda x: x["product"])

        # Group by supplier
        supplier_breakdown: Dict[str, Dict[str, Any]] = {}
        for item in allocated_items:
            sup = item["supplier"]
            if sup not in supplier_breakdown:
                supplier_breakdown[sup] = {"supplier": sup, "total_spend": 0.0, "items_count": 0, "items": []}
            supplier_breakdown[sup]["total_spend"] = round(supplier_breakdown[sup]["total_spend"] + item["total_cost"], 2)
            supplier_breakdown[sup]["items_count"] += item["qty"]
            supplier_breakdown[sup]["items"].append(item)

        # Plan dictionary with deterministic fields
        plan = {
            "plan_version": "1.0",
            "seed": self.seed,
            "approved": False, # Approval gate: initially strictly False
            "budget": round(budget, 2),
            "total_spend": round(current_spend, 2),
            "remaining_budget": remaining_budget,
            "budget_utilization_pct": round((current_spend / budget) * 100, 1) if budget > 0 else 0.0,
            "total_items_to_reorder": total_items_to_reorder,
            "at_risk_items_count": at_risk_count,
            "unfunded_items_count": len(unfunded_items),
            "allocated_items": allocated_items,
            "substitutions_applied": substitutions_applied,
            "unfunded_items": unfunded_items,
            "supplier_breakdown": supplier_breakdown
        }

        return plan

    def _find_substitute(self, product_name: str, candidate: Dict[str, Any], current_spend: float, budget: float):
        """
        Step 1: Query `live_market_prices` SQLite table for scraped real-time brand substitutions.
        Step 2: Fallback to static rule knowledge base if DB is empty or unpopulated.
        """
        original_unit_price = candidate["unit_price"]

        # 1. Check live_market_prices SQLite table
        try:
            live_match = query_live_market_substitute(
                product_name=product_name,
                original_unit_price=original_unit_price,
                prefer_lower_price=True
            )
            if live_match and live_match.price_zar:
                sub_unit_price = round(float(live_match.price_zar), 2)
                sub_qty = candidate["recommended_qty"]
                sub_cost = round(sub_qty * sub_unit_price, 2)
                savings_per_unit = round(original_unit_price - sub_unit_price, 2)

                sub_reason = (
                    f"Substituted with {live_match.product_name} via live scraped market prices from {live_match.retailer} "
                    f"to save R {savings_per_unit:.2f}/unit and stay within the R {budget:,.2f} budget."
                )

                sub_item = {
                    "product": live_match.product_name,
                    "supplier": live_match.retailer,
                    "unit_price": sub_unit_price,
                    "sub_reason": sub_reason,
                    "swapped_via_live_market_prices": True,
                    "live_market_retailer": live_match.retailer
                }
                return sub_item, sub_qty, sub_cost
        except Exception:
            logger.exception("Database substitution lookup failed; using configured fallback rules.")

        # 2. Fallback rule based substitutions
        clean_name = product_name.lower()
        for key, rule in FALLBACK_SUBSTITUTION_RULES.items():
            if key in clean_name:
                alt_name = rule["alternatives"][0]
                sub_unit_price = round(candidate["unit_price"] * (1.0 - (rule["savings_expected_pct"] / 100.0)), 2)
                sub_qty = candidate["recommended_qty"]
                sub_cost = round(sub_qty * sub_unit_price, 2)
                savings_total = round((candidate["unit_price"] * sub_qty) - sub_cost, 2)
                sub_reason = f"Substituted {product_name} for {alt_name} ({rule['supplier']}) to save R {savings_total:.2f} and stay within R {budget:,.2f} budget."

                sub_item = {
                    "product": alt_name,
                    "supplier": rule.get("supplier", candidate["supplier"]),
                    "unit_price": sub_unit_price,
                    "sub_reason": sub_reason,
                    "swapped_via_live_market_prices": False,
                    "live_market_retailer": None
                }
                return sub_item, sub_qty, sub_cost

        return None

    def serialize_plan_to_deterministic_json(self, plan: Dict[str, Any]) -> str:
        """Byte-identical JSON serialization using sorted keys."""
        return json.dumps(plan, sort_keys=True, indent=2)

optimizer = RestockingPlanOptimizer(seed=42)
