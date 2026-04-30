"""
TEST — Algorithm Service
Run: python tests/test_algorithm_service.py
"""

import sys
import os
import math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.algorithm_service import _sanitize_for_json, AlgorithmService


def test_sanitize_for_json_handles_inf_nan():
    payload = {
        "value": float("inf"),
        "nested": [1.0, float("nan"), {"inner": float("-inf")}]
    }
    sanitized = _sanitize_for_json(payload)
    assert sanitized["value"] is None
    assert sanitized["nested"][1] is None
    assert sanitized["nested"][2]["inner"] is None


def test_default_system_costs_for_india():
    class DummyPlan:
        location = "Delhi"

    costs = AlgorithmService._default_system_costs(DummyPlan)
    assert costs["solar_price_per_kw"] == 45000.0
    assert costs["battery_price_per_kwh"] == 12000.0


def test_default_system_costs_for_unknown_region():
    class DummyPlan:
        location = "Mars"

    costs = AlgorithmService._default_system_costs(DummyPlan)
    assert costs["solar_price_per_kw"] == 1000.0
    assert costs["battery_price_per_kwh"] == 300.0


if __name__ == "__main__":
    test_sanitize_for_json_handles_inf_nan()
    print("✅ test_sanitize_for_json_handles_inf_nan passed")
