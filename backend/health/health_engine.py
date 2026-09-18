from typing import Dict, Any, List, Optional
from backend.persistence.db import OperationalDatabase, db as default_db


class PredictiveHealthEngine:
    """
    Transparent Asset Health Scoring & Predictive Maintenance Intelligence.
    Calculates condition metrics based on telemetry history, cycle counts,
    and operational recovery events.
    """

    def __init__(self, database: OperationalDatabase = None):
        self.db = database or default_db

    def evaluate_fleet_health(self) -> List[Dict[str, Any]]:
        """Evaluates health scores and actionable maintenance recommendations for all AMRs."""
        robots = self.db.get_all_robots()
        results = []

        for r in robots:
            b_health = r["battery_health"]
            m_health = r["motor_health"]
            l_health = r["localization_health"]
            n_health = r["navigation_health"]
            comp_health = round(0.35 * b_health + 0.25 * m_health + 0.20 * l_health + 0.20 * n_health, 1)

            # Generate alerts & predicted actions
            recommendations = []
            if b_health < 80.0:
                recommendations.append({
                    "subsystem": "BATTERY",
                    "severity": "WARNING",
                    "issue": f"Battery capacity degradation ({b_health}%).",
                    "action": "Battery inspection recommended within next 18 operating hours."
                })
            if l_health < 85.0:
                recommendations.append({
                    "subsystem": "LOCALIZATION",
                    "severity": "INFO",
                    "issue": f"Elevated AMCL particle variance ({l_health}%).",
                    "action": "Verify landmark reflectivity and wheel encoder calibration."
                })
            if n_health < 85.0:
                recommendations.append({
                    "subsystem": "NAVIGATION",
                    "severity": "WARNING",
                    "issue": f"Frequent local recovery replans ({n_health}%).",
                    "action": "Inspect drive wheel treads for uneven wear or debris accumulation."
                })

            status = "HEALTHY"
            if comp_health < 75.0:
                status = "MAINTENANCE_DUE"
            elif comp_health < 88.0 or b_health < 80.0 or l_health < 82.0 or n_health < 82.0:
                status = "ATTENTION_REQUIRED"

            results.append({
                "robot_id": r["robot_id"],
                "vendor": r["vendor"],
                "payload_type": r["payload_type"],
                "overall_status": status,
                "composite_health": comp_health,
                "subsystems": {
                    "battery_health": b_health,
                    "motor_health": m_health,
                    "localization_health": l_health,
                    "navigation_health": n_health
                },
                "total_distance_km": round(r["total_distance_m"] / 1000.0, 1),
                "runtime_hours": round(r["runtime_s"] / 3600.0, 1),
                "recommendations": recommendations
            })

        return results

    def get_robot_health(self, robot_id: str) -> Optional[Dict[str, Any]]:
        all_evals = self.evaluate_fleet_health()
        return next((e for e in all_evals if e["robot_id"] == robot_id), None)


health_engine = PredictiveHealthEngine()
