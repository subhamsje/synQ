from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio
import time

from fms.topology.warehouse_graph import WarehouseGraph
from fms.traffic.cbs_router import AgentPlan
from fms.fleet.fleet_manager import FleetManager, RobotAgent, WarehouseOrder
from fms.vda5050.vda5050_serializer import VDA5050Serializer, VDA5050State, VDA5050Header

app = FastAPI(
    title="synQ FMS & Digital Twin API",
    description="Fleet Management System, VDA 5050 Dispatcher, and Realtime Digital Twin Gateway for synQ-AMR",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
graph = WarehouseGraph.create_standard_warehouse_grid()
fms = FleetManager(graph)

# Initialize standard multi-AMR warehouse fleet
fms.register_robot(RobotAgent(robot_id="synq-amr-01", current_node="N_0_0", battery_pct=95.0, payload_type="SCISSOR_LIFT"))
fms.register_robot(RobotAgent(robot_id="synq-amr-02", current_node="N_3_3", battery_pct=88.0, payload_type="ROLLER_CONVEYOR"))
fms.register_robot(RobotAgent(robot_id="synq-amr-03", current_node="N_0_3", battery_pct=91.0, payload_type="TOTE_GRIPPER"))

active_orders_history: List[Dict[str, Any]] = []


class OrderCreateRequest(BaseModel):
    order_id: str
    pick_node: str
    drop_node: str
    required_payload: str = Field(default="ANY", description="SCISSOR_LIFT, ROLLER_CONVEYOR, TOTE_GRIPPER, or ANY")
    priority: int = 1


class PayloadActionRequest(BaseModel):
    action_name: str
    parameter: float = 0.0


@app.get("/health")
def get_health():
    return {
        "status": "HEALTHY",
        "service": "synq-fms-backend",
        "version": "1.0.0",
        "registered_amrs": len(fms.robots)
    }


@app.get("/api/v1/warehouse/topology")
def get_warehouse_topology():
    nodes_data = [
        {"node_id": n.node_id, "x": n.x, "y": n.y, "node_type": n.node_type}
        for n in graph.nodes.values()
    ]
    edges_data = []
    seen = set()
    for src, edges in graph.edges.items():
        for e in edges:
            edge_key = tuple(sorted([e.source_id, e.target_id]))
            if edge_key not in seen:
                seen.add(edge_key)
                edges_data.append({
                    "source": e.source_id,
                    "target": e.target_id,
                    "distance": round(e.distance, 2),
                    "max_speed": e.max_speed
                })
    return {"nodes": nodes_data, "edges": edges_data}


@app.get("/api/v1/fleet")
def get_fleet_status():
    res = []
    for rid, bot in fms.robots.items():
        res.append({
            "robot_id": bot.robot_id,
            "current_node": bot.current_node,
            "battery_pct": bot.battery_pct,
            "payload_type": bot.payload_type,
            "is_busy": bot.is_busy,
            "current_mission_id": bot.current_mission_id,
            "trajectory": bot.planned_trajectory
        })
    return {"fleet": res}


@app.post("/api/v1/orders")
def create_order(req: OrderCreateRequest):
    if req.pick_node not in graph.nodes or req.drop_node not in graph.nodes:
        raise HTTPException(status_code=400, detail="Invalid pick or drop node ID")

    order = WarehouseOrder(
        order_id=req.order_id,
        pick_node=req.pick_node,
        drop_node=req.drop_node,
        required_payload=req.required_payload,
        priority=req.priority
    )

    assigned_bot = fms.submit_order(order)
    if not assigned_bot:
        raise HTTPException(status_code=409, detail="No matching idle AMR available for order")

    # Generate CBS route
    bot = fms.robots[assigned_bot]
    plans = [
        AgentPlan(agent_id=assigned_bot, start_node=bot.current_node, goal_node=req.pick_node)
    ]
    routes = fms.coordinate_trajectories(plans)

    order_record = {
        "order_id": req.order_id,
        "assigned_amr": assigned_bot,
        "pick_node": req.pick_node,
        "drop_node": req.drop_node,
        "required_payload": req.required_payload,
        "status": "DISPATCHED",
        "route": routes.get(assigned_bot, []) if routes else []
    }
    active_orders_history.append(order_record)
    return order_record


@app.get("/api/v1/orders")
def get_orders():
    return {"orders": active_orders_history}


@app.post("/api/v1/robots/{robot_id}/estop")
def trigger_estop(robot_id: str):
    if robot_id not in fms.robots and robot_id != "ALL":
        raise HTTPException(status_code=404, detail="Robot not found")

    target_robots = list(fms.robots.keys()) if robot_id == "ALL" else [robot_id]
    for rid in target_robots:
        bot = fms.robots[rid]
        bot.is_busy = False
        bot.planned_trajectory = []

    return {
        "status": "ESTOP_TRIGGERED",
        "affected_robots": target_robots,
        "timestamp": time.time()
    }


@app.post("/api/v1/robots/{robot_id}/payload")
def trigger_payload_action(robot_id: str, req: PayloadActionRequest):
    if robot_id not in fms.robots:
        raise HTTPException(status_code=404, detail="Robot not found")

    bot = fms.robots[robot_id]
    return {
        "robot_id": robot_id,
        "payload_type": bot.payload_type,
        "action": req.action_name,
        "parameter": req.parameter,
        "status": "EXECUTED"
    }


@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Emit live fleet telemetry at 5 Hz
            telemetry = {
                "timestamp": time.time(),
                "fleet": [
                    {
                        "robot_id": bot.robot_id,
                        "node": bot.current_node,
                        "battery": bot.battery_pct,
                        "payload": bot.payload_type,
                        "busy": bot.is_busy,
                        "trajectory": bot.planned_trajectory
                    }
                    for bot in fms.robots.values()
                ]
            }
            await websocket.send_json(telemetry)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend'))
if os.path.exists(frontend_path):
    @app.get("/")
    def serve_frontend_root():
        index_file = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "synQ Digital Twin Frontend not found"}
