"""
System Sizing Module
Finds the optimal solar panel size and battery capacity
"""

import numpy as np
from typing import List, Tuple

from ..models.pv_model      import PVModel
from ..models.load_model    import LoadModel
from ..models.battery_model import BatteryModel


class SystemSizer:

    def __init__(
        self,
        pv_model              : PVModel   = None,
        load_model            : LoadModel = None,
        solar_price_per_kw    : float = 1000.0,
        battery_price_per_kwh : float = 300.0,
        grid_price            : float = 0.15,
        feed_in_tariff        : float = 0.075,
        dt_hours              : float = 0.25,
        roof_area_m2          : float = 1000.0
    ):
        self.pv_model             = pv_model    or PVModel()
        self.load_model           = load_model  or LoadModel()
        self.solar_price_per_kw   = solar_price_per_kw
        self.battery_price_per_kwh= battery_price_per_kwh
        self.grid_price           = grid_price
        self.feed_in_tariff       = feed_in_tariff
        self.dt_hours             = dt_hours
        self.roof_area_m2         = roof_area_m2

    # ----------------------------------------------------------------
    def run_sizing(
        self,
        monthly_kwh       : float,
        budget            : float       = 100000.0,
        solar_range_kw    : List[float] = None,
        battery_range_kwh : List[float] = None,
        day_type          : str         = "weekday",
        peak_irr          : float       = 800.0
    ) -> dict:

        if solar_range_kw is None:
            solar_range_kw = [0, 25, 50, 75, 100, 150, 200, 250, 300]
        if battery_range_kwh is None:
            battery_range_kwh = [0, 25, 50, 75, 100, 150, 200]

        load_profile        = self.load_model.from_monthly_bill(monthly_kwh, day_type, self.dt_hours)
        loads               = [p["load_kw"] for p in load_profile]
        baseline_daily_cost = sum(l * self.grid_price * self.dt_hours for l in loads)

        best_result = None
        all_results = []

        for solar_kw in solar_range_kw:
            for batt_kwh in battery_range_kwh:

                investment = (solar_kw  * self.solar_price_per_kw
                             + batt_kwh * self.battery_price_per_kwh)
                if investment > budget:
                    continue

                if solar_kw == 0 and batt_kwh == 0:
                    all_results.append({
                        "solar_kw"      : 0,
                        "battery_kwh"   : 0,
                        "daily_cost"    : round(baseline_daily_cost, 4),
                        "investment"    : 0.0,
                        "annual_savings": 0.0,
                        "roi_years"     : float("inf")
                    })
                    continue

                # Physical Constraint: A battery cannot be charged if it's too large for the solar array.
                # (Assuming no grid charging). Rule of thumb: max battery = 3x solar peak power.
                # If solar is 0, battery must be 0 in our current simulation.
                if solar_kw == 0 and batt_kwh > 0:
                    continue
                if batt_kwh > solar_kw * 3.0:
                    continue

                daily_cost, solar_used = self._simulate_day(
                    solar_peak_kw = solar_kw,
                    battery_kwh   = batt_kwh,
                    loads         = loads,
                    peak_irr      = peak_irr
                )

                annual_savings = (baseline_daily_cost - daily_cost) * 365.0
                roi_years      = (investment / annual_savings
                                  if annual_savings > 0 else float("inf"))

                result = {
                    "solar_kw"      : solar_kw,
                    "battery_kwh"   : batt_kwh,
                    "daily_cost"    : round(daily_cost, 4),
                    "investment"    : round(investment, 2),
                    "annual_savings": round(annual_savings, 2),
                    "roi_years"     : round(roi_years, 2),
                    "solar_used_kwh": round(solar_used, 3)
                }
                all_results.append(result)

        best_result = self._select_best_result(all_results)
        if best_result is None:
            best_result = {
                "solar_kw"      : 0,
                "battery_kwh"   : 0,
                "daily_cost"    : baseline_daily_cost,
                "investment"    : 0.0,
                "annual_savings": 0.0,
                "roi_years"     : float("inf")
            }

        all_results_sorted = sorted(
            [r for r in all_results if r["roi_years"] != float("inf")],
            key=lambda x: x["roi_years"]
        )

        return {
            "best_solar_kw"      : best_result["solar_kw"],
            "best_battery_kwh"   : best_result["battery_kwh"],
            "best_daily_cost"    : best_result["daily_cost"],
            "baseline_daily_cost": round(baseline_daily_cost, 4),
            "daily_savings"      : round(baseline_daily_cost - best_result["daily_cost"], 4),
            "annual_savings"     : best_result["annual_savings"],
            "investment"         : best_result["investment"],
            "roi_years"          : best_result["roi_years"],
            "top_5_options"      : all_results_sorted[:5],
            "all_results"        : all_results
        }

    def _select_best_result(self, all_results: List[dict]) -> dict:
        """Choose a practical system rather than a trivial high-ROI minimum system.
        Prevents diminishing returns where massive investments yield negligible extra savings."""
        viable = [
            r for r in all_results
            if r["roi_years"] != float("inf") and r["annual_savings"] > 0
        ]
        if not viable:
            return None

        best_roi = min(r["roi_years"] for r in viable)
        
        # Relax threshold to allow battery inclusion. Battery lowers ROI but increases savings.
        threshold = min(max(best_roi * 1.5, best_roi + 4.0), 12.0)

        candidates = [r for r in viable if r["roi_years"] <= threshold]
        if not candidates:
            return min(viable, key=lambda r: (r["roi_years"], r["investment"]))
            
        # Diminishing Returns Penalty: Group candidates that achieve within 95% of the max savings
        max_savings = max(r["annual_savings"] for r in candidates)
        top_tier = [r for r in candidates if r["annual_savings"] >= 0.95 * max_savings]
        
        # Pick the cheapest investment among the top savers
        return min(top_tier, key=lambda r: r["investment"])

    # ----------------------------------------------------------------
    def _simulate_day(
        self,
        solar_peak_kw : float,
        battery_kwh   : float,
        loads         : List[float],
        peak_irr      : float = 800.0
    ) -> Tuple[float, float]:

        # FIX BUG 23: Scale max_charge/discharge to battery size (0.5C rate)
        # OLD: BatteryModel(capacity_kwh=battery_kwh) → always 50 kW max (default)
        #   For 10 kWh battery: 50 kW = 5C rate — physically impossible
        # NEW: cap at 0.5C rate
        battery = BatteryModel(
            capacity_kwh     = battery_kwh,
            max_charge_kw    = min(50.0, battery_kwh * 0.5),
            max_discharge_kw = min(50.0, battery_kwh * 0.5),
            initial_soc      = 0.50
        ) if battery_kwh > 0 else None

        area_m2 = (
            solar_peak_kw * 1000.0 / (self.pv_model.base_efficiency * 1000.0)
            if solar_peak_kw > 0 else 0.0
        )
        area_m2 = min(area_m2, self.roof_area_m2)

        daily_cost = 0.0
        solar_used = 0.0

        for t in range(len(loads)):
            hour = t * self.dt_hours
            irr  = self._irradiance(hour, peak_irr)
            pv   = self.pv_model.pv_power(irr, area_m2)["power_kw"] if solar_peak_kw > 0 else 0.0
            load = loads[t]
            net  = load - pv  # positive = deficit, negative = surplus

            charge_kw    = 0.0
            discharge_kw = 0.0

            # ── SURPLUS: charge battery with excess solar ───────────────
            if net < 0:
                surplus = abs(net)
                if battery and battery.soc < battery.soc_max - 0.01:
                    avail     = battery.available_charge_kw(self.dt_hours)
                    charge_kw = min(surplus, avail)
                grid_import = 0.0
                grid_export = 0.0  # no export

            # ── DEFICIT: use battery if allowed by time-of-day rule ─────
            else:
                if battery and battery.soc > battery.soc_min + 0.01:
                    avail        = battery.available_discharge_kw(self.dt_hours)
                    discharge_kw = min(net, avail)
                    net         -= discharge_kw
                grid_import = max(0.0, net)
                grid_export = 0.0

            if battery:
                battery.step(charge_kw, discharge_kw, self.dt_hours)

            cost        = grid_import * self.grid_price
            daily_cost += cost * self.dt_hours
            solar_used += pv   * self.dt_hours

        return daily_cost, solar_used

    # ----------------------------------------------------------------
    def _irradiance(self, hour: float, peak_irr: float = 800.0) -> float:
        if 6.0 <= hour <= 18.0:
            angle = np.pi * (hour - 6.0) / 12.0
            return peak_irr * np.sin(angle)
        return 0.0

    # ----------------------------------------------------------------
    def calculate_roi(
        self,
        investment             : float,
        annual_savings         : float,
        annual_maintenance_rate: float = 0.01
    ) -> dict:

        annual_maintenance  = investment * annual_maintenance_rate
        net_annual_benefit  = annual_savings - annual_maintenance

        if net_annual_benefit <= 0:
            return {
                "payback_years"     : float("inf"),
                "net_annual_benefit": round(net_annual_benefit, 2),
                "npv_10yr"          : round(-investment, 2),
                "is_viable"         : False
            }

        payback_years = investment / net_annual_benefit

        discount_rate = 0.08
        npv = -investment
        for yr in range(1, 11):
            npv += net_annual_benefit / ((1 + discount_rate) ** yr)

        irr = self._estimate_irr(investment, net_annual_benefit, years=15)

        return {
            "payback_years"     : round(payback_years, 2),
            "net_annual_benefit": round(net_annual_benefit, 2),
            "npv_10yr"          : round(npv, 2),
            "irr_percent"       : round(irr * 100, 2),
            "is_viable"         : payback_years < 15.0 and npv > 0
        }

    def _estimate_irr(self, investment, annual_benefit, years=15) -> float:
        lo, hi = 0.0, 5.0
        for _ in range(50):
            mid = (lo + hi) / 2.0
            npv = -investment + sum(
                annual_benefit / ((1 + mid) ** yr) for yr in range(1, years + 1))
            if npv > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0