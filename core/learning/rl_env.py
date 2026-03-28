"""
Reinforcement Learning Environment
Gymnasium-compatible microgrid environment for RL training
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from ..twin.twin_core   import DigitalTwin
from ..twin.twin_state  import TwinState
from ..optimizer.solver import Solver
from .reward            import RewardFunction


class MicrogridEnv(gym.Env):
    """
    OpenAI Gymnasium environment for campus microgrid.

    The RL agent learns to adjust optimization weights
    based on observed system state.

    Observation space:
        [soc, pv_norm, load_norm, price_norm, hour_norm,
         is_weekday, battery_health, dr_active,
         carbon_intensity_norm, soc_uncertainty]

    Action space:
        Continuous adjustments to optimizer weights:
        [cost_weight_adj, degradation_weight_adj, solar_bonus_adj]

    Goal:
        Minimize total daily electricity cost while
        maintaining battery health and serving all load.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        twin     : DigitalTwin  = None,
        solver   : Solver       = None,
        reward_fn: RewardFunction = None,
        n_steps  : int = 96,       # 96 × 15min = 24h episode
        day_type : str = "weekday"
    ):
        super().__init__()

        self.twin     = twin      or DigitalTwin()
        self.solver   = solver    or Solver()
        self.reward_fn = reward_fn or RewardFunction()
        self.n_steps  = n_steps
        self.day_type = day_type

        # Observation space: 10 features (all normalized 0-1 roughly)
        self.observation_space = spaces.Box(
            low   = np.zeros(10, dtype=np.float32),
            high  = np.ones(10,  dtype=np.float32),
            dtype = np.float32
        )

        # Action space: 3 continuous weight adjustments [-1, 1]
        self.action_space = spaces.Box(
            low   = np.full(3, -1.0, dtype=np.float32),
            high  = np.full(3,  1.0, dtype=np.float32),
            dtype = np.float32
        )

        # Episode state
        self.current_step  = 0
        self.current_state : TwinState = None
        self.episode_reward = 0.0
        self.episode_cost   = 0.0

    # ----------------------------------------------------------------
    def reset(self, seed=None, options=None):
        """Reset environment for new episode."""
        super().reset(seed=seed)

        self.twin.reset(initial_soc=np.random.uniform(0.30, 0.70))
        self.current_step   = 0
        self.episode_reward = 0.0
        self.episode_cost   = 0.0

        # Initial twin step
        self.current_state = self.twin.twin_step(
            hour_of_day = 0.0,
            day_type    = self.day_type
        )

        obs = np.array(self.current_state.to_vector(), dtype=np.float32)
        return obs, {}

    # ----------------------------------------------------------------
    def step(self, action: np.ndarray):
        """
        Take one environment step.

        Args:
            action : [cost_adj, deg_adj, solar_adj] — weight adjustments

        Returns:
            (observation, reward, terminated, truncated, info)
        """

        # Adjust solver weights based on RL action
        self._apply_rl_action(action)

        # Get optimizer decision
        opt_result  = self.solver.optimize(self.current_state)
        best_action = opt_result.get("best_action", {})

        charge_kw    = best_action.get("charge_kw",     0.0)
        discharge_kw = best_action.get("discharge_kw",  0.0)
        grid_import  = best_action.get("grid_import_kw", 0.0)
        grid_export  = best_action.get("grid_export_kw", 0.0)

        # Advance twin
        hour = self.current_step * self.twin.dt_hours
        self.current_state = self.twin.twin_step(
            hour_of_day    = hour,
            day_type       = self.day_type,
            charge_kw      = charge_kw,
            discharge_kw   = discharge_kw,
            grid_import_kw = grid_import,
            grid_export_kw = grid_export
        )

        # Compute reward
        deg_cost = self.solver.deg_model.degradation_cost(
            charge_kw    = charge_kw,
            discharge_kw = discharge_kw,
            current_soc  = self.current_state.soc,
            dt_hours     = self.twin.dt_hours
        )["degradation_cost"]

        reward_dict = self.reward_fn.compute(
            grid_import_kw   = grid_import,
            grid_export_kw   = grid_export,
            pv_used_kw       = self.current_state.pv_power_kw,
            pv_available_kw  = self.current_state.pv_available_kw,
            grid_price       = self.current_state.grid_price,
            degradation_cost = deg_cost,
            soc              = self.current_state.soc,
            dt_hours         = self.twin.dt_hours
        )

        reward = reward_dict["total_reward"]
        self.episode_reward += reward
        self.episode_cost   += grid_import * self.current_state.grid_price * self.twin.dt_hours
        self.current_step   += 1

        # Episode ends after n_steps
        terminated = self.current_step >= self.n_steps
        truncated  = False

        obs = np.array(self.current_state.to_vector(), dtype=np.float32)

        info = {
            "hour"           : hour,
            "soc"            : self.current_state.soc,
            "action_name"    : best_action.get("action_name", ""),
            "step_cost"      : grid_import * self.current_state.grid_price * self.twin.dt_hours,
            "episode_cost"   : self.episode_cost,
            "episode_reward" : self.episode_reward,
            "reward_breakdown": reward_dict
        }

        return obs, float(reward), terminated, truncated, info

    # ----------------------------------------------------------------
    def _apply_rl_action(self, action: np.ndarray):
        """
        Map RL action to optimizer weight adjustments.
        RL adjusts weights, not direct control.

        action[0] : cost weight adjustment       (-1 to +1)
        action[1] : degradation weight adjustment(-1 to +1)
        action[2] : solar bonus adjustment       (-1 to +1)
        """
        base_cost_w = 1.0
        base_deg_w  = 0.5
        base_solar_b = 0.2

        scale = 0.3   # Max 30% adjustment

        self.solver.cost_fn.carbon_price_per_kg = max(
            0.001, base_cost_w + float(action[0]) * scale)
        self.solver.reward_fn_cost_weight = max(
            0.1, base_deg_w  + float(action[1]) * scale)
        # Solar bonus affects candidate selection implicitly

    # ----------------------------------------------------------------
    def render(self):
        """Print current state summary."""
        if self.current_state:
            s = self.current_state
            print(
                f"Step {self.current_step:3d} | "
                f"Hour {s.hour_of_day:5.2f} | "
                f"SOC {s.soc:.2%} | "
                f"PV {s.pv_power_kw:6.1f}kW | "
                f"Load {s.load_kw:6.1f}kW | "
                f"Price ${s.grid_price:.3f} | "
                f"EpCost ${self.episode_cost:.2f}"
            )