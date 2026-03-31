"""
Battery Degradation Model
Calculates battery aging cost per timestep
"""

import numpy as np


class DegradationModel:
    """
    Estimates battery degradation cost.

    Degradation depends on:
        - Depth of Discharge (DoD)
        - SOC at time of operation
        - C-rate (charge/discharge speed)
        - Temperature

    Cost = degradation_fraction × replacement_cost
    """

    def __init__(
        self,
        battery_cost_per_kwh : float = 300.0,
        battery_capacity_kwh : float = 100.0,
        total_lifecycle_kwh  : float = 50000.0,
        stress_weight_soc    : float = 0.60,
        stress_weight_crate  : float = 0.40
    ):
        self.battery_cost_per_kwh = battery_cost_per_kwh
        self.battery_capacity_kwh = battery_capacity_kwh
        self.total_lifecycle_kwh  = total_lifecycle_kwh
        self.stress_weight_soc    = stress_weight_soc
        self.stress_weight_crate  = stress_weight_crate

        self.total_replacement_cost = battery_cost_per_kwh * battery_capacity_kwh
        self.base_cost_per_kwh      = self.total_replacement_cost / total_lifecycle_kwh

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

        Returns:
            dict with cost, factors
        """
        energy_kwh = (charge_kw + discharge_kw) * dt_hours

        if energy_kwh == 0:
            return {
                "degradation_cost"     : 0.0,
                "degradation_fraction" : 0.0,
                "soc_stress_factor"    : 0.0,
                "crate_stress_factor"  : 0.0,
                "temp_stress_factor"   : 1.0,
                "energy_kwh"           : 0.0
            }

        soc_stress    = self._soc_stress(current_soc)
        crate_stress  = self._crate_stress(
            max(charge_kw, discharge_kw) / self.battery_capacity_kwh)
        temp_stress   = self._temperature_stress(temperature_c)

        stress     = (self.stress_weight_soc   * soc_stress
                    + self.stress_weight_crate * crate_stress) * temp_stress

        deg_cost   = self.base_cost_per_kwh * energy_kwh * stress

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