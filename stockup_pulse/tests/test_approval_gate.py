"""
Tests for Strict Approval Gate (HTTP 409)
Non-negotiable: No purchase order exists until the owner explicitly approves.
"""

import pytest
from stockup_pulse.planning.optimizer import RestockingPlanOptimizer
from stockup_pulse.orders.manager import PurchaseOrderManager, PlanNotApprovedError

def test_approval_gate_raises_when_unapproved():
    opt = RestockingPlanOptimizer(seed=42)
    items = [
        {"product": "Brown Bread", "recommended_qty": 20, "unit_price": 16.50, "supplier": "Usave", "at_risk": False, "is_out_of_stock": False}
    ]
    plan = opt.optimize_plan(items, budget=1000.0)
    assert plan["approved"] is False

    mgr = PurchaseOrderManager()
    
    # Must raise PlanNotApprovedError
    with pytest.raises(PlanNotApprovedError):
        mgr.create_orders_from_plan(plan, approved=False)

def test_orders_created_only_after_approval():
    opt = RestockingPlanOptimizer(seed=42)
    items = [
        {"product": "Brown Bread", "recommended_qty": 20, "unit_price": 16.50, "supplier": "Usave", "at_risk": False, "is_out_of_stock": False}
    ]
    plan = opt.optimize_plan(items, budget=1000.0)
    plan["approved"] = True

    mgr = PurchaseOrderManager()
    orders = mgr.create_orders_from_plan(plan, approved=True)
    assert len(orders) == 1
    assert orders[0]["order_number"].startswith("PO-")
    assert orders[0]["status"] == "Ready"
