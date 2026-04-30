"""
Battery Degradation Model
Calculates battery aging cost per timestep
"""

import numpy as np


class DegradationModel:
    """
    Estimates battery degradation cost.

    FIX: total_lifecycle_kwh now scales with battery_capacity_kwh.
    OLD: fixed 50000 kWh for any battery size → base_cost wrong for small batteries
         10 kWh battery: base = 300*10/50000 = \$0.06/kWh
         100 kWh battery: base = 300*100/50000 = \$0.60/kWh  ← inconsistent
    NEW: lifecycle_cycles × capacity_kwh = total throughput
         Any battery: base = battery_cost_per_kwh / lifecycle_cycles
         = 300 / 3000 = \$0.10/kWh  ← same for all sizes, only C-rate stress differs
    """

    def __init__(
        self,
        battery_cost_per_kwh : float = 300.0,
        battery_capacity_kwh : float = 100.0,
        total_lifecycle_kwh  : float = None,    # None = auto-scale with capacity
        lifecycle_cycles     : float = 3000.0,  # typical LFP full cycles
        stress_weight_soc    : float = 0.60,
        stress_weight_crate  : float = 0.40
    ):
        self.battery_cost_per_kwh = battery_cost_per_kwh
        self.battery_capacity_kwh = battery_capacity_kwh
        self.stress_weight_soc    = stress_weight_soc
        self.stress_weight_crate  = stress_weight_crate

        if self.battery_capacity_kwh <= 0:
            self.total_lifecycle_kwh    = 0.0
            self.lifecycle_cycles       = 0.0
            self.total_replacement_cost = 0.0
            self.base_cost_per_kwh      = 0.0
            return

        # FIX: Scale total_lifecycle_kwh with capacity so base_cost_per_kwh
        # is independent of battery size — only C-rate stress differs per size.
        # OLD (wrong): total_lifecycle_kwh = 50000 always
        #   → base_cost = 300*100/50000 = $0.60/kWh (too high, kills all battery actions)
        # NEW (correct): total_lifecycle_kwh = lifecycle_cycles * capacity_kwh
        #   → base_cost = battery_cost / lifecycle_cycles = $0.10/kWh (realistic)
        if total_lifecycle_kwh is None:
            total_lifecycle_kwh = lifecycle_cycles * battery_capacity_kwh

        self.total_lifecycle_kwh    = total_lifecycle_kwh
        self.lifecycle_cycles       = lifecycle_cycles
        self.total_replacement_cost = battery_cost_per_kwh * battery_capacity_kwh
        self.base_cost_per_kwh      = self.total_replacement_cost / total_lifecycle_kwh
        # = battery_cost_per_kwh / lifecycle_cycles = 300/3000 = \$0.10/kWh

    # ----------------------------------------------------------------
    def degradation_cost(
        self,
        charge_kw     : float,
        discharge_kw  : float,
        current_soc   : float,
        dt_hours      : float = 0.25,
        temperature_c : float = 25.0
    ) -> dict:
        """
        Calculate degradation cost for one timestep.
        """
        energy_kwh = (charge_kw + discharge_kw) * dt_hours

        if energy_kwh == 0 or self.battery_capacity_kwh <= 0:
            return {
                "degradation_cost"     : 0.0,
                "degradation_fraction" : 0.0,
                "soc_stress_factor"    : 0.0,
                "crate_stress_factor"  : 0.0,
                "temp_stress_factor"   : 1.0,
                "energy_kwh"           : 0.0
            }

        soc_stress   = self._soc_stress(current_soc)
        crate_stress = self._crate_stress(
            max(charge_kw, discharge_kw) / self.battery_capacity_kwh)
        temp_stress  = self._temperature_stress(temperature_c)

        stress   = (self.stress_weight_soc   * soc_stress
                  + self.stress_weight_crate * crate_stress) * temp_stress

        deg_cost = self.base_cost_per_kwh * energy_kwh * stress

        return {
            "degradation_cost"     : round(deg_cost, 6),
            "degradation_fraction" : round(deg_cost / self.total_replacement_cost, 8),
            "soc_stress_factor"    : round(soc_stress, 4),
            "crate_stress_factor"  : round(crate_stress, 4),
            "temp_stress_factor"   : round(temp_stress, 4),
            "energy_kwh"           : round(energy_kwh, 4)
        }

    # ----------------------------------------------------------------
    def _soc_stress(self, soc: float) -> float:
        """U-shaped: low stress at 50% SOC, high at extremes."""
        return 1.0 + 2.0 * abs(soc - 0.5)

    def _crate_stress(self, c_rate: float) -> float:
        """Higher C-rate = more stress. Quadratic."""
        return 1.0 + 1.5 * (c_rate ** 2)

    def _temperature_stress(self, temperature_c: float) -> float:
        """Arrhenius-inspired: stress increases above 25°C."""
        delta = max(0.0, temperature_c - 25.0)
        return 1.0 + 0.02 * delta