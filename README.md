# synQ — Modular Autonomous Mobile Robot (AMR) Platform
> **Smart India Hackathon 2026** | **Problem Statement SIH26112** (Autodesk)  
> **GitHub Repository**: [https://github.com/subhamsje/synQ](https://github.com/subhamsje/synQ)

An industrial-grade, simulation-first, hardware-ready modular Autonomous Mobile Robot (AMR) platform and fleet management system built with **ROS 2 Jazzy**, **Mecanum Holonomic Kinematics**, **Nav2 MPPI Controller**, **Conflict-Based Search (CBS) Multi-AMR Traffic Routing**, **VDA 5050 v2.0 Protocol**, **FastAPI Backend**, and an **Interactive 2D/3D Digital Twin Operations Cockpit**.

---

## 🏛️ End-to-End System Architecture

```text
                  WMS / ERP Enterprise System
                              │
                              ▼
                ┌──────────────────────────┐
                │        synQ FMS          │
                │                          │
                │  - Order Allocation      │
                │  - CBS Spatio-Temporal   │
                │  - Opportunity Charging  │
                │  - VDA 5050 v2.0 Gateway │
                └─────────────┬────────────┘
                              │
                    VDA 5050 MQTT v2.0
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    synq-amr-01          synq-amr-02          synq-amr-03
  [SCISSOR_LIFT]      [ROLLER_CONVEYOR]      [TOTE_GRIPPER]
         │                    │                    │
   synq_executive       synq_executive       synq_executive
         │                    │                    │
    Nav2 (MPPI)          Nav2 (MPPI)          Nav2 (MPPI)
         │                    │                    │
    synq_safety          synq_safety          synq_safety
         │                    │                    │
    synq_drive           synq_drive           synq_drive
  (O-Shape Mecanum)    (O-Shape Mecanum)    (O-Shape Mecanum)
```

---

## 🎯 Implementation Status: Production-Ready & Tested

| Milestone | Title | Status | Validation Summary |
| :--- | :--- | :---: | :--- |
| **M0** | Environment & Toolchain Audit | **COMPLETE** | Darwin arm64 / Linux container toolchains verified |
| **M1** | Simulated synQ-AMR Chassis & URDF | **COMPLETE** | Full URDF/Xacro, ros2_control, Gazebo Harmonic spawn |
| **M2** | Mecanum Kinematics Solver | **COMPLETE** | O-shape roller geometry, inverse/forward solvers, odometry |
| **M3** | Sensor Processing Layer | **COMPLETE** | 360° LiDAR blindzone filtering, IMU covariance & tilt estimation |
| **M4** | Localization & SLAM Toolbox | **COMPLETE** | 50Hz EKF slip rejection, AMCL omni model, Ceres 2D mapping |
| **M5** | Nav2 Navigation Stack | **COMPLETE** | MPPI omni controller ($v_y \neq 0$), Smac 2D planner, BT recovery |
| **M6** | Mission Executive Engine | **COMPLETE** | Warehouse task state machine (`PICK`, `DROP`, `DOCK`, `CHARGE`) |
| **M7** | Modular Payload Architecture | **COMPLETE** | 1-Wire ID emulation, Lift/Conveyor/Gripper transit speed interlocks |
| **M8** | Multi-AMR Fleet Management & CBS | **COMPLETE** | Space-Time $A^*$, Constraint Tree, zero-collision guarantees |
| **M9** | VDA 5050 v2.0 Standard Interface | **COMPLETE** | MQTT Order, State, and InstantActions serialization & dispatch |
| **M10**| Backend & Digital Twin Cockpit | **COMPLETE** | FastAPI REST & WebSocket server, live canvas operations twin |
| **M11**| Safety Supervisor & Deadman System| **COMPLETE** | Multi-zone LiDAR field scaling, tilt rollover abort, watchdog |
| **M12**| Technical Docs & SIH Package | **COMPLETE** | Architecture specs, quickstart manuals, test suites |

---

## 🧪 Verification & Automated Tests

All **55 unit and integration tests** execute in **0.7 seconds**:

```bash
# Run complete test suite
python3 -m pytest tests/ -v
```

```text
============================== 55 passed in 0.73s ==============================
```

---

## 🚀 Quickstart

### 1. Launch the Backend API & Digital Twin Server
```bash
python3 backend/run_server.py
```
- Open `http://localhost:8000/` in your browser to view the interactive **Digital Twin Control Center**.
- Open `http://localhost:8000/docs` to test Swagger REST API endpoints.

### 2. Standalone Digital Twin View
```bash
open frontend/index.html
```

### 3. Docker Simulation (Ubuntu 24.04 / ROS 2 Jazzy)
```bash
docker compose up --build
```

---

## 📄 License & Attribution
Licensed under the Apache-2.0 License. Developed by Team synQ for SIH 2026 Problem Statement SIH26112.
