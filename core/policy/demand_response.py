"""
Demand Response Manager
Handles utility demand response events and constraints
"""

import time
from typing import List, Optional


class DemandResponseManager:
    """
    Manages demand response (DR) events.

    Demand Response:
        Grid operator signals campus to reduce load
        during grid stress periods.
        Campus reduces import → earns DR credits.

    Scenarios:
        - Scheduled DR events (known in advance)
        - Emergency DR events (short notice)
        - Curtailment signals
        - Load shifting incentives
    """

    def __init__(
        self,
        max_curtailment_kw   : float = 200.0,
        dr_incentive_rate    : float = 0.50,
        min_soc_during_dr    : float = 0.15,
        notification_minutes : int   = 30
    ):
        self.max_curtailment_kw   = max_curtailment_kw
        self.dr_incentive_rate    = dr_incentive_rate
        self.min_soc_during_dr    = min_soc_during_dr
        self.notification_minutes = notification_minutes

        # State
        self._is_active     = False
        self._current_event = None
        self._dr_history    = []
        self._total_credits = 0.0

    # ----------------------------------------------------------------
    def check_active(self, hour: float) -> bool:
        """
        Check if DR event is active at given hour.

        Args:
            hour : Current hour (0 - 23.75)

        Returns:
            bool
        """
        if self._current_event is None:
            return False
        start = self._current_event.get("start_hour", 0)
        end   = self._current_event.get("end_hour",   0)
        return start <= hour <= end

    # ----------------------------------------------------------------
    def activate_event(
        self,
        start_hour           : float,
        end_hour             : float,
        target_reduction_kw  : float,
        event_type           : str = "voluntary"
    ) -> dict:
        """
        Activate a demand response event.

        Args:
            start_hour          : Event start hour
            end_hour            : Event end hour
            target_reduction_kw : Required load reduction (kW)
            event_type          : "voluntary" / "mandatory" / "emergency"

        Returns:
            dict with event details
        """
        self._current_event = {
            "start_hour"          : start_hour,
            "end_hour"            : end_hour,
            "target_reduction_kw" : min(target_reduction_kw, self.max_curtailment_kw),
            "event_type"          : event_type,
            "activated_at"        : time.time(),
            "actual_reduction_kw" : 0.0,
            "credits_earned"      : 0.0
        }
        self._is_active = True

        return {
            "status"  : "activated",
            "event"   : self._current_event,
            "message" : (
                f"DR event activated: {start_hour:.1f}h to {end_hour:.1f}h | "
                f"Target reduction: {target_reduction_kw:.1f} kW"
            )
        }

    # ----------------------------------------------------------------
    def deactivate_event(self) -> dict:
        """
        Deactivate current DR event and calculate earned credits.

        Returns:
            dict with event summary and credits
        """
        if not self._current_event:
            return {"status": "no_active_event"}

        duration_h = (
            self._current_event["end_hour"]
            - self._current_event["start_hour"]
        )
        credits = (
            self._current_event["actual_reduction_kw"]
            * duration_h
            * self.dr_incentive_rate
        )

        self._current_event["credits_earned"] = round(credits, 4)
        self._total_credits += credits
        self._dr_history.append(self._current_event.copy())

        summary = {
            "status"         : "deactivated",
            "event"          : self._current_event,
            "credits_earned" : round(credits, 4),
            "total_credits"  : round(self._total_credits, 4)
        }

        self._current_event = None
        self._is_active     = False
        return summary

    # ----------------------------------------------------------------
    def get_dr_constraint(
        self,
        hour              : float,
        current_load_kw   : float,
        current_import_kw : float
    ) -> dict:
        """
        Get DR constraint for optimizer.

        Args:
            hour              : Current hour
            current_load_kw   : Current campus demand
            current_import_kw : Current grid import

        Returns:
            dict with max_import_kw, reduction_target, penalty_rate
        """
        if not self.check_active(hour):
            return {
                "dr_active"          : False,
                "max_import_kw"      : float("inf"),
                "reduction_target_kw": 0.0,
                "penalty_rate"       : 0.0,
                "incentive_rate"     : 0.0
            }

        target     = self._current_event.get("target_reduction_kw", 0.0)
        max_import = max(0.0, current_load_kw - target)

        # Track actual reduction
        actual_reduction = max(0.0, current_load_kw - current_import_kw)
        if self._current_event:
            self._current_event["actual_reduction_kw"] = actual_reduction

        return {
            "dr_active"          : True,
            "max_import_kw"      : round(max_import, 2),
            "reduction_target_kw": round(target, 2),
            "penalty_rate"       : 1.0,
            "incentive_rate"     : self.dr_incentive_rate,
            "event_type"         : self._current_event.get("event_type", "")
        }

    # ----------------------------------------------------------------
    def schedule_events_from_list(
        self,
        events: List[dict]
    ) -> List[dict]:
        """
        Schedule multiple DR events for the day.

        Args:
            events : List of event dicts with:
                     start_hour, end_hour, target_reduction_kw, event_type

        Returns:
            List of scheduled event confirmations
        """
        confirmations = []
        for ev in events:
            conf = self.activate_event(
                start_hour          = ev.get("start_hour", 17.0),
                end_hour            = ev.get("end_hour",   21.0),
                target_reduction_kw = ev.get("target_reduction_kw", 100.0),
                event_type          = ev.get("event_type", "scheduled")
            )
            confirmations.append(conf)
        return confirmations

    # ----------------------------------------------------------------
    def get_summary(self) -> dict:
        """Return DR tracking summary."""
        return {
            "is_active"           : self._is_active,
            "current_event"       : self._current_event,
            "total_events"        : len(self._dr_history),
            "total_credits_earned": round(self._total_credits, 4),
            "history"             : self._dr_history[-10:]
        }

    # ----------------------------------------------------------------
    def reset(self):
        """Reset all DR state."""
        self._is_active     = False
        self._current_event = None
        self._total_credits = 0.0