"""
Tariff Manager
Handles Time-of-Use tariffs and real-time pricing
"""

from typing import Dict, List


class TariffManager:
    """
    Manages electricity tariff schedules.

    Supports:
        - Time-of-Use (TOU) tariffs
        - Real-time pricing (RTP)
        - Demand charges
        - Feed-in tariff for exports

    Default TOU (typical campus utility):
        Off-peak  22:00–07:00 : \$0.08/kWh
        Mid-peak  07:00–17:00 : \$0.15/kWh
        On-peak   17:00–22:00 : \$0.25/kWh
    """

    DEFAULT_TOU = {
        "off_peak": {
            "hours": list(range(22, 24)) + list(range(0, 7)),
            "price": 0.08,
            "label": "Off-Peak"
        },
        "mid_peak": {
            "hours": list(range(7, 17)),
            "price": 0.15,
            "label": "Mid-Peak"
        },
        "on_peak": {
            "hours": list(range(17, 22)),
            "price": 0.25,
            "label": "On-Peak"
        }
    }

    def __init__(
        self,
        tou_schedule    : dict  = None,
        feed_in_rate    : float = None,
        demand_charge   : float = 10.0,    # $/kW of peak demand per month
        currency        : str   = "USD"
    ):
        self.tou_schedule  = tou_schedule or self.DEFAULT_TOU
        self.demand_charge = demand_charge
        self.currency      = currency

        # Feed-in is 50% of off-peak by default
        off_peak_price     = self.tou_schedule.get(
            "off_peak", {}).get("price", 0.08)
        self.feed_in_rate  = feed_in_rate if feed_in_rate is not None \
                             else off_peak_price * 0.5

        # Peak demand tracking for demand charges
        self._monthly_peak_kw = 0.0

    # ----------------------------------------------------------------
    def get_price(self, hour: float) -> float:
        """
        Get buy price for given hour.

        Args:
            hour : Hour of day (0 – 23.75)

        Returns:
            Price in $/kWh
        """
        h = int(hour) % 24

        for period, info in self.tou_schedule.items():
            if h in info["hours"]:
                return info["price"]

        # Default fallback
        return 0.10

    # ----------------------------------------------------------------
    def get_period_name(self, hour: float) -> str:
        """Get tariff period name for given hour."""
        h = int(hour) % 24
        for period, info in self.tou_schedule.items():
            if h in info["hours"]:
                return info.get("label", period)
        return "Unknown"

    # ----------------------------------------------------------------
    def get_feed_in_rate(self) -> float:
        """Get feed-in tariff for exports."""
        return self.feed_in_rate

    # ----------------------------------------------------------------
    def get_full_day_prices(
        self,
        dt_hours: float = 0.25
    ) -> List[dict]:
        """
        Get price for every timestep in a day.

        Returns:
            List of dicts — timestep, hour, price, period
        """
        n_steps = int(24 / dt_hours)
        prices  = []

        for t in range(n_steps):
            hour = t * dt_hours
            prices.append({
                "timestep" : t,
                "hour"     : round(hour, 2),
                "price"    : self.get_price(hour),
                "period"   : self.get_period_name(hour),
                "feed_in"  : self.feed_in_rate
            })

        return prices

    # ----------------------------------------------------------------
    def is_peak_hour(self, hour: float) -> bool:
        """Check if current hour is on-peak."""
        return self.get_price(hour) >= 0.20

    # ----------------------------------------------------------------
    def is_off_peak_hour(self, hour: float) -> bool:
        """Check if current hour is off-peak."""
        return self.get_price(hour) <= 0.09

    # ----------------------------------------------------------------
    def update_peak_demand(self, demand_kw: float):
        """Update monthly peak demand for demand charge calculation."""
        self._monthly_peak_kw = max(self._monthly_peak_kw, demand_kw)

    # ----------------------------------------------------------------
    def get_monthly_demand_charge(self) -> float:
        """Calculate monthly demand charge."""
        return round(self._monthly_peak_kw * self.demand_charge, 2)

    # ----------------------------------------------------------------
    def set_tou_schedule(self, schedule: dict):
        """Update TOU schedule (from user settings or API)."""
        self.tou_schedule = schedule

    # ----------------------------------------------------------------
    def get_cheapest_hours(
        self,
        n_hours: int = 6,
        dt_hours: float = 0.25
    ) -> List[float]:
        """
        Get N cheapest hours of the day.

        Useful for:
            - Scheduling EV charging
            - Pre-charging battery
        """
        prices = self.get_full_day_prices(dt_hours)
        sorted_prices = sorted(prices, key=lambda x: x["price"])
        return [p["hour"] for p in sorted_prices[:n_hours * int(1/dt_hours)]]

    # ----------------------------------------------------------------
    def get_most_expensive_hours(
        self,
        n_hours: int = 4,
        dt_hours: float = 0.25
    ) -> List[float]:
        """
        Get N most expensive hours.

        Useful for:
            - Scheduling battery discharge
            - Peak avoidance
        """
        prices = self.get_full_day_prices(dt_hours)
        sorted_prices = sorted(prices, key=lambda x: x["price"], reverse=True)
        return [p["hour"] for p in sorted_prices[:n_hours * int(1/dt_hours)]]