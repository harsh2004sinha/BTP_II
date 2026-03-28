from typing import Dict, List
import logging
from datetime import datetime
from app.services.tariff_service import TariffService

logger = logging.getLogger(__name__)


class AlgorithmService:

    @staticmethod
    def prepare_optimization_input(
        plan: dict,
        consumption_data: List[dict],
        irradiance_data: dict,
        weather_data: dict
    ) -> Dict:
        """Prepare complete optimizer input dict."""

        tariff       = TariffService.get_tariff(plan.get('location', 'default'))
        tou_schedule = TariffService.get_tou_schedule()

        # Process consumption
        total_annual_kwh = sum(r.get('units_kwh', r.get('units', 0))
                               for r in consumption_data)
        avg_monthly_kwh  = total_annual_kwh / len(consumption_data) if consumption_data else 0
        avg_daily_kwh    = avg_monthly_kwh / 30

        # Monthly bill estimate
        bill_calc    = TariffService.calculate_bill(
            avg_monthly_kwh, plan.get('location', 'default')
        )
        monthly_bill = bill_calc.get('total_bill', 0)

        return {
            # Plan
            "plan_id":           plan.get('planId'),
            "budget":            plan.get('budget', 10000),
            "roof_area_m2":      plan.get('roofArea', 50),
            "location":          plan.get('location'),
            "latitude":          plan.get('latitude'),
            "longitude":         plan.get('longitude'),

            # Consumption
            "total_annual_kwh":  total_annual_kwh,
            "avg_monthly_kwh":   avg_monthly_kwh,
            "avg_daily_kwh":     avg_daily_kwh,
            "monthly_consumption": consumption_data,

            # Solar
            "peak_sun_hours":    irradiance_data.get('peak_sun_hours', 5.5),
            "daily_ghi":         irradiance_data.get('daily_ghi_kwh_m2', 5.0),
            "hourly_irradiance": irradiance_data.get('hourly_data', []),

            # Weather
            "temperature":       weather_data.get('temperature', 25),
            "cloud_cover":       weather_data.get('cloud_cover', 20),

            # Tariff
            "electricity_rate":  tariff.get('flat_rate',
                                   tariff.get('tou_rates', [{'rate':0.12}])[0].get('rate', 0.12)),
            "monthly_bill":      monthly_bill,
            "tariff":            tariff,
            "tou_schedule":      tou_schedule,
            "export_rate":       tariff.get('export_rate', 0.08),

            # Timestamp
            "prepared_at":       datetime.utcnow().isoformat()
        }