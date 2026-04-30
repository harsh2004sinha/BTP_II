"""
core/pipeline.py
Main entry point for backend.
"""

import numpy as np
from typing import Optional

from .models.battery_model    import BatteryModel
from .models.pv_model         import PVModel
from .models.load_model       import LoadModel
from .twin.twin_core          import DigitalTwin
from .twin.twin_state         import TwinState
from .optimizer.solver        import Solver
from .optimizer.sizing        import SystemSizer
from .optimizer.cost_function import CostFunction
from .optimizer.degradation   import DegradationModel
from .explain.explain_core    import ExplainCore
from .policy.policy_manager   import PolicyManager
from .policy.tariff           import TariffManager


class CorePipeline:

    def __init__(self):
        self.pv_model   = PVModel()
        self.load_model = LoadModel()
        self.explainer  = ExplainCore()

        self.twin   : Optional[DigitalTwin]   = None
        self.solver : Optional[Solver]        = None
        self.policy : Optional[PolicyManager] = None
        self.plan   : Optional[dict]          = None

        # FIX BUG 7: Properly initialize instead of fragile getattr
        self._last_action       : dict  = {}
        # FIX BUG 12: Store location irradiance for use in prediction
        self._location_peak_irr : float = 900.0
        self._grid_cost         : float = 0.12

    # ================================================================
    # MODE 1 — PLANNING
    # ================================================================

    def create_plan(self, user_inputs: dict) -> dict:

        print("[Pipeline] Creating plan...")

        # ---- Step 1: Extract inputs ----
        budget                = user_inputs.get("budget", 100000)
        solar_price_per_kw    = user_inputs.get("solar_price_per_kw", 1000)
        battery_price_per_kwh = user_inputs.get("battery_price_per_kwh", 300)
        roof_area_m2          = user_inputs.get("roof_area_m2", 500)
        irradiance_wm2        = user_inputs.get("irradiance_wm2", 600)
        grid_cost             = user_inputs.get("grid_cost_per_kwh", 0.12)
        battery_option        = user_inputs.get("battery_option", "auto")
        solar_option          = user_inputs.get("solar_option", "yes")
        day_type              = user_inputs.get("day_type", "weekday")

        # FIX BUG 12 + 18: Store for use in prediction and twin
        self._location_peak_irr = float(irradiance_wm2)
        self._grid_cost         = float(grid_cost)

        # ---- Step 2: Get monthly consumption ----
        monthly_kwh = self._get_monthly_kwh(user_inputs)
        print(f"[Pipeline] Monthly consumption: {monthly_kwh:.1f} kWh")

        # ---- Step 3: Build load profile ----
        load_profile = self.load_model.from_monthly_bill(
            monthly_units_kwh = monthly_kwh,
            day_type          = day_type,
            dt_hours          = 0.25
        )
        loads     = [p["load_kw"]    for p in load_profile]
        daily_kwh = sum(p["energy_kwh"] for p in load_profile)
        peak_load = max(loads)
        print(f"[Pipeline] Daily load: {daily_kwh:.1f} kWh, Peak: {peak_load:.1f} kW")

        # ---- Step 4: Solar sizing ----
        # FIX BUG 6: Convert irradiance to peak_sun_hours correctly
        # irradiance_wm2 here is effective average W/m² (from algorithm_service)
        # peak_sun_hours = daily_ghi kWh/m²/day = irradiance * daylight_hours / 1000
        peak_sun_hours = self._irradiance_to_sun_hours(irradiance_wm2)

        solar_sizing = self.pv_model.size_system(
            target_kwh_per_day     = daily_kwh * 0.7,
            avg_irradiance_wm2     = irradiance_wm2,   # kept for reference
            peak_sun_hours         = peak_sun_hours,    # FIX: drives actual formula
            roof_area_available_m2 = roof_area_m2
        )
        print(f"[Pipeline] Solar sizing: "
              f"{solar_sizing['peak_power_kw']:.1f} kW, "
              f"{solar_sizing['recommended_area_m2']:.1f} m²")

        # ---- Step 5: System sizing ----
        max_solar_kw  = solar_sizing["peak_power_kw"]
        solar_range   = self._build_solar_range(
            max_kw = max_solar_kw,
            budget = budget,
            solar_price_per_kw = solar_price_per_kw
        )
        battery_range = self._build_battery_range(
            option = battery_option,
            daily_kwh = daily_kwh,
            budget = budget,
            battery_price_per_kwh = battery_price_per_kwh
        )

        sizer = SystemSizer(
            pv_model              = self.pv_model,
            load_model            = self.load_model,
            solar_price_per_kw    = solar_price_per_kw,
            battery_price_per_kwh = battery_price_per_kwh,
            grid_price            = grid_cost,
            feed_in_tariff        = 0.0, # NO EXPORT REVENUE
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

        # ---- Step 6: ROI ----
        roi_detail = sizer.calculate_roi(
            investment     = sizing_result["investment"],
            annual_savings = sizing_result["annual_savings"]
        )

        # ---- Step 7: Build twin with plan values ----
        best_solar_kw    = sizing_result["best_solar_kw"]
        best_battery_kwh = sizing_result["best_battery_kwh"]
        best_area_m2     = self._solar_kw_to_area(best_solar_kw)

        # FIX BUG 18: Pass location_peak_irr so twin doesn't hardcode 900
        self.twin = DigitalTwin(
            battery_capacity_kwh = best_battery_kwh,
            pv_area_m2           = best_area_m2,
            base_load_kw         = min(loads) * 0.9,
            peak_load_kw         = peak_load * 1.1,
            initial_soc          = 0.50,
            mode                 = "simulation",
            location_peak_irr    = float(irradiance_wm2),   # FIX BUG 18
        )

        # ---- Step 8: Build solver with actual battery capacity ----
        tariff = TariffManager()
        tariff.tou_schedule = {
            "constant": {
                "hours": list(range(0, 24)),
                "price": grid_cost,
                "label": "Constant"
            }
        }
        tariff.feed_in_rate = 0.0 # NO EXPORT REVENUE

        self.policy = PolicyManager(tariff_manager=tariff)

        # FIX BUG 20: Pass actual battery capacity to DegradationModel
        # OLD: Solver() → DegradationModel() → default 100 kWh always
        # NEW: DegradationModel uses real plan battery size
        self.solver = Solver(
            degradation_model = DegradationModel(
                battery_capacity_kwh = best_battery_kwh  # FIX BUG 20
            )
        )

        # ---- Step 9: Generate sample schedule ----
        sample_schedule = self._generate_sample_schedule(
            day_type  = day_type,
            peak_irr  = float(irradiance_wm2),  # pass raw irradiance, no cloud conversion
            grid_cost = grid_cost,
        )

        # ---- Step 10: Assemble plan ----
        self.plan = {
            "recommended_solar_kw"     : best_solar_kw,
            "recommended_solar_area_m2": best_area_m2,
            "recommended_battery_kwh"  : best_battery_kwh,
            "investment"               : sizing_result["investment"],
            "annual_savings"           : sizing_result["annual_savings"],
            "roi_years"                : sizing_result["roi_years"],
            "payback_years"            : roi_detail.get("payback_years"),
            "npv_10yr"                 : roi_detail.get("npv_10yr"),
            "is_viable"                : roi_detail.get("is_viable", True),
            "baseline_daily_cost"      : sizing_result["baseline_daily_cost"],
            "optimized_daily_cost"     : sizing_result["best_daily_cost"],
            "daily_savings"            : sizing_result["daily_savings"],
            "daily_load_profile"       : load_profile,
            "daily_kwh"                : round(daily_kwh, 2),
            "peak_load_kw"             : round(peak_load, 2),
            "monthly_kwh"              : round(monthly_kwh, 2),
            "solar_details"            : solar_sizing,
            "irradiance_wm2"           : irradiance_wm2,
            "roof_area_m2"             : roof_area_m2,
            "grid_cost_per_kwh"        : grid_cost,
            "sample_24h_schedule"      : sample_schedule,
            "top_5_options"            : sizing_result.get("top_5_options", []),
            "plan_created"             : True,
            "battery_included"         : best_battery_kwh > 0,
            "solar_included"           : best_solar_kw > 0,
        }

        print("[Pipeline] Plan created successfully.")
        return self.plan

    # ================================================================
    # MODE 2 — PREDICTION
    # ================================================================

    def predict(self, current_data: dict) -> dict:

        if self.twin is None:
            return {
                "error" : "No plan created yet. Call create_plan() first.",
                "action": "grid_only"
            }

        hour       = float(current_data.get("hour_of_day", 12.0))
        day_type   = current_data.get("day_type", "weekday")
        soc        = current_data.get("soc", None)
        pv_actual  = current_data.get("pv_actual_kw", None)
        load_act   = current_data.get("load_actual_kw", None)
        cloud      = float(current_data.get("cloud_factor", 1.0))
        # FIX BUG 7: Use stored _grid_cost as default (not None)
        grid_price = current_data.get("grid_price", self._grid_cost)

        # FIX BUG 7: No getattr needed — properly initialized in __init__
        last           = self._last_action
        prev_charge    = float(last.get("charge_kw",    0.0))
        prev_discharge = float(last.get("discharge_kw", 0.0))

        if soc is not None:
            self.twin.battery.soc = float(soc)
            self.twin.estimator.reset(initial_soc=float(soc))
            prev_charge    = 0.0
            prev_discharge = 0.0

        # FIX BUG 17: Pass grid_import/export from last action
        # OLD: grid_import_kw and grid_export_kw not passed → always 0
        # NEW: cost_so_far in twin now accumulates correctly
        state = self.twin.twin_step(
            hour_of_day    = hour,
            day_type       = day_type,
            irradiance     = self._cloud_to_irradiance(hour, cloud),
            grid_price     = grid_price,
            cloud_factor   = cloud,
            charge_kw      = prev_charge,
            discharge_kw   = prev_discharge,
            grid_import_kw = float(last.get("grid_import_kw", 0.0)),  # FIX BUG 17
            grid_export_kw = float(last.get("grid_export_kw", 0.0)),  # FIX BUG 17
        )

        if pv_actual is not None:
            state.pv_power_kw     = float(pv_actual)
            state.pv_available_kw = float(pv_actual)
        if load_act is not None:
            state.load_kw = float(load_act)

        opt_result  = self.solver.optimize(state)
        best_action = opt_result.get("best_action", {})

        pol_result   = self.policy.evaluate(
            state       = state,
            action      = best_action,
            cycle_count = state.cycle_count
        )
        final_action = pol_result["final_action"]

        # FIX BUG 16: Store final_action (after policy), NOT best_action
        # OLD: self._last_action = best_action
        #   → policy modifications were lost, wrong values fed back next step
        self._last_action = final_action   # FIX BUG 16

        cost_bd     = best_action.get("cost_breakdown", {})
        explanation = self.explainer.explain(state, best_action, cost_bd)

        predicted_costs = self._predict_next_hours(state, n_hours=4)

        return {
            "action_name"    : best_action.get("action_name", "grid_only"),
            "description"    : best_action.get("description", ""),
            "charge_kw"      : final_action.get("charge_kw",      0.0),
            "discharge_kw"   : final_action.get("discharge_kw",   0.0),
            "grid_import_kw" : final_action.get("grid_import_kw", 0.0),
            "grid_export_kw" : final_action.get("grid_export_kw", 0.0),
            "pv_used_kw"     : state.pv_power_kw,
            "current_soc"    : round(state.soc, 4),
            "current_pv_kw"  : round(state.pv_power_kw, 2),
            "current_load_kw": round(state.load_kw, 2),
            "grid_price"     : round(state.grid_price, 4),
            "hour"           : hour,
            "step_cost"      : round(cost_bd.get("total_cost", 0.0), 6),
            "cost_breakdown" : cost_bd,
            "explanation"    : explanation["full_explanation"],
            "reason"         : explanation["reason"],
            "top_factor"     : explanation["top_factor"],
            "decision_text"  : explanation["decision"],
            "predicted_next_4h": predicted_costs,
            "carbon_kg_step" : round(
                final_action.get("grid_import_kw", 0.0) * 0.40 * 0.25, 4),
            "tariff_period"  : pol_result.get("tariff_period", ""),
            "rule_violations": pol_result.get("rule_violations", [])
        }

    # ================================================================
    # HELPERS
    # ================================================================

    def _get_monthly_kwh(self, user_inputs: dict) -> float:
        monthly_data = user_inputs.get("monthly_data", None)
        if monthly_data and len(monthly_data) > 0:
            total = sum(m.get("kwh", 0) for m in monthly_data)
            return total / len(monthly_data)
        return float(user_inputs.get("monthly_consumption_kwh", 10000))

    def _build_solar_range(
        self,
        max_kw: float,
        budget: float,
        solar_price_per_kw: float
    ) -> list:
        import math
        if math.isinf(max_kw) or math.isnan(max_kw):
            return [0.0, 5.0, 10.0]

        affordable_kw = budget / solar_price_per_kw if solar_price_per_kw > 0 else max_kw
        max_kw = min(max_kw, affordable_kw)
        if max_kw <= 0:
            return [0.0]

        step = max(0.1, max_kw / 6)
        sizes = [0.0]
        kw = step

        max_iters = 100
        iters = 0
        while kw <= max_kw + step and iters < max_iters:
            sizes.append(round(kw, 2))
            kw += step
            iters += 1

        return sizes

    def _build_battery_range(
        self,
        option: str,
        daily_kwh: float,
        budget: float,
        battery_price_per_kwh: float
    ) -> list:
        if option == "no":
            return [0.0]

        if option == "yes":
            default_sizes = [round(daily_kwh * f, 1) for f in [0.1, 0.2, 0.3, 0.4, 0.5]]
        else:
            default_sizes = [round(daily_kwh * f, 1) for f in [0.1, 0.2, 0.3, 0.4]]

        if battery_price_per_kwh > 0 and budget > 0:
            affordable_batt = budget / battery_price_per_kwh
            affordable_sizes = [s for s in default_sizes if s <= affordable_batt]
            if affordable_sizes:
                battery_sizes = [0.0] + affordable_sizes
            else:
                step = max(0.1, affordable_batt / 6)
                battery_sizes = [0.0]
                kw = step
                max_iters = 50
                iters = 0
                while kw <= affordable_batt + 1e-6 and iters < max_iters:
                    battery_sizes.append(round(kw, 2))
                    kw += step
                    iters += 1
            return sorted(set(battery_sizes))

        return [0.0] + default_sizes

    def _solar_kw_to_area(self, solar_kw: float) -> float:
        if solar_kw <= 0:
            return 0.0
        return solar_kw * 1000.0 / (self.pv_model.base_efficiency * 1000.0)

    def _irradiance_to_sun_hours(self, irradiance_wm2: float) -> float:
        """
        FIX BUG 6: Convert effective average irradiance to peak sun hours.
        irradiance_wm2 from algorithm_service = daily_ghi * 1000 / 7
        So: peak_sun_hours = irradiance_wm2 * 7 / 1000
        Clamped to realistic 2-8 hour range.
        """
        # FIX: was irradiance_wm2 / 100 which only worked by coincidence
        # for values near 500 W/m² but was wrong for other locations
        return max(2.0, min(8.0, irradiance_wm2 * 7.0 / 1000.0))

    def _irradiance_to_cloud(self, irradiance_wm2: float) -> float:
        return min(1.0, irradiance_wm2 / 900.0)

    def _cloud_to_irradiance(self, hour: float, cloud_factor: float) -> float:
        """
        FIX BUG 12: Use stored location peak, not hardcoded 900 W/m²
        OLD: 900.0 * np.sin(angle) * cloud_factor  (same for Delhi and London!)
        NEW: self._location_peak_irr * np.sin(angle) * cloud_factor
        """
        if 6.0 <= hour <= 18.0:
            angle = np.pi * (hour - 6.0) / 12.0
            return max(0.0, self._location_peak_irr * np.sin(angle) * cloud_factor)
        return 0.0

    def _generate_sample_schedule(
        self,
        day_type  : str   = "weekday",
        peak_irr  : float = 600.0,
        grid_cost : float = None,
    ) -> list:
        if self.twin is None:
            return []

        self.twin.reset(initial_soc=0.50)
        results = []
        sim_soc = 0.50 if self.twin.battery.capacity_kwh > 0 else 0.0

        for t in range(96):
            hour = t * 0.25

            # Compute irradiance directly from peak_irr using sin curve
            # Avoids double-discount: irradiance→cloud_factor→irradiance applies location twice.
            if 6.0 <= hour <= 18.0:
                angle = np.pi * (hour - 6.0) / 12.0
                irr   = float(peak_irr * np.sin(angle))
            else:
                irr = 0.0

            # ── Step 1: get PV + load from twin ──────────────────────
            state = self.twin.twin_step(
                hour_of_day  = hour,
                day_type     = day_type,
                irradiance   = irr,
                grid_price   = grid_cost,
                cloud_factor = 1.0,  # irradiance already accounts for location
                charge_kw    = 0.0,
                discharge_kw = 0.0,
            )

            # Override twin's Kalman SOC with our clean simulation SOC
            state.soc = sim_soc

            # ── Step 2: optimizer decides what to do ──────────────────
            opt    = self.solver.optimize(state)
            action = opt.get("best_action", {}) or {}

            charge_kw    = float(action.get("charge_kw",    0.0))
            discharge_kw = float(action.get("discharge_kw", 0.0))

            # ── Step 3: apply action to battery immediately ───────────
            batt_result = self.twin.battery.step(charge_kw, discharge_kw, 0.25)
            sim_soc     = batt_result["soc"]

            results.append({
                "timestep"      : t,
                "hour"          : round(hour, 2),
                "soc"           : round(sim_soc, 4),
                "pv_kw"         : round(state.pv_power_kw, 2),
                "load_kw"       : round(state.load_kw, 2),
                "action"        : action.get("action_name", "grid_only"),
                "charge_kw"     : round(charge_kw, 4),
                "discharge_kw"  : round(discharge_kw, 4),
                "grid_import_kw": round(action.get("grid_import_kw", 0.0), 4),
                "grid_export_kw": round(action.get("grid_export_kw", 0.0), 4),
                "cost"          : round(
                    action.get("cost_breakdown", {}).get("total_cost", 0), 6)
            })

        self.twin.reset(initial_soc=0.50)
        return results

    def _predict_next_hours(self, state: TwinState, n_hours: int = 4) -> list:
        if state.forecast is None:
            return []
        predictions = []
        steps = int(n_hours / 0.25)
        for i in range(min(steps, state.forecast.horizon)):
            predictions.append({
                "hour"         : round(state.hour_of_day + i * 0.25, 2),
                "pv_expected"  : round(state.forecast.pv_mean[i], 2),
                "load_expected": round(state.forecast.load_mean[i], 2),
                "price"        : round(state.forecast.price_mean[i], 4)
            })
        return predictions

    def get_plan_summary(self) -> dict:
        if self.plan is None:
            return {"error": "No plan created yet"}
        return {
            "solar_kw"      : self.plan["recommended_solar_kw"],
            "solar_area_m2" : self.plan["recommended_solar_area_m2"],
            "battery_kwh"   : self.plan["recommended_battery_kwh"],
            "roi_years"     : self.plan["roi_years"],
            "annual_savings": self.plan["annual_savings"],
            "investment"    : self.plan["investment"],
            "daily_kwh"     : self.plan["daily_kwh"],
            "peak_load_kw"  : self.plan["peak_load_kw"]
        }