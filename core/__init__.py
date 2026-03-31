"""
Core Engine — Intelligent Microgrid EMS
=========================================
Complete algorithm pipeline:

    models/     → Physics simulation
    twin/       → Digital twin + forecasting
    optimizer/  → Cost minimization
    learning/   → Reinforcement learning
    explain/    → Explainable AI
    policy/     → Rules + tariff + carbon + DR

Backend imports from this package.
Core NEVER imports backend or frontend.
"""

# ---- Models ----
from .models.battery_model  import BatteryModel
from .models.pv_model       import PVModel
from .models.load_model     import LoadModel
from .models.kalman_soc     import KalmanSOCEstimator

# ---- Digital Twin ----
from .twin.twin_core        import DigitalTwin
from .twin.twin_state       import TwinState, ForecastBundle
from .twin.state_estimator  import StateEstimator
from .twin.forecast         import Forecaster

# ---- Optimizer ----
from .optimizer.solver       import Solver
from .optimizer.cost_function import CostFunction
from .optimizer.degradation  import DegradationModel
from .optimizer.constraints  import Constraints
from .optimizer.scenario     import ScenarioGenerator
from .optimizer.sizing       import SystemSizer

# ---- Learning ----
from .learning.reward        import RewardFunction
from .learning.rl_env        import MicrogridEnv
from .learning.rl_agent      import RLAgent
from .learning.trainer       import Trainer

# ---- Explainability ----
from .explain.explain_core   import ExplainCore
from .explain.decision_text  import DecisionTextGenerator
from .explain.shap_explain   import SHAPExplainer

# ---- Policy ----
from .policy.policy_manager  import PolicyManager
from .policy.tariff          import TariffManager
from .policy.carbon          import CarbonPolicy
from .policy.demand_response import DemandResponseManager
from .policy.user_rules      import UserRules

__version__ = "1.0.0"
__author__  = "Microgrid EMS Team"