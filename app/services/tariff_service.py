from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TariffService:
    """
    Service to manage electricity tariff data.
    Supports flat rate, time-of-use (TOU) and tiered pricing.
    """
    
    # Default tariff tables for common countries/regions
    DEFAULT_TARIFFS = {
        "malaysia": {
            "name": "Tenaga Nasional Berhad (TNB)",
            "currency": "MYR",
            "type": "tiered",
            "tiers": [
                {"min_units": 0, "max_units": 200, "rate": 0.218},
                {"min_units": 201, "max_units": 300, "rate": 0.334},
                {"min_units": 301, "max_units": 600, "rate": 0.516},
                {"min_units": 601, "max_units": 900, "rate": 0.546},
                {"min_units": 901, "max_units": float('inf'), "rate": 0.571}
            ],
            "fixed_charge": 7.20,  # per month
            "export_rate": 0.31    # FIT/NEM rate
        },
        "uk": {
            "name": "Ofgem",
            "currency": "GBP",
            "type": "tou",
            "tou_rates": [
                {"start": 0, "end": 7, "rate": 0.15},
                {"start": 7, "end": 16, "rate": 0.28},
                {"start": 16, "end": 19, "rate": 0.45},
                {"start": 19, "end": 22, "rate": 0.28},
                {"start": 22, "end": 24, "rate": 0.15}
            ],
            "fixed_charge": 0.53,   # per day
            "export_rate": 0.075
        },
        "australia": {
            "name": "Default Australian Tariff",
            "currency": "AUD",
            "type": "flat",
            "flat_rate": 0.28,
            "fixed_charge": 1.10,
            "export_rate": 0.08
        },
        "default": {
            "name": "Generic Tariff",
            "currency": "USD",
            "type": "flat",
            "flat_rate": 0.12,
            "fixed_charge": 10.0,
            "export_rate": 0.08
        }
    }
    
    # Time-of-Use schedule (24 hours)
    DEFAULT_TOU_SCHEDULE = [
        # hour, rate_usd_per_kwh, period_name
        {"hour": 0, "rate": 0.08, "period": "off_peak"},
        {"hour": 1, "rate": 0.08, "period": "off_peak"},
        {"hour": 2, "rate": 0.08, "period": "off_peak"},
        {"hour": 3, "rate": 0.08, "period": "off_peak"},
        {"hour": 4, "rate": 0.08, "period": "off_peak"},
        {"hour": 5, "rate": 0.08, "period": "off_peak"},
        {"hour": 6, "rate": 0.10, "period": "shoulder"},
        {"hour": 7, "rate": 0.10, "period": "shoulder"},
        {"hour": 8, "rate": 0.15, "period": "peak"},
        {"hour": 9, "rate": 0.15, "period": "peak"},
        {"hour": 10, "rate": 0.15, "period": "peak"},
        {"hour": 11, "rate": 0.12, "period": "shoulder"},
        {"hour": 12, "rate": 0.12, "period": "shoulder"},
        {"hour": 13, "rate": 0.12, "period": "shoulder"},
        {"hour": 14, "rate": 0.12, "period": "shoulder"},
        {"hour": 15, "rate": 0.12, "period": "shoulder"},
        {"hour": 16, "rate": 0.12, "period": "shoulder"},
        {"hour": 17, "rate": 0.18, "period": "peak"},
        {"hour": 18, "rate": 0.20, "period": "peak"},
        {"hour": 19, "rate": 0.20, "period": "peak"},
        {"hour": 20, "rate": 0.18, "period": "peak"},
        {"hour": 21, "rate": 0.15, "period": "peak"},
        {"hour": 22, "rate": 0.10, "period": "shoulder"},
        {"hour": 23, "rate": 0.08, "period": "off_peak"},
    ]
    
    @staticmethod
    def get_tariff(region: str = "default") -> Dict:
        """Get tariff data for a region"""
        region_lower = region.lower()
        
        for key in TariffService.DEFAULT_TARIFFS:
            if key in region_lower or region_lower in key:
                return TariffService.DEFAULT_TARIFFS[key]
        
        return TariffService.DEFAULT_TARIFFS["default"]
    
    @staticmethod
    def get_tou_schedule() -> List[Dict]:
        """Get 24-hour time-of-use schedule"""
        return TariffService.DEFAULT_TOU_SCHEDULE
    
    @staticmethod
    def calculate_bill(
        monthly_units: float,
        region: str = "default"
    ) -> Dict:
        """
        Calculate electricity bill based on usage.
        
        Args:
            monthly_units: Units consumed in kWh
            region: Location for tariff lookup
            
        Returns:
            Bill breakdown
        """
        tariff = TariffService.get_tariff(region)
        
        if tariff['type'] == 'flat':
            energy_charge = monthly_units * tariff['flat_rate']
            
        elif tariff['type'] == 'tiered':
            energy_charge = 0
            remaining_units = monthly_units
            
            for tier in tariff.get('tiers', []):
                if remaining_units <= 0:
                    break
                    
                tier_max = tier['max_units']
                tier_min = tier['min_units']
                tier_units = min(
                    remaining_units, 
                    tier_max - tier_min
                )
                
                energy_charge += tier_units * tier['rate']
                remaining_units -= tier_units
        
        elif tariff['type'] == 'tou':
            # Assume flat distribution across TOU periods
            avg_rate = sum(
                r['rate'] for r in tariff.get('tou_rates', [])
            ) / len(tariff.get('tou_rates', [1]))
            energy_charge = monthly_units * avg_rate
        
        else:
            energy_charge = monthly_units * 0.12
        
        fixed_charge = tariff.get('fixed_charge', 0)
        total_bill = energy_charge + fixed_charge
        
        return {
            'monthly_units': monthly_units,
            'energy_charge': round(energy_charge, 2),
            'fixed_charge': round(fixed_charge, 2),
            'total_bill': round(total_bill, 2),
            'average_rate': round(total_bill / monthly_units, 4) if monthly_units > 0 else 0,
            'currency': tariff.get('currency', 'USD'),
            'tariff_name': tariff.get('name', 'Default')
        }
    
    @staticmethod
    def get_rate_at_hour(hour: int) -> float:
        """Get electricity rate at specific hour"""
        for item in TariffService.DEFAULT_TOU_SCHEDULE:
            if item['hour'] == hour:
                return item['rate']
        return 0.12  # default