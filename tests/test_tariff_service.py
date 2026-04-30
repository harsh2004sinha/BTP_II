"""
TEST — Tariff Service
Run: python tests/test_tariff_service.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tariff_service import TariffService


def test_india_tariff_lookup():
    tariff = TariffService.get_tariff("Delhi")
    assert tariff["currency"] == "INR"
    assert tariff["name"] == "India Average Tariff"
    assert tariff["type"] == "tiered"
    assert len(tariff["tiers"]) >= 4


def test_india_keyword_lookup():
    tariff = TariffService.get_tariff("Bengaluru")
    assert tariff["currency"] == "INR"
    assert tariff["name"] == "India Average Tariff"


def test_default_tariff_lookup():
    tariff = TariffService.get_tariff("Unknown Place")
    assert tariff["currency"] == "USD"
    assert tariff["name"] == "Generic Tariff"


def test_bill_average_rate_for_region():
    bill = TariffService.calculate_bill(15000.0, "Delhi")
    assert bill["currency"] == "INR"
    assert bill["average_rate"] > 5.0
    assert bill["total_bill"] > bill["energy_charge"]


def test_grid_cost_fallback_uses_location():
    from app.services.algorithm_service import AlgorithmService

    class DummyPlan:
        location = "Delhi"

    plan = DummyPlan()
    rate = AlgorithmService._grid_cost_for_plan(plan, monthly_kwh=15000.0)
    assert rate > 5.0
    assert rate < 20.0
