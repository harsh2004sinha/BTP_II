"""
Decision Text Generator
Converts optimization decisions into human-readable explanations
"""

from typing import List


class DecisionTextGenerator:
    """
    Generates natural language explanations for optimizer decisions.

    Examples:
        "Battery discharged because grid price is high (\$0.25/kWh)"
        "Charging battery because solar surplus is available and SOC is low"
        "Exporting to grid because battery is full and solar is abundant"
        "Using grid only because battery SOC is at reserve level"
    """

    # ----------------------------------------------------------------
    # Action description templates
    # ----------------------------------------------------------------
    ACTION_TEMPLATES = {
        "solar_direct": [
            "Using solar power directly to serve campus load.",
            "Solar generation is covering current demand directly.",
            "Routing available solar output directly to campus loads."
        ],
        "solar_charge_battery": [
            "Charging battery with surplus solar energy.",
            "Solar output exceeds current demand — storing excess in battery.",
            "Using solar surplus to build up battery reserves."
        ],
        "battery_discharge": [
            "Discharging battery to reduce grid imports.",
            "Using stored battery energy to serve load.",
            "Battery is supplying power to reduce grid dependency."
        ],
        "peak_shaving": [
            "Peak shaving: discharging battery to avoid high tariff.",
            "Grid price is high — using battery to minimize import cost.",
            "Battery discharge activated for peak demand reduction."
        ],
        "export_surplus": [
            "Exporting surplus solar generation to grid for revenue.",
            "Solar production exceeds storage capacity — selling to grid.",
            "Grid export activated: earning feed-in revenue from surplus."
        ],
        "grid_only": [
            "Importing from grid to meet campus load.",
            "No solar or battery available — grid is only source.",
            "Grid supplying full campus demand this interval."
        ],
        "grid_charge_battery": [
            "Charging battery from grid during off-peak period.",
            "Low electricity price — pre-charging battery for later use.",
            "Using cheap off-peak electricity to fill battery."
        ]
    }

    # ----------------------------------------------------------------
    # Reason templates based on dominant factor
    # ----------------------------------------------------------------
    REASON_TEMPLATES = {
        "grid_price": {
            "high"  : "Grid price is high (${price:.2f}/kWh) — minimizing import.",
            "low"   : "Grid price is low (${price:.2f}/kWh) — good time to import or charge.",
            "medium": "Grid price is moderate (${price:.2f}/kWh)."
        },
        "battery_soc": {
            "high"  : "Battery is well charged (SOC {soc:.0%}) — available for discharge.",
            "low"   : "Battery SOC is low ({soc:.0%}) — protecting reserve.",
            "medium": "Battery SOC is moderate ({soc:.0%})."
        },
        "pv_generation": {
            "high"  : "Strong solar generation ({pv:.1f} kW) available.",
            "low"   : "Solar generation is low ({pv:.1f} kW).",
            "zero"  : "No solar generation (night or heavy cloud cover)."
        },
        "load_demand": {
            "high"  : "Campus demand is high ({load:.1f} kW).",
            "low"   : "Campus demand is low ({load:.1f} kW).",
            "medium": "Campus demand is moderate ({load:.1f} kW)."
        },
        "battery_health": {
            "degraded" : "Battery health is reduced ({health:.0%}) — limiting cycling.",
            "good"     : "Battery health is good ({health:.0%})."
        },
        "demand_response": {
            "active"   : "Demand response event is active — reducing grid import.",
            "inactive" : "No demand response event."
        }
    }

    # ----------------------------------------------------------------
    def generate(
        self,
        action_name    : str,
        state_dict     : dict,
        cost_breakdown : dict,
        importance     : dict = None
    ) -> dict:
        """
        Generate full explanation for a decision.

        Args:
            action_name    : Name of the chosen action
            state_dict     : TwinState.to_dict()
            cost_breakdown : From CostFunction.compute()
            importance     : From SHAPExplainer.compute_importance()

        Returns:
            dict with action_text, reason_text, cost_text, full_text
        """
        action_text  = self._get_action_text(action_name)
        reason_text  = self._get_reason_text(action_name, state_dict)
        cost_text    = self._get_cost_text(cost_breakdown)
        factor_text  = self._get_factor_text(importance)

        full_text = (
            f"{action_text} "
            f"{reason_text} "
            f"{cost_text}"
        )

        return {
            "action_text" : action_text,
            "reason_text" : reason_text,
            "cost_text"   : cost_text,
            "factor_text" : factor_text,
            "full_text"   : full_text,
            "action_name" : action_name
        }

    # ----------------------------------------------------------------
    def _get_action_text(self, action_name: str) -> str:
        """Get action description text."""
        templates = self.ACTION_TEMPLATES.get(action_name, [])
        if templates:
            import random
            return templates[0]   # Use first template (deterministic)
        return f"Action: {action_name}."

    # ----------------------------------------------------------------
    def _get_reason_text(self, action_name: str, state: dict) -> str:
        """Generate reason based on state variables."""
        soc    = state.get("soc",          0.5)
        pv     = state.get("pv_power_kw",  0.0)
        load   = state.get("load_kw",      0.0)
        price  = state.get("grid_price",   0.10)
        health = state.get("battery_health", 1.0)
        dr     = state.get("demand_response_active", False)

        reasons = []

        # Price reason
        if price >= 0.20:
            reasons.append(
                self.REASON_TEMPLATES["grid_price"]["high"].format(price=price))
        elif price <= 0.09:
            reasons.append(
                self.REASON_TEMPLATES["grid_price"]["low"].format(price=price))
        else:
            reasons.append(
                self.REASON_TEMPLATES["grid_price"]["medium"].format(price=price))

        # PV reason
        if pv > 50:
            reasons.append(
                self.REASON_TEMPLATES["pv_generation"]["high"].format(pv=pv))
        elif pv <= 0:
            reasons.append(
                self.REASON_TEMPLATES["pv_generation"]["zero"].format(pv=pv))
        else:
            reasons.append(
                self.REASON_TEMPLATES["pv_generation"]["low"].format(pv=pv))

        # SOC reason
        if soc < 0.25:
            reasons.append(
                self.REASON_TEMPLATES["battery_soc"]["low"].format(soc=soc))
        elif soc > 0.75:
            reasons.append(
                self.REASON_TEMPLATES["battery_soc"]["high"].format(soc=soc))

        # Battery health
        if health < 0.70:
            reasons.append(
                self.REASON_TEMPLATES["battery_health"]["degraded"].format(health=health))

        # Demand response
        if dr:
            reasons.append(
                self.REASON_TEMPLATES["demand_response"]["active"])

        return " ".join(reasons[:3])   # Top 3 reasons

    # ----------------------------------------------------------------
    def _get_cost_text(self, cost_breakdown: dict) -> str:
        """Format cost breakdown into readable text."""
        if not cost_breakdown:
            return ""

        total      = cost_breakdown.get("total_cost",     0.0)
        import_c   = cost_breakdown.get("import_cost",    0.0)
        deg_c      = cost_breakdown.get("degradation_cost", 0.0)
        export_r   = cost_breakdown.get("export_revenue", 0.0)
        carbon_c   = cost_breakdown.get("carbon_cost",    0.0)

        parts = [f"Step cost: ${total:.4f}"]

        if import_c > 0:
            parts.append(f"Grid import: ${import_c:.4f}")
        if deg_c > 0:
            parts.append(f"Battery wear: ${deg_c:.4f}")
        if export_r > 0:
            parts.append(f"Export revenue: ${export_r:.4f}")
        if carbon_c > 0:
            parts.append(f"Carbon cost: ${carbon_c:.4f}")

        return " | ".join(parts)

    # ----------------------------------------------------------------
    def _get_factor_text(self, importance: dict) -> str:
        """Format importance into readable text."""
        if not importance:
            return "Key factor: not available."

        top = importance.get("top_factor", "unknown")
        val = importance.get("top_importance", 0.0)

        labels = {
            "battery_soc"     : "Battery state of charge",
            "pv_generation"   : "Solar PV generation",
            "load_demand"     : "Campus load demand",
            "grid_price"      : "Grid electricity price",
            "hour_of_day"     : "Time of day",
            "battery_health"  : "Battery health",
            "demand_response" : "Demand response signal",
            "carbon_intensity": "Carbon intensity"
        }

        label = labels.get(top, top.replace("_", " ").title())
        return f"Key factor: {label} ({val*100:.1f}% influence)."

    # ----------------------------------------------------------------
    def generate_schedule_summary(
        self,
        schedule : List[dict]
    ) -> str:
        """
        Generate a summary of a full day schedule.

        Args:
            schedule : List of action dicts from solver.optimize_horizon()

        Returns:
            Human-readable summary string
        """
        if not schedule:
            return "No schedule available."

        action_counts = {}
        total_cost    = 0.0

        for step in schedule:
            if step:
                name = step.get("action_name", "unknown")
                action_counts[name] = action_counts.get(name, 0) + 1
                total_cost += step.get("total_cost", 0.0)

        lines = ["📅 Day Schedule Summary:"]
        for action, count in sorted(action_counts.items(),
                                    key=lambda x: x[1], reverse=True):
            pct = count / len(schedule) * 100
            lines.append(f"  • {action:30s}: {count:3d} steps ({pct:.1f}%)")

        lines.append(f"\n💰 Total day cost: ${total_cost:.4f}")
        lines.append(f"📊 Steps planned: {len(schedule)}")

        return "\n".join(lines)