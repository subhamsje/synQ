import time
import asyncio
from typing import Dict, List, Any, Optional

from fms.adapters.base_adapter import RobotAdapter
from fms.models.domain_models import Robot, RobotStatus, IncidentType
from backend.events.event_bus import event_bus
from backend.events.event_types import EventType, EventSeverity


class ObservationLoop:
    """
    Continuous Real-time Observation Loop (Expected vs. Actual).
    Monitors all AMRs in the facility to detect behavioral deviations:
    - Unexpectedly stationary while on active navigation route
    - Accelerated battery depletion
    - Telemetry stale / communication drop
    - AMCL localization covariance degradation
    """

    def __init__(self):
        self.adapters: Dict[str, RobotAdapter] = {}
        self.stoppage_timers: Dict[str, float] = {}
        self.battery_baselines: Dict[str, float] = {}
        self.detected_anomalies: List[Dict[str, Any]] = []

    def register_adapter(self, robot_id: str, adapter: RobotAdapter):
        self.adapters[robot_id] = adapter
        self.battery_baselines[robot_id] = adapter.robot.battery_pct

    def evaluate_cycle(self) -> List[Dict[str, Any]]:
        """Single synchronous evaluation cycle comparing Expected vs Actual."""
        now = time.time()
        anomalies = []

        for rid, adapter in self.adapters.items():
            bot = adapter.get_normalized_robot()

            # 1. Stale Heartbeat Watchdog
            if adapter.is_heartbeat_stale():
                anomaly = {
                    "robot_id": rid,
                    "type": "STALE_HEARTBEAT",
                    "severity": "WARNING",
                    "detail": f"No telemetry for {now - bot.last_heartbeat:.1f}s",
                    "timestamp": now
                }
                anomalies.append(anomaly)

            # 2. Unexpectedly Stopped Anomaly
            is_expected_moving = (bot.status == RobotStatus.NAVIGATING and len(bot.planned_trajectory) > 0)
            is_actual_stopped = (
                abs(bot.velocity.get("vx", 0.0)) < 0.05
                and abs(bot.velocity.get("vy", 0.0)) < 0.05
                and abs(bot.velocity.get("omega", 0.0)) < 0.05
            )

            if is_expected_moving and is_actual_stopped and not bot.safety_estop:
                if rid not in self.stoppage_timers:
                    self.stoppage_timers[rid] = now
                elif (now - self.stoppage_timers[rid]) >= 4.0:
                    anomaly = {
                        "robot_id": rid,
                        "type": "UNEXPECTED_STOPPAGE",
                        "severity": "CRITICAL",
                        "detail": f"Stationary for {now - self.stoppage_timers[rid]:.1f}s while route active",
                        "timestamp": now
                    }
                    anomalies.append(anomaly)
            else:
                self.stoppage_timers.pop(rid, None)

            # 3. Abnormal Battery Drop
            baseline = self.battery_baselines.get(rid, bot.battery_pct)
            drop = baseline - bot.battery_pct
            if drop > 15.0:  # Sudden 15% drop
                anomaly = {
                    "robot_id": rid,
                    "type": "RAPID_BATTERY_DROP",
                    "severity": "WARNING",
                    "detail": f"Sudden drop of {drop:.1f}% SoC",
                    "timestamp": now
                }
                anomalies.append(anomaly)
            self.battery_baselines[rid] = bot.battery_pct

            # 4. Localization Covariance Spike
            if bot.sensors.amcl_covariance > 0.05:
                anomaly = {
                    "robot_id": rid,
                    "type": "LOCALIZATION_DRIFT",
                    "severity": "WARNING",
                    "detail": f"AMCL covariance ({bot.sensors.amcl_covariance:.3f}) exceeds 0.05 threshold",
                    "timestamp": now
                }
                anomalies.append(anomaly)

        self.detected_anomalies.extend(anomalies)
        if len(self.detected_anomalies) > 50:
            self.detected_anomalies = self.detected_anomalies[-50:]
        return anomalies

    async def run_step(self) -> List[Dict[str, Any]]:
        """Async evaluation cycle that also publishes to EventBus."""
        anomalies = self.evaluate_cycle()
        for anom in anomalies:
            ev_type = EventType.ROBOT_FAULT if anom["severity"] == "CRITICAL" else EventType.INCIDENT_LOGGED
            ev_sev = EventSeverity.CRITICAL if anom["severity"] == "CRITICAL" else EventSeverity.WARNING
            bot_id = anom["robot_id"]
            typ = anom["type"]
            det = anom["detail"]
            await event_bus.publish(
                event_type=ev_type,
                source_entity=f"OBSERVER:{bot_id}",
                message=f"[{typ}] {det}",
                severity=ev_sev,
                metadata=anom
            )
        return anomalies


observation_loop = ObservationLoop()
