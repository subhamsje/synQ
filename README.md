# synQ — Modular Autonomous Mobile Robot (AMR) Platform
> **Smart India Hackathon 2026** | **Problem Statement SIH26112** (Autodesk)

An industrial-grade, simulation-first, hardware-ready modular Autonomous Mobile Robot (AMR) platform and fleet management system built with **ROS 2 Jazzy**, **Mecanum Holonomic Kinematics**, **ros2_control**, **VDA 5050 v2.0**, and **Autodesk Fusion 360** Generative Design.

---

## 🏛️ Project Architecture

```text
                  WMS / WES
                      │
                      ▼
               ┌─────────────┐
               │  synQ FMS   │
               │             │
               │ Orders      │
               │ Allocation  │
               │ Traffic     │
               │ Energy      │
               │ Missions    │
               └──────┬──────┘
                      │
                 VDA 5050
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     AMR-01        AMR-02        AMR-03
        │             │             │
       ROS2          ROS2          ROS2
        │             │             │
      Nav2           Nav2          Nav2
        │             │             │
     Mecanum        Mecanum       Mecanum
        │             │             │
     Hardware      Hardware      Simulation
        │
     Payload
        │
     Sensors
```

---

## 🎯 Milestones Progress

| Milestone | Title | Status | Validation |
| :--- | :--- | :---: | :--- |
| **M0** | Environment Audit | **COMPLETE** | Darwin arm64 toolchain, CMake 4.4, Python 3.10, Colcon extensions |
| **M1** | Simulated synQ-AMR & Mecanum Drive | **COMPLETE** | URDF/Xacro model, ros2_control, Gazebo spawn launcher |
| **M2** | Mecanum Kinematics Solver | **COMPLETE** | Forward/Inverse equations, $O$-shape roller sign validation, odometry integration |
| **M3** | Sensor Layer (LiDAR, IMU, TF2) | **COMPLETE** | `/sensors/lidar/scan`, `/sensors/imu`, TF tree validation, range filtering |
| **M4** | Localization & SLAM Toolbox | **COMPLETE** | EKF slip rejection, AMCL omni model, SLAM Toolbox Ceres, 18/18 tests passing |
| **M5** | Nav2 Navigation Stack | *Next* | Holonomic MPPI local controller, global planner, dynamic obstacle avoidance |
| **M6** | Mission Executive | *Planned* | BehaviorTree.CPP state machine (`PICK`, `PLACE`, `DOCK`, `CHARGE`) |
| **M7** | Modular Payload Architecture | *Planned* | 1-Wire auto-ID, dynamic costmap footprint inflation, payload profiles |
| **M8** | synQ FMS Fleet Management | *Planned* | Multi-AMR task allocation, battery routing, traffic management |
| **M9** | Multi-Robot Coordination (CBS) | *Planned* | Conflict-Based Search, space-time reservations, deadlock elimination |
| **M10**| Energy Management | *Planned* | State-of-Charge (SOC) tracking, opportunity charging policy |
| **M11**| VDA 5050 Protocol Interface | *Planned* | v2.0.0 Order, State, and InstantActions schemas |
| **M12**| Backend Modular Monolith | *Planned* | FastAPI async engine, WebSocket streams, telemetry persistence |
| **M13**| Industrial Digital Twin | *Planned* | 60 FPS Three.js operations cockpit |
| **M14**| Failure Injection & FMEA | *Planned* | LiDAR loss, motor stall, obstacle injection |
| **M15**| Physical Hardware Integration | *Planned* | STM32 micro-ROS, motor drivers, safety relay |
| **M16**| SIH Demo Hardening | *Planned* | 3-minute winning presentation walkthrough |

---

## 🧪 Quick Test

### Run Complete Test Suite
```bash
make test
```
*Executes all 18 unit tests across Mecanum kinematics, Sensor processing, EKF wheel slip rejection, AMCL convergence monitoring, and SLAM map validation.*

### Build with Docker (ROS 2 Jazzy & Gazebo Harmonic)
```bash
docker compose up --build
```
