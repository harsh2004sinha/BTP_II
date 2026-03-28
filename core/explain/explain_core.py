"""
Explain Core
Main entry point for explainability layer
Combines SHAP + decision text into one unified explanation
"""

from typing import List, Optional

from .shap_explain  import SHAPExplainer
from .decision_text import DecisionTextGenerator
from ..twin.twin_state import TwinState


class ExplainCore:
    """
    Unified explainability interface.

    Takes:
        - Current TwinState
        - Optimizer decision (action)
        - Cost breakdown

    Returns:
        - Human-readable explanation
        - Feature importances
        - Structured explanation dict

    Used by:
        - backend explain_api.py
        - scheduler loop (for logging)
    """

    def __init__(self):
        self.shap_explainer = SHAPExplainer()
        self.text_generator = DecisionTextGenerator()

        # History for trending
        self.explanation_history : List[dict] = []

    # ----------------------------------------------------------------
    def explain(
        self,
        state          : TwinState,
        action         : dict,
        cost_breakdown : dict
    ) -> dict:
        """
        Generate full explanation for one optimizer decision.

        Args:
            state          : Current TwinState
            action         : Best action dict from Solver.optimize()
            cost_breakdown : Cost dict from CostFunction.compute()

        Returns:
            dict with:
                decision     : what was decided
                reason       : why it was decided
                cost_summary : cost breakdown text
                importances  : feature importance dict
                full_text    : complete explanation
                action_name  : action identifier
        """

        state_vector = state.to_vector()
        total_cost   = cost_breakdown.get("total_cost", 0.0)
        action_name  = action.get("action_name", "unknown")

        # Record for SHAP background
        self.shap_explainer.record_sample(state_vector, total_cost)

        # Compute importances
        importance = self.shap_explainer.compute_importance(
            state_vector, total_cost)

        # Generate text
        text_result = self.text_generator.generate(
            action_name    = action_name,
            state_dict     = state.to_dict(),
            cost_breakdown = cost_breakdown,
            importance     = importance
        )

        # Top factors
        top_factors = self.shap_explainer.get_top_factors(
            state_vector, total_cost, top_n=3)

        # Assemble full explanation
        explanation = {
            "timestep"          : state.timestep,
            "hour"              : state.hour_of_day,
            "action_name"       : action_name,
            "decision"          : text_result["action_text"],
            "reason"            : text_result["reason_text"],
            "cost_summary"      : text_result["cost_text"],
            "factor_summary"    : text_result["factor_text"],
            "full_explanation"  : text_result["full_text"],
            "top_factors"       : top_factors,
            "importances"       : importance["importances"],
            "top_factor"        : importance["top_factor"],
            "cost_breakdown"    : cost_breakdown,
            "state_snapshot"    : {
                "soc"       : round(state.soc, 4),
                "pv_kw"     : round(state.pv_power_kw, 3),
                "load_kw"   : round(state.load_kw, 3),
                "grid_price": round(state.grid_price, 4),
                "hour"      : round(state.hour_of_day, 2)
            }
        }

        self.explanation_history.append(explanation)

        # Keep only last 200 explanations
        if len(self.explanation_history) > 200:
            self.explanation_history = self.explanation_history[-200:]

        return explanation

    # ----------------------------------------------------------------
    def explain_schedule(
        self,
        states    : List[TwinState],
        actions   : List[dict],
        costs     : List[dict]
    ) -> List[dict]:
        """
        Explain a full day schedule.

        Args:
            states  : List of TwinStates
            actions : List of action dicts
            costs   : List of cost dicts

        Returns:
            List of explanation dicts
        """
        explanations = []
        n = min(len(states), len(actions), len(costs))

        for i in range(n):
            exp = self.explain(states[i], actions[i], costs[i])
            explanations.append(exp)

        return explanations

    # ----------------------------------------------------------------
    def get_schedule_summary_text(
        self,
        actions: List[dict]
    ) -> str:
        """Get human-readable summary of a full schedule."""
        return self.text_generator.generate_schedule_summary(actions)

    # ----------------------------------------------------------------
    def get_latest_explanation(self) -> Optional[dict]:
        """Return most recent explanation."""
        if self.explanation_history:
            return self.explanation_history[-1]
        return None

    # ----------------------------------------------------------------
    def get_explanation_history(
        self,
        last_n: int = 96
    ) -> List[dict]:
        """Return last N explanations."""
        return self.explanation_history[-last_n:]

    # ----------------------------------------------------------------
    def get_action_frequency(self) -> dict:
        """
        Count how often each action was chosen in history.

        Returns:
            dict — action_name: count
        """
        freq = {}
        for exp in self.explanation_history:
            name = exp.get("action_name", "unknown")
            freq[name] = freq.get(name, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))