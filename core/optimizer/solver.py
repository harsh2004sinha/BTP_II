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
            soc, pv_kw, load_kw, grid_price, batt_cap, batt_health, state.hour_of_day)

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
                sim_soc, pv_kw, load_kw, grid_price, batt_cap, state.battery_health, (state.hour_of_day + t * self.dt_hours) % 24)

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
        batt_health: float,
        hour       : float = 12.0
    ) -> List[dict]:
        """
        Generate candidate actions based on time-aware, priority-driven rules.

        Rules:
          SURPLUS (solar > load):
            - ALWAYS charge battery first (SOC < 90%)
            - Leftover surplus is curtailed — no grid export

          DEFICIT (load > solar):
            - Solar always covers what it can
            - Morning/Midday (06-15h): use battery (SOC > 10%) + grid for the rest
            - Afternoon Reserve (15-18h): save battery for night, use grid only
            - Night (18-06h): freely discharge battery (SOC > 10%) + grid for rest
        """
        candidates = []
        net_load = max(0.0, load_kw - pv_kw)   # gap not covered by solar
        surplus  = max(0.0, pv_kw   - load_kw)  # solar beyond load

        soc_min    = self.constraints.battery_soc_min   # 0.10
        soc_max    = self.constraints.battery_soc_max   # 0.90
        max_chg    = self.constraints.max_charge_kw
        max_dis    = self.constraints.max_discharge_kw

        # ── How much can we charge without exceeding 90% SOC? ────────
        if soc < soc_max and batt_cap > 0:
            avail_charge = min((soc_max - soc) * batt_cap / (0.95 * self.dt_hours), max_chg)
        else:
            avail_charge = 0.0

        # ── How much can we discharge without dropping below 10% SOC? ─
        if soc > soc_min and batt_cap > 0:
            avail_discharge = min((soc - soc_min) * batt_cap * 0.95 / self.dt_hours, max_dis)
        else:
            avail_discharge = 0.0

        # ── Afternoon Reserve Rule (15:00–18:00) ────────────────────
        # Block discharge during the last hours of sunlight so the battery
        # stays full for the night. Override only if price is exceptionally high.
        if 15.0 <= hour < 18.0 and grid_price < 0.20:
            avail_discharge = 0.0

        _PV_MIN   = 0.05
        has_solar = pv_kw >= _PV_MIN

        # ════════════════════════════════════════════════════════════
        # SURPLUS: solar output > load
        # Priority: charge battery → curtail excess
        # ════════════════════════════════════════════════════════════
        if surplus > 0.0:
            if avail_charge > 0.0:
                charge = min(surplus, avail_charge)
                candidates.append({
                    "action_name"   : "solar_charge_battery",
                    "charge_kw"     : round(charge, 4),
                    "discharge_kw"  : 0.0,
                    "grid_import_kw": 0.0,
                    "grid_export_kw": 0.0,
                    "pv_used_kw"    : round(min(pv_kw, load_kw + charge), 4),
                    "description"   : "Solar covers load + charges battery, excess curtailed",
                })
            # solar-direct (battery full or unavailable) — surplus curtailed
            candidates.append({
                "action_name"   : "solar_direct",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": 0.0,
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(min(pv_kw, load_kw), 4),
                "description"   : "Solar covers load, surplus curtailed",
            })

        # ════════════════════════════════════════════════════════════
        # DEFICIT: load > solar  (net_load > 0)
        # Priority: solar partial → battery (if allowed) → grid for rest
        # ════════════════════════════════════════════════════════════
        if net_load > 0.0:
            pv_partial = round(min(pv_kw, load_kw), 4)

            # Option A — Battery + Grid hybrid (battery helps reduce grid import)
            if avail_discharge > 0.0:
                batt_contrib = min(net_load, avail_discharge)
                grid_needed  = max(0.0, net_load - batt_contrib)
                candidates.append({
                    "action_name"   : "battery_discharge",
                    "charge_kw"     : 0.0,
                    "discharge_kw"  : round(batt_contrib, 4),
                    "grid_import_kw": round(grid_needed, 4),
                    "grid_export_kw": 0.0,
                    "pv_used_kw"    : pv_partial,
                    "description"   : "Solar + battery cover load, grid fills remainder",
                })
                # Peak-shaving variant — explicit when grid tariff is high
                if grid_price >= 0.20:
                    candidates.append({
                        "action_name"   : "peak_shaving",
                        "charge_kw"     : 0.0,
                        "discharge_kw"  : round(batt_contrib, 4),
                        "grid_import_kw": round(grid_needed, 4),
                        "grid_export_kw": 0.0,
                        "pv_used_kw"    : pv_partial,
                        "description"   : "Peak-shaving: battery + solar, grid fills remainder",
                    })

            # Option B — Grid only (battery skipped or in reserve)
            candidates.append({
                "action_name"   : "grid_only",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": round(net_load, 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : pv_partial,
                "description"   : "Solar + grid covers load, battery held in reserve",
            })

        # ════════════════════════════════════════════════════════════
        # BALANCED: load == solar (edge case)
        # ════════════════════════════════════════════════════════════
        if net_load == 0.0 and surplus == 0.0 and has_solar:
            candidates.append({
                "action_name"   : "solar_direct",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": 0.0,
                "grid_export_kw": 0.0,
                "pv_used_kw"    : round(pv_kw, 4),
                "description"   : "Solar exactly meets load",
            })

        # ════════════════════════════════════════════════════════════
        # Fallback safety net
        # ════════════════════════════════════════════════════════════
        if not candidates:
            candidates.append({
                "action_name"   : "grid_only",
                "charge_kw"     : 0.0,
                "discharge_kw"  : 0.0,
                "grid_import_kw": round(max(0.0, load_kw), 4),
                "grid_export_kw": 0.0,
                "pv_used_kw"    : 0.0,
                "description"   : "Grid only fallback",
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