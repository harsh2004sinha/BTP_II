"""
Optimization Constraints
Defines all physical and operational limits for microgrid
"""


class Constraints:
    """
    Defines and validates all microgrid constraints.

    Hard constraints (must never be violated):
        - Power balance: supply == demand always
        - Battery SOC limits
        - PV cannot exceed available generation
        - Grid power limits

    Soft constraints (penalized if violated):
        - Reserve SOC requirement
        - Demand response rules
        - Carbon budget
    """

    def __init__(
        self,
        battery_soc_min     : float = 0.10,
        battery_soc_max     : float = 0.90,
        battery_soc_reserve : float = 0.20,
        max_charge_kw       : float = 50.0,
        max_discharge_kw    : float = 50.0,
        max_grid_import_kw  : float = 500.0,
        max_grid_export_kw  : float = 200.0,
        reserve_penalty     : float = 5.0,
        balance_tolerance   : float = 0.5
    ):
        self.battery_soc_min     = battery_soc_min
        self.battery_soc_max     = battery_soc_max
        self.battery_soc_reserve = battery_soc_reserve
        self.max_charge_kw       = max_charge_kw
        self.max_discharge_kw    = max_discharge_kw
        self.max_grid_import_kw  = max_grid_import_kw
        self.max_grid_export_kw  = max_grid_export_kw
        self.reserve_penalty     = reserve_penalty
        self.balance_tolerance   = balance_tolerance

    # ----------------------------------------------------------------
    def check_power_balance(
        self,
        load_kw        : float,
        pv_kw          : float,
        discharge_kw   : float,
        charge_kw      : float,
        grid_import_kw : float,
        grid_export_kw : float
    ) -> dict:
        """
        Verify:
            PV + discharge + grid_import = load + charge + grid_export

        Returns:
            dict — balance_error, is_valid
        """
        supply = pv_kw + discharge_kw + grid_import_kw
        demand = load_kw + charge_kw + grid_export_kw
        error  = abs(supply - demand)

        return {
            "supply_kw"     : round(supply, 4),
            "demand_kw"     : round(demand, 4),
            "balance_error" : round(error, 4),
            "is_valid"      : error <= self.balance_tolerance
        }

    # ----------------------------------------------------------------
    def check_battery(
        self,
        soc          : float,
        charge_kw    : float,
        discharge_kw : float
    ) -> dict:
        """
        Check battery constraints.

        Returns:
            dict — violations list, penalty, is_valid
        """
        violations = []
        penalty    = 0.0

        # SOC range
        if soc < self.battery_soc_min:
            violations.append(f"SOC {soc:.2f} below min {self.battery_soc_min}")
            penalty += 10.0 * (self.battery_soc_min - soc)

        if soc > self.battery_soc_max:
            violations.append(f"SOC {soc:.2f} above max {self.battery_soc_max}")
            penalty += 10.0 * (soc - self.battery_soc_max)

        # SOC reserve (soft)
        if soc < self.battery_soc_reserve:
            violations.append(f"SOC {soc:.2f} below reserve {self.battery_soc_reserve}")
            penalty += self.reserve_penalty * (self.battery_soc_reserve - soc)

        # Power limits
        if charge_kw > self.max_charge_kw:
            violations.append(f"Charge {charge_kw:.1f}kW exceeds max {self.max_charge_kw}kW")
            penalty += 2.0

        if discharge_kw > self.max_discharge_kw:
            violations.append(f"Discharge {discharge_kw:.1f}kW exceeds max {self.max_discharge_kw}kW")
            penalty += 2.0

        # Simultaneous charge + discharge
        if charge_kw > 0 and discharge_kw > 0:
            violations.append("Simultaneous charge and discharge")
            penalty += 5.0

        return {
            "violations" : violations,
            "penalty"    : round(penalty, 4),
            "is_valid"   : len(violations) == 0
        }

    # ----------------------------------------------------------------
    def check_grid(
        self,
        grid_import_kw : float,
        grid_export_kw : float
    ) -> dict:
        """
        Check grid power constraints.

        Returns:
            dict — violations, penalty, is_valid
        """
        violations = []
        penalty    = 0.0

        if grid_import_kw < 0:
            violations.append("Negative grid import")
            penalty += 5.0

        if grid_export_kw < 0:
            violations.append("Negative grid export")
            penalty += 5.0

        if grid_import_kw > self.max_grid_import_kw:
            violations.append(
                f"Grid import {grid_import_kw:.1f}kW exceeds {self.max_grid_import_kw}kW")
            penalty += 3.0

        if grid_export_kw > self.max_grid_export_kw:
            violations.append(
                f"Grid export {grid_export_kw:.1f}kW exceeds {self.max_grid_export_kw}kW")
            penalty += 3.0

        # Cannot import and export simultaneously
        if grid_import_kw > 0 and grid_export_kw > 0:
            violations.append("Simultaneous grid import and export")
            penalty += 5.0

        return {
            "violations" : violations,
            "penalty"    : round(penalty, 4),
            "is_valid"   : len(violations) == 0
        }

    # ----------------------------------------------------------------
    def check_pv(
        self,
        pv_used_kw      : float,
        pv_available_kw : float
    ) -> dict:
        """Check PV usage does not exceed available generation."""
        violations = []
        penalty    = 0.0

        if pv_used_kw < 0:
            violations.append("Negative PV usage")
            penalty += 3.0

        if pv_used_kw > pv_available_kw + 0.1:
            violations.append(
                f"PV used {pv_used_kw:.2f}kW > available {pv_available_kw:.2f}kW")
            penalty += 5.0 * (pv_used_kw - pv_available_kw)

        return {
            "violations" : violations,
            "penalty"    : round(penalty, 4),
            "is_valid"   : len(violations) == 0
        }

    # ----------------------------------------------------------------
    def total_penalty(
        self,
        soc            : float,
        charge_kw      : float,
        discharge_kw   : float,
        grid_import_kw : float,
        grid_export_kw : float,
        pv_used_kw     : float,
        pv_available_kw: float,
        load_kw        : float
    ) -> dict:
        """
        Compute total constraint penalty for optimizer.

        Returns:
            dict — total_penalty, all_violations, all_valid
        """
        batt = self.check_battery(soc, charge_kw, discharge_kw)
        grid = self.check_grid(grid_import_kw, grid_export_kw)
        pv   = self.check_pv(pv_used_kw, pv_available_kw)
        bal  = self.check_power_balance(
            load_kw, pv_used_kw, discharge_kw,
            charge_kw, grid_import_kw, grid_export_kw
        )

        all_violations = batt["violations"] + grid["violations"] + pv["violations"]
        if not bal["is_valid"]:
            all_violations.append(
                f"Power imbalance: {bal['balance_error']:.3f} kW")

        total = (batt["penalty"] + grid["penalty"]
                 + pv["penalty"]
                 + (10.0 if not bal["is_valid"] else 0.0))

        return {
            "total_penalty"    : round(total, 4),
            "all_violations"   : all_violations,
            "all_valid"        : len(all_violations) == 0,
            "battery_check"    : batt,
            "grid_check"       : grid,
            "pv_check"         : pv,
            "balance_check"    : bal
        }

    # ----------------------------------------------------------------
    def clamp_action(
        self,
        charge_kw      : float,
        discharge_kw   : float,
        grid_import_kw : float,
        grid_export_kw : float,
        pv_available_kw: float,
        soc            : float,
        battery_capacity_kwh: float = 100.0,
        dt_hours       : float = 0.25
    ) -> dict:
        """
        Clamp action to physically feasible range.
        Use this before applying actions to the system.

        Returns:
            dict — clamped action values
        """
        import numpy as np

        # Clamp powers to hardware limits
        charge_kw      = float(np.clip(charge_kw,      0.0, self.max_charge_kw))
        discharge_kw   = float(np.clip(discharge_kw,   0.0, self.max_discharge_kw))
        grid_import_kw = float(np.clip(grid_import_kw, 0.0, self.max_grid_import_kw))
        grid_export_kw = float(np.clip(grid_export_kw, 0.0, self.max_grid_export_kw))

        # PV cannot exceed available
        pv_used_kw = float(np.clip(pv_available_kw, 0.0, pv_available_kw))

        # Prevent over-charge (SOC would exceed max)
        # Formula: energy_in = charge_kw * charge_efficiency * dt_hours
        # So: max_charge_kw = energy / (charge_efficiency * dt_hours)
        max_charge_energy = (self.battery_soc_max - soc) * battery_capacity_kwh
        charge_efficiency = 0.95  # Standard efficiency factor
        max_charge_kw_now = max_charge_energy / (charge_efficiency * dt_hours) if dt_hours > 0 else 0.0
        charge_kw = float(np.clip(charge_kw, 0.0, max(0.0, max_charge_kw_now)))

        # Prevent over-discharge (SOC would go below min)
        # Formula: energy_out = discharge_kw / discharge_efficiency * dt_hours
        # So: max_discharge_kw = energy * discharge_efficiency / dt_hours
        max_discharge_energy = (soc - self.battery_soc_min) * battery_capacity_kwh
        discharge_efficiency = 0.95  # Standard efficiency factor
        max_discharge_kw_now = max_discharge_energy * discharge_efficiency / dt_hours if dt_hours > 0 else 0.0
        discharge_kw = float(np.clip(discharge_kw, 0.0, max(0.0, max_discharge_kw_now)))

        return {
            "charge_kw"      : round(charge_kw, 4),
            "discharge_kw"   : round(discharge_kw, 4),
            "grid_import_kw" : round(grid_import_kw, 4),
            "grid_export_kw" : round(grid_export_kw, 4),
            "pv_used_kw"     : round(pv_used_kw, 4)
        }