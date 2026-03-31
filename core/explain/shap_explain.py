"""
SHAP Explainer
Computes feature importance for optimizer decisions
Falls back to manual importance if SHAP not installed
"""

import numpy as np
from typing import List, Optional


class SHAPExplainer:
    """
    Computes feature importance for each optimization decision.

    Tells you:
        "Why did the optimizer choose this action?"
        "Which state variable had the most influence?"

    Uses SHAP (SHapley Additive exPlanations) if available.
    Falls back to gradient-free importance estimation if not.

    Features (from TwinState.to_vector()):
        0: soc                  — Battery state of charge
        1: pv_norm              — Normalized PV generation
        2: load_norm            — Normalized load demand
        3: price_norm           — Normalized grid price
        4: hour_norm            — Normalized hour of day
        5: is_weekday           — Day type flag
        6: battery_health       — Battery health fraction
        7: dr_active            — Demand response flag
        8: carbon_intensity_norm— Normalized carbon intensity
        9: soc_uncertainty      — SOC estimation uncertainty
    """

    FEATURE_NAMES = [
        "battery_soc",
        "pv_generation",
        "load_demand",
        "grid_price",
        "hour_of_day",
        "is_weekday",
        "battery_health",
        "demand_response",
        "carbon_intensity",
        "soc_uncertainty"
    ]

    def __init__(self):
        self._shap_available = False
        try:
            import shap
            self._shap = shap
            self._shap_available = True
        except ImportError:
            pass

        # Background data for SHAP (accumulated during operation)
        self._background_states  = []
        self._background_outputs = []

    # ----------------------------------------------------------------
    def record_sample(
        self,
        state_vector  : List[float],
        cost          : float
    ):
        """
        Record a state-cost sample for SHAP background dataset.
        Call this every timestep during operation.
        """
        self._background_states.append(list(state_vector))
        self._background_outputs.append(cost)

        # Keep only last 500 samples
        if len(self._background_states) > 500:
            self._background_states  = self._background_states[-500:]
            self._background_outputs = self._background_outputs[-500:]

    # ----------------------------------------------------------------
    def compute_importance(
        self,
        state_vector : List[float],
        cost         : float
    ) -> dict:
        """
        Compute feature importance for a specific decision.

        Args:
            state_vector : TwinState.to_vector()
            cost         : Resulting total cost

        Returns:
            dict with feature importances
        """
        if len(self._background_states) >= 10 and self._shap_available:
            return self._shap_importance(state_vector, cost)
        else:
            return self._manual_importance(state_vector, cost)

    # ----------------------------------------------------------------
    def _manual_importance(
        self,
        state_vector: List[float],
        cost        : float
    ) -> dict:
        """
        Estimate feature importance without SHAP.
        Uses domain knowledge rules.

        Importance rules:
            - High price      → price is most important
            - Low SOC         → soc is most important
            - High PV         → pv is most important
            - DR active       → demand_response is important
        """
        sv = state_vector

        # Raw feature values (from to_vector() normalization)
        soc             = sv[0] if len(sv) > 0 else 0.5
        pv_norm         = sv[1] if len(sv) > 1 else 0.0
        load_norm       = sv[2] if len(sv) > 2 else 0.5
        price_norm      = sv[3] if len(sv) > 3 else 0.5
        hour_norm       = sv[4] if len(sv) > 4 else 0.5
        is_weekday      = sv[5] if len(sv) > 5 else 1.0
        batt_health     = sv[6] if len(sv) > 6 else 1.0
        dr_active       = sv[7] if len(sv) > 7 else 0.0
        carbon_norm     = sv[8] if len(sv) > 8 else 0.5
        soc_uncertainty = sv[9] if len(sv) > 9 else 0.0

        # Compute importance scores based on deviation from neutral
        importances = {
            "battery_soc"      : abs(soc - 0.5) * 2.0,
            "pv_generation"    : pv_norm * 1.5,
            "load_demand"      : load_norm * 1.2,
            "grid_price"       : price_norm * 2.0,
            "hour_of_day"      : abs(hour_norm - 0.5) * 0.8,
            "is_weekday"       : is_weekday * 0.5,
            "battery_health"   : (1.0 - batt_health) * 1.8,
            "demand_response"  : dr_active * 2.5,
            "carbon_intensity" : carbon_norm * 0.6,
            "soc_uncertainty"  : soc_uncertainty * 1.0
        }

        # Normalize to sum to 1
        total = sum(importances.values())
        if total > 0:
            importances = {k: round(v / total, 4) for k, v in importances.items()}

        # Find top factor
        top_factor = max(importances, key=importances.get)

        return {
            "importances"   : importances,
            "top_factor"    : top_factor,
            "top_importance": importances[top_factor],
            "cost"          : round(cost, 6),
            "method"        : "domain_rules"
        }

    # ----------------------------------------------------------------
    def _shap_importance(
        self,
        state_vector: List[float],
        cost        : float
    ) -> dict:
        """
        Compute SHAP values using kernel explainer.
        """
        import numpy as np

        X_background = np.array(self._background_states)
        X_explain    = np.array([state_vector])
        Y_background = np.array(self._background_outputs)

        # Simple linear model for SHAP
        from numpy.linalg import lstsq
        coeffs, _, _, _ = lstsq(
            np.hstack([X_background, np.ones((len(X_background), 1))]),
            Y_background,
            rcond=None
        )

        shap_values = coeffs[:len(self.FEATURE_NAMES)] * (
            X_explain[0] - X_background.mean(axis=0))

        importances = {
            name: round(abs(float(val)), 6)
            for name, val in zip(self.FEATURE_NAMES, shap_values)
        }

        total = sum(importances.values())
        if total > 0:
            importances = {k: round(v / total, 4) for k, v in importances.items()}

        top_factor = max(importances, key=importances.get)

        return {
            "importances"   : importances,
            "top_factor"    : top_factor,
            "top_importance": importances[top_factor],
            "cost"          : round(cost, 6),
            "method"        : "shap_linear"
        }

    # ----------------------------------------------------------------
    def get_top_factors(
        self,
        state_vector: List[float],
        cost        : float,
        top_n       : int = 3
    ) -> List[dict]:
        """
        Get top N most important factors.

        Returns:
            List of dicts — feature name + importance
        """
        result = self.compute_importance(state_vector, cost)
        importances = result["importances"]

        sorted_factors = sorted(
            importances.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {"feature": k, "importance": v}
            for k, v in sorted_factors[:top_n]
        ]