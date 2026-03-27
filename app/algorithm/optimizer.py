import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  MAIN OPTIMIZER
# ═══════════════════════════════════════════════════════════════

def run_optimizer(input_data: Dict) -> Dict:
    """
    Main optimization function.

    Receives all plan data and returns optimal
    solar + battery sizing with financial metrics.

    Args:
        input_data: Complete dict with consumption,
                    budget, irradiance, tariff etc.

    Returns:
        Dict with sizing and financial results
    """
    logger.info("Starting optimization...")

    try:
        # ── Extract inputs ───────────────────────────────────
        budget           = input_data.get("budget", 10000)
        roof_area        = input_data.get("roof_area_m2", 50)
        avg_daily_kwh    = input_data.get("avg_daily_kwh", 20)
        peak_sun_hours   = input_data.get("peak_sun_hours", 5.5)
        electricity_rate = input_data.get("electricity_rate", 0.12)
        monthly_bill     = input_data.get("monthly_bill", 0)
        annual_kwh       = input_data.get("total_annual_kwh", avg_daily_kwh * 365)
        monthly_data     = input_data.get("monthly_consumption", [])

        # ── Step 1: Calculate max solar from roof area ───────
        panel_efficiency  = 0.20    # 20% monocrystalline
        m2_per_kw         = 6.5     # approx m2 per kW installed
        max_solar_kw      = roof_area / m2_per_kw

        # ── Step 2: Calculate needed solar capacity ──────────
        system_efficiency = 0.75    # inverter + wiring losses
        needed_solar_kw   = avg_daily_kwh / (peak_sun_hours * system_efficiency)

        # ── Step 3: Optimal solar = min of max and needed ────
        optimal_solar_kw  = round(min(max_solar_kw, needed_solar_kw), 2)
        optimal_solar_kw  = max(1.0, optimal_solar_kw)  # min 1 kW

        # ── Step 4: Battery sizing ───────────────────────────
        # Battery stores excess for night use
        # Typically 1-2x daily consumption
        battery_hours     = 4      # 4 hours of storage
        avg_hourly_kwh    = avg_daily_kwh / 24
        optimal_battery   = round(avg_hourly_kwh * battery_hours * 2, 2)
        optimal_battery   = max(2.5, min(optimal_battery, 20.0))

        # ── Step 5: Cost calculations ────────────────────────
        solar_cost_per_kw  = 1000   # USD per kW installed
        battery_cost_per_kwh = 400  # USD per kWh storage
        installation_factor  = 1.20 # 20% for installation

        solar_cost    = optimal_solar_kw * solar_cost_per_kw * installation_factor
        battery_cost  = optimal_battery  * battery_cost_per_kwh
        total_cost    = round(solar_cost + battery_cost, 2)

        # ── Step 6: Budget check & scale down if needed ──────
        if total_cost > budget:
            scale_factor  = budget / total_cost
            optimal_solar_kw = round(optimal_solar_kw * scale_factor, 2)
            optimal_battery  = round(optimal_battery  * scale_factor, 2)
            solar_cost    = optimal_solar_kw * solar_cost_per_kw * installation_factor
            battery_cost  = optimal_battery  * battery_cost_per_kwh
            total_cost    = round(solar_cost + battery_cost, 2)

        # ── Step 7: Annual generation ────────────────────────
        annual_gen_kwh = round(
            optimal_solar_kw * peak_sun_hours * 365 * system_efficiency, 2
        )

        # ── Step 8: Savings calculation ──────────────────────
        # Solar covers self-consumption
        solar_self_use   = min(annual_gen_kwh, annual_kwh)
        annual_saving    = round(solar_self_use * electricity_rate, 2)

        # ── Step 9: ROI calculation ──────────────────────────
        roi_years = round(
            total_cost / annual_saving, 2
        ) if annual_saving > 0 else 25.0

        payback_period = roi_years

        # ── Step 10: CO2 reduction ───────────────────────────
        # Average grid emission: 0.4 kg CO2 per kWh
        co2_reduction = round(annual_gen_kwh * 0.4, 2)

        # ── Step 11: Graph data ──────────────────────────────
        graph_data = _build_graph_data(
            monthly_data     = monthly_data,
            solar_kw         = optimal_solar_kw,
            peak_sun_hours   = peak_sun_hours,
            system_efficiency= system_efficiency,
            electricity_rate = electricity_rate
        )

        result = {
            # Sizing
            "solar_size_kw":       optimal_solar_kw,
            "battery_size_kwh":    optimal_battery,

            # Financials
            "total_cost":          total_cost,
            "solar_cost":          round(solar_cost, 2),
            "battery_cost":        round(battery_cost, 2),
            "annual_saving":       annual_saving,
            "monthly_saving":      round(annual_saving / 12, 2),
            "roi_years":           roi_years,
            "payback_period":      payback_period,

            # Energy
            "annual_generation_kwh": annual_gen_kwh,
            "solar_coverage_pct":  round(
                (solar_self_use / annual_kwh) * 100, 1
            ) if annual_kwh > 0 else 0,

            # Environment
            "co2_reduction_kg":    co2_reduction,
            "trees_equivalent":    round(co2_reduction / 21, 1),

            # Metadata
            "graph_data":          graph_data,
            "optimized_at":        datetime.utcnow().isoformat(),
            "status":              "success"
        }

        logger.info(
            f"Optimization done: {optimal_solar_kw}kW solar, "
            f"{optimal_battery}kWh battery, "
            f"ROI={roi_years}y"
        )
        return result

    except Exception as e:
        logger.error(f"Optimizer error: {e}")
        return {
            "status":  "error",
            "message": str(e),
            "solar_size_kw":    0,
            "battery_size_kwh": 0,
            "total_cost":       0,
            "annual_saving":    0,
            "roi_years":        0
        }


# ═══════════════════════════════════════════════════════════════
#  PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════════

def run_prediction(input_data: Dict) -> List[Dict]:
    """
    Generate 24-hour hourly energy predictions.

    Args:
        input_data: Dict with irradiance, tou schedule etc.

    Returns:
        List of 24 hourly prediction dicts
    """
    logger.info("Generating 24-hour predictions...")

    irradiance_data = input_data.get("irradiance", {})
    tou_schedule    = input_data.get("tou", [])
    hours           = input_data.get("hours", 24)

    # Build hourly irradiance lookup
    hourly_ghi = {}
    for item in irradiance_data.get("hourly_data", []):
        hourly_ghi[item['hour']] = item['ghi']

    # Build TOU rate lookup
    tou_rates = {}
    for item in tou_schedule:
        tou_rates[item['hour']] = item['rate']

    # Solar panel config
    solar_kw        = input_data.get("solar_kw", 5.0)
    battery_capacity= input_data.get("battery_kwh", 10.0)
    avg_consumption = input_data.get("avg_daily_kwh", 20.0)

    # Simulate 24 hours
    battery_soc = 50.0   # Start at 50%
    predictions = []

    # Hourly consumption pattern (typical household)
    consumption_pattern = {
        0: 0.3, 1: 0.2, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.3,
        6: 0.6, 7: 0.8, 8: 0.7, 9: 0.6, 10: 0.6, 11: 0.7,
        12: 0.8, 13: 0.7, 14: 0.6, 15: 0.6, 16: 0.7, 17: 0.9,
        18: 1.2, 19: 1.3, 20: 1.2, 21: 1.0, 22: 0.7, 23: 0.4
    }

    total_pattern = sum(consumption_pattern.values())

    for hour in range(hours):
        # Solar generation this hour
        ghi       = hourly_ghi.get(hour, 0)
        solar_gen = round(
            (ghi / 1000) * solar_kw * 0.75, 3
        )  # W to kW with efficiency

        # Consumption this hour
        weight      = consumption_pattern.get(hour, 0.5)
        consumption = round(
            (avg_consumption / 24) * (weight / (total_pattern / 24)), 3
        )

        # Grid rate this hour
        grid_rate = tou_rates.get(hour, 0.12)

        # Energy balance
        net_energy = solar_gen - consumption

        grid_import = 0.0
        grid_export = 0.0
        action      = "idle"

        if net_energy > 0:
            # Excess solar → charge battery or export
            if battery_soc < 90:
                charge    = min(net_energy, battery_capacity * 0.1)
                battery_soc = min(100, battery_soc + (charge / battery_capacity) * 100)
                action    = "charging"
                remaining = net_energy - charge
                if remaining > 0:
                    grid_export = round(remaining, 3)
            else:
                grid_export = round(net_energy, 3)
                action      = "exporting"
        else:
            # Deficit → use battery or grid
            deficit = abs(net_energy)
            if battery_soc > 20:
                discharge   = min(deficit, battery_capacity * 0.1)
                battery_soc = max(0, battery_soc - (discharge / battery_capacity) * 100)
                remaining   = deficit - discharge
                action      = "discharging"
                if remaining > 0:
                    grid_import = round(remaining, 3)
            else:
                grid_import = round(deficit, 3)
                action      = "grid_import"

        grid_cost = round(grid_import * grid_rate, 4)

        predictions.append({
            "hour":        hour,
            "solar_kw":    solar_gen,
            "consumption": consumption,
            "battery_soc": round(battery_soc, 1),
            "grid_import": grid_import,
            "grid_export": grid_export,
            "grid_cost":   grid_cost,
            "action":      action
        })

    return predictions


# ═══════════════════════════════════════════════════════════════
#  HELPER: BUILD GRAPH DATA
# ═══════════════════════════════════════════════════════════════

def _build_graph_data(
    monthly_data: List[Dict],
    solar_kw: float,
    peak_sun_hours: float,
    system_efficiency: float,
    electricity_rate: float
) -> Dict:
    """Build chart-ready data for frontend graphs."""

    months = [
        'Jan','Feb','Mar','Apr','May','Jun',
        'Jul','Aug','Sep','Oct','Nov','Dec'
    ]

    consumption_by_month = {}
    if monthly_data:
        for r in monthly_data:
            m = r.get('month', '')
            if m:
                key = m[:3] if len(m) >= 3 else m
                consumption_by_month[key] = r.get('units_kwh', 0)

    monthly_chart = []
    for month in months:
        monthly_gen = round(
            solar_kw * peak_sun_hours * 30 * system_efficiency, 2
        )
        consumed = consumption_by_month.get(month, 0)
        saving   = round(min(monthly_gen, consumed) * electricity_rate, 2)

        monthly_chart.append({
            "month":      month,
            "generation": monthly_gen,
            "consumption": consumed,
            "saving":     saving
        })

    # Cash flow projection (10 years)
    cashflow = []
    annual_saving = sum(m['saving'] for m in monthly_chart) * 12
    total_cost    = solar_kw * 1000 * 1.2 + 10 * 400
    cumulative    = -total_cost

    for year in range(1, 11):
        cumulative += annual_saving
        cashflow.append({
            "year":       year,
            "cumulative": round(cumulative, 2),
            "annual":     round(annual_saving, 2)
        })

    return {
        "monthly":  monthly_chart,
        "cashflow": cashflow,
        "labels":   months
    }