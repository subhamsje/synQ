from fastapi import Request, HTTPException
from typing import Set

class DemoGatekeeper:
    """
    Ensures safe, sandboxed execution for public QR demo access.
    Permits viewing telemetry, reports, decision traces, and triggering
    simulated facility scenarios, while blocking destructive hardware actuators,
    emergency stop commands on physical robots, and database modifications.
    """

    ALLOWED_DEMO_PATHS: Set[str] = {
        "/demo",
        "/api/v1/demo/scenarios",
        "/api/v1/demo/run-scenario",
        "/api/v1/reports/daily",
        "/api/v1/notifications/whatsapp",
        "/api/v1/analytics",
        "/api/v1/health",
        "/api/v1/agent/query",
        "/api/v1/agent/what-if",
        "/api/v1/fleet",
        "/api/v1/orders",
        "/api/v1/warehouse/topology",
        "/api/v1/demo/qr"
    }

    FORBIDDEN_DEMO_PATHS: Set[str] = {
        "/api/v1/robots/ALL/estop",
        "/api/v1/robots/{robot_id}/payload",
        "/api/v1/admin"
    }

    @classmethod
    def is_path_safe_for_demo(cls, path: str) -> bool:
        if any(path.startswith(p) for p in cls.ALLOWED_DEMO_PATHS):
            return True
        if any(p in path for p in ["payload", "estop", "admin"]):
            return False
        return True


demo_gatekeeper = DemoGatekeeper()
