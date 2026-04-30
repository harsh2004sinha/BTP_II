"""
Photovoltaic (Solar) Generation Model
Calculates real solar power output from irradiance and panel specs
"""

import numpy as np
from typing import List


class PVModel:
    """
    Simulates solar PV generation for campus rooftop installation.

    Physics model:
        P = Area × Efficiency × Irradiance × Temperature_derating
    """

    def __init__(
        self,
        panel_efficiency    : float = 0.20,
        system_losses       : float = 0.14,
        temp_coefficient    : float = -0.004,
        noct                : float = 45.0,
        stc_irradiance      : float = 1000.0,
        inverter_efficiency : float = 0.97
    ):
        self.panel_efficiency    = panel_efficiency
        self.system_losses       = system_losses
        self.temp_coefficient    = temp_coefficient
        self.noct                = noct
        self.stc_irradiance      = stc_irradiance
        self.inverter_efficiency = inverter_efficiency

        # Combined base efficiency (without temperature)
        self.base_efficiency = (
            self.panel_efficiency
            * (1 - self.system_losses)
            * self.inverter_efficiency
        )

    # ----------------------------------------------------------------
    def pv_power(
        self,
        irradiance_wm2  : float,
        area_m2         : float,
        ambient_temp_c  : float = 25.0
    ) -> dict:
        """
        Calculate solar power output at a single timestep.
        """
        if irradiance_wm2 <= 0:
            return {
                "power_kw"   : 0.0,
                "power_w"    : 0.0,
                "cell_temp_c": ambient_temp_c,
                "efficiency" : 0.0,
                "irradiance" : irradiance_wm2
            }

        # Cell temperature via NOCT model
        cell_temp_c  = ambient_temp_c + (self.noct - 20) * (irradiance_wm2 / 800)

        # Temperature derating
        temp_derate  = 1 + self.temp_coefficient * (cell_temp_c - 25.0)
        temp_derate  = max(temp_derate, 0.5)

        effective_eff = self.base_efficiency * temp_derate

        power_w  = effective_eff * irradiance_wm2 * area_m2
        power_kw = power_w / 1000.0

        return {
            "power_kw"   : round(power_kw, 4),
            "power_w"    : round(power_w, 3),
            "cell_temp_c": round(cell_temp_c, 2),
            "efficiency" : round(effective_eff, 4),
            "irradiance" : irradiance_wm2
        }

    # ----------------------------------------------------------------
    def generate_daily_profile(
        self,
        irradiance_profile: List[float],
        area_m2           : float,
        temp_profile      : List[float] = None,
        dt_hours          : float = 0.25
    ) -> List[dict]:
        """
        Generate full-day PV profile from irradiance timeseries.
        """
        n = len(irradiance_profile)
        if temp_profile is None:
            temp_profile = [25.0] * n

        results = []
        for t in range(n):
            res = self.pv_power(irradiance_profile[t], area_m2, temp_profile[t])
            res["timestep"]   = t
            res["energy_kwh"] = round(res["power_kw"] * dt_hours, 4)
            res["hour"]       = round(t * dt_hours, 2)
            results.append(res)
        return results

    # ----------------------------------------------------------------
    def size_system(
        self,
        target_kwh_per_day         : float,
        avg_irradiance_wm2         : float = 500.0,   # kept for API compat, not used in formula
        peak_sun_hours             : float = 5.0,
        roof_area_available_m2     : float = 1000.0
    ) -> dict:
        """
        Estimate required panel area for a daily energy target.

        FIX BUG 11: Removed double-counting of solar resource.
        OLD (wrong): energy_per_m2 = base_efficiency * avg_irradiance_wm2 * peak_sun_hours / 1000
            → This multiplied irradiance AND peak_sun_hours (both encode the same resource)
            → Caused 70% overestimate in solar sizing
        NEW (correct): energy_per_m2 = base_efficiency * peak_sun_hours
            → peak_sun_hours = kWh/m²/day at reference 1 kW/m² — already the full resource
        """
        # FIXED: peak_sun_hours already = kWh/m²/day, no need to multiply irradiance
        energy_per_m2    = self.base_efficiency * peak_sun_hours
        required_area_m2 = target_kwh_per_day / energy_per_m2 if energy_per_m2 > 0 else 0
        actual_area_m2   = min(required_area_m2, roof_area_available_m2)
        # peak_power is always rated at STC (1000 W/m²) — this formula is correct
        peak_power_kw    = actual_area_m2 * self.base_efficiency * self.stc_irradiance / 1000

        return {
            "required_area_m2"   : round(required_area_m2, 2),
            "recommended_area_m2": round(actual_area_m2, 2),
            "peak_power_kw"      : round(peak_power_kw, 3),
            "daily_energy_kwh"   : round(actual_area_m2 * energy_per_m2, 3),
            "roof_limited"       : required_area_m2 > roof_area_available_m2
        }

    # ----------------------------------------------------------------
    @staticmethod
    def synthetic_irradiance(
        n_steps   : int   = 96,
        dt_hours  : float = 0.25,
        peak_irr  : float = 900.0,
        sunrise_h : float = 6.0,
        sunset_h  : float = 18.0,
        noise_std : float = 30.0
    ) -> List[float]:
        """Generate synthetic bell-curve irradiance profile."""
        out = []
        for t in range(n_steps):
            hour = t * dt_hours
            if sunrise_h <= hour <= sunset_h:
                angle = np.pi * (hour - sunrise_h) / (sunset_h - sunrise_h)
                base  = peak_irr * np.sin(angle)
                noise = np.random.normal(0, noise_std)
                out.append(max(0.0, base + noise))
            else:
                out.append(0.0)
        return out