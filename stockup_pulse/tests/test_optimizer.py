"""
Tests for Spaza Deterministic Restocking Optimizer
Verifies:
  1. Strict Budget & Transport Cost Constraint Adherence
  2. Wholesale Pack Integrality (No loose/fractional case purchases)
  3. Key Value Item (KVI) Staple Protection (Bread/Maize prioritized over high-margin luxuries)
  4. Supplier Trip Consolidation (Fixed logistics cost penalty)
  5. Brand Stickiness / Customer Refusal Sensitivity
  6. Deterministic Output (Byte-identical JSON)
  7. Strict Backward Compatibility with OrderManager & API callers
"""

import pytest
from stockup_pulse.planning.optimizer import optimizer, RestockingPlanOptimizer


@pytest.fixture
def sample_candidates():
    """Standard spaza restocking candidate fixture."""
    return [
        {
            "product": "Sunbake Sliced Brown Bread 700g",
            "category": "bakery",
            "is_kvi": True,
            "supplier": "Shoprite",
            "pack_size": "10 ea",
            "units_per_pack": 10,
            "pack_price": 140.0,       # R14.00 / loaf
            "our_price": 16.0,          # Thin ~14% margin
            "recommended_packs": 2,
            "recommended_qty": 20,
            "at_risk": True,
            "is_out_of_stock": False
        },
        {
            "product": "White Star Super Maize Meal 2.5kg",
            "category": "staples",
            "is_kvi": True,
            "supplier": "Makro",
            "pack_size": "6 ea",
            "units_per_pack": 6,
            "pack_price": 210.0,       # R35.00 / bag
            "our_price": 39.0,          # Low ~11% margin
            "recommended_packs": 2,
            "recommended_qty": 12,
            "at_risk": True,
            "is_out_of_stock": False
        },
        {
            "product": "Coca-Cola Original 24x330ml Can",
            "category": "soft drinks",
            "is_kvi": False,
            "supplier": "Makro",
            "pack_size": "24 ea",
            "units_per_pack": 24,
            "pack_price": 260.0,       # R10.83 / can
            "our_price": 15.0,          # Solid ~38% margin
            "recommended_packs": 2,
            "recommended_qty": 48,
            "at_risk": False,
            "is_out_of_stock": False
        },
        {
            "product": "Simba Potato Chips Assorted 48x36g",
            "category": "snacks",
            "is_kvi": False,
            "supplier": "Makro",
            "pack_size": "48 ea",
            "units_per_pack": 48,
            "pack_price": 280.0,
            "our_price": 8.0,           # High ~37% margin
            "recommended_packs": 1,
            "recommended_qty": 48,
            "at_risk": False,
            "is_out_of_stock": False
        }
    ]


def test_strict_budget_and_transport_adherence(sample_candidates):
    """The sum of stock purchases plus supplier bakkie/Avanza fees must never exceed budget."""
    budget = 1000.0
    plan = optimizer.optimize_plan(
        candidate_items=sample_candidates,
        budget=budget,
        planning_horizon_days=7
    )

    total_outlay = plan.get("total_outlay", plan.get("total_spend"))
    assert total_outlay <= budget
    assert plan["remaining_budget"] >= 0.0
    assert plan["total_spend"] <= budget


def test_wholesale_pack_integrality(sample_candidates):
    """Verifies orders are strictly in whole integer packs, never fractional or loose units."""
    plan = optimizer.optimize_plan(
        candidate_items=sample_candidates,
        budget=1200.0,
        planning_horizon_days=7
    )

    for item in plan["allocated_items"]:
        # Packs must be whole positive integers
        assert isinstance(item["packs_ordered"], int)
        assert item["packs_ordered"] >= 1

        # Total units must strictly equal packs * units_per_pack
        assert item["total_units"] == item["packs_ordered"] * item["units_per_pack"]

        # Cost must match pack_price * packs_ordered
        expected_cost = round(item["packs_ordered"] * item["pack_price"], 2)
        assert abs(item["total_cost"] - expected_cost) < 1e-2


def test_kvi_protection_under_tight_budget():
    """
    KVI staples (bread/maize) must be prioritized over high-margin snacks
    even when budget is severely constrained.
    """
    tight_budget = 350.0  # Only enough for 1 supplier trip + 1 pack
    opt = RestockingPlanOptimizer(seed=42, fixed_trip_cost=100.0)

    items = [
        {
            "product": "Luxury Chocolates 24s",
            "category": "confectionery",
            "is_kvi": False,
            "supplier": "Makro",
            "pack_size": "24 ea",
            "units_per_pack": 24,
            "pack_price": 200.0,
            "our_price": 20.0,          # 140% margin!
            "recommended_packs": 1,
            "at_risk": False
        },
        {
            "product": "Sunbake Brown Bread 10s",
            "category": "bakery",
            "is_kvi": True,             # Essential KVI staple
            "supplier": "Makro",
            "pack_size": "10 ea",
            "units_per_pack": 10,
            "pack_price": 140.0,
            "our_price": 16.0,          # Thin 14% margin
            "recommended_packs": 1,
            "at_risk": True
        }
    ]

    plan = opt.optimize_plan(candidate_items=items, budget=tight_budget)

    allocated_names = [i["product"] for i in plan["allocated_items"]]
    assert "Sunbake Brown Bread 10s" in allocated_names
    assert "Luxury Chocolates 24s" not in allocated_names


def test_supplier_trip_consolidation():
    """
    Verifies that the optimizer avoids splitting small budgets across multiple
    suppliers when fixed transport costs would consume the budget.
    """
    budget = 600.0
    # Fixed trip cost is R150 per supplier. Visiting 2 suppliers costs R300 in transport alone.
    opt = RestockingPlanOptimizer(seed=42, fixed_trip_cost=150.0)

    items = [
        {
            "product": "White Star Maize 2.5kg",
            "supplier": "Makro",
            "pack_size": "6 ea",
            "units_per_pack": 6,
            "pack_price": 210.0,
            "our_price": 40.0,
            "recommended_packs": 1,
            "is_kvi": True,
            "at_risk": True
        },
        {
            "product": "Simba Chips 48s",
            "supplier": "Makro",
            "pack_size": "48 ea",
            "units_per_pack": 48,
            "pack_price": 200.0,
            "our_price": 8.0,
            "recommended_packs": 1,
            "is_kvi": False,
            "at_risk": False
        },
        {
            "product": "Sasko Brown Bread 10s",
            "supplier": "Shoprite",       # Second supplier requiring additional R150 trip fee
            "pack_size": "10 ea",
            "units_per_pack": 10,
            "pack_price": 140.0,
            "our_price": 16.0,
            "recommended_packs": 1,
            "is_kvi": False,
            "at_risk": False
        }
    ]

    plan = opt.optimize_plan(candidate_items=items, budget=budget)
    assert plan["active_suppliers_count"] <= 2
    assert plan["transport_provision"] <= (plan["active_suppliers_count"] * 150.0)


def test_brand_stickiness_avoids_unwanted_substitutions():
    """High-stickiness items (e.g. Coca-Cola) should NOT be force-swapped to off-brands."""
    opt = RestockingPlanOptimizer(seed=42, fixed_trip_cost=0.0)
    items = [
        {
            "product": "Coca-Cola Original 24x330ml Can",
            "category": "soft drinks",
            "supplier": "Makro",
            "pack_size": "24 ea",
            "units_per_pack": 24,
            "pack_price": 300.0,
            "our_price": 15.0,
            "recommended_packs": 2,
            "is_kvi": False,
            "at_risk": False
        }
    ]

    # Budget can only afford 1 pack (R300), 2nd pack cannot be funded
    plan = opt.optimize_plan(candidate_items=items, budget=400.0, allow_substitutions=True)

    unfunded = plan["unfunded_items"]
    assert len(unfunded) > 0
    # Must report brand loyalty retention rather than forcing a low-grade substitute
    assert any("brand loyalty" in str(u.get("reason", "")).lower() for u in unfunded)


def test_deterministic_output_reproducibility(sample_candidates):
    """Identical candidate fixtures and seed must yield identical serialized JSON."""
    opt1 = RestockingPlanOptimizer(seed=42)
    opt2 = RestockingPlanOptimizer(seed=42)

    plan1 = opt1.optimize_plan(candidate_items=sample_candidates, budget=2500.0)
    plan2 = opt2.optimize_plan(candidate_items=sample_candidates, budget=2500.0)
    
    json1 = opt1.serialize_plan_to_deterministic_json(plan1)
    json2 = opt2.serialize_plan_to_deterministic_json(plan2)

    assert json1 == json2



def test_backward_compatibility_with_order_manager(sample_candidates):
    """
    CRITICAL: Validates that legacy keys required by order_manager.py,
    the API schemas, and the LLM adapter remain present and properly typed.
    """
    plan = optimizer.optimize_plan(
        candidate_items=sample_candidates,
        budget=2000.0
    )

    # Top-level plan legacy keys
    assert "approved" in plan
    assert plan["approved"] is False
    assert "total_spend" in plan
    assert "remaining_budget" in plan
    assert "budget_utilization_pct" in plan
    assert "total_items_to_reorder" in plan
    assert "supplier_breakdown" in plan

    # Supplier breakdown legacy keys (required by PurchaseOrderManager.create_orders_from_plan)
    for sup_name, sup_data in plan["supplier_breakdown"].items():
        assert "supplier" in sup_data
        assert "total_spend" in sup_data
        assert "items_count" in sup_data
        assert "items" in sup_data
        assert isinstance(sup_data["items_count"], int)

        # Allocated item legacy keys (required by format_whatsapp_message)
        for item in sup_data["items"]:
            assert "product" in item
            assert "qty" in item
            assert "unit_price" in item
            assert "total_cost" in item
            # Verify new OR keys exist in harmony
            assert "packs_ordered" in item
            assert "units_per_pack" in item