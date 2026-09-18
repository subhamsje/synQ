import sqlite3
import json
import os
import time
from typing import Dict, List, Any, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "synq_ops.db"))


class OperationalDatabase:
    """
    SQLite-backed Operational Memory for the FLTX Platform.
    Maintains persistent fleet asset state, mission lifecycles, event logs,
    and daily operational snapshots.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Robots table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS robots (
                robot_id TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                payload_type TEXT NOT NULL,
                battery_pct REAL DEFAULT 100.0,
                status TEXT DEFAULT 'IDLE',
                current_node TEXT DEFAULT 'N_0_0',
                total_distance_m REAL DEFAULT 0.0,
                runtime_s REAL DEFAULT 0.0,
                battery_health REAL DEFAULT 100.0,
                motor_health REAL DEFAULT 100.0,
                localization_health REAL DEFAULT 100.0,
                navigation_health REAL DEFAULT 100.0,
                composite_health REAL DEFAULT 100.0,
                updated_at REAL NOT NULL
            )
            """)

            # 2. Missions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id TEXT PRIMARY KEY,
                pick_node TEXT NOT NULL,
                drop_node TEXT NOT NULL,
                payload_type TEXT NOT NULL,
                assigned_robot TEXT,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                sla_deadline_s REAL,
                created_at REAL NOT NULL,
                completed_at REAL,
                duration_s REAL,
                decision_trace_json TEXT
            )
            """)

            # 3. Events audit table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_entity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata_json TEXT
            )
            """)

            # 4. Incidents & Autonomy Recoveries
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                incident_type TEXT NOT NULL,
                source_entity TEXT NOT NULL,
                location TEXT,
                resolved INTEGER DEFAULT 1,
                resolution_summary TEXT,
                timestamp REAL NOT NULL
            )
            """)

            # 5. Daily Operations Snapshots
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                date_str TEXT PRIMARY KEY,
                total_missions INTEGER DEFAULT 0,
                completed_missions INTEGER DEFAULT 0,
                failed_missions INTEGER DEFAULT 0,
                distance_km REAL DEFAULT 0.0,
                uptime_pct REAL DEFAULT 99.4,
                availability_pct REAL DEFAULT 96.2,
                utilization_pct REAL DEFAULT 81.0,
                obstacle_avoidances INTEGER DEFAULT 0,
                route_replans INTEGER DEFAULT 0,
                cbs_conflicts INTEGER DEFAULT 0,
                battery_recoveries INTEGER DEFAULT 0,
                safety_incidents INTEGER DEFAULT 0,
                payload_transported_kg REAL DEFAULT 0.0,
                operating_hours REAL DEFAULT 0.0,
                summary_json TEXT
            )
            """)
            conn.commit()

    # Robot operations
    def upsert_robot(self, robot_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO robots (
                robot_id, vendor, payload_type, battery_pct, status, current_node,
                total_distance_m, runtime_s, battery_health, motor_health,
                localization_health, navigation_health, composite_health, updated_at
            ) VALUES (
                :robot_id, :vendor, :payload_type, :battery_pct, :status, :current_node,
                :total_distance_m, :runtime_s, :battery_health, :motor_health,
                :localization_health, :navigation_health, :composite_health, :updated_at
            ) ON CONFLICT(robot_id) DO UPDATE SET
                vendor=excluded.vendor,
                payload_type=excluded.payload_type,
                battery_pct=excluded.battery_pct,
                status=excluded.status,
                current_node=excluded.current_node,
                total_distance_m=excluded.total_distance_m,
                runtime_s=excluded.runtime_s,
                battery_health=excluded.battery_health,
                motor_health=excluded.motor_health,
                localization_health=excluded.localization_health,
                navigation_health=excluded.navigation_health,
                composite_health=excluded.composite_health,
                updated_at=excluded.updated_at
            """, robot_data)
            conn.commit()

    def get_all_robots(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM robots ORDER BY robot_id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_robot(self, robot_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM robots WHERE robot_id = ?", (robot_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Mission operations
    def record_mission(self, mission_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            data = dict(mission_data)
            data["assigned_robot"] = data.get("assigned_robot") or data.get("assigned_amr")
            data.setdefault("sla_deadline_s", 300.0)
            data.setdefault("completed_at", None)
            data.setdefault("duration_s", None)
            data.setdefault("priority", 1)
            data.setdefault("created_at", time.time())

            if "decision_trace" in data and isinstance(data["decision_trace"], (dict, list)):
                data["decision_trace_json"] = json.dumps(data["decision_trace"])
            elif "decision_trace_json" not in data:
                data["decision_trace_json"] = "{}"

            cursor.execute("""
            INSERT INTO missions (
                mission_id, pick_node, drop_node, payload_type, assigned_robot,
                status, priority, sla_deadline_s, created_at, completed_at, duration_s, decision_trace_json
            ) VALUES (
                :mission_id, :pick_node, :drop_node, :payload_type, :assigned_robot,
                :status, :priority, :sla_deadline_s, :created_at, :completed_at, :duration_s, :decision_trace_json
            ) ON CONFLICT(mission_id) DO UPDATE SET
                assigned_robot=excluded.assigned_robot,
                status=excluded.status,
                completed_at=excluded.completed_at,
                duration_s=excluded.duration_s,
                decision_trace_json=excluded.decision_trace_json
            """, data)
            conn.commit()

    def get_missions(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM missions WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cursor.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # Events
    def record_event(self, event_id: str, event_type: str, severity: str, source_entity: str, message: str, timestamp: float, metadata: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO events (event_id, event_type, severity, source_entity, message, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, event_type, severity, source_entity, message, timestamp, json.dumps(metadata)))
            conn.commit()

    def get_events(self, limit: int = 50, source_entity: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if source_entity:
                cursor.execute("SELECT * FROM events WHERE source_entity = ? ORDER BY timestamp DESC LIMIT ?", (source_entity, limit))
            else:
                cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # Daily snapshots
    def get_latest_daily_snapshot(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_snapshots ORDER BY date_str DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None


# Global Database Instance
db = OperationalDatabase()
