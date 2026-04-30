"""
Core Unit Tests — Intelligent Microgrid EMS
Run:  pytest tests/test_core_units.py -v
"""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.battery_model    import BatteryModel
from core.models.pv_model         import PVModel
from core.models.load_model       import LoadModel
from core.optimizer.cost_function import CostFunction
from core.optimizer.degradation   import DegradationModel
from core.optimizer.sizing        import SystemSizer
from core.optimizer.solver        import Solver
from core.twin.twin_core          import DigitalTwin
from core.twin.twin_state         import TwinState
from core.pipeline                import CorePipeline


# ============================================================
# HELPERS
# ============================================================

def make_twin_state(**kwargs) -> TwinState:
    defaults = dict(
        soc             = 0.50,
        pv_power_kw     = 2.0,
        pv_available_kw = 2.0,
        load_kw         = 3.0,
        grid_price      = 0.15,
        feed_in_tariff  = 0.075,
        battery_health  = 1.0,
        hour_of_day     = 12.0,
        day_type        = "weekday",
        forecast        = None,
        cycle_count     = 0.0,
        irradiance      = 600.0,
    )
    defaults.update(kwargs)
    return TwinState(**defaults)


def make_battery(**kwargs) -> BatteryModel:
    defaults = dict(
        capacity_kwh     = 100.0,
        max_charge_kw    = 50.0,
        max_discharge_kw = 50.0,
        soc_min          = 0.10,
        soc_max          = 0.95,
        initial_soc      = 0.50,
    )
    defaults.update(kwargs)
    return BatteryModel(**defaults)


def make_pipeline_with_plan() -> CorePipeline:
    """Helper: create pipeline with a standard plan already created."""
    pipeline = CorePipeline()
    pipeline.create_plan({
        "budget"               : 200000,
        "solar_price_per_kw"   : 1000,
        "battery_price_per_kwh": 300,
        "roof_area_m2"         : 200,
        "irradiance_wm2"       : 571,
        "grid_cost_per_kwh"    : 0.12,
        "battery_option"       : "auto",
        "solar_option"         : "yes",
        "day_type"             : "weekday",
        "monthly_data"         : [
            {"month": "Jan", "kwh": 8000},
            {"month": "Feb", "kwh": 7500},
            {"month": "Mar", "kwh": 8200},
            {"month": "Apr", "kwh": 9000},
            {"month": "May", "kwh": 9500},
            {"month": "Jun", "kwh": 8800},
            {"month": "Jul", "kwh": 8600},
            {"month": "Aug", "kwh": 8400},
            {"month": "Sep", "kwh": 8200},
            {"month": "Oct", "kwh": 8000},
            {"month": "Nov", "kwh": 7800},
            {"month": "Dec", "kwh": 7600},
        ]
    })
    return pipeline


BASE_INPUTS = {
    "budget"               : 200000,
    "solar_price_per_kw"   : 1000,
    "battery_price_per_kwh": 300,
    "roof_area_m2"         : 200,
    "irradiance_wm2"       : 571,
    "grid_cost_per_kwh"    : 0.12,
    "battery_option"       : "auto",
    "solar_option"         : "yes",
    "day_type"             : "weekday",
    "monthly_data"         : [
        {"month": "Jan", "kwh": 8000},
        {"month": "Feb", "kwh": 7500},
        {"month": "Mar", "kwh": 8200},
        {"month": "Apr", "kwh": 9000},
        {"month": "May", "kwh": 9500},
        {"month": "Jun", "kwh": 8800},
        {"month": "Jul", "kwh": 8600},
        {"month": "Aug", "kwh": 8400},
        {"month": "Sep", "kwh": 8200},
        {"month": "Oct", "kwh": 8000},
        {"month": "Nov", "kwh": 7800},
        {"month": "Dec", "kwh": 7600},
    ]
}


# ============================================================
# 1. BATTERY MODEL
# ============================================================

class TestBatteryModel:

    def setup_method(self):
        self.batt = make_battery()

    # --- Charging ---
    def test_charge_increases_soc(self):
        before = self.batt.soc
        self.batt.step(10.0, 0.0, 0.25)
        assert self.batt.soc > before

    def test_charge_physics(self):
        # 10 kW * 0.95 eff * 0.25 h / 100 kWh = +0.02375
        self.batt.step(10.0, 0.0, 0.25)
        expected = 0.50 + (10.0 * 0.95 * 0.25) / 100.0
        assert abs(self.batt.soc - expected) < 0.001

    def test_charge_capped_at_soc_max(self):
        self.batt.soc = 0.93
        self.batt.step(50.0, 0.0, 0.25)
        assert self.batt.soc <= self.batt.soc_max + 1e-6

    def test_charge_clamped_at_max_charge_kw(self):
        result = self.batt.step(999.0, 0.0, 0.25)
        assert result["charge_kw"] <= self.batt.max_charge_kw

    # --- Discharging ---
    def test_discharge_decreases_soc(self):
        before = self.batt.soc
        self.batt.step(0.0, 10.0, 0.25)
        assert self.batt.soc < before

    def test_discharge_physics(self):
        # 10 kW / 0.95 eff * 0.25 h / 100 kWh = -0.02632
        self.batt.step(0.0, 10.0, 0.25)
        expected = 0.50 - (10.0 / 0.95 * 0.25) / 100.0
        assert abs(self.batt.soc - expected) < 0.001

    def test_discharge_capped_at_soc_min(self):
        self.batt.soc = 0.12
        self.batt.step(0.0, 50.0, 0.25)
        assert self.batt.soc >= self.batt.soc_min - 1e-6

    def test_discharge_clamped_at_max_discharge_kw(self):
        result = self.batt.step(0.0, 999.0, 0.25)
        assert result["discharge_kw"] <= self.batt.max_discharge_kw

    def test_no_simultaneous_charge_discharge(self):
        # Net positive (charge > discharge) → only charging
        result = self.batt.step(20.0, 5.0, 0.25)
        assert result["discharge_kw"] == 0.0
        assert result["charge_kw"]    >  0.0

    def test_no_simultaneous_discharge_charge(self):
        # Net negative (discharge > charge) → only discharging
        result = self.batt.step(5.0, 20.0, 0.25)
        assert result["charge_kw"]    == 0.0
        assert result["discharge_kw"] >  0.0

    # --- Idle ---
    def test_idle_soc_unchanged(self):
        before = self.batt.soc
        self.batt.step(0.0, 0.0, 0.25)
        assert self.batt.soc == before

    def test_soc_always_in_range(self):
        for _ in range(300):
            self.batt.step(30.0, 0.0, 0.25)
        assert self.batt.soc_min - 1e-6 <= self.batt.soc <= self.batt.soc_max + 1e-6

    # --- Cycle count ---
    def test_cycle_count_increments_on_charge(self):
        before = self.batt.cycle_count
        self.batt.step(10.0, 0.0, 0.25)
        assert self.batt.cycle_count > before

    def test_cycle_count_unchanged_on_idle(self):
        before = self.batt.cycle_count
        self.batt.step(0.0, 0.0, 0.25)
        assert self.batt.cycle_count == before

    def test_cycle_count_never_negative(self):
        self.batt.step(0.0, 10.0, 0.25)
        assert self.batt.cycle_count >= 0.0

    # --- Available power helpers ---
    def test_available_discharge_at_full(self):
        self.batt.soc = 0.95
        assert self.batt.available_discharge_kw(0.25) > 0.0

    def test_available_discharge_zero_at_min(self):
        self.batt.soc = self.batt.soc_min
        assert self.batt.available_discharge_kw(0.25) == pytest.approx(0.0, abs=0.01)

    def test_available_charge_at_empty(self):
        self.batt.soc = 0.10
        assert self.batt.available_charge_kw(0.25) > 0.0

    def test_available_charge_zero_at_max(self):
        self.batt.soc = self.batt.soc_max
        assert self.batt.available_charge_kw(0.25) == pytest.approx(0.0, abs=0.01)

    def test_available_discharge_not_exceed_max_kw(self):
        self.batt.soc = 0.95
        assert self.batt.available_discharge_kw(0.25) <= self.batt.max_discharge_kw

    def test_available_charge_not_exceed_max_kw(self):
        self.batt.soc = 0.10
        assert self.batt.available_charge_kw(0.25) <= self.batt.max_charge_kw

    # --- Reset ---
    def test_reset_restores_soc(self):
        self.batt.step(40.0, 0.0, 0.25)
        self.batt.reset(soc=0.70)
        assert self.batt.soc == pytest.approx(0.70)

    def test_reset_clears_cycle_count(self):
        self.batt.step(10.0, 0.0, 0.25)
        self.batt.reset()
        assert self.batt.cycle_count == 0.0

    def test_reset_clears_energy_trackers(self):
        self.batt.step(10.0, 0.0, 0.25)
        self.batt.reset()
        assert self.batt.total_energy_charged_kwh    == 0.0
        assert self.batt.total_energy_discharged_kwh == 0.0

    # --- Bug 23 regression ---
    def test_small_battery_crate_realistic(self):
        """10 kWh battery: max charge must be 5 kW (0.5C), not 50 kW."""
        small  = make_battery(capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
        result = small.step(999.0, 0.0, 0.25)
        assert result["charge_kw"] <= 5.0, \
            "Bug 23: 10 kWh battery must not charge at 50 kW"

    def test_large_battery_crate_realistic(self):
        large  = make_battery(capacity_kwh=500.0, max_charge_kw=50.0, max_discharge_kw=50.0)
        result = large.step(999.0, 0.0, 0.25)
        assert result["charge_kw"] <= 50.0

    def test_get_status_returns_dict(self):
        status = self.batt.get_status()
        for key in ["soc", "soc_percent", "capacity_kwh",
                    "cycle_count", "max_charge_kw", "max_discharge_kw"]:
            assert key in status


# ============================================================
# 2. PV MODEL
# ============================================================

class TestPVModel:

    def setup_method(self):
        self.pv = PVModel(
            panel_efficiency    = 0.20,
            system_losses       = 0.14,
            inverter_efficiency = 0.97
        )

    # --- pv_power ---
    def test_zero_irradiance_zero_power(self):
        assert self.pv.pv_power(0.0, 100.0)["power_kw"] == 0.0

    def test_negative_irradiance_zero_power(self):
        assert self.pv.pv_power(-100.0, 100.0)["power_kw"] == 0.0

    def test_power_increases_with_irradiance(self):
        r1 = self.pv.pv_power(400.0, 100.0)
        r2 = self.pv.pv_power(800.0, 100.0)
        assert r2["power_kw"] > r1["power_kw"]

    def test_power_increases_with_area(self):
        r1 = self.pv.pv_power(700.0,  50.0)
        r2 = self.pv.pv_power(700.0, 100.0)
        assert r2["power_kw"] > r1["power_kw"]

    def test_power_never_negative(self):
        for irr in [0, 100, 500, 1000, 1200]:
            assert self.pv.pv_power(float(irr), 100.0)["power_kw"] >= 0.0

    def test_high_temp_reduces_output(self):
        r_cool = self.pv.pv_power(800.0, 100.0, ambient_temp_c=15.0)
        r_hot  = self.pv.pv_power(800.0, 100.0, ambient_temp_c=45.0)
        assert r_cool["power_kw"] > r_hot["power_kw"], \
            "Higher temperature must reduce PV output"

    def test_output_keys_present(self):
        result = self.pv.pv_power(700.0, 100.0)
        for key in ["power_kw", "power_w", "cell_temp_c", "efficiency", "irradiance"]:
            assert key in result

    # --- size_system: Bug 11 regression ---
    def test_size_system_no_double_count(self):
        """
        Bug 11: energy_per_m2 = base_eff * peak_sun_hours  (NOT * irradiance / 1000)
        base_eff = 0.20 * 0.86 * 0.97 = 0.16724
        energy/m2 = 0.16724 * 5.5 = 0.9198 kWh/m²/day
        required_area = 50 / 0.9198 = 54.4 m²
        """
        result = self.pv.size_system(
            target_kwh_per_day     = 50.0,
            avg_irradiance_wm2     = 700.0,   # must NOT affect result after fix
            peak_sun_hours         = 5.5,
            roof_area_available_m2 = 1000.0
        )
        assert result["required_area_m2"] == pytest.approx(54.4, rel=0.05), \
            "Bug 11: size_system is double-counting irradiance"

    def test_size_system_irradiance_does_not_affect_area(self):
        """After Bug 11 fix, changing avg_irradiance_wm2 must NOT change area."""
        r1 = self.pv.size_system(
            target_kwh_per_day=50.0, avg_irradiance_wm2=500.0,
            peak_sun_hours=5.5, roof_area_available_m2=1000.0)
        r2 = self.pv.size_system(
            target_kwh_per_day=50.0, avg_irradiance_wm2=900.0,
            peak_sun_hours=5.5, roof_area_available_m2=1000.0)
        assert r1["required_area_m2"] == pytest.approx(r2["required_area_m2"], rel=0.001), \
            "Bug 11: avg_irradiance_wm2 should not affect sizing after fix"

    def test_size_system_roof_limited(self):
        result = self.pv.size_system(
            target_kwh_per_day=5000.0, peak_sun_hours=5.5,
            roof_area_available_m2=50.0)
        assert result["roof_limited"] is True
        assert result["recommended_area_m2"] <= 50.0

    def test_size_system_peak_power_uses_stc(self):
        result = self.pv.size_system(
            target_kwh_per_day=50.0, peak_sun_hours=5.5,
            roof_area_available_m2=1000.0)
        expected_kw = result["recommended_area_m2"] * self.pv.base_efficiency
        assert abs(result["peak_power_kw"] - expected_kw) < 0.01

    def test_size_system_zero_target(self):
        result = self.pv.size_system(
            target_kwh_per_day=0.0, peak_sun_hours=5.5,
            roof_area_available_m2=1000.0)
        assert result["required_area_m2"] == pytest.approx(0.0, abs=0.01)

    # --- synthetic_irradiance ---
    def test_synthetic_irradiance_zero_at_night(self):
        profile = PVModel.synthetic_irradiance(
            n_steps=96, dt_hours=0.25, peak_irr=900.0, noise_std=0.0)
        night = [profile[t] for t in range(96) if not (6.0 <= t * 0.25 <= 18.0)]
        assert all(v == 0.0 for v in night)

    def test_synthetic_irradiance_peaks_at_noon(self):
        profile  = PVModel.synthetic_irradiance(
            n_steps=96, dt_hours=0.25, peak_irr=900.0, noise_std=0.0)
        noon_idx = int(12.0 / 0.25)
        assert profile[noon_idx] == pytest.approx(900.0, abs=5.0)

    def test_synthetic_irradiance_all_non_negative(self):
        profile = PVModel.synthetic_irradiance(n_steps=96, dt_hours=0.25)
        assert all(v >= 0.0 for v in profile)

    def test_generate_daily_profile_length(self):
        irr = PVModel.synthetic_irradiance(n_steps=96, dt_hours=0.25)
        profile = self.pv.generate_daily_profile(irr, area_m2=100.0, dt_hours=0.25)
        assert len(profile) == 96

    def test_generate_daily_profile_energy_kwh(self):
        irr = [700.0] * 96
        profile = self.pv.generate_daily_profile(irr, area_m2=100.0, dt_hours=0.25)
        for row in profile:
            assert row["energy_kwh"] == pytest.approx(row["power_kw"] * 0.25, rel=0.001)


# ============================================================
# 3. LOAD MODEL
# ============================================================

class TestLoadModel:

    def setup_method(self):
        self.lm = LoadModel(base_load_kw=200.0, peak_load_kw=800.0)

    def test_load_positive_all_hours(self):
        for h in range(24):
            assert self.lm.load_power(float(h), "weekday", add_noise=False) > 0

    def test_weekend_lower_than_weekday(self):
        wd = self.lm.load_power(12.0, "weekday",  add_noise=False)
        we = self.lm.load_power(12.0, "sunday",   add_noise=False)
        assert we < wd

    def test_holiday_lowest(self):
        wd = self.lm.load_power(12.0, "weekday", add_noise=False)
        hd = self.lm.load_power(12.0, "holiday", add_noise=False)
        assert hd < wd

    def test_from_monthly_bill_total_matches(self):
        monthly_kwh = 10000.0
        profile     = self.lm.from_monthly_bill(monthly_kwh, "weekday", dt_hours=0.25)
        total       = sum(p["energy_kwh"] for p in profile)
        assert abs(total - monthly_kwh / 30.0) < 0.5

    def test_from_monthly_bill_96_steps(self):
        assert len(self.lm.from_monthly_bill(10000.0, "weekday", 0.25)) == 96

    def test_from_monthly_bill_all_positive(self):
        profile = self.lm.from_monthly_bill(5000.0, "weekday", 0.25)
        assert all(p["load_kw"] > 0 for p in profile)

    def test_higher_bill_higher_load(self):
        p1 = self.lm.from_monthly_bill(5000.0,  "weekday", 0.25)
        p2 = self.lm.from_monthly_bill(10000.0, "weekday", 0.25)
        avg1 = sum(p["load_kw"] for p in p1) / len(p1)
        avg2 = sum(p["load_kw"] for p in p2) / len(p2)
        assert avg2 > avg1

    def test_from_monthly_bill_has_required_keys(self):
        profile = self.lm.from_monthly_bill(5000.0, "weekday", 0.25)
        for row in profile:
            for key in ["timestep", "hour", "load_kw", "energy_kwh"]:
                assert key in row

    def test_peak_demand_positive(self):
        assert self.lm.get_peak_demand_kw("weekday") > 0.0

    def test_daily_energy_less_than_peak_times_24(self):
        energy = self.lm.get_daily_energy_kwh("weekday")
        peak   = self.lm.get_peak_demand_kw("weekday")
        assert energy < peak * 24

    def test_energy_kwh_consistent_with_load_kw(self):
        profile = self.lm.from_monthly_bill(8000.0, "weekday", 0.25)
        for row in profile:
            assert row["energy_kwh"] == pytest.approx(row["load_kw"] * 0.25, rel=0.001)


# ============================================================
# 4. COST FUNCTION
# ============================================================

class TestCostFunction:

    def setup_method(self):
        self.cf = CostFunction(
            carbon_price_per_kg = 0.02,
            maintenance_rate    = 0.005,
            unserved_penalty    = 2.00
        )

    def _base_compute(self, **overrides):
        params = dict(
            grid_import_kw   = 5.0,
            grid_export_kw   = 0.0,
            charge_kw        = 0.0,
            discharge_kw     = 0.0,
            pv_kw            = 0.0,
            load_kw          = 5.0,
            grid_price       = 0.15,
            feed_in_tariff   = 0.075,
            degradation_cost = 0.0,
            dt_hours         = 0.25
        )
        params.update(overrides)
        return self.cf.compute(**params)

    def test_import_cost_correct(self):
        # 10 kW * 0.15 * 0.25 = 0.375
        result = self._base_compute(grid_import_kw=10.0, load_kw=10.0)
        assert result["import_cost"] == pytest.approx(0.375, rel=0.01)

    def test_total_positive_with_import(self):
        result = self._base_compute(grid_import_kw=5.0)
        assert result["total_cost"] > 0.0

    def test_export_reduces_total(self):
        r_no  = self._base_compute(grid_export_kw=0.0)
        r_yes = self._base_compute(grid_export_kw=2.0)
        assert r_yes["total_cost"] < r_no["total_cost"]

    def test_degradation_adds_to_cost(self):
        r1 = self._base_compute(degradation_cost=0.0)
        r2 = self._base_compute(degradation_cost=0.05)
        assert r2["total_cost"] > r1["total_cost"]

    def test_zero_import_zero_import_cost(self):
        result = self._base_compute(grid_import_kw=0.0, load_kw=0.0)
        assert result["import_cost"] == 0.0

    def test_carbon_proportional_to_import(self):
        r1 = self._base_compute(grid_import_kw=5.0,  load_kw=5.0)
        r2 = self._base_compute(grid_import_kw=10.0, load_kw=10.0)
        assert r2["carbon_cost"] == pytest.approx(r1["carbon_cost"] * 2, rel=0.01)

    def test_carbon_zero_when_no_import(self):
        result = self._base_compute(grid_import_kw=0.0)
        assert result["carbon_cost"] == 0.0

    def test_all_output_keys_present(self):
        result = self._base_compute()
        for key in ["total_cost", "import_cost", "export_revenue",
                    "degradation_cost", "carbon_cost", "maintenance_cost",
                    "unserved_cost", "carbon_kg"]:
            assert key in result

    def test_daily_summary_sums_correctly(self):
        steps = [self._base_compute() for _ in range(4)]
        summary = self.cf.daily_summary(steps)
        expected_total = sum(s["total_cost"] for s in steps)
        assert summary["total_cost"] == pytest.approx(expected_total, rel=0.001)


# ============================================================
# 5. DEGRADATION MODEL
# ============================================================

class TestDegradationModel:

    def setup_method(self):
        self.dm = DegradationModel(
            battery_cost_per_kwh = 300.0,
            battery_capacity_kwh = 100.0,
            total_lifecycle_kwh  = 50000.0
        )

    def test_zero_throughput_zero_cost(self):
        result = self.dm.degradation_cost(0.0, 0.0, 0.5, 0.25)
        assert result["degradation_cost"] == 0.0

    def test_charge_gives_positive_cost(self):
        result = self.dm.degradation_cost(10.0, 0.0, 0.5, 0.25)
        assert result["degradation_cost"] > 0.0

    def test_discharge_gives_positive_cost(self):
        result = self.dm.degradation_cost(0.0, 10.0, 0.5, 0.25)
        assert result["degradation_cost"] > 0.0

    def test_extreme_soc_higher_stress_than_mid(self):
        mid     = self.dm.degradation_cost(10.0, 0.0, 0.50, 0.25)
        extreme = self.dm.degradation_cost(10.0, 0.0, 0.95, 0.25)
        assert extreme["degradation_cost"] > mid["degradation_cost"]

    def test_low_soc_higher_stress_than_mid(self):
        mid = self.dm.degradation_cost(10.0, 0.0, 0.50, 0.25)
        low = self.dm.degradation_cost(10.0, 0.0, 0.10, 0.25)
        assert low["degradation_cost"] > mid["degradation_cost"]

    def test_higher_crate_more_degradation_per_kwh(self):
        slow = self.dm.degradation_cost(5.0,  0.0, 0.5, 0.25)
        fast = self.dm.degradation_cost(40.0, 0.0, 0.5, 0.25)
        slow_per = slow["degradation_cost"] / (5.0  * 0.25)
        fast_per = fast["degradation_cost"] / (40.0 * 0.25)
        assert fast_per > slow_per

    def test_all_output_keys_present(self):
        result = self.dm.degradation_cost(10.0, 0.0, 0.5, 0.25)
        for key in ["degradation_cost", "degradation_fraction",
                    "soc_stress_factor", "crate_stress_factor",
                    "temp_stress_factor", "energy_kwh"]:
            assert key in result

        # Bug 20 regression
    def test_custom_capacity_changes_crate_stress(self):
        """
        Bug 20: DegradationModel must use actual battery capacity.
        After fix: base_cost_per_kwh = battery_cost / lifecycle_cycles (same for all sizes).
        Only the C-rate stress differs → small battery (higher C-rate) degrades more per kWh.

        5 kW charge:
          10 kWh battery  → C-rate = 0.50 → crate_stress = 1 + 1.5*(0.5²)  = 1.375
          100 kWh battery → C-rate = 0.05 → crate_stress = 1 + 1.5*(0.05²) = 1.004
        """
        dm_small = DegradationModel(battery_capacity_kwh=10.0)
        dm_large = DegradationModel(battery_capacity_kwh=100.0)

        r_small = dm_small.degradation_cost(5.0, 0.0, 0.5, 0.25)
        r_large = dm_large.degradation_cost(5.0, 0.0, 0.5, 0.25)

        energy_kwh = 5.0 * 0.25

        cost_per_kwh_small = r_small["degradation_cost"] / energy_kwh
        cost_per_kwh_large = r_large["degradation_cost"] / energy_kwh

        assert cost_per_kwh_small > cost_per_kwh_large, (
            f"Bug 20: Small battery (C-rate=0.5) must degrade more per kWh "
            f"than large (C-rate=0.05). "
            f"Got small={cost_per_kwh_small:.5f}, large={cost_per_kwh_large:.5f}"
        )
# ============================================================
# 6. SOLVER
# ============================================================

class TestSolver:

    def setup_method(self):
        self.solver = Solver(
            degradation_model=DegradationModel(battery_capacity_kwh=100.0)
        )

    def test_returns_best_action(self):
        state  = make_twin_state()
        result = self.solver.optimize(state)
        assert result["best_action"] is not None

    def test_best_action_required_keys(self):
        result = self.solver.optimize(make_twin_state())
        for key in ["action_name", "charge_kw", "discharge_kw",
                    "grid_import_kw", "grid_export_kw", "total_cost"]:
            assert key in result["best_action"]

    def test_charge_discharge_non_negative(self):
        result = self.solver.optimize(make_twin_state())
        assert result["best_action"]["charge_kw"]    >= 0.0
        assert result["best_action"]["discharge_kw"] >= 0.0

    def test_grid_import_non_negative(self):
        result = self.solver.optimize(make_twin_state())
        assert result["best_action"]["grid_import_kw"] >= 0.0

    def test_no_solar_at_night(self):
        state  = make_twin_state(
            pv_power_kw=0.0, pv_available_kw=0.0,
            load_kw=3.0, hour_of_day=2.0
        )
        result = self.solver.optimize(state)
        action = result["best_action"]["action_name"]
        assert action in ["grid_only", "battery_discharge", "peak_shaving"], \
            f"Night action must not use solar, got: {action}"

    def test_surplus_solar_charges_or_exports(self):
        state  = make_twin_state(
            soc=0.30, pv_power_kw=10.0, pv_available_kw=10.0,
            load_kw=2.0, hour_of_day=12.0
        )
        result = self.solver.optimize(state)
        action = result["best_action"]["action_name"]
        assert action in ["solar_charge_battery", "export_surplus", "solar_direct"], \
            f"Surplus solar must charge/export, got: {action}"

    def test_battery_discharges_at_high_price(self):
        """
        High tariff + available battery → solver must discharge.
        After degradation fix: base_cost=\$0.10/kWh < grid_price=\$0.25/kWh
        so battery discharge wins.
        """
        solver = Solver(
            degradation_model=DegradationModel(
                battery_cost_per_kwh = 300.0,
                battery_capacity_kwh = 100.0,
            )
        )
        state  = make_twin_state(
            soc=0.80, pv_power_kw=0.0, pv_available_kw=0.0,
            load_kw=5.0, grid_price=0.25, hour_of_day=18.0
        )
        result = solver.optimize(state)
        action = result["best_action"]["action_name"]
        assert action in ["battery_discharge", "peak_shaving"], (
            f"High price (\$0.25) + charged battery (SOC=0.80) must discharge. "
            f"Got: {action}"
        )

    def test_grid_only_when_no_resources(self):
        state  = make_twin_state(
            soc=0.10, pv_power_kw=0.0, pv_available_kw=0.0,
            load_kw=5.0, hour_of_day=2.0
        )
        result = self.solver.optimize(state)
        assert result["best_action"]["action_name"] == "grid_only"

    def test_all_candidates_evaluated(self):
        state  = make_twin_state(soc=0.50, pv_power_kw=3.0, load_kw=2.0)
        result = self.solver.optimize(state)
        assert len(result["all_candidates"]) > 0

    def test_best_cost_is_minimum(self):
        state      = make_twin_state()
        result     = self.solver.optimize(state)
        best_cost  = result["best_action"]["total_cost"]
        all_costs  = [c["total_cost"] for c in result["all_candidates"]]
        assert best_cost <= min(all_costs) + 1e-6


# ============================================================
# 7. DIGITAL TWIN
# ============================================================

class TestDigitalTwin:

    def setup_method(self):
        self.twin = DigitalTwin(
            battery_capacity_kwh = 50.0,
            pv_area_m2           = 100.0,
            base_load_kw         = 5.0,
            peak_load_kw         = 20.0,
            initial_soc          = 0.50,
            location_peak_irr    = 800.0,
        )

    def test_step_returns_twin_state(self):
        state = self.twin.twin_step(hour_of_day=12.0)
        assert isinstance(state, TwinState)

    def test_state_has_required_fields(self):
        state = self.twin.twin_step(hour_of_day=10.0)
        for field in ["soc", "pv_power_kw", "load_kw",
                      "grid_price", "hour_of_day", "battery_health"]:
            assert hasattr(state, field)

    def test_soc_in_valid_range(self):
        state = self.twin.twin_step(hour_of_day=12.0, charge_kw=5.0)
        assert 0.0 <= state.soc <= 1.0

    def test_soc_increases_on_charge(self):
        before = self.twin.battery.soc
        self.twin.twin_step(hour_of_day=12.0, charge_kw=10.0, discharge_kw=0.0)
        assert self.twin.battery.soc > before

    def test_soc_decreases_on_discharge(self):
        before = self.twin.battery.soc
        self.twin.twin_step(hour_of_day=12.0, charge_kw=0.0, discharge_kw=10.0)
        assert self.twin.battery.soc < before

    def test_pv_zero_at_night(self):
        """
        At 2am with irradiance=0, PV must be effectively zero.
        abs=0.1 tolerance accounts for Kalman/EMA estimator residual (~0.02 kW).
        """
        state = self.twin.twin_step(hour_of_day=2.0, irradiance=0.0)
        assert state.pv_power_kw == pytest.approx(0.0, abs=0.1), (
            f"PV at 2am with irradiance=0 must be ~0. "
            f"Got {state.pv_power_kw:.4f} kW"
        )

    def test_pv_positive_at_noon(self):
        state = self.twin.twin_step(hour_of_day=12.0, irradiance=800.0)
        assert state.pv_power_kw > 0.0

    def test_load_always_positive(self):
        state = self.twin.twin_step(hour_of_day=3.0)
        assert state.load_kw > 0.0

    def test_timestep_increments(self):
        for _ in range(4):
            self.twin.twin_step(12.0)
        assert self.twin.timestep == 4

    def test_reset_clears_history(self):
        for _ in range(5):
            self.twin.twin_step(12.0)
        self.twin.reset(initial_soc=0.60)
        assert self.twin.timestep              == 0
        assert len(self.twin.state_history)    == 0
        assert self.twin.battery.soc           == pytest.approx(0.60)

    def test_reset_resets_cycle_count(self):
        self.twin.twin_step(12.0, charge_kw=10.0)
        self.twin.reset()
        assert self.twin.battery.cycle_count == 0.0

    # Bug 18 regression: location irradiance
    def test_location_irradiance_affects_pv(self):
        """Bug 18: twin must use location_peak_irr, not hardcoded 900."""
        twin_low  = DigitalTwin(
            pv_area_m2=100.0, battery_capacity_kwh=50.0,
            base_load_kw=5.0,  peak_load_kw=20.0,
            location_peak_irr=300.0
        )
        twin_high = DigitalTwin(
            pv_area_m2=100.0, battery_capacity_kwh=50.0,
            base_load_kw=5.0,  peak_load_kw=20.0,
            location_peak_irr=950.0
        )
        s_low  = twin_low.twin_step(hour_of_day=12.0,  cloud_factor=1.0)
        s_high = twin_high.twin_step(hour_of_day=12.0, cloud_factor=1.0)
        assert s_high.pv_power_kw > s_low.pv_power_kw, \
            "Bug 18: Higher location_peak_irr must produce more PV"

    # Bug 21 regression: noise scaling
    def test_sensor_noise_scaled_to_system(self):
        """Bug 21: noise must be < 15% of mean reading."""
        readings = []
        for _ in range(50):
            state = self.twin.twin_step(
                hour_of_day=12.0, irradiance=700.0, cloud_factor=1.0)
            readings.append(state.pv_power_kw)
        mean = float(np.mean(readings))
        std  = float(np.std(readings))
        if mean > 0.1:
            assert std / mean < 0.15, \
                f"Bug 21: PV noise {std/mean:.1%} too large for system size"

    def test_run_day_returns_96_entries(self):
        results = self.twin.run_day(day_type="weekday", cloud_factor=0.9)
        assert len(results) == 96


# ============================================================
# 8. SYSTEM SIZER
# ============================================================

class TestSystemSizer:

    def setup_method(self):
        self.sizer = SystemSizer(
            solar_price_per_kw    = 1000.0,
            battery_price_per_kwh = 300.0,
            grid_price            = 0.12,
            feed_in_tariff        = 0.06,
            roof_area_m2          = 500.0
        )

    def test_returns_required_keys(self):
        result = self.sizer.run_sizing(
            monthly_kwh=5000.0, budget=100000.0,
            solar_range_kw=[0, 10, 20],
            battery_range_kwh=[0, 10],
            peak_irr=700.0
        )
        for key in ["best_solar_kw", "best_battery_kwh", "best_daily_cost",
                    "annual_savings", "investment", "roi_years",
                    "baseline_daily_cost", "top_5_options"]:
            assert key in result

    def test_investment_within_budget(self):
        budget = 50000.0
        result = self.sizer.run_sizing(
            monthly_kwh=5000.0, budget=budget,
            solar_range_kw=[0, 10, 20, 30],
            battery_range_kwh=[0, 10, 20],
            peak_irr=700.0
        )
        assert result["investment"] <= budget + 1.0

    def test_solar_reduces_daily_cost(self):
        result = self.sizer.run_sizing(
            monthly_kwh=5000.0, budget=200000.0,
            solar_range_kw=[0, 20, 50],
            battery_range_kwh=[0],
            peak_irr=700.0
        )
        assert result["best_daily_cost"] <= result["baseline_daily_cost"] + 0.001

    def test_zero_budget_no_system(self):
        result = self.sizer.run_sizing(
            monthly_kwh=5000.0, budget=0.0,
            solar_range_kw=[0, 10, 20],
            battery_range_kwh=[0, 10]
        )
        assert result["investment"] == 0.0

    # Bug 24 regression
    def test_selects_meaningful_plan_with_near_best_roi(self):
        """When a slightly lower ROI produces much higher savings, prefer the more practical plan."""
        result = self.sizer.run_sizing(
            monthly_kwh=11825.0, budget=300000.0,
            solar_range_kw=[10.95, 21.9, 32.85, 43.8],
            battery_range_kwh=[0.0, 39.4],
            peak_irr=600.0
        )
        assert result["best_battery_kwh"] > 0.0, \
            "Battery should be selected when it increases savings within a near-best ROI range"

    def test_calculate_roi_payback_correct(self):
        roi = self.sizer.calculate_roi(
            investment=100000.0, annual_savings=20000.0)
        # net_benefit = 20000 - 1000 = 19000, payback = 100000/19000
        assert roi["payback_years"] == pytest.approx(100000.0 / 19000.0, rel=0.01)

    def test_calculate_roi_viable_flag(self):
        roi = self.sizer.calculate_roi(
            investment=100000.0, annual_savings=20000.0)
        assert roi["is_viable"] is True

    def test_calculate_roi_not_viable_no_savings(self):
        roi = self.sizer.calculate_roi(
            investment=100000.0, annual_savings=0.0)
        assert roi["is_viable"] is False

    def test_calculate_roi_npv_negative_if_bad(self):
        roi = self.sizer.calculate_roi(
            investment=1000000.0, annual_savings=1000.0)
        assert roi["npv_10yr"] < 0


# ============================================================
# 9. FULL PIPELINE INTEGRATION
# ============================================================

class TestCorePipeline:

    def setup_method(self):
        self.pipeline = CorePipeline()

    def test_create_plan_returns_dict(self):
        plan = self.pipeline.create_plan(BASE_INPUTS)
        assert isinstance(plan, dict)

    def test_plan_has_required_keys(self):
        plan = self.pipeline.create_plan(BASE_INPUTS)
        for key in ["recommended_solar_kw", "recommended_battery_kwh",
                    "investment", "annual_savings", "roi_years",
                    "daily_load_profile", "sample_24h_schedule",
                    "baseline_daily_cost", "optimized_daily_cost"]:
            assert key in plan, f"Plan missing key: {key}"

    def test_solar_size_positive(self):
        plan = self.pipeline.create_plan(BASE_INPUTS)
        assert plan["recommended_solar_kw"] > 0.0

    def test_investment_within_budget(self):
        plan = self.pipeline.create_plan(BASE_INPUTS)
        assert plan["investment"] <= BASE_INPUTS["budget"] * 1.01

    def test_sample_schedule_96_steps(self):
        plan = self.pipeline.create_plan(BASE_INPUTS)
        assert len(plan["sample_24h_schedule"]) == 96

    def test_sample_schedule_has_required_keys(self):
        plan  = self.pipeline.create_plan(BASE_INPUTS)
        first = plan["sample_24h_schedule"][0]
        for key in ["hour", "soc", "pv_kw", "load_kw",
                    "action", "charge_kw", "discharge_kw",
                    "grid_import_kw", "grid_export_kw", "cost"]:
            assert key in first, f"Schedule row missing key: {key}"

    def test_soc_changes_in_schedule(self):
        """Battery must actually charge/discharge during simulation."""
        plan   = self.pipeline.create_plan(BASE_INPUTS)
        socs   = [s["soc"] for s in plan["sample_24h_schedule"]]
        unique = len(set(round(s, 2) for s in socs))
        assert unique > 3, \
            "SOC never changes in 24h schedule — battery not working"

    def test_location_irradiance_stored(self):
        """Bug 12: pipeline must store location_peak_irr."""
        self.pipeline.create_plan(BASE_INPUTS)
        assert self.pipeline._location_peak_irr == pytest.approx(
            BASE_INPUTS["irradiance_wm2"], rel=0.01), \
            "Bug 12: _location_peak_irr not stored correctly"

    def test_grid_cost_stored(self):
        self.pipeline.create_plan(BASE_INPUTS)
        assert self.pipeline._grid_cost == pytest.approx(
            BASE_INPUTS["grid_cost_per_kwh"], rel=0.01)

    def test_last_action_initialized(self):
        """Bug 7: _last_action must exist from __init__, not via getattr."""
        fresh = CorePipeline()
        assert hasattr(fresh, "_last_action")
        assert fresh._last_action == {}

    def test_predict_without_plan_returns_error(self):
        fresh  = CorePipeline()
        result = fresh.predict({"hour_of_day": 12.0})
        assert "error" in result

    def test_predict_after_plan_returns_action(self):
        self.pipeline.create_plan(BASE_INPUTS)
        result = self.pipeline.predict({
            "hour_of_day" : 12.0,
            "day_type"    : "weekday",
            "cloud_factor": 0.8,
            "grid_price"  : 0.12
        })
        assert "action_name" in result
        assert result["action_name"] != ""

    def test_predict_soc_in_range(self):
        self.pipeline.create_plan(BASE_INPUTS)
        result = self.pipeline.predict({"hour_of_day": 12.0})
        assert 0.0 <= result["current_soc"] <= 1.0

    def test_predict_updates_last_action(self):
        """Bug 16: _last_action must be updated after predict."""
        self.pipeline.create_plan(BASE_INPUTS)
        self.pipeline.predict({"hour_of_day": 12.0, "cloud_factor": 0.8})
        assert self.pipeline._last_action != {}, \
            "Bug 16: _last_action not updated after predict"

    def test_predict_last_action_stores_final_not_best(self):
        """Bug 16: must store final_action (after policy), not best_action."""
        self.pipeline.create_plan(BASE_INPUTS)
        self.pipeline.predict({"hour_of_day": 12.0})
        last = self.pipeline._last_action
        # final_action from policy always has these keys
        for key in ["charge_kw", "discharge_kw", "grid_import_kw"]:
            assert key in last, \
                f"Bug 16: _last_action missing key {key} — may be storing wrong action"

    def test_predict_pv_correct_at_noon(self):
        self.pipeline.create_plan(BASE_INPUTS)
        result = self.pipeline.predict({
            "hour_of_day" : 12.0,
            "cloud_factor": 1.0,
            "grid_price"  : 0.12
        })
        assert result["current_pv_kw"] >= 0.0

    def test_predict_pv_zero_at_night(self):
        self.pipeline.create_plan(BASE_INPUTS)
        result = self.pipeline.predict({
            "hour_of_day" : 2.0,
            "cloud_factor": 1.0
        })
        assert result["current_pv_kw"] == pytest.approx(0.0, abs=0.1), \
            "PV must be ~0 at 2am"

    def test_predict_uses_location_irradiance(self):
        """Bug 12: two plans with different irradiance must give different PV."""
        p_low  = CorePipeline()
        p_high = CorePipeline()
        inputs_low  = {**BASE_INPUTS, "irradiance_wm2": 300.0}
        inputs_high = {**BASE_INPUTS, "irradiance_wm2": 850.0}
        p_low.create_plan(inputs_low)
        p_high.create_plan(inputs_high)
        r_low  = p_low.predict({"hour_of_day": 12.0, "cloud_factor": 1.0})
        r_high = p_high.predict({"hour_of_day": 12.0, "cloud_factor": 1.0})
        assert r_high["current_pv_kw"] > r_low["current_pv_kw"], \
            "Bug 12: higher location irradiance must give more PV in prediction"

    def test_multiple_predictions_soc_evolves(self):
        """Battery SOC must change across multiple prediction calls."""
        self.pipeline.create_plan(BASE_INPUTS)
        socs = []
        for h in range(0, 24, 2):
            result = self.pipeline.predict({
                "hour_of_day" : float(h),
                "cloud_factor": 0.8,
                "grid_price"  : 0.12
            })
            socs.append(result["current_soc"])
        unique = len(set(round(s, 3) for s in socs))
        assert unique > 2, \
            "Battery SOC never changes across predictions — charge/discharge broken"

    def test_different_monthly_data_different_solar(self):
        """Different consumption must produce different solar recommendations."""
        p1 = CorePipeline()
        p2 = CorePipeline()
        low_inputs  = {**BASE_INPUTS,
                       "monthly_data": [{"month": "Jan", "kwh": 2000}] * 12}
        high_inputs = {**BASE_INPUTS,
                       "monthly_data": [{"month": "Jan", "kwh": 15000}] * 12}
        plan1 = p1.create_plan(low_inputs)
        plan2 = p2.create_plan(high_inputs)
        assert plan2["recommended_solar_kw"] >= plan1["recommended_solar_kw"], \
            "Higher consumption must recommend at least as much solar"

    def test_get_plan_summary_after_create(self):
        self.pipeline.create_plan(BASE_INPUTS)
        summary = self.pipeline.get_plan_summary()
        assert "error" not in summary
        for key in ["solar_kw", "battery_kwh", "roi_years",
                    "annual_savings", "investment"]:
            assert key in summary

    def test_get_plan_summary_before_create(self):
        fresh   = CorePipeline()
        summary = fresh.get_plan_summary()
        assert "error" in summary


# ============================================================
# 10. EDGE CASES & BOUNDARY CONDITIONS
# ============================================================

class TestEdgeCases:

    def test_battery_full_cycle(self):
        """Charge from 10% to 95% then discharge back to 10%."""
        batt = make_battery(initial_soc=0.10)
        # Charge
        while batt.soc < 0.90:
            batt.step(20.0, 0.0, 0.25)
        assert batt.soc >= 0.85
        # Discharge
        while batt.soc > 0.15:
            batt.step(0.0, 20.0, 0.25)
        assert batt.soc <= 0.20

    def test_pv_model_zero_area(self):
        pv     = PVModel()
        result = pv.pv_power(800.0, 0.0)
        assert result["power_kw"] == 0.0

    def test_solver_handles_zero_pv_zero_battery(self):
        solver = Solver()
        state  = make_twin_state(
            soc=0.10, pv_power_kw=0.0, pv_available_kw=0.0,
            load_kw=5.0, hour_of_day=3.0
        )
        result = solver.optimize(state)
        assert result["best_action"]["action_name"] == "grid_only"

    def test_twin_handles_zero_irradiance(self):
        """
        irradiance=0.0 must give ~0 PV output.
        abs=0.1 tolerance for state estimator smoothing residual.
        """
        twin  = DigitalTwin(
            battery_capacity_kwh=50.0, pv_area_m2=100.0,
            base_load_kw=5.0, peak_load_kw=20.0
        )
        state = twin.twin_step(hour_of_day=12.0, irradiance=0.0)
        assert state.pv_power_kw == pytest.approx(0.0, abs=0.1), (
            f"irradiance=0.0 must give ~0 PV. "
            f"Got {state.pv_power_kw:.4f} kW"
        )
        assert state.load_kw > 0.0

    def test_pipeline_single_month_data(self):
        """Pipeline must work even with just 1 month of data."""
        pipeline = CorePipeline()
        inputs   = {**BASE_INPUTS,
                    "monthly_data": [{"month": "Jan", "kwh": 8000}]}
        plan     = pipeline.create_plan(inputs)
        assert plan["recommended_solar_kw"] > 0.0

    def test_pipeline_very_small_budget(self):
        """Very small budget should not crash — returns zero system."""
        pipeline = CorePipeline()
        inputs   = {**BASE_INPUTS, "budget": 100.0}
        plan     = pipeline.create_plan(inputs)
        assert plan["investment"] <= 100.0 + 1.0

    def test_pipeline_zero_roof_area(self):
        """Zero roof area should give zero solar."""
        pipeline = CorePipeline()
        inputs   = {**BASE_INPUTS, "roof_area_m2": 0.0}
        plan     = pipeline.create_plan(inputs)
        assert plan["recommended_solar_kw"] == pytest.approx(0.0, abs=0.5)

    def test_cost_function_all_zeros(self):
        cf     = CostFunction()
        result = cf.compute(
            grid_import_kw=0.0, grid_export_kw=0.0,
            charge_kw=0.0, discharge_kw=0.0,
            pv_kw=0.0, load_kw=0.0,
            grid_price=0.15, feed_in_tariff=0.075,
            degradation_cost=0.0, dt_hours=0.25
        )
        assert result["total_cost"] == pytest.approx(0.0, abs=1e-9)