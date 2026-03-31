"""
Twin State — Complete system state snapshot
Shared across all layers: twin, optimizer, learner, explainer
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import time


@dataclass
class ForecastBundle:
    """Holds probabilistic forecast arrays."""
    pv_mean    : List[float] = field(default_factory=list)
    pv_std     : List[float] = field(default_factory=list)
    load_mean  : List[float] = field(default_factory=list)
    load_std   : List[float] = field(default_factory=list)
    price_mean : List[float] = field(default_factory=list)
    price_std  : List[float] = field(default_factory=list)
    horizon    : int = 96


@dataclass
class TwinState:
    """
    Complete microgrid state at a single moment.

    This is the main data object passed between all layers.
    Think of it as a live snapshot of the real campus.
    """

    # ---- Time ----
    timestamp      : float = field(default_factory=time.time)
    timestep       : int   = 0
    hour_of_day    : float = 0.0
    day_type       : str   = "weekday"

    # ---- Battery ----
    soc             : float = 0.50
    soc_uncertainty : float = 0.02
    battery_kw      : float = 0.0    # + = charging, - = discharging
    battery_health  : float = 1.0    # 0–1 remaining capacity fraction
    cycle_count     : float = 0.0

    # ---- Solar PV ----
    pv_power_kw     : float = 0.0
    pv_available_kw : float = 0.0
    irradiance      : float = 0.0
    pv_curtailed_kw : float = 0.0

    # ---- Load ----
    load_kw         : float = 0.0
    load_unserved   : float = 0.0

    # ---- Grid ----
    grid_import_kw  : float = 0.0
    grid_export_kw  : float = 0.0
    grid_price      : float = 0.10
    feed_in_tariff  : float = 0.05

    # ---- Economics ----
    cost_so_far     : float = 0.0
    revenue_so_far  : float = 0.0

    # ---- Carbon ----
    carbon_intensity : float = 0.40
    carbon_emitted   : float = 0.0

    # ---- Forecast ----
    forecast         : Optional[ForecastBundle] = None

    # ---- Flags ----
    demand_response_active : bool = False
    islanded               : bool = False
    emergency_mode         : bool = False

    # ----------------------------------------------------------------
    def to_dict(self) -> dict:
        """Convert state to plain dictionary (JSON-safe)."""
        d = asdict(self)
        return d

    def to_vector(self) -> List[float]:
        """
        Flat numeric vector for RL agent observation space.
        All values normalized to [0, 1] roughly.
        """
        return [
            self.soc,
            self.pv_power_kw    / 500.0,
            self.load_kw        / 1000.0,
            self.grid_price     / 0.30,
            self.hour_of_day    / 24.0,
            float(self.day_type == "weekday"),
            self.battery_health,
            float(self.demand_response_active),
            self.carbon_intensity / 0.60,
            self.soc_uncertainty  / 0.10
        ]

    @property
    def net_load_kw(self) -> float:
        """Net demand after PV covers what it can."""
        return max(0.0, self.load_kw - self.pv_power_kw)

    @property
    def pv_surplus_kw(self) -> float:
        """PV generation beyond current load."""
        return max(0.0, self.pv_power_kw - self.load_kw)

    @property
    def observation_space_size(self) -> int:
        return len(self.to_vector())