"""
TEST — Core Pipeline
Run: python tests/test_pipeline.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import CorePipeline


def test_pipeline():
    print("\n" + "="*60)
    print("  TEST — CORE PIPELINE")
    print("="*60)

    pipeline = CorePipeline()

    # ---- Test 1: Create Plan ----
    print("\n--- Test 1: Create Plan (user inputs) ---")

    user_inputs = {
        # Financial
        "budget"               : 150000,
        "solar_price_per_kw"   : 1000,
        "battery_price_per_kwh": 300,

        # Physical
        "roof_area_m2"         : 800,
        "irradiance_wm2"       : 600,
        "location"             : "Delhi",

        # Electricity
        "grid_cost_per_kwh"    : 0.12,

        # Monthly data (12 months)
        "monthly_data": [
            {"month": "Jan", "kwh": 14000},
            {"month": "Feb", "kwh": 13500},
            {"month": "Mar", "kwh": 13000},
            {"month": "Apr", "kwh": 14500},
            {"month": "May", "kwh": 16000},
            {"month": "Jun", "kwh": 17000},
            {"month": "Jul", "kwh": 16500},
            {"month": "Aug", "kwh": 16000},
            {"month": "Sep", "kwh": 15000},
            {"month": "Oct", "kwh": 14000},
            {"month": "Nov", "kwh": 13500},
            {"month": "Dec", "kwh": 14000},
        ],

        # Options
        "battery_option"       : "auto",
        "solar_option"         : "yes",
        "day_type"             : "weekday"
    }

    plan = pipeline.create_plan(user_inputs)

    print(f"\n  ✅ Plan created successfully")
    print(f"\n  📋 RECOMMENDED PLAN:")
    print(f"  {'─'*40}")
    print(f"  Solar Size      : {plan['recommended_solar_kw']} kW")
    print(f"  Solar Area      : {plan['recommended_solar_area_m2']:.1f} m²")
    print(f"  Battery Size    : {plan['recommended_battery_kwh']} kWh")
    print(f"  {'─'*40}")
    print(f"  Investment      : ${plan['investment']:,.2f}")
    print(f"  Annual Savings  : ${plan['annual_savings']:,.2f}")
    print(f"  ROI             : {plan['roi_years']} years")
    print(f"  NPV (10yr)      : ${plan.get('npv_10yr', 0):,.2f}")
    print(f"  {'─'*40}")
    print(f"  Monthly kWh     : {plan['monthly_kwh']:,.1f}")
    print(f"  Daily kWh       : {plan['daily_kwh']:,.1f}")
    print(f"  Peak Load       : {plan['peak_load_kw']:.1f} kW")
    print(f"  {'─'*40}")
    print(f"  Baseline Cost/day: ${plan['baseline_daily_cost']:.4f}")
    print(f"  Optimized Cost/d : ${plan['optimized_daily_cost']:.4f}")
    print(f"  Daily Savings    : ${plan['daily_savings']:.4f}")
    print(f"  {'─'*40}")
    print(f"  Battery included: {plan['battery_included']}")
    print(f"  Solar included  : {plan['solar_included']}")
    print(f"  Is viable       : {plan['is_viable']}")

    # Top 5 options
    print(f"\n  📊 TOP 5 OPTIONS:")
    for i, opt in enumerate(plan['top_5_options'][:5]):
        print(f"  {i+1}. Solar={opt['solar_kw']}kW "
              f"Battery={opt['battery_kwh']}kWh "
              f"ROI={opt['roi_years']}yr "
              f"Savings=${opt['annual_savings']:,.0f}")

    # Sample schedule
    schedule = plan["sample_24h_schedule"]
    print(f"\n  📅 SAMPLE 24H SCHEDULE:")
    print(f"  Steps: {len(schedule)}")
    for s in schedule[::8]:   # Every 2 hours
        print(f"  Hour {s['hour']:5.1f} | "
              f"SOC {s['soc']:.0%} | "
              f"PV {s['pv_kw']:6.1f}kW | "
              f"Load {s['load_kw']:6.1f}kW | "
              f"{s['action']:25s} | "
              f"${s['cost']:.5f}")

    assert plan["plan_created"], "❌ Plan not created"
    assert plan["recommended_solar_kw"] >= 0, "❌ Invalid solar size"
    assert plan["recommended_battery_kwh"] >= 0, "❌ Invalid battery size"
    assert plan["roi_years"] > 0, "❌ Invalid ROI"

    # ---- Test 2: Prediction Mode ----
    print(f"\n{'─'*60}")
    print("--- Test 2: Prediction (every 15 min) ---")

    test_cases = [
        {
            "hour_of_day"    : 10.0,
            "day_type"       : "weekday",
            "soc"            : 0.65,
            "pv_actual_kw"   : 80.0,
            "load_actual_kw" : 600.0,
            "cloud_factor"   : 0.9,
            "grid_price"     : 0.12,
            "label"          : "Morning (solar available)"
        },
        {
            "hour_of_day"    : 19.0,
            "day_type"       : "weekday",
            "soc"            : 0.70,
            "pv_actual_kw"   : 0.0,
            "load_actual_kw" : 750.0,
            "cloud_factor"   : 0.0,
            "grid_price"     : 0.12,
            "label"          : "Evening (no solar, high load)"
        },
        {
            "hour_of_day"    : 2.0,
            "day_type"       : "weekday",
            "soc"            : 0.40,
            "pv_actual_kw"   : 0.0,
            "load_actual_kw" : 220.0,
            "cloud_factor"   : 0.0,
            "grid_price"     : 0.12,
            "label"          : "Night (low load, low SOC)"
        },
    ]

    for tc in test_cases:
        label = tc.pop("label")
        result = pipeline.predict(tc)

        print(f"\n  🕐 {label}")
        print(f"     Action     : {result['action_name']}")
        print(f"     Decision   : {result['description']}")
        print(f"     Charge kW  : {result['charge_kw']}")
        print(f"     Discharge  : {result['discharge_kw']}")
        print(f"     Grid import: {result['grid_import_kw']}")
        print(f"     Step cost  : ${result['step_cost']:.6f}")
        print(f"     Explanation: {result['explanation'][:80]}...")
        print(f"     Top factor : {result['top_factor']}")

        assert result["action_name"] is not None, "❌ No action returned"
        assert result["step_cost"] >= 0, "❌ Negative cost"

    print(f"\n  ✅ Prediction mode working")

    # ---- Test 3: No battery plan ----
    print(f"\n{'─'*60}")
    print("--- Test 3: Plan with no battery ---")

    no_batt_inputs = {
        "budget"               : 50000,
        "solar_price_per_kw"   : 1000,
        "battery_price_per_kwh": 300,
        "roof_area_m2"         : 300,
        "irradiance_wm2"       : 550,
        "grid_cost_per_kwh"    : 0.12,
        "monthly_consumption_kwh": 8000,
        "battery_option"       : "no",
        "solar_option"         : "yes"
    }

    plan_no_batt = pipeline.create_plan(no_batt_inputs)
    print(f"  Solar: {plan_no_batt['recommended_solar_kw']} kW")
    print(f"  Battery: {plan_no_batt['recommended_battery_kwh']} kWh")
    print(f"  Battery included: {plan_no_batt['battery_included']}")
    assert plan_no_batt["recommended_battery_kwh"] == 0.0, \
        "❌ Battery should be 0 when option=no"
    print(f"  ✅ No battery plan working")

    # ---- Test 4: Plan summary ----
    print(f"\n{'─'*60}")
    print("--- Test 4: Plan summary ---")
    summary = pipeline.get_plan_summary()
    print(f"  Summary: {summary}")
    assert "solar_kw" in summary, "❌ Missing solar_kw in summary"
    print(f"  ✅ Plan summary working")

    print("\n" + "="*60)
    print("  ✅ ALL PIPELINE TESTS PASSED")
    print("="*60)


if __name__ == "__main__":
    test_pipeline()