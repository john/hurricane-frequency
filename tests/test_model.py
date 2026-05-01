import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from runner import run


MIAMI = {"latitude": 25.7617, "longitude": -80.1918, "name": "Miami, FL"}
WINDOW = {"start_year": 1900, "end_year": 2024}


def test_smoke_miami_cat4():
    out = run({
        "location": MIAMI,
        "radius_km": 100,
        "min_saffir_simpson_category": 4,
        "observation_window": WINDOW,
    })
    expected_keys = {
        "lambda_annual",
        "probability_at_least_one_per_year",
        "historical_event_count",
        "observation_years",
        "expected_events_in_3yr_term",
        "metadata",
    }
    assert expected_keys.issubset(out.keys())
    assert math.isfinite(out["lambda_annual"])
    assert out["lambda_annual"] >= 0


def test_lower_category_more_frequent():
    cat1 = run({
        "location": MIAMI,
        "radius_km": 100,
        "min_saffir_simpson_category": 1,
        "observation_window": WINDOW,
    })
    cat4 = run({
        "location": MIAMI,
        "radius_km": 100,
        "min_saffir_simpson_category": 4,
        "observation_window": WINDOW,
    })
    assert cat1["lambda_annual"] > cat4["lambda_annual"]


def test_far_from_atlantic_returns_zero():
    out = run({
        "location": {"latitude": 0.0, "longitude": -150.0},
        "radius_km": 100,
        "min_saffir_simpson_category": 1,
        "observation_window": WINDOW,
    })
    assert out["historical_event_count"] == 0
    assert out["lambda_annual"] == 0.0
