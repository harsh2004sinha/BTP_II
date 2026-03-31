"""
User Rules
Stores and enforces user-defined constraints and preferences
"""

from typing import Dict, List, Optional


class UserRules:
    """
    User-defined rules and constraints for the microgrid.

    Users can set:
        - Minimum SOC reserve (never discharge below X%)
        - Maximum grid import limit
        - Preferred solar usage fraction
        - Battery cycling preferences
        - Export preferences
        - Blackout windows (no grid export during certain hours)
        - Priority loads (always serve specific loads)
        - Budget limit per day
    """

    # Default rules (conservative and safe)
    DEFAULT_RULES = {
        "min_soc_reserve"         : 0.20,    # Never go below 20% SOC
        "max_soc_target"          : 0.90,    # Charge up to 90% max
        "max_grid_import_kw"      : 500.0,   # Max grid import
        "max_grid_export_kw"      : 200.0,   # Max grid export
        "allow_grid_export"       : True,    # Allow selling to grid
        "allow_grid_charging"     : True,    # Allow charging battery from grid
        "prefer_solar_first"      : True,    # Always use solar before grid
        "max_daily_cost"          : None,    # No daily budget limit
        "min_solar_fraction"      : 0.0,     # No minimum solar requirement
        "max_battery_cycles_day"  : 2.0,     # Max full cycles per day
        "export_blackout_hours"   : [],      # Hours when export not allowed
        "charge_only_hours"       : [],      # Hours when only charging allowed
        "discharge_only_hours"    : [],      # Hours when only discharging allowed
        "emergency_reserve_soc"   : 0.30,   # Reserve for emergencies
        "enable_peak_shaving"     : True,    # Allow peak shaving
        "enable_dr_participation" : True,    # Participate in demand response
    }

    def __init__(self, custom_rules: dict = None):
        """
        Initialize with default rules, override with custom.

        Args:
            custom_rules : Dict of user-defined rule overrides
        """
        self.rules = self.DEFAULT_RULES.copy()

        if custom_rules:
            self.update_rules(custom_rules)

        # Violation tracking
        self._violations = []

    # ----------------------------------------------------------------
    def update_rules(self, new_rules: dict) -> dict:
        """
        Update rules with new user settings.

        Args:
            new_rules : Dict with rule name → value

        Returns:
            dict with updated rules and validation result
        """
        validated  = {}
        rejected   = {}

        for key, value in new_rules.items():
            if key in self.rules:
                valid, msg = self._validate_rule(key, value)
                if valid:
                    self.rules[key] = value
                    validated[key]  = value
                else:
                    rejected[key] = {"value": value, "reason": msg}
            else:
                rejected[key] = {"value": value, "reason": "Unknown rule"}

        return {
            "validated" : validated,
            "rejected"  : rejected,
            "current"   : self.rules.copy()
        }

    # ----------------------------------------------------------------
    def _validate_rule(self, key: str, value) -> tuple:
        """
        Validate a rule value.

        Returns:
            (is_valid: bool, message: str)
        """
        # SOC rules must be 0-1
        if "soc" in key and isinstance(value, (int, float)):
            if not 0.0 <= value <= 1.0:
                return False, f"{key} must be between 0 and 1"

        # Power limits must be positive
        if "kw" in key and isinstance(value, (int, float)):
            if value < 0:
                return False, f"{key} must be non-negative"

        # Boolean rules
        if key.startswith("allow_") or key.startswith("enable_") or key.startswith("prefer_"):
            if not isinstance(value, bool):
                return False, f"{key} must be True or False"

        # Lists
        if key.endswith("_hours"):
            if not isinstance(value, list):
                return False, f"{key} must be a list"

        return True, "OK"

    # ----------------------------------------------------------------
    def check_action(
        self,
        action       : dict,
        state        : dict,
        hour         : float,
        cycle_count  : float = 0.0
    ) -> dict:
        """
        Check if a proposed action complies with user rules.

        Args:
            action      : Action dict from solver
            state       : State dict (TwinState.to_dict())
            hour        : Current hour
            cycle_count : Battery cycles used today

        Returns:
            dict with is_allowed, violations, penalty, modified_action
        """
        violations      = []
        penalty         = 0.0
        modified_action = action.copy()

        soc          = state.get("soc", 0.5)
        charge_kw    = action.get("charge_kw",     0.0)
        discharge_kw = action.get("discharge_kw",  0.0)
        grid_import  = action.get("grid_import_kw", 0.0)
        grid_export  = action.get("grid_export_kw", 0.0)

        # --- Rule 1: Minimum SOC reserve ---
        min_soc = self.rules["min_soc_reserve"]
        if soc <= min_soc and discharge_kw > 0:
            violations.append(
                f"Discharge blocked: SOC {soc:.1%} at/below reserve {min_soc:.1%}")
            penalty += 10.0
            modified_action["discharge_kw"] = 0.0
            modified_action["grid_import_kw"] = max(
                grid_import, action.get("discharge_kw", 0.0))

        # --- Rule 2: Max grid import ---
        max_import = self.rules["max_grid_import_kw"]
        if grid_import > max_import:
            violations.append(
                f"Grid import {grid_import:.1f}kW exceeds rule limit {max_import:.1f}kW")
            penalty += 3.0
            modified_action["grid_import_kw"] = max_import

        # --- Rule 3: Grid export allowed ---
        if not self.rules["allow_grid_export"] and grid_export > 0:
            violations.append("Grid export not allowed by user rule")
            modified_action["grid_export_kw"] = 0.0

        # --- Rule 4: Export blackout hours ---
        blackout = self.rules["export_blackout_hours"]
        if int(hour) in blackout and grid_export > 0:
            violations.append(
                f"Export blocked: hour {int(hour)} is in export blackout window")
            modified_action["grid_export_kw"] = 0.0

        # --- Rule 5: Grid charging allowed ---
        if not self.rules["allow_grid_charging"]:
            if charge_kw > 0 and grid_import > 0:
                violations.append("Battery charging from grid not allowed")
                modified_action["charge_kw"] = 0.0

        # --- Rule 6: Battery cycle limit ---
        max_cycles = self.rules["max_battery_cycles_day"]
        if cycle_count >= max_cycles:
            if charge_kw > 0 or discharge_kw > 0:
                violations.append(
                    f"Battery cycle limit reached ({cycle_count:.2f} of {max_cycles})")
                penalty += 5.0
                modified_action["charge_kw"]    = 0.0
                modified_action["discharge_kw"] = 0.0

        # --- Rule 7: Charge only hours ---
        charge_only = self.rules["charge_only_hours"]
        if int(hour) in charge_only and discharge_kw > 0:
            violations.append(
                f"Discharge blocked: hour {int(hour)} is charge-only window")
            modified_action["discharge_kw"] = 0.0

        # --- Rule 8: Discharge only hours ---
        discharge_only = self.rules["discharge_only_hours"]
        if int(hour) in discharge_only and charge_kw > 0:
            violations.append(
                f"Charge blocked: hour {int(hour)} is discharge-only window")
            modified_action["charge_kw"] = 0.0

        # --- Rule 9: Peak shaving enabled ---
        if not self.rules["enable_peak_shaving"]:
            if action.get("action_name") == "peak_shaving":
                violations.append("Peak shaving disabled by user rule")
                modified_action["discharge_kw"] = 0.0

        return {
            "is_allowed"      : len(violations) == 0,
            "violations"      : violations,
            "penalty"         : round(penalty, 4),
            "modified_action" : modified_action,
            "rules_checked"   : True
        }

    # ----------------------------------------------------------------
    def get_rules(self) -> dict:
        """Return current rules."""
        return self.rules.copy()

    # ----------------------------------------------------------------
    def get_soc_limits(self) -> dict:
        """Return SOC limit rules."""
        return {
            "min_soc"      : self.rules["min_soc_reserve"],
            "max_soc"      : self.rules["max_soc_target"],
            "emergency_soc": self.rules["emergency_reserve_soc"]
        }

    # ----------------------------------------------------------------
    def reset_to_defaults(self):
        """Reset all rules to default values."""
        self.rules      = self.DEFAULT_RULES.copy()
        self._violations = []

    # ----------------------------------------------------------------
    def get_rule_summary(self) -> str:
        """Return human-readable rule summary."""
        lines = ["📋 Active User Rules:"]
        lines.append(f"  Min SOC Reserve     : {self.rules['min_soc_reserve']:.0%}")
        lines.append(f"  Max SOC Target      : {self.rules['max_soc_target']:.0%}")
        lines.append(f"  Max Grid Import     : {self.rules['max_grid_import_kw']:.0f} kW")
        lines.append(f"  Allow Grid Export   : {self.rules['allow_grid_export']}")
        lines.append(f"  Allow Grid Charging : {self.rules['allow_grid_charging']}")
        lines.append(f"  Prefer Solar First  : {self.rules['prefer_solar_first']}")
        lines.append(f"  Max Cycles/Day      : {self.rules['max_battery_cycles_day']}")
        lines.append(f"  Peak Shaving        : {self.rules['enable_peak_shaving']}")
        lines.append(f"  DR Participation    : {self.rules['enable_dr_participation']}")
        if self.rules["export_blackout_hours"]:
            lines.append(f"  Export Blackout Hrs : {self.rules['export_blackout_hours']}")
        if self.rules["max_daily_cost"] is not None:
            lines.append(f"  Max Daily Cost      : ${self.rules['max_daily_cost']:.2f}")
        return "\n".join(lines)