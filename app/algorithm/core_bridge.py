"""
app/algorithm/core_bridge.py
============================
Bridge between backend and core engine.
Backend ONLY talks to core through this file.
Core NEVER imports from backend.
"""

import sys
import os

# Add project root to path so core can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from core.pipeline import CorePipeline

# ============================================================
# SINGLETON PIPELINE
# One pipeline per user plan (stored in memory or DB)
# ============================================================

# Simple in-memory store: {plan_id: CorePipeline}
_pipelines: dict = {}


def get_pipeline(plan_id: str) -> CorePipeline:
    """
    Get or create pipeline for a plan.
    Each plan gets its own pipeline instance.
    """
    if plan_id not in _pipelines:
        _pipelines[plan_id] = CorePipeline()
    return _pipelines[plan_id]


def clear_pipeline(plan_id: str):
    """Remove pipeline when plan is deleted."""
    if plan_id in _pipelines:
        del _pipelines[plan_id]


# ============================================================
# FUNCTION 1 — PLANNING
# Called by: POST /results/optimize/{plan_id}
# ============================================================

def run_planning(plan_data: dict) -> dict:
    """
    Run full planning optimization for a user plan.

    Args:
        plan_data = {
            # From plans table
            "plan_id"              : "uuid-string",
            "budget"               : 150000,
            "roof_area_m2"         : 500,
            "location"             : "Delhi",

            # From weather service
            "irradiance_wm2"       : 600,

            # From consumption table
            "monthly_consumption_kwh": 15000,
            # OR
            "monthly_data": [
                {"month": "Jan", "kwh": 14000},
                ...
            ],

            # From tariff service
            "grid_cost_per_kwh"    : 0.12,

            # User preferences (optional)
            "solar_price_per_kw"   : 1000,
            "battery_price_per_kwh": 300,
            "battery_option"       : "auto",
            "solar_option"         : "yes",
            "day_type"             : "weekday"
        }

    Returns:
        Complete plan dict from core
    """
    plan_id  = plan_data.get("plan_id", "default")
    pipeline = get_pipeline(plan_id)

    # Build core input format
    core_input = {
        "budget"                : float(plan_data.get("budget", 100000)),
        "solar_price_per_kw"    : float(plan_data.get("solar_price_per_kw", 1000)),
        "battery_price_per_kwh" : float(plan_data.get("battery_price_per_kwh", 300)),
        "roof_area_m2"          : float(plan_data.get("roof_area_m2", 500)),
        "irradiance_wm2"        : float(plan_data.get("irradiance_wm2", 500)),
        "location"              : str(plan_data.get("location", "Unknown")),
        "grid_cost_per_kwh"     : float(plan_data.get("grid_cost_per_kwh", 0.12)),
        "battery_option"        : str(plan_data.get("battery_option", "auto")),
        "solar_option"          : str(plan_data.get("solar_option", "yes")),
        "day_type"              : str(plan_data.get("day_type", "weekday")),
    }

    # Monthly data — handle both formats
    if "monthly_data" in plan_data and plan_data["monthly_data"]:
        core_input["monthly_data"] = plan_data["monthly_data"]
    else:
        core_input["monthly_consumption_kwh"] = float(
            plan_data.get("monthly_consumption_kwh", 10000))

    # Run core planning
    plan = pipeline.create_plan(core_input)

    # Convert to backend-friendly format
    return _format_plan_result(plan, plan_id)


def _format_plan_result(plan: dict, plan_id: str) -> dict:
    """
    Convert core plan output to backend result format.
    Matches the results table schema.
    """
    return {
        # Matches results table columns
        "plan_id"             : plan_id,
        "solar_size_kw"       : plan.get("recommended_solar_kw", 0),
        "battery_size_kwh"    : plan.get("recommended_battery_kwh", 0),
        "solar_area_m2"       : plan.get("recommended_solar_area_m2", 0),
        "roi"                 : plan.get("roi_years", 0),
        "saving"              : plan.get("annual_savings", 0),
        "total_cost"          : plan.get("investment", 0),
        "payback_period"      : plan.get("payback_years", 0),
        "npv_10yr"            : plan.get("npv_10yr", 0),
        "is_viable"           : plan.get("is_viable", True),

        # Energy info
        "daily_kwh"           : plan.get("daily_kwh", 0),
        "peak_load_kw"        : plan.get("peak_load_kw", 0),
        "monthly_kwh"         : plan.get("monthly_kwh", 0),
        "baseline_daily_cost" : plan.get("baseline_daily_cost", 0),
        "optimized_daily_cost": plan.get("optimized_daily_cost", 0),
        "daily_savings"       : plan.get("daily_savings", 0),

        # Flags
        "battery_included"    : plan.get("battery_included", False),
        "solar_included"      : plan.get("solar_included", True),

        # Chart data (JSON)
        "graph_data"          : {
            "daily_load_profile" : plan.get("daily_load_profile", []),
            "sample_schedule"    : plan.get("sample_24h_schedule", []),
            "top_5_options"      : plan.get("top_5_options", []),
            "solar_details"      : plan.get("solar_details", {})
        },

        # Raw output
        "raw_output"          : plan,
        "status"              : "success"
    }


# ============================================================
# FUNCTION 2 — PREDICTION (every 15 min)
# Called by: GET /prediction/{plan_id}
#            Scheduler every 15 min
# ============================================================

def run_prediction(predict_data: dict) -> list:
    """
    Run 15-min prediction for a plan.

    Args:
        predict_data = {
            "plan_id"        : "uuid",
            "hour_of_day"    : 14.5,
            "day_type"       : "weekday",

            # Real sensor values (if available)
            "soc"            : 0.65,       # None = use simulated
            "pv_actual_kw"   : 85.3,       # None = use simulated
            "load_actual_kw" : 650.0,      # None = use simulated

            # Weather
            "cloud_factor"   : 0.9,

            # Grid price (constant from user)
            "grid_price"     : 0.12
        }

    Returns:
        List of prediction records (matches predictions table)
    """
    plan_id  = predict_data.get("plan_id", "default")
    pipeline = get_pipeline(plan_id)

    # Build core input
    current_data = {
        "hour_of_day"    : float(predict_data.get("hour_of_day", 12.0)),
        "day_type"       : str(predict_data.get("day_type", "weekday")),
        "cloud_factor"   : float(predict_data.get("cloud_factor", 1.0)),
        "grid_price"     : predict_data.get("grid_price", None)
    }

    # Only include sensor readings if provided
    if predict_data.get("soc") is not None:
        current_data["soc"] = float(predict_data["soc"])
    if predict_data.get("pv_actual_kw") is not None:
        current_data["pv_actual_kw"] = float(predict_data["pv_actual_kw"])
    if predict_data.get("load_actual_kw") is not None:
        current_data["load_actual_kw"] = float(predict_data["load_actual_kw"])

    # Run core prediction
    result = pipeline.predict(current_data)

    # Format for database
    return _format_prediction_result(result, plan_id)


def _format_prediction_result(result: dict, plan_id: str) -> dict:
    """
    Convert core prediction output to backend prediction format.
    Matches the predictions table schema.
    """
    return {
        # Matches predictions table columns
        "plan_id"        : plan_id,
        "hour"           : result.get("hour", 0),
        "solar_kw"       : result.get("pv_used_kw", 0),
        "battery_soc"    : round(result.get("current_soc", 0) * 100, 1),
        "grid_cost"      : result.get("step_cost", 0),
        "grid_import_kw" : result.get("grid_import_kw", 0),
        "grid_export_kw" : result.get("grid_export_kw", 0),
        "consumption_kw" : result.get("current_load_kw", 0),
        "action"         : result.get("action_name", "grid_only"),

        # Extra fields from core (bonus)
        "charge_kw"      : result.get("charge_kw", 0),
        "discharge_kw"   : result.get("discharge_kw", 0),
        "pv_kw"          : result.get("current_pv_kw", 0),
        "explanation"    : result.get("explanation", ""),
        "reason"         : result.get("reason", ""),
        "top_factor"     : result.get("top_factor", ""),
        "decision_text"  : result.get("decision_text", ""),
        "grid_price"     : result.get("grid_price", 0),
        "tariff_period"  : result.get("tariff_period", ""),
        "carbon_kg"      : result.get("carbon_kg_step", 0),
        "predicted_next_4h": result.get("predicted_next_4h", [])
    }


# ============================================================
# FUNCTION 3 — CHECK PIPELINE STATUS
# Called by: health check endpoints
# ============================================================

def get_pipeline_status(plan_id: str) -> dict:
    """Check if pipeline exists and has a plan."""
    if plan_id not in _pipelines:
        return {
            "exists"      : False,
            "has_plan"    : False,
            "plan_summary": None
        }

    pipeline = _pipelines[plan_id]
    return {
        "exists"      : True,
        "has_plan"    : pipeline.plan is not None,
        "plan_summary": pipeline.get_plan_summary()
    }