"""
Policy Manager
Single entry point for all policy layers
Combines tariff + carbon + demand response + user rules
"""

from typing import Optional

from .tariff          import TariffManager
from .carbon          import CarbonPolicy
from .demand_response import DemandResponseManager
from .user_rules      import UserRules
from ..twin.twin_state import TwinState


class PolicyManager:
    """
    Master policy controller for the microgrid.

    Combines all policy layers:
        1. TariffManager      → electricity pricing
        2. CarbonPolicy       → carbon costs + tracking
        3. DemandResponseManager → DR events + credits
        4. UserRules          → user preferences + constraints

    The optimizer calls this before finalizing any action.

    Flow:
        Optimizer proposes action
        → PolicyManager checks all rules
        → Returns modified action + combined penalty
        → Optimizer uses modified action
    """

    def __init__(
        self,
        tariff_manager  : TariffManager           = None,
        carbon_policy   : CarbonPolicy             = None,
        dr_manager      : DemandResponseManager    = None,
        user_rules      : UserRules                = None
    ):
        self.tariff  = tariff_manager or TariffManager()
        self.carbon  = carbon_policy  or CarbonPolicy()
        self.dr      = dr_manager     or DemandResponseManager()
        self.rules   = user_rules     or UserRules()

        # Session tracking
        self._step_count    = 0
        self._daily_cost    = 0.0
        self._daily_credits = 0.0

    # ----------------------------------------------------------------
    def evaluate(
        self,
        state        : TwinState,
        action       : dict,
        cycle_count  : float = 0.0
    ) -> dict:
        """
        Evaluate and modify an action according to all policies.

        Args:
            state       : Current TwinState
            action      : Proposed action from optimizer
            cycle_count : Battery cycles used today

        Returns:
            dict with:
                final_action    : Modified action after policy checks
                total_penalty   : Sum of all policy penalties
                policy_costs    : Itemized policy costs
                grid_price      : Current tariff price
                feed_in_rate    : Current feed-in tariff
                dr_constraint   : Demand response constraint
                carbon_info     : Carbon cost info
                rule_violations : User rule violations
        """
        hour       = state.hour_of_day
        load_kw    = state.load_kw
        import_kw  = action.get("grid_import_kw", 0.0)
        export_kw  = action.get("grid_export_kw", 0.0)
        charge_kw  = action.get("charge_kw",     0.0)
        discharge_kw = action.get("discharge_kw", 0.0)
        pv_kw      = state.pv_power_kw

        # ---- 1. Tariff ----
        grid_price   = self.tariff.get_price(hour)
        feed_in_rate = self.tariff.get_feed_in_rate()
        self.tariff.update_peak_demand(import_kw)

        # ---- 2. Carbon cost ----
        carbon_info = self.carbon.compute_carbon_cost(
            grid_import_kw = import_kw,
            dt_hours       = state.__class__.__dataclass_fields__.get(
                "dt_hours", None) or 0.25
        )
        avoided_carbon = self.carbon.compute_avoided_emissions(pv_kw)

        # ---- 3. Demand Response ----
        dr_constraint = self.dr.get_dr_constraint(
            hour              = hour,
            current_load_kw   = load_kw,
            current_import_kw = import_kw
        )

        # Apply DR constraint to action
        dr_modified_action = action.copy()
        if dr_constraint["dr_active"]:
            max_import = dr_constraint["max_import_kw"]
            if import_kw > max_import:
                dr_modified_action["grid_import_kw"] = max_import

        # ---- 4. User Rules ----
        rule_result = self.rules.check_action(
            action      = dr_modified_action,
            state       = state.to_dict(),
            hour        = hour,
            cycle_count = cycle_count
        )

        final_action = rule_result["modified_action"]

        # ---- 5. Budget check ----
        budget_penalty = 0.0
        max_daily = self.rules.rules.get("max_daily_cost")
        if max_daily is not None and self._daily_cost >= max_daily:
            budget_penalty = 5.0

        # ---- 6. Carbon budget check ----
        carbon_penalty = self.carbon.get_carbon_penalty()

        # ---- 7. DR penalty ----
        dr_penalty = 0.0
        if dr_constraint["dr_active"]:
            overshoot = max(0.0, import_kw - dr_constraint["max_import_kw"])
            dr_penalty = overshoot * dr_constraint["penalty_rate"]

        # ---- Total penalty ----
        total_penalty = (
            rule_result["penalty"]
            + budget_penalty
            + carbon_penalty
            + dr_penalty
        )

        # ---- Update daily tracking ----
        step_cost = import_kw * grid_price * 0.25
        self._daily_cost += step_cost
        self._step_count += 1

        # ---- Override state prices with policy prices ----
        final_action["grid_price_used"]   = grid_price
        final_action["feed_in_rate_used"] = feed_in_rate

        return {
            "final_action"    : final_action,
            "total_penalty"   : round(total_penalty, 4),
            "policy_costs"    : {
                "carbon_cost"       : carbon_info["carbon_cost"],
                "carbon_kg"         : carbon_info["carbon_kg"],
                "budget_penalty"    : round(budget_penalty, 4),
                "dr_penalty"        : round(dr_penalty, 4),
                "rule_penalty"      : rule_result["penalty"],
                "avoided_carbon_kg" : round(avoided_carbon, 5)
            },
            "grid_price"      : grid_price,
            "feed_in_rate"    : feed_in_rate,
            "tariff_period"   : self.tariff.get_period_name(hour),
            "dr_constraint"   : dr_constraint,
            "carbon_info"     : carbon_info,
            "rule_violations" : rule_result["violations"],
            "daily_cost_so_far": round(self._daily_cost, 4)
        }

    # ----------------------------------------------------------------
    def get_prices(self, hour: float) -> dict:
        """
        Get current buy/sell prices.

        Returns:
            dict with grid_price, feed_in_rate, period
        """
        return {
            "grid_price"   : self.tariff.get_price(hour),
            "feed_in_rate" : self.tariff.get_feed_in_rate(),
            "period"       : self.tariff.get_period_name(hour),
            "is_peak"      : self.tariff.is_peak_hour(hour),
            "is_off_peak"  : self.tariff.is_off_peak_hour(hour)
        }

    # ----------------------------------------------------------------
    def get_full_day_prices(self, dt_hours: float = 0.25) -> list:
        """Get price for every timestep in a day."""
        return self.tariff.get_full_day_prices(dt_hours)

    # ----------------------------------------------------------------
    def activate_dr_event(
        self,
        start_hour          : float,
        end_hour            : float,
        target_reduction_kw : float,
        event_type          : str = "voluntary"
    ) -> dict:
        """Activate a demand response event."""
        return self.dr.activate_event(
            start_hour          = start_hour,
            end_hour            = end_hour,
            target_reduction_kw = target_reduction_kw,
            event_type          = event_type
        )

    # ----------------------------------------------------------------
    def update_user_rules(self, new_rules: dict) -> dict:
        """Update user rules from frontend settings."""
        return self.rules.update_rules(new_rules)

    # ----------------------------------------------------------------
    def get_carbon_summary(self) -> dict:
        """Get carbon tracking summary."""
        return self.carbon.get_summary()

    # ----------------------------------------------------------------
    def get_dr_summary(self) -> dict:
        """Get demand response summary."""
        return self.dr.get_summary()

    # ----------------------------------------------------------------
    def reset_daily(self):
        """Reset all daily trackers. Call at midnight."""
        self._daily_cost    = 0.0
        self._step_count    = 0
        self._daily_credits = 0.0
        self.carbon.reset_daily()

    # ----------------------------------------------------------------
    def get_full_summary(self) -> dict:
        """Return complete policy status summary."""
        return {
            "daily_cost"   : round(self._daily_cost, 4),
            "step_count"   : self._step_count,
            "carbon"       : self.carbon.get_summary(),
            "dr"           : self.dr.get_summary(),
            "user_rules"   : self.rules.get_rules(),
            "monthly_demand_charge": self.tariff.get_monthly_demand_charge()
        }