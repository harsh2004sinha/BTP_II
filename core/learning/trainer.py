"""
RL Trainer
Manages the full training pipeline for the RL agent
"""

import os
import json
import numpy as np
from typing import Optional

from .rl_env   import MicrogridEnv
from .rl_agent import RLAgent
from ..twin.twin_core import DigitalTwin
from ..optimizer.solver import Solver
from .reward import RewardFunction


class Trainer:
    """
    Full training pipeline for microgrid RL agent.

    Steps:
        1. Build environment
        2. Build agent
        3. Train
        4. Evaluate
        5. Save model + metrics
    """

    def __init__(
        self,
        save_dir          : str   = "models/",
        total_timesteps   : int   = 100000,
        eval_episodes     : int   = 5,
        battery_capacity  : float = 100.0,
        pv_area_m2        : float = 500.0,
        base_load_kw      : float = 200.0,
        peak_load_kw      : float = 800.0,
        n_scenarios       : int   = 5
    ):
        self.save_dir         = save_dir
        self.total_timesteps  = total_timesteps
        self.eval_episodes    = eval_episodes
        self.battery_capacity = battery_capacity
        self.pv_area_m2       = pv_area_m2
        self.base_load_kw     = base_load_kw
        self.peak_load_kw     = peak_load_kw
        self.n_scenarios      = n_scenarios

        self.env   = None
        self.agent = None

        os.makedirs(save_dir, exist_ok=True)

    # ----------------------------------------------------------------
    def setup(self) -> "Trainer":
        """
        Build environment and agent.

        Returns:
            self (for chaining)
        """
        print("[Trainer] Setting up environment...")

        # Build digital twin
        twin = DigitalTwin(
            battery_capacity_kwh = self.battery_capacity,
            pv_area_m2           = self.pv_area_m2,
            base_load_kw         = self.base_load_kw,
            peak_load_kw         = self.peak_load_kw,
            mode                 = "simulation"
        )

        # Build solver
        solver = Solver(n_scenarios=self.n_scenarios)

        # Build reward function
        reward_fn = RewardFunction()

        # Build environment
        self.env = MicrogridEnv(
            twin      = twin,
            solver    = solver,
            reward_fn = reward_fn,
            n_steps   = 96,
            day_type  = "weekday"
        )

        # Build agent
        self.agent = RLAgent(
            env       = self.env,
            model_path= os.path.join(self.save_dir, "rl_microgrid")
        )
        self.agent.build()

        print("[Trainer] Setup complete.")
        return self

    # ----------------------------------------------------------------
    def train(self) -> dict:
        """
        Run full training loop.

        Returns:
            dict with training metrics
        """
        if self.agent is None:
            self.setup()

        print(f"[Trainer] Training for {self.total_timesteps} timesteps...")
        train_result = self.agent.train(
            total_timesteps=self.total_timesteps)

        print("[Trainer] Evaluating...")
        eval_result = self.agent.evaluate(
            n_episodes=self.eval_episodes)

        # Save model
        self.agent.save()

        # Save metrics
        metrics = {
            "training"   : train_result,
            "evaluation" : eval_result,
            "config"     : {
                "total_timesteps"  : self.total_timesteps,
                "battery_capacity" : self.battery_capacity,
                "pv_area_m2"       : self.pv_area_m2
            }
        }

        metrics_path = os.path.join(self.save_dir, "training_metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"[Trainer] Metrics saved to: {metrics_path}")
        print(f"[Trainer] Mean reward: {eval_result['mean_reward']:.4f}")
        print(f"[Trainer] Mean daily cost: ${eval_result['mean_cost']:.2f}")

        return metrics

    # ----------------------------------------------------------------
    def run_baseline_comparison(self) -> dict:
        """
        Compare RL agent against rule-based baseline.

        Returns:
            dict with comparison results
        """
        if self.env is None:
            self.setup()

        n_eps = 10
        rl_costs      = []
        baseline_costs = []

        for ep in range(n_eps):
            # ---- RL Agent ----
            obs, _ = self.env.reset()
            ep_cost = 0.0
            done = False

            while not done:
                if self.agent.is_trained:
                    action, _ = self.agent.model.predict(obs, deterministic=True)
                else:
                    action = self.agent._rule_based_action(self.env.current_state)
                obs, _, terminated, truncated, info = self.env.step(action)
                ep_cost += info.get("step_cost", 0.0)
                done = terminated or truncated
            rl_costs.append(ep_cost)

            # ---- Rule-based Baseline ----
            obs, _ = self.env.reset()
            ep_cost_base = 0.0
            done = False

            while not done:
                action = np.zeros(3, dtype=np.float32)  # Neutral weights
                obs, _, terminated, truncated, info = self.env.step(action)
                ep_cost_base += info.get("step_cost", 0.0)
                done = terminated or truncated
            baseline_costs.append(ep_cost_base)

        rl_mean   = float(np.mean(rl_costs))
        base_mean = float(np.mean(baseline_costs))
        improvement = ((base_mean - rl_mean) / base_mean * 100
                       if base_mean > 0 else 0.0)

        return {
            "rl_mean_cost"        : round(rl_mean, 4),
            "baseline_mean_cost"  : round(base_mean, 4),
            "improvement_percent" : round(improvement, 2),
            "rl_costs_per_episode": [round(c, 4) for c in rl_costs],
            "base_costs_per_episode": [round(c, 4) for c in baseline_costs]
        }

    # ----------------------------------------------------------------
    def load_agent(self) -> RLAgent:
        """Load previously trained agent."""
        if self.agent is None:
            self.setup()
        self.agent.load()
        return self.agent