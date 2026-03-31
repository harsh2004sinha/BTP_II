"""
State Estimator
Fuses raw sensor data with Kalman filter for clean state values
"""

import numpy as np
from ..models.kalman_soc import KalmanSOCEstimator


class StateEstimator:
    """
    Estimates true system state from noisy sensor readings.

    SOC   → Kalman filter
    PV    → Exponential Moving Average (resets with twin)
    Load  → Exponential Moving Average (resets with twin)
    """

    def __init__(
        self,
        initial_soc     : float = 0.50,
        smoothing_alpha : float = 0.30
    ):
        self.kalman = KalmanSOCEstimator(initial_soc=initial_soc)
        self.alpha  = smoothing_alpha

        # EMA state — None means "not initialized yet"
        self._pv_smooth   = None
        self._load_smooth = None

    # ----------------------------------------------------------------
    def estimate(
        self,
        soc_model        : float,
        voltage_sensor   : float,
        pv_sensor_kw     : float,
        load_sensor_kw   : float,
        battery_capacity : float = 100.0
    ) -> dict:
        """
        Run one estimation step.

        Args:
            soc_model        : SOC from battery model (coulomb counting)
            voltage_sensor   : Raw terminal voltage reading (V)
            pv_sensor_kw     : Raw PV power meter reading (kW)
            load_sensor_kw   : Raw load meter reading (kW)
            battery_capacity : Battery kWh

        Returns:
            dict with estimated values + uncertainties
        """

        # SOC via Kalman
        k = self.kalman.update(soc_model, voltage_sensor, battery_capacity)

        # PV EMA smoothing
        # On first call OR after reset, initialize to sensor value directly
        if self._pv_smooth is None:
            self._pv_smooth = pv_sensor_kw
        else:
            self._pv_smooth = (
                self.alpha * pv_sensor_kw
                + (1 - self.alpha) * self._pv_smooth
            )

        # Load EMA smoothing
        if self._load_smooth is None:
            self._load_smooth = load_sensor_kw
        else:
            self._load_smooth = (
                self.alpha * load_sensor_kw
                + (1 - self.alpha) * self._load_smooth
            )

        return {
            "soc_estimate"      : k["soc_estimate"],
            "soc_uncertainty"   : k["uncertainty_std"],
            "soc_percent"       : k["soc_percent"],
            "pv_estimated_kw"   : round(max(0.0, self._pv_smooth), 3),
            "load_estimated_kw" : round(max(0.0, self._load_smooth), 3),
            "confidence_interval": self.kalman.get_confidence_interval(),
            "kalman_gain"       : k["kalman_gain"],
            "innovation"        : k["innovation"]
        }

    # ----------------------------------------------------------------
    def reset(self, initial_soc: float = 0.50):
        """
        Full reset — clears EMA state and Kalman filter.
        Call this whenever twin.reset() is called.
        """
        self.kalman.reset(initial_soc)

        # KEY FIX: Set to None so next estimate() starts fresh
        self._pv_smooth   = None
        self._load_smooth = None