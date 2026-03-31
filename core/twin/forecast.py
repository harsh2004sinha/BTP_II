"""
Forecast Module
Generates probabilistic forecasts for PV, load, and electricity price
"""

import numpy as np
from typing import List, Tuple

from ..models.pv_model   import PVModel
from ..models.load_model import LoadModel


class Forecaster:
    """
    Short-horizon probabilistic forecasts for microgrid optimization.

    Outputs: mean + standard deviation per timestep.
    In production: replace with LSTM / Prophet model.
    Here     : physics-based + empirical patterns.
    """

    def __init__(
        self,
        pv_model              : PVModel   = None,
        load_model            : LoadModel = None,
        horizon               : int   = 96,
        dt_hours              : float = 0.25,
        pv_uncertainty_frac   : float = 0.15,
        load_uncertainty_frac : float = 0.08,
        price_uncertainty_frac: float = 0.05
    ):
        self.pv_model               = pv_model   or PVModel()
        self.load_model             = load_model or LoadModel()
        self.horizon                = horizon
        self.dt_hours               = dt_hours
        self.pv_uncertainty_frac    = pv_uncertainty_frac
        self.load_uncertainty_frac  = load_uncertainty_frac
        self.price_uncertainty_frac = price_uncertainty_frac

    # ----------------------------------------------------------------
    def forecast_pv(
        self,
        current_hour : float,
        area_m2      : float,
        peak_irr     : float = 800.0,
        cloud_factor : float = 1.0
    ) -> Tuple[List[float], List[float]]:
        """Forecast PV for next `horizon` timesteps. Returns (mean, std)."""
        mean_kw, std_kw = [], []
        for i in range(self.horizon):
            fhour = (current_hour + i * self.dt_hours) % 24.0
            if 6.0 <= fhour <= 18.0:
                angle      = np.pi * (fhour - 6.0) / 12.0
                irradiance = peak_irr * np.sin(angle) * cloud_factor
            else:
                irradiance = 0.0
            res    = self.pv_model.pv_power(irradiance, area_m2)
            pv_mu  = res["power_kw"]
            pv_sig = pv_mu * self.pv_uncertainty_frac * (1.0 + 0.5 * i / self.horizon)
            mean_kw.append(round(pv_mu, 3))
            std_kw.append(round(pv_sig, 3))
        return mean_kw, std_kw

    # ----------------------------------------------------------------
    def forecast_load(
        self,
        current_hour : float,
        day_type     : str = "weekday"
    ) -> Tuple[List[float], List[float]]:
        """Forecast campus load for next `horizon` timesteps. Returns (mean, std)."""
        mean_kw, std_kw = [], []
        for i in range(self.horizon):
            fhour   = (current_hour + i * self.dt_hours) % 24.0
            mu      = self.load_model.load_power(fhour, day_type, add_noise=False)
            sig     = mu * self.load_uncertainty_frac * (1.0 + 0.3 * i / self.horizon)
            mean_kw.append(round(mu, 3))
            std_kw.append(round(sig, 3))
        return mean_kw, std_kw

    # ----------------------------------------------------------------
    def forecast_price(
        self,
        current_hour    : float,
        tariff_schedule : dict = None
    ) -> Tuple[List[float], List[float]]:
        """
        Forecast electricity price using TOU tariff.

        Default TOU:
            Off-peak  22:00–07:00 → \$0.08 / kWh
            Mid-peak  07:00–17:00 → \$0.15 / kWh
            On-peak   17:00–22:00 → \$0.25 / kWh
        """
        if tariff_schedule is None:
            tariff_schedule = {
                "off_peak": {"hours": list(range(22, 24)) + list(range(0, 7)), "price": 0.08},
                "mid_peak": {"hours": list(range(7, 17)),  "price": 0.15},
                "on_peak" : {"hours": list(range(17, 22)), "price": 0.25}
            }
        mean_p, std_p = [], []
        for i in range(self.horizon):
            fhour = int((current_hour + i * self.dt_hours) % 24)
            price = 0.10
            for _, info in tariff_schedule.items():
                if fhour in info["hours"]:
                    price = info["price"]
                    break
            mean_p.append(round(price, 4))
            std_p.append(round(price * self.price_uncertainty_frac, 4))
        return mean_p, std_p

    # ----------------------------------------------------------------
    def get_forecast_bundle(
        self,
        current_hour : float,
        area_m2      : float,
        day_type     : str   = "weekday",
        cloud_factor : float = 1.0
    ):
        """Return complete ForecastBundle for the optimizer."""
        from ..twin.twin_state import ForecastBundle

        pv_mu,    pv_sig    = self.forecast_pv(current_hour, area_m2, cloud_factor=cloud_factor)
        load_mu,  load_sig  = self.forecast_load(current_hour, day_type)
        price_mu, price_sig = self.forecast_price(current_hour)

        return ForecastBundle(
            pv_mean    = pv_mu,
            pv_std     = pv_sig,
            load_mean  = load_mu,
            load_std   = load_sig,
            price_mean = price_mu,
            price_std  = price_sig,
            horizon    = self.horizon
        )