"""
Campus Load Demand Model
Converts billing data into 15-minute load profiles
"""

import numpy as np
from typing import List


class LoadModel:
    """
    Generates realistic campus electricity load profiles.

    Campus loads:
        - Classrooms / Labs
        - HVAC systems
        - Lighting
        - Hostels / dormitories
        - Administrative buildings
    """

    # Normalized hourly distribution (24 hours, fraction of peak)
    CAMPUS_HOURLY_DISTRIBUTION = [
        0.30, 0.25, 0.22, 0.20, 0.22, 0.28,   # 00–05 night / low
        0.40, 0.58, 0.75, 0.88, 0.95, 0.98,   # 06–11 morning rise
        1.00, 0.97, 0.95, 0.93, 0.90, 0.88,   # 12–17 daytime high
        0.85, 0.80, 0.72, 0.62, 0.50, 0.38,   # 18–23 evening drop
    ]

    DAY_MULTIPLIERS = {
        "weekday" : 1.00,
        "saturday": 0.75,
        "sunday"  : 0.55,
        "holiday" : 0.40,
        "exam"    : 0.85,
    }

    def __init__(
        self,
        base_load_kw        : float = 200.0,
        peak_load_kw        : float = 800.0,
        noise_std_fraction  : float = 0.05
    ):
        self.base_load_kw       = base_load_kw
        self.peak_load_kw       = peak_load_kw
        self.noise_std_fraction = noise_std_fraction

    # ----------------------------------------------------------------
    def load_power(
        self,
        hour     : float,
        day_type : str  = "weekday",
        add_noise: bool = True
    ) -> float:
        """
        Get load demand at a specific hour.

        Args:
            hour      : Hour of day (0 – 23.75)
            day_type  : "weekday" / "saturday" / "sunday" / "holiday"
            add_noise : Add stochastic noise for realism

        Returns:
            Load in kW
        """
        hour_idx   = int(hour) % 24
        dist_val   = self.CAMPUS_HOURLY_DISTRIBUTION[hour_idx]
        multiplier = self.DAY_MULTIPLIERS.get(day_type, 1.0)

        load = (self.base_load_kw
                + (self.peak_load_kw - self.base_load_kw) * dist_val * multiplier)

        if add_noise:
            noise = np.random.normal(0, self.noise_std_fraction * load)
            load  = max(self.base_load_kw * 0.5, load + noise)

        return round(load, 3)

    # ----------------------------------------------------------------
    def generate_daily_profile(
        self,
        day_type  : str   = "weekday",
        dt_hours  : float = 0.25,
        add_noise : bool  = True
    ) -> List[dict]:
        """Generate full-day 15-min load profile."""
        n_steps = int(24 / dt_hours)
        profile = []
        for t in range(n_steps):
            hour    = t * dt_hours
            load_kw = self.load_power(hour, day_type, add_noise)
            profile.append({
                "timestep": t,
                "hour"    : round(hour, 2),
                "load_kw" : load_kw,
                "day_type": day_type
            })
        return profile

    # ----------------------------------------------------------------
    def from_monthly_bill(
        self,
        monthly_units_kwh: float,
        day_type         : str   = "weekday",
        dt_hours         : float = 0.25
    ) -> List[dict]:
        """
        Build scaled daily profile from monthly electricity bill.

        Args:
            monthly_units_kwh : Total kWh in bill
            day_type          : Day type

        Returns:
            Scaled 15-min profile
        """
        daily_kwh   = monthly_units_kwh / 30.0
        raw_profile = self.generate_daily_profile(day_type, dt_hours, add_noise=False)
        total_raw   = sum(p["load_kw"] * dt_hours for p in raw_profile)
        scale       = daily_kwh / total_raw if total_raw > 0 else 1.0

        scaled = []
        for p in raw_profile:
            scaled.append({
                "timestep"  : p["timestep"],
                "hour"      : p["hour"],
                "load_kw"   : round(p["load_kw"] * scale, 4),
                "energy_kwh": round(p["load_kw"] * scale * dt_hours, 4),
                "day_type"  : day_type
            })
        return scaled

    # ----------------------------------------------------------------
    def get_daily_energy_kwh(self, day_type: str = "weekday") -> float:
        profile = self.generate_daily_profile(day_type, dt_hours=1.0, add_noise=False)
        return round(sum(p["load_kw"] for p in profile), 2)

    def get_peak_demand_kw(self, day_type: str = "weekday") -> float:
        profile = self.generate_daily_profile(day_type, dt_hours=0.25, add_noise=False)
        return max(p["load_kw"] for p in profile)