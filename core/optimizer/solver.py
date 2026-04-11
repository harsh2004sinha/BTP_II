"""
Main Optimizer / Solver
Decides the best action for every 15-minute timestep
"""

import numpy as np
from typing import List, Optional

from .cost_function  import CostFunction
from .degradation    import DegradationModel
from .constraints    import Constraints
from .scenario       import ScenarioGenerator
from ..twin.twin_state import TwinState, ForecastBundle


class Solver:
    """
    Microgrid Energy Management Optimizer.

    Strategy: Rule-Enhanced MPC (Model Predictive Control)

    For each timestep:
        1. Get current state from Digital Twin
        2. Generate scenarios from forecast
        3. Evaluate candidate actions using cost function
        4. Apply constraints
        5. Return best action with cost breakdown

    Candidate actions:
        - Use solar directly
        - Charge battery from solar surplus
        - Discharge battery to cover load
        - Import from grid
        - Export to grid
        - Hybrid combinations
    """

    def __init__(
        self,
        cost_function     : CostFunction    = None,
        degradation_model : DegradationModel = None,
        constraints       : Constraints     = None,
        scenario_gen      : ScenarioGenerator = None,
        dt_hours          : float = 0.25,
        horizon           : int   = 96,
        n_scenarios       : int   = 5
    ):
        self.cost_fn    = cost_function     or CostFunction()
        self.deg_model  = degradation_model or DegradationModel()
        self.constraints= constraints       or Constraints()
        self.scenario_gen = scenario_gen    or ScenarioGenerator(n_scenarios=n_scenarios)
        self.dt_hours   = dt_hours
        self.horizon    = horizon
        self.n_scenarios= n_scenarios

        # Tracking
        self.last_action  = {}
        self.action_history = []

    # ----------------------------------------------------------------
    def optimize(self, state: TwinState) -> dict:
        """
        Main optimization call. Returns best action for current state.

        Args:
            state : Current TwinState from Digital Twin

        Returns:
            dict with action, cost breakdown, explanation hint
        """
        # Extract state
        soc         = state.soc
        pv_kw       = state.pv_power_kw
        load_kw     = state.load_kw
        grid_price  = state.grid_price
        feed_in     = state.feed_in_tariff
        batt_health = state.battery_health
        batt_cap    = self.deg_model.battery_capacity_kwh

        # Use forecast if available, else use current values
        if state.forecast:
            forecast = state.forecast
        else:
            forecast = None

        # Generate candidate actions
        candidates = self._generate_candidates(
            soc, pv_kw, load_kw, grid_price, batt_cap, batt_health)

        # Evaluate each candidate
        best_action = None
        best_cost   = float("inf")
        evaluated   = []

        for action in candidates:
            result = self._evaluate_action(
                action, soc, pv_kw, load_kw, grid_price, feed_in,
                batt_cap, batt_health)

            evaluated.append({**action, **result})

            # Strict less-than: ties keep the earlier (more specific) action.
            # But only accept solar/battery actions when they genuinely help.
            if result["total_cost"] < best_cost:
                best_cost   = result["total_cost"]
                best_action = {**action, **result}

        # Add MPC lookahead if forecast is available
        if forecast and best_action:
            mpc_bonus = self._mpc_lookahead(best_action, forecast, soc)
            best_action["mpc_adjustment"] = mpc_bonus

        # Apply constraint clamping
        if best_action:
            clamped = self.constraints.clamp_action(
                charge_kw       = best_action.get("charge_kw", 0.0),
                discharge_kw    = best_action.get("discharge_kw", 0.0),
                grid_import_kw  = best_action.get("grid_import_kw", 0.0),
                grid_export_kw  = best_action.get("grid_export_kw", 0.0),
                pv_available_kw = pv_kw,
                soc             = soc,
                battery_capacity_kwh = batt_cap,
                dt_hours        = self.dt_hours
            )
            best_action.update(clamped)

        self.last_action = best_action or {}
        self.action_history.append(self.last_action)

        return {
            "best_action"  : best_action,
            "all_candidates": evaluated,
            "timestep"     : state.timestep,
            "hour"         : state.hour_of_day
        }

    # ----------------------------------------------------------------
    def optimize_horizon(
        self,
        state    : TwinState,
        forecast : ForecastBundle = None
    ) -> List[dict]:
        """
        Optimize over full planning horizon (MPC).
        Returns a schedule of actions for each timestep.

        Args:
            state    : Current state
            forecast : Forecast bundle

        Returns:
            List of action dicts for each timestep
        """
        schedule = []
        forecast = forecast or (state.forecast)

        if forecast is None:
            # Single-step fallback
            return [self.optimize(state)["best_action"]]

        # Simulate forward
        sim_soc = state.soc
        batt_cap = self.deg_model.battery_capacity_kwh

        for t in range(min(self.horizon, forecast.horizon)):
            pv_kw      = forecast.pv_mean[t]
            load_kw    = forecast.load_mean[t]
            grid_price = forecast.price_mean[t]
            feed_in    = grid_price * 0.5

            # Get best action for this simulated state
            candidates = self._generate_candidates(
                sim_soc, pv_kw, load_kw, grid_price, batt_cap, state.battery_health)

            best_a    = None
            best_c    = float("inf")

            for action in candidates:
                result = self._evaluate_action(
                    action, sim_soc, pv_kw, load_kw, grid_price, feed_in,
                    batt_cap, state.battery_health)
                if result["total_cost"] < best_c:
                    best_c = result["total_cost"]
                    best_a = {**action, **result, "timestep": t}

            if best_a:
                # Update simulated SOC
                charge_kw    = best_a.get("charge_kw", 0.0)
                discharge_kw = best_a.get("discharge_kw", 0.0)
                delta_soc = (
                    charge_kw    * 0.95  * self.dt_hours
                    - discharge_kw / 0.95 * self.dt_hours
                ) / batt_cap if batt_cap > 0 else 0.0
                sim_soc = float(np.clip(sim_soc + delta_soc, 0.10, 0.95))
                best_a["predicted_soc"] = round(sim_soc, 4)

            schedule.append(best_a or {})

        return schedule

    # ----------------------------------------------------------------
    def _generate_candidates(
        self,
        soc        : float,
        pv_kw      : float,
        load_kw    : float,
        grid_price : float,
        batt_cap   : float,
        batt_health: float
    ) -> List[dict]:
        """
        Generate candidate actions to evaluate.

        Covers all meaningful microgrid operating modes:
            1. Solar only (no battery, no grid)
            2. Solar + charge battery
            3. Solar + grid (no battery)
            4. Battery discharge only
            5. Solar + battery discharge
            6. Grid import only
            7. Export solar surplus
            8. Battery discharge + grid (hybrid)
        """
        candidates = []
        net_load   = max(0.0, load_kw - pv_kw)
        surplus    = max(0.0, pv_kw   - load_kw)

        max_charge    = self.constraints.max_charge_kw
        max_discharge = self.constraints.max_discharge_kw
        soc_min       = self.constraints.battery_soc_min
        soc_max       = self.constraints.battery_soc_max

        # Available battery energy
        avail_discharge = ((soc - soc_min) * batt_cap * 0.95
                           / self.dt_hours) if soc > soc_min else 0.0
        avail_discharge = min(avail_discharge, max_discharge)

        avail_charge = ((soc_max - soc) * batt_cap
                        / (0.95 * self.dt_hours)) if soc < soc_max else 0.0
        avail_charge = min(avail_charge, max_charge)

        # Meaningful solar threshold — below this we treat PV as zero
        _PV_MIN = 0.05  # kW
        has_solar = pv_kw >= _PV_MIN

        # --- Action 1: Use solar directly, cover deficit from grid ---
        # Only add this candidate when solar is actually generating something
        if has_solar:
            candidates.append({
                "action_name"   : "solar_direct",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": round(max(0.0, net_load), 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Use solar directly, grid covers rest"
            })

        # --- Action 2: Solar + charge battery with surplus ---
        if surplus > 0 and avail_charge > 0:
            charge = min(surplus, avail_charge)
            remaining_surplus = surplus - charge
            candidates.append({
                "action_name"   : "solar_charge_battery",
                "charge_kw"     : round(charge, 4),
                "discharge_kw"  : 0.0,
                "grid_import_kw": 0.0,
                "grid_export_kw": round(remaining_surplus, 4),
                "pv_used_kw"    : round(pv_kw, 4),
                "description"   : "Charge battery with solar surplus"
            })

        # --- Action 3: Export all surplus to grid ---
        if surplus > 0:
            candidates.append({
                "action_name"   : "export_surplus",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": 0.0,
                "grid_export_kw": round(surplus, 4),
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Export surplus solar to grid"
            })

        # --- Action 4: Discharge battery to cover load deficit ---
        if net_load > 0 and avail_discharge > 0:
            discharge = min(net_load, avail_discharge)
            grid_needed = max(0.0, net_load - discharge)
            candidates.append({
                "action_name"   : "battery_discharge",
                "charge_kw"     : 0.0,
                "discharge_kw"  : round(discharge, 4),
                "grid_import_kw": round(grid_needed, 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Discharge battery to reduce grid import"
            })

        # --- Action 5: Full battery discharge (avoid peak tariff) ---
        if grid_price >= 0.20 and avail_discharge > 0:
            candidates.append({
                "action_name"   : "peak_shaving",
                "charge_kw"     : 0.0,
                "discharge_kw"  : round(min(net_load, avail_discharge), 4),
                "grid_import_kw": round(max(0.0, net_load - avail_discharge), 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Peak shaving: battery discharge during high tariff"
            })

        # --- Action 6: Grid import only (no battery) ---
        candidates.append({
            "action_name"   : "grid_only",
            "charge_kw"     : 0.0,
            "discharge_kw"  : 0.0,
            "grid_import_kw": round(net_load, 4),
            "grid_export_kw": 0.0,
            "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
            "description"   : "Import all deficit from grid"
        })

        # --- Action 7: Charge battery from grid (off-peak) ---
        if grid_price <= 0.09 and avail_charge > 0 and soc < 0.80:
            candidates.append({
                "action_name"   : "grid_charge_battery",
                "charge_kw"     : round(min(avail_charge * 0.5, max_charge), 4),
                "discharge_kw"  : 0.0,
                "grid_import_kw": round(net_load + min(avail_charge * 0.5, max_charge), 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Charge battery from cheap off-peak grid"
            })

        return candidates

    # ----------------------------------------------------------------
    def _evaluate_action(
        self,
        action      : dict,
        soc         : float,
        pv_kw       : float,
        load_kw     : float,
        grid_price  : float,
        feed_in     : float,
        batt_cap    : float,
        batt_health : float
    ) -> dict:
        """
        Evaluate total cost of a candidate action.

        Returns:
            dict with total_cost, cost breakdown, constraint_penalty
        """
        charge_kw    = action.get("charge_kw",     0.0)
        discharge_kw = action.get("discharge_kw",  0.0)
        grid_import  = action.get("grid_import_kw", 0.0)
        grid_export  = action.get("grid_export_kw", 0.0)
        pv_used      = action.get("pv_used_kw",     0.0)

        # Degradation cost
        deg = self.deg_model.degradation_cost(
            charge_kw     = charge_kw,
            discharge_kw  = discharge_kw,
            current_soc   = soc,
            dt_hours      = self.dt_hours
        )

        # Main cost
        costs = self.cost_fn.compute(
            grid_import_kw   = grid_import,
            grid_export_kw   = grid_export,
            charge_kw        = charge_kw,
            discharge_kw     = discharge_kw,
            pv_kw            = pv_used,
            load_kw          = load_kw,
            grid_price       = grid_price,
            feed_in_tariff   = feed_in,
            degradation_cost = deg["degradation_cost"],
            dt_hours         = self.dt_hours
        )

        # Constraint penalty
        cp = self.constraints.total_penalty(
            soc             = soc,
            charge_kw       = charge_kw,
            discharge_kw    = discharge_kw,
            grid_import_kw  = grid_import,
            grid_export_kw  = grid_export,
            pv_used_kw      = pv_used,
            pv_available_kw = pv_kw,
            load_kw         = load_kw
        )

        total_cost = costs["total_cost"] + cp["total_penalty"]

        return {
            "total_cost"         : round(total_cost, 6),
            "cost_breakdown"     : costs,
            "degradation"        : deg,
            "constraint_penalty" : cp["total_penalty"],
            "violations"         : cp["all_violations"]
        }

    # ----------------------------------------------------------------
    def _mpc_lookahead(
        self,
        current_action : dict,
        forecast       : ForecastBundle,
        current_soc    : float,
        lookahead_steps: int = 4
    ) -> float:
        """
        Simple lookahead cost adjustment.
        Checks if current action is good given near-future forecast.

        Returns:
            float — adjustment bonus (negative = action is better)
        """
        bonus = 0.0
        sim_soc = current_soc
        batt_cap = self.deg_model.battery_capacity_kwh

        # Simulate forward a few steps with current action tendency
        for t in range(min(lookahead_steps, forecast.horizon)):
            future_price = forecast.price_mean[t]
            future_pv    = forecast.pv_mean[t]
            future_load  = forecast.load_mean[t]

            # Reward: having SOC available for upcoming high-price periods
            if future_price >= 0.20 and sim_soc < 0.40:
                bonus -= 0.5   # Penalize being low before peak

            # Reward: charging now if price will be much higher later
            max_future_price = max(forecast.price_mean[:min(8, forecast.horizon)])
            if (forecast.price_mean[0] <= 0.09
                    and max_future_price >= 0.20
                    and sim_soc < 0.80):
                bonus -= 0.3   # Incentivize off-peak charging

        return round(bonus, 4)

    # ----------------------------------------------------------------
    def get_action_summary(self, action: dict) -> str:
        """Get human-readable summary of an action."""
        if not action:
            return "No action"
        name = action.get("action_name", "unknown")
        desc = action.get("description", "")
        cost = action.get("total_cost", 0.0)
        return f"[{name}] {desc} | Cost: ${cost:.4f}"