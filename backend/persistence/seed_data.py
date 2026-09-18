import time
import random
import json
from datetime import datetime, timedelta
from backend.persistence.db import OperationalDatabase, DB_PATH


def seed_operational_memory(db: OperationalDatabase = None):
    """
    Seeds the SQLite database with 12 heterogeneous AMRs,
    147 completed historical missions, realistic incidents, and daily snapshots.
    """
    if db is None:
        db = OperationalDatabase()

    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Check if already seeded
        cursor.execute("SELECT COUNT(*) FROM robots")
        if cursor.fetchone()[0] >= 12:
            return

    now = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Seed 12 Heterogeneous AMRs
    # Vendors: Vendor-X (Heavy Lifters), Vendor-Y (High-speed Conveyors), Vendor-Z (Smart Grippers)
    robots_config = [
        # Vendor X - Scissor Lifts
        {"robot_id": "AMR-01", "vendor": "Vendor-X Robotics", "payload_type": "SCISSOR_LIFT", "battery_pct": 94.5, "status": "IDLE", "current_node": "N_0_0", "total_distance_m": 12400.0, "runtime_s": 14200.0, "battery_health": 98.0, "motor_health": 97.5, "localization_health": 99.0, "navigation_health": 98.0, "composite_health": 98.1},
        {"robot_id": "AMR-02", "vendor": "Vendor-X Robotics", "payload_type": "SCISSOR_LIFT", "battery_pct": 88.0, "status": "NAVIGATING", "current_node": "N_1_1", "total_distance_m": 15800.0, "runtime_s": 17800.0, "battery_health": 95.0, "motor_health": 96.0, "localization_health": 98.0, "navigation_health": 97.0, "composite_health": 96.5},
        {"robot_id": "AMR-03", "vendor": "Vendor-X Robotics", "payload_type": "SCISSOR_LIFT", "battery_pct": 91.2, "status": "IDLE", "current_node": "N_0_3", "total_distance_m": 8200.0, "runtime_s": 9800.0, "battery_health": 96.0, "motor_health": 95.0, "localization_health": 81.0, "navigation_health": 92.0, "composite_health": 88.5}, # Localization drift noted
        {"robot_id": "AMR-04", "vendor": "Vendor-X Robotics", "payload_type": "SCISSOR_LIFT", "battery_pct": 92.0, "status": "IDLE", "current_node": "N_3_0", "total_distance_m": 11100.0, "runtime_s": 12900.0, "battery_health": 97.0, "motor_health": 96.0, "localization_health": 97.5, "navigation_health": 96.5, "composite_health": 96.8},

        # Vendor Y - Roller Conveyors
        {"robot_id": "AMR-05", "vendor": "Vendor-Y Conveyors", "payload_type": "ROLLER_CONVEYOR", "battery_pct": 86.5, "status": "NAVIGATING", "current_node": "N_2_2", "total_distance_m": 13900.0, "runtime_s": 15600.0, "battery_health": 94.0, "motor_health": 95.5, "localization_health": 98.5, "navigation_health": 97.0, "composite_health": 96.2},
        {"robot_id": "AMR-06", "vendor": "Vendor-Y Conveyors", "payload_type": "ROLLER_CONVEYOR", "battery_pct": 89.0, "status": "IDLE", "current_node": "N_3_3", "total_distance_m": 10500.0, "runtime_s": 11800.0, "battery_health": 96.5, "motor_health": 97.0, "localization_health": 99.0, "navigation_health": 98.0, "composite_health": 97.6},
        {"robot_id": "AMR-07", "vendor": "Vendor-Y Conveyors", "payload_type": "ROLLER_CONVEYOR", "battery_pct": 54.0, "status": "CHARGING", "current_node": "N_0_0", "total_distance_m": 22100.0, "runtime_s": 24800.0, "battery_health": 72.0, "motor_health": 94.0, "localization_health": 96.0, "navigation_health": 96.0, "composite_health": 84.0}, # Battery degradation target
        {"robot_id": "AMR-08", "vendor": "Vendor-Y Conveyors", "payload_type": "ROLLER_CONVEYOR", "battery_pct": 97.0, "status": "IDLE", "current_node": "N_1_3", "total_distance_m": 9400.0, "runtime_s": 10500.0, "battery_health": 99.0, "motor_health": 98.0, "localization_health": 99.0, "navigation_health": 99.0, "composite_health": 98.8},

        # Vendor Z - Tote Grippers
        {"robot_id": "AMR-09", "vendor": "Vendor-Z Autonomous", "payload_type": "TOTE_GRIPPER", "battery_pct": 93.0, "status": "IDLE", "current_node": "N_2_0", "total_distance_m": 7800.0, "runtime_s": 8900.0, "battery_health": 98.0, "motor_health": 98.5, "localization_health": 98.0, "navigation_health": 97.5, "composite_health": 98.0},
        {"robot_id": "AMR-10", "vendor": "Vendor-Z Autonomous", "payload_type": "TOTE_GRIPPER", "battery_pct": 91.5, "status": "NAVIGATING", "current_node": "N_0_2", "total_distance_m": 8900.0, "runtime_s": 10100.0, "battery_health": 97.5, "motor_health": 97.0, "localization_health": 98.5, "navigation_health": 98.0, "composite_health": 97.8},
        {"robot_id": "AMR-11", "vendor": "Vendor-Z Autonomous", "payload_type": "TOTE_GRIPPER", "battery_pct": 42.0, "status": "CHARGING", "current_node": "N_3_3", "total_distance_m": 14200.0, "runtime_s": 16400.0, "battery_health": 91.0, "motor_health": 93.0, "localization_health": 97.0, "navigation_health": 96.0, "composite_health": 94.2},
        {"robot_id": "AMR-12", "vendor": "Vendor-Z Autonomous", "payload_type": "TOTE_GRIPPER", "battery_pct": 95.0, "status": "IDLE", "current_node": "N_2_3", "total_distance_m": 6900.0, "runtime_s": 7900.0, "battery_health": 99.0, "motor_health": 98.5, "localization_health": 99.0, "navigation_health": 98.5, "composite_health": 98.8},
    ]

    for r in robots_config:
        r["updated_at"] = now
        db.upsert_robot(r)

    # 2. Seed 147 Completed Historical Missions
    nodes = [f"N_{r}_{c}" for r in range(4) for c in range(4)]
    payloads = ["SCISSOR_LIFT", "ROLLER_CONVEYOR", "TOTE_GRIPPER"]
    robot_ids = [r["robot_id"] for r in robots_config]

    # Create 147 completed missions throughout the day
    start_of_day = now - 3600 * 14
    for i in range(1, 148):
        m_id = f"TASK-{8000 + i}"
        pick = random.choice(nodes[:8])
        drop = random.choice(nodes[8:])
        p_type = random.choice(payloads)
        assigned = random.choice(robot_ids)
        m_time = start_of_day + (i * 320) + random.uniform(-60, 60)
        dur = random.uniform(180, 420)  # 3 to 7 minutes

        db.record_mission({
            "mission_id": m_id,
            "pick_node": pick,
            "drop_node": drop,
            "payload_type": p_type,
            "assigned_robot": assigned,
            "status": "COMPLETED",
            "priority": 1 if i % 10 != 0 else 2,
            "sla_deadline_s": dur + 120,
            "created_at": m_time,
            "completed_at": m_time + dur,
            "duration_s": round(dur, 1),
            "decision_trace_json": json.dumps({
                "selected_robot": assigned,
                "rationale": f"Optimal composite cost score for payload {p_type}.",
                "cbs_deconfliction": "Collision-free path verified."
            })
        })

    # 3. Seed 3 Failed and 2 Interrupted missions
    for i, status in enumerate(["FAILED", "FAILED", "FAILED", "INTERRUPTED", "INTERRUPTED"], start=148):
        m_id = f"TASK-{8000 + i}"
        db.record_mission({
            "mission_id": m_id,
            "pick_node": "N_0_1",
            "drop_node": "N_2_2",
            "payload_type": "ROLLER_CONVEYOR",
            "assigned_robot": "AMR-07" if i % 2 == 0 else "AMR-03",
            "status": status,
            "priority": 1,
            "sla_deadline_s": 300,
            "created_at": now - 3600 * 2,
            "completed_at": now - 3600 * 2 + 150,
            "duration_s": 150.0,
            "decision_trace_json": json.dumps({"note": f"Mission {status.lower()} due to simulated physical disruption."})
        })

    # 4. Seed Historical Events & Incidents
    # Aisle C04 congestion events
    for t_offset in [7200, 5400, 3600]:
        db.record_event(
            event_id=f"EVT-HIST-{t_offset}",
            event_type="traffic.congestion.detected",
            severity="WARNING",
            source_entity="FACILITY-MONITOR",
            message="Aisle C04 experienced 18% higher traffic congestion during peak transfer window.",
            timestamp=now - t_offset,
            metadata={"corridor": "C04", "waiting_time_delta_pct": 18}
        )

    # AMR-07 battery degradation events
    db.record_event(
        event_id="EVT-HIST-BATT-07",
        event_type="maintenance.predicted",
        severity="WARNING",
        source_entity="AMR-07",
        message="Battery health degradation detected (72%). Cell inspection recommended within 18 operating hours.",
        timestamp=now - 1800,
        metadata={"robot_id": "AMR-07", "battery_health": 72.0, "recommended_action": "BATTERY_INSPECTION"}
    )

    # AMR-03 localization correction events
    for i in range(3):
        db.record_event(
            event_id=f"EVT-HIST-LOC-03-{i}",
            event_type="health.degradation.detected",
            severity="INFO",
            source_entity="AMR-03",
            message=f"Localization correction {i+1}/3 detected: AMCL particle spread exceeded 0.08 m² in Aisle B02.",
            timestamp=now - (2400 + i * 600),
            metadata={"robot_id": "AMR-03", "metric": "AMCL_COVARIANCE"}
        )

    # 5. Seed Daily Operations Snapshot (Matching prompt specification)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO daily_snapshots (
            date_str, total_missions, completed_missions, failed_missions,
            distance_km, uptime_pct, availability_pct, utilization_pct,
            obstacle_avoidances, route_replans, cbs_conflicts, battery_recoveries,
            safety_incidents, payload_transported_kg, operating_hours, summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date_str) DO UPDATE SET
            total_missions=excluded.total_missions,
            completed_missions=excluded.completed_missions,
            distance_km=excluded.distance_km
        """, (
            today_str, 152, 147, 3,
            82.4, 99.4, 96.2, 81.0,
            23, 8, 6, 4,
            0, 2840.0, 31.7,
            json.dumps({
                "top_issue": "AMR-07 battery degradation (72%)",
                "recommendation": "Schedule AMR-07 for battery inspection; review C04 traffic.",
                "congested_aisle": "C04"
            })
        ))
        conn.commit()


if __name__ == "__main__":
    seed_operational_memory()
    print("Operational Memory successfully seeded with 12 AMRs, 147 missions, and telemetry history.")
