"""
RL Agent
Wraps Stable-Baselines3 PPO for microgrid optimization
Falls back to rule-based if stable-baselines3 not installed
"""

import os
import numpy as np
from typing import Optional

from .rl_env import MicrogridEnv
from ..twin.twin_state import TwinState


class RLAgent:
    """
    Reinforcement Learning Agent for microgrid energy management.

    Uses PPO (Proximal Policy Optimization) from Stable-Baselines3.

    Role:
        - NOT direct controller
        - Adjusts optimizer weights dynamically
        - Learns patterns: demand, price, battery aging
        - Improves decisions over time

    Fallback:
        If stable-baselines3 not installed,
        uses rule-based weight adjustment.
    """

    def __init__(
        self,
        env          : MicrogridEnv = None,
        model_path   : str  = "models/rl_microgrid",
        learning_rate: float = 3e-4,
        n_steps      : int   = 2048,
        batch_size   : int   = 64,
        n_epochs     : int   = 10,
        gamma        : float = 0.99,
        verbose      : int   = 0
    ):
        self.env          = env
        self.model_path   = model_path
        self.learning_rate = learning_rate
        self.n_steps      = n_steps
        self.batch_size   = batch_size
        self.n_epochs     = n_epochs
        self.gamma        = gamma
        self.verbose      = verbose

        self.model        = None
        self.is_trained   = False
        self._sb3_available = False

        # Try to import stable-baselines3
        try:
            from stable_baselines3 import PPO
            self._PPO = PPO
            self._sb3_available = True
        except ImportError:
            print("[RLAgent] stable-baselines3 not found. Using rule-based fallback.")
            self._PPO = None

    # ----------------------------------------------------------------
    def build(self):
        """
        Build PPO model.
        Call this before training.
        """
        if not self._sb3_available:
            print("[RLAgent] Cannot build: stable-baselines3 not installed.")
            return

        if self.env is None:
            self.env = MicrogridEnv()

        self.model = self._PPO(
            policy        = "MlpPolicy",
            env           = self.env,
            learning_rate = self.learning_rate,
            n_steps       = self.n_steps,
            batch_size    = self.batch_size,
            n_epochs      = self.n_epochs,
            gamma         = self.gamma,
            verbose       = self.verbose,
            policy_kwargs = dict(net_arch=[64, 64])
        )
        print("[RLAgent] PPO model built.")

    # ----------------------------------------------------------------
    def train(self, total_timesteps: int = 50000) -> dict:
        """
        Train the RL agent.

        Args:
            total_timesteps : Total training steps

        Returns:
            dict with training info
        """
        if not self._sb3_available:
            print("[RLAgent] Training skipped: stable-baselines3 not installed.")
            return {"status": "skipped", "reason": "sb3_not_available"}

        if self.model is None:
            self.build()

        print(f"[RLAgent] Starting training: {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)
        self.is_trained = True
        print("[RLAgent] Training complete.")

        return {
            "status"          : "trained",
            "total_timesteps" : total_timesteps,
            "model_path"      : self.model_path
        }

    # ----------------------------------------------------------------
    def save(self, path: str = None):
        """Save trained model to disk."""
        if self.model is None:
            print("[RLAgent] No model to save.")
            return

        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.model.save(save_path)
        print(f"[RLAgent] Model saved to: {save_path}")

    # ----------------------------------------------------------------
    def load(self, path: str = None) -> bool:
        """
        Load trained model from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._sb3_available:
            return False

        load_path = path or self.model_path

        if not os.path.exists(load_path + ".zip"):
            print(f"[RLAgent] Model file not found: {load_path}.zip")
            return False

        if self.env is None:
            self.env = MicrogridEnv()

        self.model      = self._PPO.load(load_path, env=self.env)
        self.is_trained = True
        print(f"[RLAgent] Model loaded from: {load_path}")
        return True

    # ----------------------------------------------------------------
    def predict_action(
        self,
        state       : TwinState,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Predict weight adjustments for current state.

        Args:
            state         : Current TwinState
            deterministic : Use deterministic policy (no exploration)

        Returns:
            np.ndarray — [cost_adj, deg_adj, solar_adj]
        """
        obs = np.array(state.to_vector(), dtype=np.float32)

        if self.is_trained and self.model is not None:
            action, _ = self.model.predict(obs, deterministic=deterministic)
            return action

        # Rule-based fallback
        return self._rule_based_action(state)

    # ----------------------------------------------------------------
    def _rule_based_action(self, state: TwinState) -> np.ndarray:
        """
        Rule-based weight adjustment when RL model not available.

        Logic:
            High price  → increase cost weight (be more cost-conscious)
            Low SOC     → reduce degradation weight (save battery)
            High PV     → increase solar bonus (use more solar)

        Returns:
            np.ndarray — adjustments in [-1, 1]
        """
        cost_adj  = 0.0
        deg_adj   = 0.0
        solar_adj = 0.0

        # Price-based adjustment
        if state.grid_price >= 0.20:
            cost_adj = 0.5    # Increase cost avoidance during peak
        elif state.grid_price <= 0.08:
            cost_adj = -0.3   # Relax cost constraint during off-peak

        # SOC-based adjustment
        if state.soc < 0.25:
            deg_adj = -0.5    # Reduce degradation weight to protect battery
        elif state.soc > 0.80:
            deg_adj = 0.3     # Can afford more cycling

        # PV availability adjustment
        if state.pv_available_kw > 50.0:
            solar_adj = 0.4   # Prioritize solar when plenty available
        elif state.pv_available_kw <= 0.0:
            solar_adj = -0.5  # No solar available

        return np.array([cost_adj, deg_adj, solar_adj], dtype=np.float32)

    # ----------------------------------------------------------------
    def get_weight_adjustments(self, state: TwinState) -> dict:
        """
        Get weight adjustments as named dict.

        Returns:
            dict with cost_weight_adj, deg_weight_adj, solar_bonus_adj
        """
        action = self.predict_action(state)
        return {
            "cost_weight_adj"  : round(float(action[0]), 4),
            "deg_weight_adj"   : round(float(action[1]), 4),
            "solar_bonus_adj"  : round(float(action[2]), 4),
            "source"           : "rl_model" if self.is_trained else "rule_based"
        }

    # ----------------------------------------------------------------
    def evaluate(self, n_episodes: int = 5) -> dict:
        """
        Evaluate agent performance over N episodes.

        Returns:
            dict with mean_reward, mean_cost, std_reward
        """
        if self.env is None:
            self.env = MicrogridEnv()

        episode_rewards = []
        episode_costs   = []

        for ep in range(n_episodes):
            obs, _ = self.env.reset()
            ep_reward = 0.0
            ep_cost   = 0.0
            done = False

            while not done:
                if self.is_trained and self.model:
                    action, _ = self.model.predict(obs, deterministic=True)
                else:
                    action = self._rule_based_action(self.env.current_state)

                obs, reward, terminated, truncated, info = self.env.step(action)
                ep_reward += reward
                ep_cost   += info.get("step_cost", 0.0)
                done = terminated or truncated

            episode_rewards.append(ep_reward)
            episode_costs.append(ep_cost)

        return {
            "n_episodes"   : n_episodes,
            "mean_reward"  : round(float(np.mean(episode_rewards)), 4),
            "std_reward"   : round(float(np.std(episode_rewards)), 4),
            "mean_cost"    : round(float(np.mean(episode_costs)), 4),
            "min_cost"     : round(float(np.min(episode_costs)), 4),
            "max_cost"     : round(float(np.max(episode_costs)), 4)
        }