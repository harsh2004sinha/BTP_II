"""
Carbon Policy
Manages carbon pricing and emissions tracking
"""

from typing import List


class CarbonPolicy:
    """
    Handles carbon pricing and emissions constraints.

    Features:
        - Carbon cost per kWh of grid electricity
        - Carbon budget enforcement
        - Renewable energy credits
        - Scope 2 emissions tracking
    """

    # Typical grid carbon intensities (kg CO2 per kWh)
    GRID_CARBON_INTENSITIES = {
        "coal_heavy"  : 0.82,
        "average_us"  : 0.40,
        "average_eu"  : 0.27,
        "california"  : 0.20,
        "renewables"  : 0.05,
        "custom"      : 0.40
    }

    def __init__(
        self,
        carbon_price_per_kg   : float = 0.02,    # $/kg CO2
        grid_type             : str   = "average_us",
        custom_intensity      : float = None,
        daily_carbon_budget_kg: float = None,    # None = no budget
        enable_carbon_cost    : bool  = True
    ):
        self.carbon_price_per_kg    = carbon_price_per_kg
        self.enable_carbon_cost     = enable_carbon_cost
        self.daily_carbon_budget_kg = daily_carbon_budget_kg

        # Set carbon intensity
        if custom_intensity is not None:
            self.carbon_intensity_kg_kwh = custom_intensity
        else:
            self.carbon_intensity_kg_kwh = self.GRID_CARBON_INTENSITIES.get(
                grid_type, 0.40)

        # Tracking
        self._total_carbon_kg  = 0.0
        self._total_avoided_kg = 0.0

    # ----------------------------------------------------------------
    def compute_carbon_cost(
        self,
        grid_import_kw : float,
        dt_hours       : float = 0.25
    ) -> dict:
        """
        Compute carbon cost for one timestep.

        Args:
            grid_import_kw : Power imported from grid (kW)
            dt_hours       : Timestep duration

        Returns:
            dict with carbon_kg, carbon_cost, budget_remaining
        """
        if not self.enable_carbon_cost:
            return {
                "carbon_kg"       : 0.0,
                "carbon_cost"     : 0.0,
                "carbon_kwh"      : 0.0,
                "budget_remaining": None
            }

        energy_kwh = grid_import_kw * dt_hours
        carbon_kg  = energy_kwh * self.carbon_intensity_kg_kwh
        carbon_cost = carbon_kg * self.carbon_price_per_kg

        self._total_carbon_kg += carbon_kg

        budget_remaining = None
        if self.daily_carbon_budget_kg is not None:
            budget_remaining = max(
                0.0,
                self.daily_carbon_budget_kg - self._total_carbon_kg
            )

        return {
            "carbon_kg"        : round(carbon_kg, 5),
            "carbon_cost"      : round(carbon_cost, 6),
            "energy_kwh"       : round(energy_kwh, 4),
            "budget_remaining" : (round(budget_remaining, 3)
                                  if budget_remaining is not None else None),
            "total_carbon_kg"  : round(self._total_carbon_kg, 4)
        }

    # ----------------------------------------------------------------
    def compute_avoided_emissions(
        self,
        pv_kw        : float,
        dt_hours     : float = 0.25
    ) -> float:
        """
        Calculate CO2 avoided by using solar instead of grid.

        Args:
            pv_kw    : Solar power used (kW)
            dt_hours : Timestep duration

        Returns:
            Avoided kg CO2
        """
        avoided = pv_kw * dt_hours * self.carbon_intensity_kg_kwh
        self._total_avoided_kg += avoided
        return round(avoided, 5)

    # ----------------------------------------------------------------
    def is_over_budget(self) -> bool:
        """Check if daily carbon budget exceeded."""
        if self.daily_carbon_budget_kg is None:
            return False
        return self._total_carbon_kg >= self.daily_carbon_budget_kg

    # ----------------------------------------------------------------
    def get_carbon_penalty(self) -> float:
        """
        Get penalty if carbon budget is exceeded.

        Returns:
            float — penalty value for optimizer
        """
        if not self.is_over_budget():
            return 0.0
        overshoot = self._total_carbon_kg - self.daily_carbon_budget_kg
        return overshoot * self.carbon_price_per_kg * 5.0  # 5x penalty

    # ----------------------------------------------------------------
    def get_summary(self) -> dict:
        """Return carbon tracking summary."""
        return {
            "total_carbon_kg"    : round(self._total_carbon_kg, 4),
            "total_avoided_kg"   : round(self._total_avoided_kg, 4),
            "net_carbon_kg"      : round(self._total_carbon_kg - self._total_avoided_kg, 4),
            "carbon_intensity"   : self.carbon_intensity_kg_kwh,
            "daily_budget_kg"    : self.daily_carbon_budget_kg,
            "budget_exceeded"    : self.is_over_budget(),
            "total_carbon_cost"  : round(
                self._total_carbon_kg * self.carbon_price_per_kg, 4)
        }

    # ----------------------------------------------------------------
    def reset_daily(self):
        """Reset daily tracking (call at midnight)."""
        self._total_carbon_kg  = 0.0
        self._total_avoided_kg = 0.0

    # ----------------------------------------------------------------
    def set_carbon_price(self, price_per_kg: float):
        """Update carbon price (from policy settings)."""
        self.carbon_price_per_kg = max(0.0, price_per_kg)

    # ----------------------------------------------------------------
    def get_daily_profile(
        self,
        grid_import_profile: List[float],
        pv_profile         : List[float],
        dt_hours           : float = 0.25
    ) -> dict:
        """
        Calculate carbon stats for a full day profile.

        Args:
            grid_import_profile : List of grid import values (kW)
            pv_profile          : List of PV values (kW)
            dt_hours            : Timestep duration

        Returns:
            dict with daily carbon stats
        """
        total_carbon  = 0.0
        total_avoided = 0.0
        total_cost    = 0.0

        for g, p in zip(grid_import_profile, pv_profile):
            c_step   = g * dt_hours * self.carbon_intensity_kg_kwh
            av_step  = p * dt_hours * self.carbon_intensity_kg_kwh
            total_carbon  += c_step
            total_avoided += av_step
            total_cost    += c_step * self.carbon_price_per_kg

        return {
            "total_carbon_kg"  : round(total_carbon, 3),
            "total_avoided_kg" : round(total_avoided, 3),
            "net_carbon_kg"    : round(total_carbon - total_avoided, 3),
            "total_carbon_cost": round(total_cost, 4),
            "renewable_fraction": round(
                total_avoided / (total_carbon + total_avoided)
                if (total_carbon + total_avoided) > 0 else 0.0, 4)
        }