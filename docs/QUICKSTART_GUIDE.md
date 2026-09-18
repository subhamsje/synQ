# synQ — Developer & Evaluator Quickstart Guide

This guide provides zero-config, instant instructions to evaluate, test, and run the **synQ** modular AMR platform.

---

## 1. Run Automated Test Suite

The entire synQ software stack—including Mecanum kinematics, sensor filtering, EKF slip rejection, AMCL localization, Nav2 MPPI configuration, Mission Executive, Modular Payloads, Multi-AMR Conflict-Based Search, VDA 5050 serialization, Safety Supervisor, and FastAPI backend—executes natively in **0.7 seconds**:

```bash
# Run all 55 automated unit & integration tests
python3 -m pytest tests/ -v
```

---

## 2. Launch the synQ FMS Backend API Server

Start the FastAPI REST and WebSocket server:

```bash
python3 backend/run_server.py
```
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Digital Twin Web Dashboard: `http://localhost:8000/`
- Fleet Status API: `http://localhost:8000/api/v1/fleet`

---

## 3. Launch the Interactive Digital Twin 2D/3D Dashboard

You can also open the dashboard directly in your browser without any server:

```bash
open frontend/index.html
```

### Dashboard Capabilities:
- **Live 15m x 15m Warehouse Canvas**: Displays 16 topological nodes, storage aisles, and charging docks.
- **Fleet Telemetry Cards**: Monitor battery SoC, current node, active payload module, and transit state.
- **Mission Dispatch**: Select Pick Station, Drop Station, and required payload (`SCISSOR_LIFT`, `ROLLER_CONVEYOR`, `TOTE_GRIPPER`) and dispatch via Conflict-Based Search.
- **Global Emergency Stop**: One-click physical killswitch halts all AMRs instantly.
- **VDA 5050 Inspector**: Inspects raw JSON MQTT state telemetry in real time.

---

## 4. Run Full Simulation in Docker (Ubuntu 24.04 / ROS 2 Jazzy)

For complete Gazebo physics simulation with `ros2_control` and RViz2:

```bash
docker compose up --build
```
