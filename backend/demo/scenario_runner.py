import time
from typing import Dict, Any, List
from backend.events.event_bus import event_bus
from backend.events.event_types import EventType, EventSeverity
from backend.persistence.db import db


class FacilityScenarioRunner:
    """
    Executes interactive facility simulation scenarios for Hackathon Demonstration:
    1. BLOCK_AISLE_C04: Force autonomous replanning
    2. DISABLE_ROBOT_AMR07: Failure recovery & task reallocation
    3. DEGRADE_BATTERY: Autonomous low-battery handover & dock reroute
    4. CONGEST_CORRIDOR: 5 AMRs converge on shared intersection -> CBS deconfliction
    5. ADD_URGENT_TASK: Medical component 4m SLA preemption
    6. BURST_10_TASKS: Rapid multi-AMR batch allocation
    """

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "BLOCK_AISLE_C04",
                "title": "Block Aisle C04",
                "description": "Inject dynamic obstacle in primary transit corridor. Observe LiDAR detection, trajectory invalidation, CBS detour, and SLA preservation.",
                "complexity": "HIGH"
            },
            {
                "id": "DISABLE_ROBOT_AMR07",
                "title": "Robot Hardware Failure (AMR-07)",
                "description": "Simulate unexpected drive motor fault on AMR-07. FLTX reallocates 3 active tasks across AMR-02, AMR-03, and AMR-04 without mission cancellation.",
                "complexity": "CRITICAL"
            },
            {
                "id": "DEGRADE_BATTERY",
                "title": "In-Transit Low Battery Emergency",
                "description": "Force AMR-05 battery drop to 14%. Demonstrates automatic mission handoff and autonomous return to Fast Charger C1.",
                "complexity": "MEDIUM"
            },
            {
                "id": "CONGEST_CORRIDOR",
                "title": "Fleet Corridor Congestion",
                "description": "Converge 5 AMRs on intersection N_1_1. Demonstrates Space-Time Constraint Tree resolution and zero-deadlock scheduling.",
                "complexity": "HIGH"
            },
            {
                "id": "ADD_URGENT_TASK",
                "title": "Urgent Medical Component Dispatch",
                "description": "Inject critical priority order with 4-minute strict SLA deadline. Lower-priority pallet moves yield right-of-way.",
                "complexity": "HIGH"
            },
            {
                "id": "BURST_10_TASKS",
                "title": "Batch Inbound Spike (10 Tasks)",
                "description": "Simulate simultaneous arrival of 10 pallet/tote orders. Demonstrates multi-criteria fleet auction across all 12 AMRs.",
                "complexity": "EXTREME"
            }
        ]

    async def run_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Runs the chosen scenario and emits operational events to the Event Bus."""
        now = time.time()

        if scenario_id == "BLOCK_AISLE_C04":
            await event_bus.publish(
                event_type=EventType.AISLE_BLOCKED,
                source_entity="FACILITY-SIMULATOR",
                message="Physical obstacle detected at Aisle C04 (Node N_1_2 <-> N_1_1). Corridor closed.",
                severity=EventSeverity.WARNING,
                metadata={"corridor": "C04", "location": "N_1_2 <-> N_1_1"}
            )
            await event_bus.publish(
                event_type=EventType.ROUTE_REPLANNED,
                source_entity="CBS-ROUTER",
                message="Space-Time A* detour computed for 3 affected AMRs via bypass corridor N_2_2 (+4.7m).",
                severity=EventSeverity.INFO,
                metadata={"bypass_corridor": "N_2_2", "cost_delta_m": 4.7}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "Aisle C04 Blocked — Autonomous Detour Successful",
                "narrative": [
                    "1. LiDAR detected obstruction in Aisle C04",
                    "2. Active routes for AMR-01 and AMR-05 invalidated",
                    "3. Constraint Tree updated with edge block (N_1_2 <-> N_1_1)",
                    "4. Alternate bypass route selected via East Corridor (+4.7m travel)",
                    "5. Mission SLAs preserved; zero headway collisions"
                ],
                "affected_amrs": ["AMR-01", "AMR-05"],
                "cost_delta": "+4.7m transit distance",
                "sla_status": "PRESERVED"
            }

        elif scenario_id == "DISABLE_ROBOT_AMR07":
            await event_bus.publish(
                event_type=EventType.ROBOT_FAULT,
                source_entity="AMR-07",
                message="Drive motor inverter failure reported. AMR-07 switched to SAFE_HALT state.",
                severity=EventSeverity.CRITICAL,
                metadata={"robot_id": "AMR-07", "fault_code": "INV_TRIP_ERR_04"}
            )
            await event_bus.publish(
                event_type=EventType.MISSION_REALLOCATED,
                source_entity="FMS-ORCHESTRATOR",
                message="Tasks TASK-991, TASK-992, TASK-993 reallocated to AMR-03, AMR-04, and AMR-02.",
                severity=EventSeverity.WARNING,
                metadata={"reassignments": {"TASK-991": "AMR-03", "TASK-992": "AMR-04", "TASK-993": "AMR-02"}}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "AMR-07 Fault — Self-Healing Fleet Reallocation",
                "narrative": [
                    "1. AMR-07 flagged hardware fault -> switched to safe halt",
                    "2. 3 active/pending missions automatically retrieved by FMS",
                    "3. Multi-criteria auction evaluated 8 idle AMRs",
                    "4. Tasks reallocated to AMR-03, AMR-04, and AMR-02",
                    "5. Zero missions canceled; fleet throughput preserved at 96%"
                ],
                "affected_amrs": ["AMR-07", "AMR-02", "AMR-03", "AMR-04"],
                "reassigned_tasks": 3,
                "missions_canceled": 0
            }

        elif scenario_id == "DEGRADE_BATTERY":
            await event_bus.publish(
                event_type=EventType.BATTERY_WARNING,
                source_entity="AMR-05",
                message="Battery SoC dropped to 14.2% (< 18.0% mission cutoff).",
                severity=EventSeverity.WARNING,
                metadata={"robot_id": "AMR-05", "battery_pct": 14.2}
            )
            await event_bus.publish(
                event_type=EventType.BATTERY_RECOVERY_TRIGGERED,
                source_entity="ENERGY-SUPERVISOR",
                message="AMR-05 diverted to Fast Charger Dock C1. Task handed off to AMR-06.",
                severity=EventSeverity.INFO,
                metadata={"divert_dock": "C1"}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "Low Battery Handover & Dock Reroute",
                "narrative": [
                    "1. AMR-05 battery threshold breached (<15% SoC)",
                    "2. In-transit preemption triggered at staging node",
                    "3. Fast Charger Dock C1 reserved via CBS priority lock",
                    "4. Ongoing transfer task handed off to AMR-06",
                    "5. AMR-05 commenced 48V fast recharge at 5%/s"
                ],
                "affected_amrs": ["AMR-05", "AMR-06"],
                "dock_reserved": "Fast Charger C1"
            }

        elif scenario_id == "CONGEST_CORRIDOR":
            await event_bus.publish(
                event_type=EventType.CONGESTION_DETECTED,
                source_entity="TRAFFIC-FLOW-ENGINE",
                message="5 AMRs converging on intersection N_1_1. CBS deconfliction activated.",
                severity=EventSeverity.WARNING,
                metadata={"intersection": "N_1_1", "converging_amrs": 5}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "Fleet Corridor Congestion Resolved",
                "narrative": [
                    "1. 5 AMRs detected within 2-hop radius of intersection N_1_1",
                    "2. Space-Time Constraint Tree generated 6 deconfliction branches",
                    "3. Right-of-way assigned by mission priority and heading",
                    "4. AMR-09 and AMR-10 assigned 1-time-step wait constraints",
                    "5. Total headway delay < 3 seconds; deadlock avoided"
                ],
                "converging_amrs_count": 5,
                "branches_evaluated": 6,
                "deadlocks": 0
            }

        elif scenario_id == "ADD_URGENT_TASK":
            await event_bus.publish(
                event_type=EventType.MISSION_CREATED,
                source_entity="WMS-INBOUND",
                message="CRITICAL PRIORITY: Urgent medical component transfer (SLA: 4m).",
                severity=EventSeverity.CRITICAL,
                metadata={"order_id": "URGENT-MED-99", "priority": 1, "deadline_sec": 240}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "Urgent Medical Order Dispatched",
                "narrative": [
                    "1. Received urgent medical component transfer (Storage B04 -> Assembly P02)",
                    "2. SLA deadline: 4 minutes (CRITICAL)",
                    "3. AMR-01 selected: Heavy payload capability with 94.5% SoC",
                    "4. Lower-priority pallet transfers commanded to yield right-of-way",
                    "5. Projected transit time: 1m 48s (Well within 4m SLA)"
                ],
                "assigned_amr": "AMR-01",
                "sla_target_sec": 240,
                "projected_transit_sec": 108
            }

        elif scenario_id == "BURST_10_TASKS":
            await event_bus.publish(
                event_type=EventType.MISSION_CREATED,
                source_entity="WMS-INBOUND",
                message="Batch Inbound Spike: 10 simultaneous orders submitted to FMS auction.",
                severity=EventSeverity.INFO,
                metadata={"batch_count": 10}
            )
            return {
                "scenario_id": scenario_id,
                "status": "EXECUTED",
                "title": "10-Task Batch Distributed Across 12 AMRs",
                "narrative": [
                    "1. 10 simultaneous warehouse orders submitted",
                    "2. FMS evaluated capability matrix: 4 Lifters, 4 Conveyors, 4 Grippers",
                    "3. 10 matching AMRs assigned optimal tasks in 34ms",
                    "4. Multi-agent CBS generated 10 synchronized trajectories",
                    "5. Fleet utilization increased from 81% to 98%"
                ],
                "dispatched_tasks_count": 10,
                "computation_time_ms": 34,
                "fleet_utilization_pct": 98.0
            }

        return {"error": f"Unknown scenario_id: {scenario_id}"}


scenario_runner = FacilityScenarioRunner()
