"""
Tests for WAPE Metric, Perishability Bounds, and Pack Sizing
"""

import numpy as np
import pytest
from stockup_pulse.forecast.forecaster import  forecaster, DemandForecaster



def test_forecaster_transparency():
    eval_res = forecaster.evaluate_wape()
    assert "model_wape" in eval_res
    assert "baseline_wape" in eval_res
    assert eval_res["model_wape"] < eval_res["baseline_wape"]
    assert eval_res["forecast_accuracy"] > eval_res["baseline_accuracy"]
    assert eval_res["dataset_type"] == "illustrative_fixture"
    assert eval_res["sample_count"] == 10


def test_forecaster_requires_real_sales_history():
    with pytest.raises(ValueError, match="Sales history is required"):
        DemandForecaster().forecast_item([], lead_time_days=3)


def test_forecaster_perishability_shelf_life_capping():
    """Fresh brown bread has a 4-day shelf life and must not order for a 14-day horizon."""
    sales_history = [10.0, 12.0, 11.0, 9.0, 10.0, 13.0, 11.0]  # ~10 loaves/day
    fc = DemandForecaster().forecast_item(
        sales_history=sales_history,
        lead_time_days=1,
        planning_horizon_days=14,
        category="bakery",
        units_per_pack=10,
        is_kvi=True
    )

    # Shelf life caps horizon to 4 days rather than 14 days
    assert fc["effective_horizon_days"] == 4
    assert fc["is_spoilage_risk"] is True
    # Recommended packs must be bounded (should order ~5-6 packs of 10, not 16 packs)
    assert fc["recommended_packs"] <= 7


def test_forecaster_backward_compatible_keys():
    """Ensures legacy orchestrator keys exist alongside the new OR keys."""
    sales_history = [5.0, 4.0, 6.0, 5.0, 5.0]
    fc = DemandForecaster().forecast_item(
        sales_history=sales_history,
        lead_time_days=2,
        units_per_pack=24
    )

    # Legacy keys
    assert "recommended_qty" in fc
    assert "daily_demand_forecast" in fc
    assert "at_risk_before_delivery" in fc
    # New OR keys
    assert "recommended_packs" in fc
    assert "units_per_pack" in fc
    assert fc["units_per_pack"] == 24