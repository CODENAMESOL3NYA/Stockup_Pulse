"""
Tests for Restocking Plan Optimizer
Validates:
1. Determinism: identical input + seed => byte-identical plan JSON.
2. Budget invariant: total_spend <= budget.
3. Automated brand substitution for stockouts / budget breaches.
"""

import pytest
import json
from stockup_pulse.planning.optimizer import RestockingPlanOptimizer
from stockup_pulse.core.db import init_db

@pytest.fixture
def sample_items():
    return [
        {
            "product": "Coca-Cola 440ml",
            "pack_size": "24 x 440ml",
            "supplier": "Makro",
            "recommended_qty": 96,
            "unit_price": 12.09,
            "our_price": 16.00,
            "at_risk": False,
            "is_out_of_stock": False
        },
        {
            "product": "Sprite 440ml",
            "pack_size": "24 x 440ml",
            "supplier": "Makro",
            "recommended_qty": 72,
            "unit_price": 11.48,
            "our_price": 15.50,
            "at_risk": False,
            "is_out_of_stock": False
        },
        {
            "product": "Chicken Flavour Noodles",
            "pack_size": "5 x 70g",
            "supplier": "Shoprite",
            "recommended_qty": 50,
            "unit_price": 8.40,
            "our_price": 12.00,
            "at_risk": True,
            "is_out_of_stock": False
        }
    ]

def test_determinism_byte_identical_json(sample_items):
    opt1 = RestockingPlanOptimizer(seed=42)
    opt2 = RestockingPlanOptimizer(seed=42)

    plan1 = opt1.optimize_plan(sample_items, budget=3000.0)
    plan2 = opt2.optimize_plan(sample_items, budget=3000.0)

    json1 = opt1.serialize_plan_to_deterministic_json(plan1)
    json2 = opt2.serialize_plan_to_deterministic_json(plan2)

    assert json1 == json2, "Deterministic optimizer produced differing JSON output for identical input and seed!"

def test_budget_constraint_never_breached(sample_items):
    opt = RestockingPlanOptimizer(seed=42)
    budgets = [500.0, 1000.0, 2500.0, 3000.0, 10000.0]

    for b in budgets:
        plan = opt.optimize_plan(sample_items, budget=b)
        assert plan["total_spend"] <= b, f"Plan total spend {plan['total_spend']} exceeded budget {b}"
        assert plan["remaining_budget"] >= 0.0

def test_brand_substitution_on_stockout():
    init_db()
    opt = RestockingPlanOptimizer(seed=42)
    items = [
        {
            "product": "Coca-Cola 440ml",
            "pack_size": "24 x 440ml",
            "supplier": "Makro",
            "recommended_qty": 48,
            "unit_price": 12.00,
            "our_price": 16.00,
            "at_risk": False,
            "is_out_of_stock": True # Stockout!
        }
    ]
    plan = opt.optimize_plan(items, budget=2000.0, allow_substitutions=True)
    assert len(plan["substitutions_applied"]) > 0, "Failed to substitute stockout item"
    sub = plan["substitutions_applied"][0]
    assert "Coca-Cola" in sub["original_product"]
    assert any(term in sub["substituted_with"] for term in ["Jive", "Twizza", "Sparletta"])
    assert sub.get("swapped_via_live_market_prices") is True

def test_brand_substitution_from_live_market_prices():
    init_db()
    opt = RestockingPlanOptimizer(seed=42)
    # Item that exceeds budget constraint
    items = [
        {
            "product": "Golden Delight Cooking Oil 6x1L",
            "pack_size": "6 x 1L",
            "supplier": "Makro",
            "recommended_qty": 10,
            "unit_price": 40.00,
            "our_price": 50.00,
            "at_risk": False,
            "is_out_of_stock": False
        }
    ]
    # Restrict budget so item must either be substituted with cheaper live market alternative or unfunded
    plan = opt.optimize_plan(items, budget=300.0, allow_substitutions=True)
    assert plan["total_spend"] <= 300.0


@pytest.mark.parametrize(
    ("budget", "items"),
    [
        (0, [{"product": "Rice", "recommended_qty": 1, "unit_price": 1}]),
        (10, [{"product": "Rice", "recommended_qty": 1.5, "unit_price": 1}]),
        (10, [{"product": "Rice", "recommended_qty": 1, "unit_price": float("nan")}]),
        (10, [{"product": "Rice", "recommended_qty": 1, "unit_price": -1}]),
        (10, [{"product": "", "recommended_qty": 1, "unit_price": 1}]),
    ],
)
def test_optimizer_rejects_invalid_financial_inputs(budget, items):
    with pytest.raises(ValueError):
        RestockingPlanOptimizer().optimize_plan(items, budget=budget)


def test_partial_allocation_uses_integer_cents():
    plan = RestockingPlanOptimizer().optimize_plan(
        [{"product": "Rice", "recommended_qty": 3, "unit_price": 0.10}],
        budget=0.29,
        allow_substitutions=False,
    )
    assert plan["total_spend"] == 0.20
    assert plan["remaining_budget"] == 0.09

