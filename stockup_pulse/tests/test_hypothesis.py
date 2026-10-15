"""
Property-based Testing with Hypothesis
Invariants:
1. Total spend is ALWAYS <= budget.
2. Remaining budget is ALWAYS >= 0.
3. Order quantities are ALWAYS non-negative integers.
"""

from hypothesis import given, strategies as st
from stockup_pulse.planning.optimizer import RestockingPlanOptimizer

@given(
    budget=st.floats(min_value=100.0, max_value=50000.0),
    qty1=st.integers(min_value=1, max_value=200),
    qty2=st.integers(min_value=1, max_value=200),
    price1=st.floats(min_value=5.0, max_value=500.0),
    price2=st.floats(min_value=5.0, max_value=500.0),
)
def test_hypothesis_budget_invariant(budget, qty1, qty2, price1, price2):
    items = [
        {"product": "Item A", "recommended_qty": qty1, "unit_price": round(price1, 2), "supplier": "Makro", "at_risk": False, "is_out_of_stock": False},
        {"product": "Item B", "recommended_qty": qty2, "unit_price": round(price2, 2), "supplier": "Shoprite", "at_risk": True, "is_out_of_stock": False}
    ]
    opt = RestockingPlanOptimizer(seed=42)
    plan = opt.optimize_plan(items, budget=budget)
    
    # Invariant: Total spend never exceeds budget
    assert plan["total_spend"] <= round(budget, 2) + 0.01
    assert plan["remaining_budget"] >= -0.01
    for item in plan["allocated_items"]:
        assert item["qty"] >= 0
