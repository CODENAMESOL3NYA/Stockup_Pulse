"""
Tests for WAPE Metric & Forecasting Accuracy
Ensures honest and transparent reporting of Model WAPE vs Baseline WAPE.
"""

import numpy as np
from stockup_pulse.forecast.forecaster import calculate_wape, DemandForecaster

def test_wape_calculation():
    actuals = np.array([10.0, 20.0, 30.0])
    predictions = np.array([12.0, 18.0, 33.0])
    # sum(|actual - pred|) = |10-12| + |20-18| + |30-33| = 2 + 2 + 3 = 7
    # sum(actual) = 60
    # WAPE = 7 / 60 = 0.116666...
    wape = calculate_wape(actuals, predictions)
    assert abs(wape - (7.0 / 60.0)) < 1e-4

def test_forecaster_transparency():
    forecaster = DemandForecaster()
    eval_res = forecaster.evaluate_wape()
    
    assert "model_wape" in eval_res
    assert "baseline_wape" in eval_res
    assert eval_res["model_wape"] < eval_res["baseline_wape"]
    assert eval_res["forecast_accuracy"] > eval_res["baseline_accuracy"]
    assert eval_res["dataset_type"] == "illustrative_fixture"
    assert eval_res["sample_count"] == 10
