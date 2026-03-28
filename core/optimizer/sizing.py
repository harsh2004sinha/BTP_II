"""
System Sizing Module
Finds the optimal solar panel size and battery capacity for a campus
"""

import numpy as np
from typing import List, Tuple

from ..models.pv_model   import PVModel
from ..models.load_model import LoadModel
from ..models.battery_model import BatteryModel


class SystemSizer:
    """
    Determines optimal solar PV size and battery size.

    Approach:
        Grid search over (solar_size, battery_size) combinations.
        For each combination: simulate one day, compute cost.
        Select combination with minimum total cost.
        Calculate ROI based on savings vs investment.
    """

    def __init__(
        self,
        pv_model         : PVModel    = None,
        load_model       : LoadModel  = None,
        solar_price_per_kw  : float = 1000.0,   # $ per kW peak
        battery_price_per_kwh: float = 300.0,   # $ per kWh
        grid_price          : float = 0.15,
        feed_in_tariff      : float = 0.075,
        dt_hours            : float = 0.25,
        roof_area_m2        : float = 1000.0
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
        budget            : float      = 100000.0,
        solar_range_kw    : List[float] = None,
        battery_range_kwh : List[float] = None,
        day_type          : str         = "weekday",
        peak_irr          : float       = 800.0
    ) -> dict:
        """
        Main sizing function.
        Finds best solar + battery combination within budget.

        Args:
            monthly_kwh       : Monthly consumption from bill (kWh)
            budget            : Maximum investment budget ($)
            solar_range_kw    : List of solar sizes to test (kW peak)
            battery_range_kwh : List of battery sizes to test (kWh)
            day_type          : Day type for simulation
            peak_irr          : Peak irradiance for location

        Returns:
            dict with best_solar_kw, best_battery_kwh, roi, savings, all_results
        """

        # Default ranges if not given
        if solar_range_kw is None:
            solar_range_kw = [0, 25, 50, 75, 100, 150, 200, 250, 300]

        if battery_range_kwh is None:
            battery_range_kwh = [0, 25, 50, 75, 100, 150, 200]

        # Load profile (scaled from bill)
        load_profile = self.load_model.from_monthly_bill(monthly_kwh, day_type, self.dt_hours)
        loads        = [p["load_kw"] for p in load_profile]

        # Baseline cost (no solar, no battery)
        baseline_daily_cost = sum(l * self.grid_price * self.dt_hours for l in loads)

        best_result = None
        all_results = []

        for solar_kw in solar_range_kw:
            for batt_kwh in battery_range_kwh:

                # Check budget
                investment = (solar_kw    * self.solar_price_per_kw
                             + batt_kwh   * self.battery_price_per_kwh)
                if investment > budget:
                    continue

                # Skip if no system at all
                if solar_kw == 0 and batt_kwh == 0:
                    all_results.append({
                        "solar_kw"         : 0,
                        "battery_kwh"      : 0,
                        "daily_cost"       : round(baseline_daily_cost, 4),
                        "investment"       : 0.0,
                        "annual_savings"   : 0.0,
                        "roi_years"        : float("inf")
                    })
                    continue

                # Run single-day simulation
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
                    "solar_kw"       : solar_kw,
                    "battery_kwh"    : batt_kwh,
                    "daily_cost"     : round(daily_cost, 4),
                    "investment"     : round(investment, 2),
                    "annual_savings" : round(annual_savings, 2),
                    "roi_years"      : round(roi_years, 2),
                    "solar_used_kwh" : round(solar_used, 3)
                }

                all_results.append(result)

                # Track best (lowest daily cost within budget)
                if best_result is None or daily_cost < best_result["daily_cost"]:
                    best_result = result

        if best_result is None:
            best_result = {
                "solar_kw": 0, "battery_kwh": 0,
                "daily_cost": baseline_daily_cost,
                "investment": 0.0, "annual_savings": 0.0, "roi_years": float("inf")
            }

        # Sort all_results by roi
        all_results_sorted = sorted(
            [r for r in all_results if r["roi_years"] != float("inf")],
            key=lambda x: x["roi_years"]
        )

        return {
            "best_solar_kw"     : best_result["solar_kw"],
            "best_battery_kwh"  : best_result["battery_kwh"],
            "best_daily_cost"   : best_result["daily_cost"],
            "baseline_daily_cost": round(baseline_daily_cost, 4),
            "daily_savings"     : round(baseline_daily_cost - best_result["daily_cost"], 4),
            "annual_savings"    : best_result["annual_savings"],
            "investment"        : best_result["investment"],
            "roi_years"         : best_result["roi_years"],
            "top_5_options"     : all_results_sorted[:5],
            "all_results"       : all_results
        }

    # ----------------------------------------------------------------
    def _simulate_day(
        self,
        solar_peak_kw : float,
        battery_kwh   : float,
        loads         : List[float],
        peak_irr      : float = 800.0
    ) -> Tuple[float, float]:
        """
        Simulate one day with given solar + battery.
        Uses simple rule-based control for costing.

        Returns:
            (daily_cost, total_solar_used_kwh)
        """
        n_steps = len(loads)
        battery = BatteryModel(
            capacity_kwh = battery_kwh if battery_kwh > 0 else 1.0,
            initial_soc  = 0.50
        ) if battery_kwh > 0 else None

        # Compute solar peak area from kW
        # Peak kW = area × base_efficiency × 1000 W/m²
        area_m2 = (solar_peak_kw * 1000.0
                   / (self.pv_model.base_efficiency * 1000.0)
                   ) if solar_peak_kw > 0 else 0.0
        area_m2 = min(area_m2, self.roof_area_m2)

        daily_cost  = 0.0
        solar_used  = 0.0

        for t in range(n_steps):
            hour = t * self.dt_hours

            # PV generation
            irr = self._irradiance(hour, peak_irr)
            pv  = self.pv_model.pv_power(irr, area_m2)["power_kw"] if solar_peak_kw > 0 else 0.0

            load = loads[t]
            net  = load - pv   # Positive = deficit, Negative = surplus

            charge_kw    = 0.0
            discharge_kw = 0.0

            if net > 0:
                # Deficit: try to cover from battery first
                if battery and battery.soc > battery.soc_min + 0.05:
                    avail_batt = battery.available_discharge_kw(self.dt_hours)
                    discharge_kw = min(net, avail_batt)
                    net -= discharge_kw
                # Remaining from grid
                grid_import = max(0.0, net)
                grid_export = 0.0
            else:
                # Surplus PV: charge battery first
                surplus = abs(net)
                if battery and battery.soc < battery.soc_max - 0.05:
                    avail_charge = battery.available_charge_kw(self.dt_hours)
                    charge_kw = min(surplus, avail_charge)
                    surplus -= charge_kw
                # Remaining surplus → export
                grid_import = 0.0
                grid_export = surplus

            # Apply battery step
            if battery:
                battery.step(charge_kw, discharge_kw, self.dt_hours)

            # Compute cost
            cost = (grid_import * self.grid_price - grid_export * self.feed_in_tariff)
            daily_cost += cost * self.dt_hours
            solar_used += pv * self.dt_hours

        return daily_cost, solar_used

    # ----------------------------------------------------------------
    def _irradiance(self, hour: float, peak_irr: float = 800.0) -> float:
        """Synthetic irradiance for sizing simulation."""
        if 6.0 <= hour <= 18.0:
            angle = np.pi * (hour - 6.0) / 12.0
            return peak_irr * np.sin(angle)
        return 0.0

    # ----------------------------------------------------------------
    def calculate_roi(
        self,
        investment      : float,
        annual_savings  : float,
        annual_maintenance_rate: float = 0.01
    ) -> dict:
        """
        Detailed ROI calculation with payback period.

        Args:
            investment             : Total upfront cost ($)
            annual_savings         : Yearly electricity savings ($)
            annual_maintenance_rate: Maintenance as fraction of investment

        Returns:
            dict with payback_years, npv_10yr, irr_approx
        """
        annual_maintenance = investment * annual_maintenance_rate
        net_annual_benefit = annual_savings - annual_maintenance

        if net_annual_benefit <= 0:
            return {
                "payback_years"   : float("inf"),
                "net_annual_benefit": round(net_annual_benefit, 2),
                "npv_10yr"        : round(-investment, 2),
                "is_viable"       : False
            }

        payback_years = investment / net_annual_benefit

        # 10-year NPV at 8% discount rate
        discount_rate = 0.08
        npv = -investment
        for yr in range(1, 11):
            npv += net_annual_benefit / ((1 + discount_rate) ** yr)

        # Approximate IRR (binary search)
        irr = self._estimate_irr(investment, net_annual_benefit, years=15)

        return {
            "payback_years"     : round(payback_years, 2),
            "net_annual_benefit": round(net_annual_benefit, 2),
            "npv_10yr"          : round(npv, 2),
            "irr_percent"       : round(irr * 100, 2),
            "is_viable"         : payback_years < 15.0 and npv > 0
        }

    def _estimate_irr(
        self,
        investment    : float,
        annual_benefit: float,
        years         : int = 15
    ) -> float:
        """Estimate IRR using binary search."""
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