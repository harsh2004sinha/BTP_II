"""
Battery Physical Model
Simulates real battery behavior: charging, discharging, SOC tracking
"""

import numpy as np


class BatteryModel:
    """
    Simulates a lithium-ion / LiFePO4 battery for campus microgrid.

    Tracks:
        - State of Charge (SOC)
        - Charge / Discharge power
        - Efficiency losses
        - Cycle count (for degradation)
    """

    def __init__(
        self,
        capacity_kwh       : float = 100.0,
        max_charge_kw      : float = 50.0,
        max_discharge_kw   : float = 50.0,
        soc_min            : float = 0.10,
        soc_max            : float = 0.90,
        charge_efficiency  : float = 0.95,
        discharge_efficiency: float = 0.95,
        initial_soc        : float = 0.50,
        temperature_c      : float = 25.0
    ):
        self.capacity_kwh         = capacity_kwh
        self.max_charge_kw        = max_charge_kw
        self.max_discharge_kw     = max_discharge_kw
        self.soc_min              = soc_min
        self.soc_max              = soc_max
        self.charge_efficiency    = charge_efficiency
        self.discharge_efficiency = discharge_efficiency
        self.soc                  = initial_soc
        self.temperature_c        = temperature_c

        # Tracking
        self.total_energy_charged_kwh    = 0.0
        self.total_energy_discharged_kwh = 0.0
        self.cycle_count                 = 0.0
        self.soc_history                 = [initial_soc]

    # ----------------------------------------------------------------
    def step(
        self,
        charge_kw   : float,
        discharge_kw: float,
        dt_hours    : float = 0.25
    ) -> dict:
        """
        Advance battery by one timestep.

        Args:
            charge_kw    : Power going INTO battery (kW)
            discharge_kw : Power coming OUT of battery (kW)
            dt_hours     : Duration of timestep in hours (default 15 min)

        Returns:
            dict — new SOC, actual powers, cycle count, flags
        """

        if self.capacity_kwh <= 0:
            return {
                "soc"            : 0.0,
                "charge_kw"      : 0.0,
                "discharge_kw"   : 0.0,
                "energy_in_kwh"  : 0.0,
                "energy_out_kwh" : 0.0,
                "cycle_count"    : 0.0,
                "at_min_soc"     : True,
                "at_max_soc"     : True
            }

        # Clamp to physical limits
        charge_kw    = np.clip(charge_kw,    0.0, self.max_charge_kw)
        discharge_kw = np.clip(discharge_kw, 0.0, self.max_discharge_kw)

        # Cannot do both simultaneously — net decides direction
        if charge_kw > 0 and discharge_kw > 0:
            net = charge_kw - discharge_kw
            if net > 0:
                charge_kw, discharge_kw = net, 0.0
            else:
                charge_kw, discharge_kw = 0.0, -net

        # Energy delta
        energy_in  = charge_kw    * self.charge_efficiency    * dt_hours
        energy_out = discharge_kw / self.discharge_efficiency * dt_hours

        # SOC update
        soc_new = self.soc + (energy_in - energy_out) / self.capacity_kwh
        soc_new = np.clip(soc_new, self.soc_min, self.soc_max)

        # Recalculate actual power after clamping
        actual_delta = (soc_new - self.soc) * self.capacity_kwh

        if actual_delta >= 0:
            actual_charge_kw    = actual_delta / (self.charge_efficiency * dt_hours)
            actual_discharge_kw = 0.0
        else:
            actual_charge_kw    = 0.0
            actual_discharge_kw = abs(actual_delta) * self.discharge_efficiency / dt_hours

        # Update trackers
        self.total_energy_charged_kwh    += actual_charge_kw    * dt_hours
        self.total_energy_discharged_kwh += actual_discharge_kw * dt_hours
        self.cycle_count                 += (actual_charge_kw * dt_hours) / self.capacity_kwh

        self.soc = soc_new
        self.soc_history.append(self.soc)

        return {
            "soc"            : round(self.soc, 4),
            "charge_kw"      : round(actual_charge_kw, 4),
            "discharge_kw"   : round(actual_discharge_kw, 4),
            "energy_in_kwh"  : round(actual_charge_kw    * dt_hours, 4),
            "energy_out_kwh" : round(actual_discharge_kw * dt_hours, 4),
            "cycle_count"    : round(self.cycle_count, 4),
            "at_min_soc"     : self.soc <= self.soc_min + 0.01,
            "at_max_soc"     : self.soc >= self.soc_max - 0.01
        }

    # ----------------------------------------------------------------
    def available_discharge_kw(self, dt_hours: float = 0.25) -> float:
        """Max power battery can deliver right now."""
        if self.capacity_kwh <= 0: return 0.0
        max_energy = (self.soc - self.soc_min) * self.capacity_kwh
        return min(self.max_discharge_kw,
                   max_energy * self.discharge_efficiency / dt_hours)

    def available_charge_kw(self, dt_hours: float = 0.25) -> float:
        """Max power battery can absorb right now."""
        if self.capacity_kwh <= 0: return 0.0
        max_energy = (self.soc_max - self.soc) * self.capacity_kwh
        return min(self.max_charge_kw,
                   max_energy / (self.charge_efficiency * dt_hours))

    def reset(self, soc: float = 0.50):
        self.soc                          = soc
        self.total_energy_charged_kwh     = 0.0
        self.total_energy_discharged_kwh  = 0.0
        self.cycle_count                  = 0.0
        self.soc_history                  = [soc]

    def get_status(self) -> dict:
        return {
            "soc"                        : round(self.soc, 4),
            "soc_percent"                : round(self.soc * 100, 2),
            "capacity_kwh"               : self.capacity_kwh,
            "usable_energy_kwh"          : round((self.soc - self.soc_min) * self.capacity_kwh, 3),
            "total_energy_charged_kwh"   : round(self.total_energy_charged_kwh, 3),
            "total_energy_discharged_kwh": round(self.total_energy_discharged_kwh, 3),
            "cycle_count"                : round(self.cycle_count, 3),
            "max_discharge_kw"           : self.max_discharge_kw,
            "max_charge_kw"              : self.max_charge_kw,
        }