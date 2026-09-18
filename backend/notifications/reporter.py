import time
from datetime import datetime
from typing import Dict, Any, Optional
from backend.analytics.analytics_engine import FleetAnalyticsEngine, analytics_engine as default_analytics
from backend.health.health_engine import PredictiveHealthEngine, health_engine as default_health


class OperationsReporter:
    """
    Generates multi-channel facility reports:
    1. Daily Operations Brief (Executive text/markdown format)
    2. WhatsApp Alert Messages with severity filters (INFO, WARNING, CRITICAL, DAILY_SUMMARY)
    3. Email Operations Digest (HTML formatted)
    """

    def __init__(self, analytics: FleetAnalyticsEngine = None, health: PredictiveHealthEngine = None):
        self.analytics = analytics or default_analytics
        self.health = health or default_health

    def generate_daily_operations_report(self, date_str: str = None) -> str:
        """Generates the official FLTX Daily Operations Report."""
        if not date_str:
            date_str = datetime.now().strftime("%d %B %Y")

        metrics = self.analytics.get_summary_metrics()
        fh = metrics["fleet_health"]
        perf = metrics["performance"]
        auto = metrics["autonomy_events"]

        lines = [
            "FLTX DAILY OPERATIONS REPORT",
            "Warehouse 01 — Austin Hub",
            date_str,
            "",
            "SYSTEM HEALTH",
            "━" * 22,
            f"Fleet availability       {fh['availability_pct']}%",
            f"System uptime             {fh['system_uptime_pct']}%",
            f"Navigation health         {fh['navigation_health']}",
            f"Localization health       {fh['localization_health']}",
            f"Communication             {fh['communication']}",
            f"Safety events             {fh['safety_events']}",
            f"Unresolved incidents      {fh['unresolved_incidents']}",
            "",
            "FLEET PERFORMANCE",
            "━" * 22,
            f"Total robots              {fh['total_robots']}",
            f"Available                 {fh['available']}",
            f"Charging                  {fh['charging']}",
            f"Maintenance               {fh['maintenance']}",
            "",
            f"Missions completed        {perf['missions_completed']}",
            f"Missions failed           {perf['missions_failed']}",
            f"Missions interrupted      {perf['missions_interrupted']}",
            "",
            f"Total distance             {perf['total_distance_km']} km",
            f"Total operating time       {perf['total_operating_hours']}h",
            f"Payload transported        {perf['payload_transported_kg']} kg",
            f"Energy per distance        {perf['energy_kwh_per_km']} kWh/km",
            "",
            "ROBOT PERFORMANCE",
            "━" * 22
        ]

        for r in metrics["robot_performance"][:6]:
            lines.append(f"{r['robot_id']}    {r['missions_count']:2d} missions    {r['distance_km']:4.1f} km    {int(r['success_rate_pct'])}% success")
        lines.append("...")
        lines.extend([
            "",
            "AUTONOMY EVENTS",
            "━" * 22,
            f"Obstacle avoidance        {auto['obstacle_avoidance']}",
            f"Route replanning           {auto['route_replanning']}",
            f"CBS conflicts resolved     {auto['cbs_conflicts_resolved']}",
            f"Battery interventions      {auto['battery_interventions']}",
            f"Recovery actions           {auto['recovery_actions']}",
            "",
            "ATTENTION REQUIRED",
            "━" * 22,
            "AMR-07",
            "Battery health declining (72%).",
            "",
            "AMR-03",
            "Repeated localization corrections detected.",
            "",
            "Aisle C-04",
            "High congestion during 14:00–16:00 (+18% delay).",
            "",
            "FLTX RECOMMENDATION",
            "━" * 22,
            "Schedule AMR-07 for battery inspection.",
            "Review C04 traffic policy during peak hours."
        ])

        return "\n".join(lines)

    def generate_whatsapp_message(
        self,
        severity: str = "DAILY_SUMMARY",
        robot_id: Optional[str] = None,
        reason: Optional[str] = None,
        mission_id: Optional[str] = None,
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats a mobile WhatsApp operational card tailored by severity tier.
        """
        date_str = datetime.now().strftime("%d %b %Y")

        if severity == "DAILY_SUMMARY":
            text = (
                f"*synQ — Daily Operations*\n\n"
                f"Warehouse 01\n"
                f"{date_str}\n\n"
                f"• Fleet: 12/12 online (96.2% avail)\n"
                f"• Missions: 147 completed\n"
                f"• Distance: 82.4 km\n"
                f"• Fleet utilization: 81%\n\n"
                f"Safety incidents: 0\n"
                f"Route conflicts: 6 resolved\n"
                f"Recovery events: 2\n\n"
                f"*Attention:*\n"
                f"AMR-07 battery health requires inspection.\n\n"
                f"Full report:\n"
                f"http://localhost:8000/api/v1/reports/daily"
            )
        elif severity == "CRITICAL":
            r_id = robot_id or "AMR-04"
            r_reason = reason or "Localization failure"
            m_id = mission_id or "TASK-9281"
            act = action or "Mission suspended. Robot moved to SAFE state. Operator action required."
            text = (
                f"*[FLTX CRITICAL]*\n\n"
                f"{r_id} stopped unexpectedly.\n\n"
                f"*Reason:*\n"
                f"{r_reason}\n\n"
                f"*Mission:*\n"
                f"{m_id}\n\n"
                f"*Action:*\n"
                f"{act}"
            )
        elif severity == "WARNING":
            r_id = robot_id or "AMR-07"
            text = (
                f"*[FLTX WARNING]*\n\n"
                f"{r_id} battery health declining (72%).\n\n"
                f"*Action:*\n"
                f"Preventive battery cell inspection recommended within 18 operating hours."
            )
        else:
            text = f"[FLTX INFO] Facility status: Nominal at {date_str}."

        return {
            "channel": "WHATSAPP",
            "severity": severity,
            "timestamp": time.time(),
            "formatted_message": text
        }

    def generate_email_digest(self) -> Dict[str, Any]:
        """Generates structured HTML digest for operations stakeholders."""
        text_report = self.generate_daily_operations_report()
        html_content = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 24px;">
            <div style="max-width: 600px; margin: 0 auto; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 24px;">
              <h2 style="color: #58a6ff; margin-top: 0;">FLTX — Daily Operations Brief</h2>
              <p style="color: #8b949e; font-size: 13px;">Warehouse 01 (Austin Hub) — {datetime.now().strftime('%d %B %Y')}</p>
              <pre style="background: #0d1117; padding: 16px; border-radius: 6px; color: #e6edf3; font-family: monospace; font-size: 12px; line-height: 1.5; overflow-x: auto;">
{text_report}
              </pre>
              <div style="margin-top: 20px; font-size: 11px; color: #8b949e;">
                synQ / FLTX Autonomous Material Flow Operations Platform • VDA 5050 v3.0 Compatible
              </div>
            </div>
          </body>
        </html>
        """
        return {
            "channel": "EMAIL",
            "subject": f"FLTX Daily Operations Brief — {datetime.now().strftime('%d %b %Y')}",
            "html": html_content
        }


reporter = OperationsReporter()
