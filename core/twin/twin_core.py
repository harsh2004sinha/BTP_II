"""
Digital Twin Core
Virtual real-time copy of the campus microgrid
"""

import numpy as np
import time
from typing import List, Optional

from ..models.battery_model import BatteryModel
from ..models.pv_model      import PVModel
from ..models.load_model    import LoadModel
from .state_estimator       import StateEstimator
from .forecast              import Forecaster
from .twin_state            import TwinState, ForecastBundle


class DigitalTwin:
    """
    The digital twin continuously tracks and simulates the campus microgrid.
    """

    def __init__(
        self,
        battery_capacity_kwh : float = 100.0,
        pv_area_m2           : float = 500.0,
        base_load_kw         : float = 200.0,
        peak_load_kw         : float = 800.0,
        initial_soc          : float = 0.50,
        dt_hours             : float = 0.25,
        forecast_horizon     : int   = 96,
        mode                 : str   = "simulation",
        location_peak_irr    : float = 900.0,    # FIX BUG 18: location-specific peak irradiance
    ):
        self.dt_hours             = dt_hours
        self.forecast_horizon     = forecast_horizon
        self.pv_area_m2           = pv_area_m2
        self.mode                 = mode
        # FIX BUG 18: store location peak irradiance instead of hardcoding 900
        self.location_peak_irr    = location_peak_irr

        # Store init params for reset
        self._battery_capacity_kwh = battery_capacity_kwh
        self._base_load_kw         = base_load_kw
        self._peak_load_kw         = peak_load_kw
        self._initial_soc          = initial_soc

        # Subsystem models
        self.battery    = BatteryModel(
            capacity_kwh = battery_capacity_kwh,
            soc_min      = 0.10,
            soc_max      = 0.90,
            initial_soc  = initial_soc
        )
        self.pv_model   = PVModel()
        self.load_model = LoadModel(
            base_load_kw = base_load_kw,
            peak_load_kw = peak_load_kw
        )

        # Estimator + Forecaster
        self.estimator  = StateEstimator(initial_soc=initial_soc)
        self.forecaster = Forecaster(
            pv_model   = self.pv_model,
            load_model = self.load_model,
            horizon    = forecast_horizon,
            dt_hours   = dt_hours
        )

        # State tracking
        self.current_state = TwinState(soc=initial_soc)
        self.timestep      = 0
        self.state_history : List[dict] = []

    # ----------------------------------------------------------------
    def twin_step(
        self,
        hour_of_day    : float,
        day_type       : str   = "weekday",
        irradiance     : float = None,
        ambient_temp_c : float = 25.0,
        grid_price     : float = None,
        charge_kw      : float = 0.0,
        discharge_kw   : float = 0.0,
        grid_import_kw : float = 0.0,
        grid_export_kw : float = 0.0,
        cloud_factor   : float = 1.0
    ) -> TwinState:
        """
        Advance the twin by one 15-minute timestep.
        """

        # 1. Generate sensor readings
        irradiance = (irradiance
                      if irradiance is not None
                      else self._simulate_irradiance(hour_of_day, cloud_factor))

        grid_price = (grid_price
                      if grid_price is not None
                      else self._get_tou_price(hour_of_day))

        pv_res  = self.pv_model.pv_power(irradiance, self.pv_area_m2, ambient_temp_c)
        pv_kw   = pv_res["power_kw"]
        load_kw = self.load_model.load_power(hour_of_day, day_type, add_noise=True)

        # 2. Update battery model
        batt = self.battery.step(charge_kw, discharge_kw, self.dt_hours)

        # 3. Simulate voltage (for Kalman)
        voltage_sim = self._soc_to_voltage(batt["soc"])

        # 4. State estimation
        # FIX BUG 21: Scale sensor noise to system size (was fixed 0.5/1.0 kW)
        # Old: np.random.normal(0, 0.5) on PV, np.random.normal(0, 1.0) on load
        # These are fine for 100+ kW campus but cause 17-50% error on small systems
        pv_noise   = max(0.05, pv_kw   * 0.03) if pv_kw > 0.001 else 0.0
        load_noise = max(0.10, load_kw * 0.03)

        est = self.estimator.estimate(
            soc_model        = batt["soc"],
            voltage_sensor   = voltage_sim + np.random.normal(0, 0.2),
            pv_sensor_kw     = pv_kw   + (np.random.normal(0, pv_noise) if pv_noise > 0 else 0.0),
            load_sensor_kw   = load_kw + np.random.normal(0, load_noise),
            battery_capacity = self.battery.capacity_kwh
        )

        # 5. Forecast bundle
        forecast = self.forecaster.get_forecast_bundle(
            current_hour = hour_of_day,
            area_m2      = self.pv_area_m2,
            day_type     = day_type,
            cloud_factor = cloud_factor
        )

        # 6. Build TwinState
        feed_in = grid_price * 0.5
        prev    = self.current_state

        state = TwinState(
            timestamp        = time.time(),
            timestep         = self.timestep,
            hour_of_day      = hour_of_day,
            day_type         = day_type,

            soc              = est["soc_estimate"],
            soc_uncertainty  = est["soc_uncertainty"],
            battery_kw       = batt["charge_kw"] - batt["discharge_kw"],
            battery_health   = max(0.5, 1.0 - batt["cycle_count"] / 3000.0),
            cycle_count      = batt["cycle_count"],

            pv_power_kw      = est["pv_estimated_kw"],
            pv_available_kw  = pv_kw,
            irradiance       = irradiance,
            pv_curtailed_kw  = max(0.0, pv_kw - est["pv_estimated_kw"]),

            load_kw          = est["load_estimated_kw"],
            load_unserved    = 0.0,

            grid_import_kw   = grid_import_kw,
            grid_export_kw   = grid_export_kw,
            grid_price       = grid_price,
            feed_in_tariff   = feed_in,

            cost_so_far      = (prev.cost_so_far
                                + grid_import_kw * grid_price * self.dt_hours),
            revenue_so_far   = (prev.revenue_so_far
                                + grid_export_kw * feed_in * self.dt_hours),

            carbon_intensity = 0.40,
            carbon_emitted   = (prev.carbon_emitted
                                + grid_import_kw * 0.40 * self.dt_hours),

            forecast         = forecast
        )

        self.current_state = state
        self.state_history.append(state.to_dict())
        self.timestep += 1
        return state

    # ----------------------------------------------------------------
    def run_day(
        self,
        actions      : list  = None,
        day_type     : str   = "weekday",
        cloud_factor : float = 1.0
    ) -> List[dict]:
        """Run a full 24-hour simulation day."""
        n_steps = int(24 / self.dt_hours)
        results = []

        for t in range(n_steps):
            hour = t * self.dt_hours

            if actions and t < len(actions):
                act = actions[t]
            else:
                act = {}

            state = self.twin_step(
                hour_of_day    = hour,
                day_type       = day_type,
                charge_kw      = act.get("charge_kw",      0.0),
                discharge_kw   = act.get("discharge_kw",   0.0),
                grid_import_kw = act.get("grid_import_kw", 0.0),
                grid_export_kw = act.get("grid_export_kw", 0.0),
                cloud_factor   = cloud_factor
            )
            results.append(state.to_dict())

        return results

    # ----------------------------------------------------------------
    def get_current_state(self) -> TwinState:
        """Return the current system state."""
        return self.current_state

    # ----------------------------------------------------------------
    def reset(self, initial_soc: float = 0.50):
        """Full reset of twin to initial conditions."""
        self.battery.reset(soc=initial_soc)
        self.estimator.reset(initial_soc=initial_soc)
        self.current_state = TwinState(soc=initial_soc)
        self.timestep      = 0
        self.state_history = []

    # ----------------------------------------------------------------
    def reset_full(self):
        """Complete rebuild of all subsystems."""
        self.battery = BatteryModel(
            capacity_kwh = self._battery_capacity_kwh,
            soc_min      = 0.10,
            soc_max      = 0.90,
            initial_soc  = self._initial_soc
        )
        self.estimator = StateEstimator(
            initial_soc = self._initial_soc
        )
        self.current_state = TwinState(soc=self._initial_soc)
        self.timestep      = 0
        self.state_history = []

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    def _simulate_irradiance(
        self,
        hour        : float,
        cloud_factor: float = 1.0
    ) -> float:
        """
        Synthetic irradiance for simulation mode.
        FIX BUG 18: Uses location_peak_irr instead of hardcoded 900 W/m²
        """
        if 6.0 <= hour <= 18.0:
            angle = np.pi * (hour - 6.0) / 12.0
            # FIX BUG 18: was 900.0 (hardcoded), now uses actual location peak
            base  = self.location_peak_irr * np.sin(angle) * cloud_factor
            return max(0.0, base + np.random.normal(0, 30.0))
        return 0.0

    def _get_tou_price(self, hour: float) -> float:
        """Time-of-Use tariff pricing (fallback when no grid_price passed)."""
        h = int(hour) % 24
        if h in range(17, 22):
            return 0.25    # On-peak
        if h in range(7, 17):
            return 0.15    # Mid-peak
        return 0.08        # Off-peak

    def _soc_to_voltage(self, soc: float) -> float:
        """Convert SOC to approximate pack voltage (27S LiFePO4)."""
        cells      = 27
        soc_pts    = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]
        v_cell_pts = [3.00, 3.20, 3.30, 3.35, 3.42, 3.50, 3.58, 3.65]
        v_cell     = float(np.interp(soc, soc_pts, v_cell_pts))
        return v_cell * cells