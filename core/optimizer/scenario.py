"""
Scenario Generator
Creates multiple possible future scenarios for stochastic optimization
"""

import numpy as np
from typing import List, Tuple
from ..twin.twin_state import ForecastBundle


class ScenarioGenerator:
    """
    Generates N scenarios from forecast mean + std.

    Purpose:
        Optimizer uses multiple scenarios to make robust decisions
        that work well under uncertainty.

    Method:
        Monte Carlo sampling from normal distribution
        defined by forecast mean and std.
    """

    def __init__(
        self,
        n_scenarios   : int   = 10,
        seed          : int   = 42,
        clip_negative : bool  = True
    ):
        self.n_scenarios   = n_scenarios
        self.clip_negative = clip_negative
        np.random.seed(seed)

    # ----------------------------------------------------------------
    def generate(
        self,
        forecast     : ForecastBundle,
        n_scenarios  : int = None
    ) -> List[dict]:
        """
        Generate N scenarios from a ForecastBundle.

        Each scenario has:
            pv    : List[float]   — kW per timestep
            load  : List[float]   — kW per timestep
            price : List[float]   — $/kWh per timestep

        Args:
            forecast    : ForecastBundle from Forecaster
            n_scenarios : Override default n_scenarios

        Returns:
            List of scenario dicts
        """
        n = n_scenarios or self.n_scenarios
        horizon = forecast.horizon

        scenarios = []

        for s in range(n):
            pv_scenario    = self._sample(forecast.pv_mean,    forecast.pv_std,    horizon)
            load_scenario  = self._sample(forecast.load_mean,  forecast.load_std,  horizon)
            price_scenario = self._sample(forecast.price_mean, forecast.price_std, horizon)

            # Price stays non-negative always
            price_scenario = [max(0.01, p) for p in price_scenario]

            scenarios.append({
                "scenario_id" : s,
                "pv"          : pv_scenario,
                "load"        : load_scenario,
                "price"       : price_scenario,
                "weight"      : 1.0 / n       # Equal probability
            })

        return scenarios

    # ----------------------------------------------------------------
    def generate_from_arrays(
        self,
        pv_mean    : List[float],
        pv_std     : List[float],
        load_mean  : List[float],
        load_std   : List[float],
        price_mean : List[float],
        price_std  : List[float],
        n_scenarios: int = None
    ) -> List[dict]:
        """
        Generate scenarios directly from arrays.

        Returns:
            List of scenario dicts
        """
        n       = n_scenarios or self.n_scenarios
        horizon = len(pv_mean)
        scenarios = []

        for s in range(n):
            scenarios.append({
                "scenario_id" : s,
                "pv"          : self._sample(pv_mean,    pv_std,    horizon),
                "load"        : self._sample(load_mean,  load_std,  horizon),
                "price"       : [max(0.01, p) for p in
                                 self._sample(price_mean, price_std, horizon)],
                "weight"      : 1.0 / n
            })

        return scenarios

    # ----------------------------------------------------------------
    def _sample(
        self,
        mean   : List[float],
        std    : List[float],
        horizon: int
    ) -> List[float]:
        """
        Sample one scenario from mean ± std.

        Args:
            mean    : Mean forecast
            std     : Standard deviation
            horizon : Number of timesteps

        Returns:
            List of sampled values
        """
        samples = []
        for t in range(min(horizon, len(mean))):
            mu  = mean[t]
            sig = std[t] if t < len(std) else 0.0
            val = np.random.normal(mu, sig)
            if self.clip_negative:
                val = max(0.0, val)
            samples.append(round(val, 4))
        return samples

    # ----------------------------------------------------------------
    def get_percentile_scenario(
        self,
        forecast   : ForecastBundle,
        percentile : float = 50.0
    ) -> dict:
        """
        Get a specific percentile scenario (e.g., worst case = p5).

        Args:
            forecast   : ForecastBundle
            percentile : 0–100

        Returns:
            Single scenario dict
        """
        # Generate many samples and pick percentile
        n_large = 500
        all_pv    = np.array([self._sample(forecast.pv_mean,    forecast.pv_std,    forecast.horizon) for _ in range(n_large)])
        all_load  = np.array([self._sample(forecast.load_mean,  forecast.load_std,  forecast.horizon) for _ in range(n_large)])
        all_price = np.array([self._sample(forecast.price_mean, forecast.price_std, forecast.horizon) for _ in range(n_large)])

        pv_p    = np.percentile(all_pv,   percentile, axis=0).tolist()
        load_p  = np.percentile(all_load, percentile, axis=0).tolist()
        price_p = np.percentile(all_price,percentile, axis=0).tolist()

        return {
            "scenario_id" : f"p{int(percentile)}",
            "pv"          : [round(v, 4) for v in pv_p],
            "load"        : [round(v, 4) for v in load_p],
            "price"       : [max(0.01, round(v, 4)) for v in price_p],
            "weight"      : 1.0
        }

    # ----------------------------------------------------------------
    def expected_scenario(self, forecast: ForecastBundle) -> dict:
        """Return the mean/expected scenario (no sampling)."""
        return {
            "scenario_id" : "expected",
            "pv"          : forecast.pv_mean,
            "load"        : forecast.load_mean,
            "price"       : forecast.price_mean,
            "weight"      : 1.0
        }