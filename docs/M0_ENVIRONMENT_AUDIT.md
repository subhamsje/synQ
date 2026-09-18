# synQ — M0: Environment Audit Report

**Date:** 2026-09-18  
**Auditor:** synQ Lead Robotics Systems Engineer

---

## 1. Host Environment Identification

* **Operating System:** Darwin 25.6.0 (macOS on Apple Silicon arm64)
* **Host Machine:** `Subhams-MacBook-Air.local` (Apple Silicon M-series CPU/GPU)
* **Compiler / Toolchain:**
  - C/C++: Apple Clang 21.0.0 (`clang-2100.3.34.2`, target: `arm64-apple-darwin25.6.0`)
  - Make: GNU Make 3.81
  - CMake: CMake 4.4.3 (installed via Homebrew)
  - Colcon: Colcon 0.21.3 with `colcon-common-extensions`
* **Python Runtime:** Python 3.10.18 (`/Users/subham/.pyenv/shims/python3`)
  - Key packages: `pytest 9.1.1`, `numpy 1.26.4`, `scipy 1.12.0`, `PyYAML 6.0.3`, `fastapi 0.110.0`, `transforms3d 0.4.2`
* **Node.js Runtime:** Node.js v26.0.0 (`/opt/homebrew/bin/node`)
* **Package Manager:** Homebrew 7.0.3
* **Git Version & Remote:**
  - Git: 2.x (`/opt/homebrew/bin/git`)
  - Active GitHub Account: `subhamsje`
  - GitHub Remote: `https://github.com/subhamsje/synQ` (branch `main`)

---

## 2. Robotics & Simulation Status

* **ROS 2:** Not natively installed on host macOS (ROS 2 Humble/Jazzy strictly targets Ubuntu 22.04/24.04 LTS).
* **Gazebo Sim:** Not natively installed on host macOS (Gazebo Harmonic native to Linux).

---

## 3. Potential Conflicts & Resolution Strategy

1. **Host OS vs. Robotics Target:**
   - Robotics industry standard for ROS 2 Jazzy and Gazebo Harmonic is **Ubuntu 24.04 LTS (Noble Numbat)**.
   - Running directly on macOS without virtualization causes missing ROS 2 apt repositories, incompatible Gazebo rendering backends, and missing `ros2_control` drivers.
2. **Resolution & Development Architecture:**
   - **Tier 1 (Native Local Development & CI):** Pure kinematics algorithms, pathfinding solvers, VDA 5050 protocol validators, unit tests, and backend/frontend develop natively on macOS using Python 3.10+, CMake, Colcon, and Node.js.
   - **Tier 2 (Full Robotics Simulation & Hardware Abstraction):** Containerized Ubuntu 24.04 environment using standard multi-arch Docker / Colima with ROS 2 Jazzy, Gazebo Harmonic, `gz_ros2_control`, and Nav2.
   - A standard `Dockerfile` and `docker-compose.yml` are provided in the repository root for deterministic 1-click execution across both macOS (arm64) and Linux x86_64 development stations.

---

## 4. Minimum Reproducible Setup Established

* [x] Scaffolding created conforming to Section 6 repository manifest
* [x] Python test harness with `pytest` and `numpy` ready for Mecanum kinematics verification
* [x] Git repository configured and tracking `https://github.com/subhamsje/synQ`
* [x] Colcon build system ready
