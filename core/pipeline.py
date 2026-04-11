"""
core/pipeline.py
================
Main entry point for backend.
Handles two modes:
    1. PLANNING  — user gives inputs, get best plan
    2. PREDICTION — every 15 min, get best action
"""

import numpy as np
from typing import Optional

from .models.battery_model   import BatteryModel
from .models.pv_model        import PVModel
from .models.load_model      import LoadModel
from .twin.twin_core         import DigitalTwin
from .twin.twin_state        import TwinState
from .optimizer.solver       import Solver
from .optimizer.sizing       import SystemSizer
from .optimizer.cost_function import CostFunction
from .explain.explain_core   import ExplainCore
from .policy.policy_manager  import PolicyManager
from .policy.tariff          import TariffManager


class CorePipeline:
    """
    Master pipeline — connects all core layers.

    Backend calls this. Never calls layers directly.

    Two modes:
        plan    = CorePipeline.create_plan(user_inputs)
        predict = CorePipeline.predict(current_data)
    """

    def __init__(self):
        self.pv_model    = PVModel()
        self.load_model  = LoadModel()
        self.explainer   = ExplainCore()

        # These are set after plan is created
        self.twin    : Optional[DigitalTwin]   = None
        self.solver  : Optional[Solver]        = None
        self.policy  : Optional[PolicyManager] = None
        self.plan    : Optional[dict]          = None

    # ================================================================
    # MODE 1 — PLANNING
    # Called once when user submits their inputs
    # ================================================================

    def create_plan(self, user_inputs: dict) -> dict:
        """
        Create best energy plan for user.

        Args:
            user_inputs = {
                # Financial
                "budget"              : 100000,   # $ total budget
                "solar_price_per_kw"  : 1000,     # $ per kW peak
                "battery_price_per_kwh": 300,     # $ per kWh

                # Location & Physical
                "roof_area_m2"        : 500,      # m² available
                "irradiance_wm2"      : 600,      # W/m² average
                "location"            : "Delhi",  # city name

                # Electricity
                "grid_cost_per_kwh"   : 0.12,     # $/kWh constant
                "monthly_consumption_kwh": 15000, # single month
                # OR
                "monthly_data": [                 # 12 months
                    {"month": "Jan", "kwh": 14000},
                    {"month": "Feb", "kwh": 13500},
                    ...
                ],

                # Options
                "battery_option"      : "auto",   # "yes"/"no"/"auto"
                "solar_option"        : "yes",    # "yes"/"no"
                "day_type"            : "weekday"
            }

        Returns:
            Complete plan dict with:
                recommended_solar_kw
                recommended_battery_kwh
                recommended_area_m2
                daily_load_profile
                annual_savings
                roi_years
                investment
                daily_schedule
                explanation
        """

        print("[Pipeline] Creating plan...")

        # ---- Step 1: Extract inputs ----
        budget               = user_inputs.get("budget", 100000)
        solar_price_per_kw   = user_inputs.get("solar_price_per_kw", 1000)
        battery_price_per_kwh= user_inputs.get("battery_price_per_kwh", 300)
        roof_area_m2         = user_inputs.get("roof_area_m2", 500)
        irradiance_wm2       = user_inputs.get("irradiance_wm2", 600)
        grid_cost            = user_inputs.get("grid_cost_per_kwh", 0.12)
        battery_option       = user_inputs.get("battery_option", "auto")
        solar_option         = user_inputs.get("solar_option", "yes")
        day_type             = user_inputs.get("day_type", "weekday")

        # ---- Step 2: Get monthly consumption ----
        monthly_kwh = self._get_monthly_kwh(user_inputs)
        print(f"[Pipeline] Monthly consumption: {monthly_kwh:.1f} kWh")

        # ---- Step 3: Build load profile ----
        load_profile = self.load_model.from_monthly_bill(
            monthly_units_kwh = monthly_kwh,
            day_type          = day_type,
            dt_hours          = 0.25
        )
        loads    = [p["load_kw"]    for p in load_profile]
        daily_kwh = sum(p["energy_kwh"] for p in load_profile)
        peak_load = max(loads)
        print(f"[Pipeline] Daily load: {daily_kwh:.1f} kWh, Peak: {peak_load:.1f} kW")

        # ---- Step 4: Solar sizing ----
        solar_sizing = self.pv_model.size_system(
            target_kwh_per_day     = daily_kwh * 0.7,  # Cover 70% with solar
            avg_irradiance_wm2     = irradiance_wm2,
            peak_sun_hours         = self._irradiance_to_sun_hours(irradiance_wm2),
            roof_area_available_m2 = roof_area_m2
        )
        print(f"[Pipeline] Solar sizing: "
              f"{solar_sizing['peak_power_kw']:.1f} kW, "
              f"{solar_sizing['recommended_area_m2']:.1f} m²")

        # ---- Step 5: System sizing (solar + battery combined) ----
        # Build solar range based on roof area
        max_solar_kw = solar_sizing["peak_power_kw"]
        solar_range  = self._build_solar_range(max_solar_kw)

        # Build battery range based on option
        battery_range = self._build_battery_range(
            battery_option, daily_kwh)

        sizer = SystemSizer(
            pv_model              = self.pv_model,
            load_model            = self.load_model,
            solar_price_per_kw    = solar_price_per_kw,
            battery_price_per_kwh = battery_price_per_kwh,
            grid_price            = grid_cost,
            feed_in_tariff        = grid_cost * 0.5,
            roof_area_m2          = roof_area_m2
        )

        sizing_result = sizer.run_sizing(
            monthly_kwh       = monthly_kwh,
            budget            = budget,
            solar_range_kw    = solar_range,
            battery_range_kwh = battery_range,
            day_type          = day_type,
            peak_irr          = irradiance_wm2
        )
        print(f"[Pipeline] Best plan: "
              f"Solar={sizing_result['best_solar_kw']} kW, "
              f"Battery={sizing_result['best_battery_kwh']} kWh")

        # ---- Step 6: ROI calculation ----
        roi_detail = sizer.calculate_roi(
            investment     = sizing_result["investment"],
            annual_savings = sizing_result["annual_savings"]
        )

        # ---- Step 7: Build twin with the chosen plan ----
        best_solar_kw   = sizing_result["best_solar_kw"]
        best_battery_kwh = sizing_result["best_battery_kwh"]

        # Convert kW peak to area
        best_area_m2 = self._solar_kw_to_area(best_solar_kw)

        self.twin = DigitalTwin(
            battery_capacity_kwh = max(10.0, best_battery_kwh),
            pv_area_m2           = best_area_m2,
            base_load_kw         = min(loads) * 0.9,
            peak_load_kw         = peak_load * 1.1,
            initial_soc          = 0.50,
            mode                 = "simulation"
        )

        # ---- Step 8: Build solver with constant grid price ----
        tariff = TariffManager()
        # Override with user's constant grid cost
        tariff.tou_schedule = {
            "constant": {
                "hours": list(range(0, 24)),
                "price": grid_cost,
                "label": "Constant"
            }
        }
        tariff.feed_in_rate = grid_cost * 0.5

        self.policy = PolicyManager(tariff_manager=tariff)
        self.solver = Solver()

        # ---- Step 9: Generate sample 24h schedule ----
        sample_schedule = self._generate_sample_schedule(
            day_type     = day_type,
            cloud_factor = self._irradiance_to_cloud(irradiance_wm2)
        )

        # ---- Step 10: Assemble complete plan ----
        self.plan = {
            # System design
            "recommended_solar_kw"    : best_solar_kw,
            "recommended_solar_area_m2": best_area_m2,
            "recommended_battery_kwh" : best_battery_kwh,

            # Financial
            "investment"              : sizing_result["investment"],
            "annual_savings"          : sizing_result["annual_savings"],
            "roi_years"               : sizing_result["roi_years"],
            "payback_years"           : roi_detail.get("payback_years"),
            "npv_10yr"                : roi_detail.get("npv_10yr"),
            "is_viable"               : roi_detail.get("is_viable", True),
            "baseline_daily_cost"     : sizing_result["baseline_daily_cost"],
            "optimized_daily_cost"    : sizing_result["best_daily_cost"],
            "daily_savings"           : sizing_result["daily_savings"],

            # Load profile
            "daily_load_profile"      : load_profile,
            "daily_kwh"               : round(daily_kwh, 2),
            "peak_load_kw"            : round(peak_load, 2),
            "monthly_kwh"             : round(monthly_kwh, 2),

            # Solar info
            "solar_details"           : solar_sizing,
            "irradiance_wm2"          : irradiance_wm2,
            "roof_area_m2"            : roof_area_m2,

            # Grid info
            "grid_cost_per_kwh"       : grid_cost,

            # Sample schedule
            "sample_24h_schedule"     : sample_schedule,

            # Top 5 alternatives
            "top_5_options"           : sizing_result.get("top_5_options", []),

            # Status
            "plan_created"            : True,
            "battery_included"        : best_battery_kwh > 0,
            "solar_included"          : best_solar_kw > 0,
        }

        print("[Pipeline] Plan created successfully.")
        return self.plan

    # ================================================================
    # MODE 2 — PREDICTION (every 15 minutes)
    # Called repeatedly by scheduler
    # ================================================================

    def predict(self, current_data: dict) -> dict:
        """
        Get best action for current moment.
        Called every 15 minutes by scheduler.

        CLOSED-LOOP ARCHITECTURE:
          1. Read current real-time inputs (hour, cloud, pv_actual, load_actual).
          2. Apply PREVIOUS optimizer action's charge/discharge to update battery SOC.
          3. Run Digital Twin to get full state (PV, load, SOC, forecasts).
          4. Run Optimizer on that state to get best action.
          5. Return the decision — next call will apply it to battery first.

        This ensures SOC only changes when the optimizer actually commands
        charge/discharge, not due to phantom noise or out-of-order calls.
        """

        if self.twin is None:
            return {
                "error"  : "No plan created yet. Call create_plan() first.",
                "action" : "grid_only"
            }

        hour       = float(current_data.get("hour_of_day", 12.0))
        day_type   = current_data.get("day_type", "weekday")
        soc        = current_data.get("soc", None)
        pv_actual  = current_data.get("pv_actual_kw", None)
        load_act   = current_data.get("load_actual_kw", None)
        cloud      = float(current_data.get("cloud_factor", 1.0))
        grid_price = current_data.get("grid_price", None)

        # ── Step 1: Apply the LAST optimizer decision to the battery ──────
        # These are the actual commands that were decided last timestep.
        # They now actually move the SOC.
        last = getattr(self, "_last_action", {})
        prev_charge    = float(last.get("charge_kw",    0.0))
        prev_discharge = float(last.get("discharge_kw", 0.0))

        # If a real sensor SOC reading is provided, it overrides simulation
        if soc is not None:
            self.twin.battery.soc = float(soc)
            # Also reset estimator to match
            self.twin.estimator.reset(initial_soc=float(soc))
            prev_charge    = 0.0   # don't double-apply
            prev_discharge = 0.0

        # ── Step 2: Advance Digital Twin with last action's battery cmds ──
        state = self.twin.twin_step(
            hour_of_day    = hour,
            day_type       = day_type,
            irradiance     = self._cloud_to_irradiance(hour, cloud),
            grid_price     = grid_price,
            cloud_factor   = cloud,
            charge_kw      = prev_charge,     # ← feeds back last decision
            discharge_kw   = prev_discharge,  # ← feeds back last decision
        )

        # ── Step 3: Override with real sensor readings if available ───────
        if pv_actual is not None:
            state.pv_power_kw     = float(pv_actual)
            state.pv_available_kw = float(pv_actual)
        if load_act is not None:
            state.load_kw = float(load_act)

        # ── Step 4: Run optimizer on this state ───────────────────────────
        opt_result  = self.solver.optimize(state)
        best_action = opt_result.get("best_action", {})

        # Store this decision so next call can apply it to battery
        self._last_action = best_action

        # ── Step 5: Policy + Explain ──────────────────────────────────────
        pol_result   = self.policy.evaluate(
            state       = state,
            action      = best_action,
            cycle_count = state.cycle_count
        )
        final_action = pol_result["final_action"]

        cost_bd     = best_action.get("cost_breakdown", {})
        explanation = self.explainer.explain(state, best_action, cost_bd)

        predicted_costs = self._predict_next_hours(state, n_hours=4)

        return {
            # Main decision
            "action_name"    : best_action.get("action_name", "grid_only"),
            "description"    : best_action.get("description", ""),
            "charge_kw"      : final_action.get("charge_kw",      0.0),
            "discharge_kw"   : final_action.get("discharge_kw",   0.0),
            "grid_import_kw" : final_action.get("grid_import_kw", 0.0),
            "grid_export_kw" : final_action.get("grid_export_kw", 0.0),
            "pv_used_kw"     : state.pv_power_kw,

            # Current state (AFTER applying last action to battery)
            "current_soc"    : round(state.soc, 4),
            "current_pv_kw"  : round(state.pv_power_kw, 2),
            "current_load_kw": round(state.load_kw, 2),
            "grid_price"     : round(state.grid_price, 4),
            "hour"           : hour,

            # Cost
            "step_cost"      : round(cost_bd.get("total_cost", 0.0), 6),
            "cost_breakdown" : cost_bd,

            # Explanation
            "explanation"    : explanation["full_explanation"],
            "reason"         : explanation["reason"],
            "top_factor"     : explanation["top_factor"],
            "decision_text"  : explanation["decision"],

            # Future
            "predicted_next_4h": predicted_costs,

            # Carbon
            "carbon_kg_step" : round(
                final_action.get("grid_import_kw", 0.0) * 0.40 * 0.25, 4),

            # Policy
            "tariff_period"  : pol_result.get("tariff_period", ""),
            "rule_violations": pol_result.get("rule_violations", [])
        }


    # ================================================================
    # HELPER FUNCTIONS
    # ================================================================

    def _get_monthly_kwh(self, user_inputs: dict) -> float:
        """
        Extract representative monthly kWh from user inputs.
        Handles both single value and 12-month data.
        """
        # Option 1: 12 months of data → use average
        monthly_data = user_inputs.get("monthly_data", None)
        if monthly_data and len(monthly_data) > 0:
            total = sum(m.get("kwh", 0) for m in monthly_data)
            return total / len(monthly_data)

        # Option 2: Single monthly value
        return float(user_inputs.get("monthly_consumption_kwh", 10000))

    def _build_solar_range(self, max_kw: float) -> list:
        """Build solar size options to test."""
        step = max(10.0, max_kw / 6)
        sizes = [0.0]
        kw = step
        while kw <= max_kw + step:
            sizes.append(round(kw, 0))
            kw += step
        return sizes

    def _build_battery_range(
        self,
        option    : str,
        daily_kwh : float
    ) -> list:
        """Build battery size options based on user preference."""
        if option == "no":
            return [0.0]   # No battery

        if option == "yes":
            # Force battery — range from small to large
            return [
                round(daily_kwh * f, 0)
                for f in [0.1, 0.2, 0.3, 0.4, 0.5]
            ]

        # "auto" — test with and without
        return [
            0.0,
            round(daily_kwh * 0.1, 0),
            round(daily_kwh * 0.2, 0),
            round(daily_kwh * 0.3, 0),
            round(daily_kwh * 0.4, 0),
        ]

    def _solar_kw_to_area(self, solar_kw: float) -> float:
        """Convert peak kW to panel area in m²."""
        if solar_kw <= 0:
            return 0.0
        return solar_kw * 1000.0 / (self.pv_model.base_efficiency * 1000.0)

    def _irradiance_to_sun_hours(self, irradiance_wm2: float) -> float:
        """Convert average irradiance to peak sun hours."""
        # Typical range: 400 W/m² avg → 4h, 700 W/m² → 7h
        return max(2.0, min(8.0, irradiance_wm2 / 100.0))

    def _irradiance_to_cloud(self, irradiance_wm2: float) -> float:
        """Convert irradiance to cloud factor (0-1)."""
        return min(1.0, irradiance_wm2 / 900.0)

    def _cloud_to_irradiance(
        self,
        hour        : float,
        cloud_factor: float
    ) -> float:
        """Convert hour + cloud factor to irradiance."""
        if 6.0 <= hour <= 18.0:
            angle = np.pi * (hour - 6.0) / 12.0
            return max(0.0, 900.0 * np.sin(angle) * cloud_factor)
        return 0.0

    def _generate_sample_schedule(
        self,
        day_type    : str   = "weekday",
        cloud_factor: float = 0.9
    ) -> list:
        """Generate sample 24h schedule for the plan (closed-loop simulation)."""
        if self.twin is None:
            return []

        self.twin.reset(initial_soc=0.50)
        results = []

        # Start with no action
        prev_charge    = 0.0
        prev_discharge = 0.0

        for t in range(96):
            hour  = t * 0.25

            # Apply PREVIOUS action's battery commands when stepping twin
            state = self.twin.twin_step(
                hour_of_day  = hour,
                day_type     = day_type,
                cloud_factor = cloud_factor,
                charge_kw    = prev_charge,
                discharge_kw = prev_discharge,
            )

            opt    = self.solver.optimize(state)
            action = opt.get("best_action", {})

            # Store this timestep's decision for the next iteration
            prev_charge    = float(action.get("charge_kw",    0.0))
            prev_discharge = float(action.get("discharge_kw", 0.0))

            results.append({
                "timestep"    : t,
                "hour"        : round(hour, 2),
                "soc"         : round(state.soc, 4),
                "pv_kw"       : round(state.pv_power_kw, 2),
                "load_kw"     : round(state.load_kw, 2),
                "action"      : action.get("action_name", "grid_only"),
                "charge_kw"   : round(prev_charge, 4),
                "discharge_kw": round(prev_discharge, 4),
                "cost"        : round(
                    action.get("cost_breakdown", {}).get("total_cost", 0), 6)
            })

        self.twin.reset(initial_soc=0.50)
        return results


    def _predict_next_hours(
        self,
        state   : TwinState,
        n_hours : int = 4
    ) -> list:
        """Predict costs for next N hours."""
        if state.forecast is None:
            return []

        predictions = []
        steps = int(n_hours / 0.25)

        for i in range(min(steps, state.forecast.horizon)):
            predictions.append({
                "hour"        : round(state.hour_of_day + i * 0.25, 2),
                "pv_expected" : round(state.forecast.pv_mean[i], 2),
                "load_expected": round(state.forecast.load_mean[i], 2),
                "price"       : round(state.forecast.price_mean[i], 4)
            })

        return predictions

    # ================================================================
    # UTILITY — Get plan summary
    # ================================================================

    def get_plan_summary(self) -> dict:
        """Return short summary of current plan."""
        if self.plan is None:
            return {"error": "No plan created yet"}

        return {
            "solar_kw"       : self.plan["recommended_solar_kw"],
            "solar_area_m2"  : self.plan["recommended_solar_area_m2"],
            "battery_kwh"    : self.plan["recommended_battery_kwh"],
            "roi_years"      : self.plan["roi_years"],
            "annual_savings" : self.plan["annual_savings"],
            "investment"     : self.plan["investment"],
            "daily_kwh"      : self.plan["daily_kwh"],
            "peak_load_kw"   : self.plan["peak_load_kw"]
        }