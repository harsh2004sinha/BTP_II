"""
Kalman Filter — State of Charge Estimator
Fuses voltage sensor readings with battery model to get true SOC
"""

import numpy as np


class KalmanSOCEstimator:
    """
    Extended Kalman Filter for Battery SOC estimation.

    Problem  : SOC cannot be measured directly; sensors are noisy
    Solution : Fuse model prediction (coulomb counting) with
               voltage measurement (OCV curve) using Kalman math

    State       : [SOC]
    Measurement : [Terminal Voltage]
    """

    def __init__(
        self,
        initial_soc          : float = 0.50,
        process_noise        : float = 0.001,
        measurement_noise    : float = 0.01,
        initial_uncertainty  : float = 0.1
    ):
        self.soc_estimate = initial_soc
        self.P            = initial_uncertainty
        self.Q            = process_noise
        self.R            = measurement_noise

        self.history = [{"soc_estimate": initial_soc, "uncertainty": initial_uncertainty}]

    # ----------------------------------------------------------------
    def update(
        self,
        current_soc_model   : float,
        voltage_measurement : float,
        capacity_kwh        : float = 100.0
    ) -> dict:
        """
        One Kalman filter step.

        Args:
            current_soc_model   : SOC from coulomb counting
            voltage_measurement : Raw terminal voltage (V)
            capacity_kwh        : Battery capacity

        Returns:
            dict — soc_estimate, uncertainty, innovation, kalman_gain
        """

        # ---- PREDICT ----
        soc_predicted = current_soc_model
        P_predicted   = self.P + self.Q

        # ---- MEASUREMENT ----
        soc_from_voltage = self._ocv_to_soc(voltage_measurement)
        innovation       = np.clip(soc_from_voltage - soc_predicted, -0.20, 0.20)

        # ---- UPDATE ----
        S           = P_predicted + self.R
        K           = P_predicted / S
        soc_updated = np.clip(soc_predicted + K * innovation, 0.05, 1.0)
        P_updated   = (1 - K) * P_predicted

        self.soc_estimate = soc_updated
        self.P            = P_updated

        result = {
            "soc_estimate"    : round(soc_updated, 4),
            "soc_percent"     : round(soc_updated * 100, 2),
            "uncertainty_std" : round(np.sqrt(P_updated), 4),
            "kalman_gain"     : round(K, 4),
            "innovation"      : round(innovation, 4),
            "soc_from_model"  : round(soc_predicted, 4),
            "soc_from_voltage": round(soc_from_voltage, 4)
        }

        self.history.append({"soc_estimate": soc_updated, "uncertainty": P_updated})
        return result

    # ----------------------------------------------------------------
    def _ocv_to_soc(self, voltage_v: float) -> float:
        """
        Convert Open Circuit Voltage to SOC.
        Piecewise linear for LiFePO4 (27S pack, ~100 V nominal).
        """
        cells_series = 27
        v_cell = voltage_v / cells_series
        ocv_pts = [3.00, 3.20, 3.30, 3.35, 3.40, 3.45, 3.50, 3.55, 3.60, 3.65]
        soc_pts = [0.00, 0.10, 0.20, 0.30, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
        return float(np.clip(np.interp(v_cell, ocv_pts, soc_pts), 0.0, 1.0))

    def reset(self, initial_soc: float = 0.50, initial_uncertainty: float = 0.1):
        self.soc_estimate = initial_soc
        self.P            = initial_uncertainty
        self.history      = [{"soc_estimate": initial_soc, "uncertainty": initial_uncertainty}]

    def get_confidence_interval(self, z_score: float = 1.96) -> tuple:
        std   = np.sqrt(self.P)
        lower = float(np.clip(self.soc_estimate - z_score * std, 0.0, 1.0))
        upper = float(np.clip(self.soc_estimate + z_score * std, 0.0, 1.0))
        return (round(lower, 4), round(upper, 4))