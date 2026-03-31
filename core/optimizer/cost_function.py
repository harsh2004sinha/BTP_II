"""
Cost Function
Computes total system cost at each timestep
"""


class CostFunction:
    """
    Computes total cost of microgrid operation.

    Total Cost =
        Grid Import Cost
        + Battery Degradation Cost
        + Carbon Cost
        + Demand Response Penalty
        - Solar Savings (avoided grid cost)
        - Grid Export Revenue
    """

    def __init__(
        self,
        carbon_price_per_kg    : float = 0.02,
        maintenance_rate       : float = 0.005,
        unserved_penalty       : float = 2.00,
    ):
        self.carbon_price_per_kg = carbon_price_per_kg
        self.maintenance_rate    = maintenance_rate
        self.unserved_penalty    = unserved_penalty

    # ----------------------------------------------------------------
    def compute(
        self,
        grid_import_kw  : float,
        grid_export_kw  : float,
        charge_kw       : float,
        discharge_kw    : float,
        pv_kw           : float,
        load_kw         : float,
        grid_price      : float,
        feed_in_tariff  : float,
        degradation_cost: float,
        carbon_intensity: float = 0.40,
        dt_hours        : float = 0.25,
        dr_penalty      : float = 0.0,
        load_unserved   : float = 0.0
    ) -> dict:
        """
        Compute total cost for one timestep.

        Args:
            grid_import_kw   : Power imported from grid (kW)
            grid_export_kw   : Power exported to grid (kW)
            charge_kw        : Battery charge power (kW)
            discharge_kw     : Battery discharge power (kW)
            pv_kw            : PV generation (kW)
            load_kw          : Campus demand (kW)
            grid_price       : Buy price $/kWh
            feed_in_tariff   : Sell price $/kWh
            degradation_cost : Battery aging cost ($)
            carbon_intensity : kg CO2 per kWh of grid electricity
            dt_hours         : Timestep duration (hours)
            dr_penalty       : Demand response violation cost ($)
            load_unserved    : Unmet load (kW)

        Returns:
            dict with itemized costs and total
        """
        # Grid import cost
        import_cost = grid_import_kw * grid_price * dt_hours

        # Grid export revenue (negative cost)
        export_revenue = grid_export_kw * feed_in_tariff * dt_hours

        # Carbon cost
        carbon_kg   = grid_import_kw * carbon_intensity * dt_hours
        carbon_cost = carbon_kg * self.carbon_price_per_kg

        # Maintenance cost (proportional to active power)
        active_kw       = charge_kw + discharge_kw + pv_kw
        maintenance_cost = active_kw * self.maintenance_rate * dt_hours

        # Unserved load penalty
        unserved_cost = load_unserved * self.unserved_penalty * dt_hours

        # Total cost
        total = (
            import_cost
            + degradation_cost
            + carbon_cost
            + maintenance_cost
            + dr_penalty
            + unserved_cost
            - export_revenue
        )

        return {
            "total_cost"       : round(total, 6),
            "import_cost"      : round(import_cost, 6),
            "export_revenue"   : round(export_revenue, 6),
            "degradation_cost" : round(degradation_cost, 6),
            "carbon_cost"      : round(carbon_cost, 6),
            "maintenance_cost" : round(maintenance_cost, 6),
            "unserved_cost"    : round(unserved_cost, 6),
            "dr_penalty"       : round(dr_penalty, 6),
            "carbon_kg"        : round(carbon_kg, 4),
            "net_cost"         : round(total, 6)
        }

    # ----------------------------------------------------------------
    def daily_summary(self, timestep_costs: list) -> dict:
        """Aggregate per-timestep cost dicts into daily summary."""
        keys = ["total_cost", "import_cost", "export_revenue",
                "degradation_cost", "carbon_cost", "carbon_kg"]
        summary = {k: 0.0 for k in keys}
        for tc in timestep_costs:
            for k in keys:
                summary[k] += tc.get(k, 0.0)
        summary = {k: round(v, 4) for k, v in summary.items()}
        summary["net_daily_cost"] = round(
            summary["total_cost"] - summary["export_revenue"], 4)
        return summary