"""
Reward Function for Reinforcement Learning Agent
"""


class RewardFunction:
    """
    Calculates reward signal for RL agent.

    Good actions:
        + Low grid cost
        + Using solar
        + Avoiding peak tariff
        + Exporting surplus
        + Maintaining healthy SOC

    Bad actions:
        - High grid import during peak price
        - Battery at extremes
        - Unmet load
        - Unnecessary degradation
    """

    def __init__(
        self,
        cost_weight        : float = 1.0,
        degradation_weight : float = 0.5,
        solar_bonus        : float = 0.2,
        reserve_penalty    : float = 1.0,
        unserved_penalty   : float = 5.0,
        export_bonus       : float = 0.1
    ):
        self.cost_weight        = cost_weight
        self.degradation_weight = degradation_weight
        self.solar_bonus        = solar_bonus
        self.reserve_penalty    = reserve_penalty
        self.unserved_penalty   = unserved_penalty
        self.export_bonus       = export_bonus

    # ----------------------------------------------------------------
    def compute(
        self,
        grid_import_kw   : float,
        grid_export_kw   : float,
        pv_used_kw       : float,
        pv_available_kw  : float,
        grid_price       : float,
        degradation_cost : float,
        soc              : float,
        load_unserved    : float = 0.0,
        dt_hours         : float = 0.25
    ) -> dict:
        """
        Compute reward for one timestep.

        Returns:
            dict with total_reward, components
        """

        # Cost penalty (main signal)
        cost_penalty = -(grid_import_kw * grid_price * dt_hours) * self.cost_weight

        # Degradation penalty
        deg_penalty  = -degradation_cost * self.degradation_weight

        # Solar usage bonus
        pv_ratio     = (pv_used_kw / pv_available_kw
                        if pv_available_kw > 0 else 0.0)
        solar_reward = pv_ratio * self.solar_bonus

        # Export bonus (selling energy)
        export_reward = grid_export_kw * 0.05 * self.export_bonus

        # SOC reserve penalty
        soc_penalty = 0.0
        if soc < 0.20:
            soc_penalty = -self.reserve_penalty * (0.20 - soc)
        elif soc > 0.90:
            soc_penalty = -0.2 * (soc - 0.90)

        # Unserved load penalty
        unserved_penalty = -load_unserved * self.unserved_penalty * dt_hours

        total_reward = (
            cost_penalty
            + deg_penalty
            + solar_reward
            + export_reward
            + soc_penalty
            + unserved_penalty
        )

        return {
            "total_reward"   : round(total_reward, 6),
            "cost_penalty"   : round(cost_penalty, 6),
            "deg_penalty"    : round(deg_penalty, 6),
            "solar_reward"   : round(solar_reward, 6),
            "export_reward"  : round(export_reward, 6),
            "soc_penalty"    : round(soc_penalty, 6),
            "unserved_penalty": round(unserved_penalty, 6)
        }