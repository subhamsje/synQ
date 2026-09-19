# synQ Robotics Infrastructure & Autonomy Layer Specification

## 1. Architectural Philosophy & Separation of Concerns

synQ follows a **simulation-first, hardware-ready** design pattern. Proven open-source robotics infrastructure is leveraged for mature primitives (middleware, navigation, SLAM, point-cloud operations, standard protocols), while proprietary autonomy algorithms drive warehouse semantic reasoning, topological roadmap derivation, conflict-free multi-agent pathfinding, and real-time digital twin synchronization.

```
             REAL / SIMULATED SENSORS
         (Ouster LiDAR, RealSense, Encoders, Gazebo)
                       ↓
                  ROS 2 + TF2
            (DDS, Lifecycle Nodes)
                       ↓
             SLAM / PERCEPTION
      (SLAM Toolbox 2D + Open3D Spatial Engine)
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
     3D WORLD MODEL            2D NAV MAP
  (Point Cloud / Mesh)     (Occupancy Grid & Costmap)
          ↓                         ↓
    Semantic Graph                Nav2
(Racks, Docks, Workstations)  (MPPI / Behaviors)
          └────────────┬────────────┘
                       ↓
                SYNQ WORLD MODEL
       (4 Synchronized Representations)
                       ↓
                FMS / MISSIONS
       (CBS MAPF, Energy & Capability Match)
                       ↓
              DIGITAL TWIN / UI
          (Three.js 3D WebGL Command Center)
```

---

## 2. Core Open-Source Stack

| Component | Technology | Responsibility in synQ | Configuration File |
| :--- | :--- | :--- | :--- |
| **Middleware** | ROS 2 (Humble / Iron / Jazzy) | Distributed DDS, TF2 tree, lifecycle nodes, parameter server, hardware abstraction | `ros2_ws/src/synq_bringup` |
| **Autonomous Navigation** | Nav2 | Omnidirectional MPPI controller, Smac/NavFn global planners, costmaps, behavior trees | `ros2_ws/src/synq_navigation/config/nav2_params.yaml` |
| **2D Mapping & SLAM** | SLAM Toolbox | Online asynchronous Ceres-solver graph SLAM, loop closure, 2D occupancy grid generation | `ros2_ws/src/synq_slam/config/slam_toolbox_async.yaml` |
| **3D Point Cloud Engine**| Open3D / Open3D-SLAM | Voxel downsampling, statistical outlier removal, RANSAC ground plane isolation, Euclidean clustering | `backend/automap/reconstruction.py` |
| **Physics Simulation** | Gazebo Harmonic | Dynamic physics, sensor simulation (`gpu_lidar`, `depth_camera`, `imu`), hardware-in-the-loop parity | `ros2_ws/src/synq_simulation/worlds/warehouse_simple.sdf` |
| **Fleet Interoperability** | VDA 5050 v3.0 | Standardized JSON orders, instant actions, connection states, and vehicle telemetry | `fms/vda5050/vda5050_serializer.py` |

---

## 3. synQ Proprietary Autonomy Layer

### 3.1 AutoMap: Scan-to-Twin Pipeline
A 7-stage automated pipeline that turns raw sensor streams into production-grade warehouse digital twins:
1. **SCAN**: Ingestion of real-time or recorded sensor feeds (`/scan`, `/camera/depth/points`, `/odom`, `/tf`).
2. **MAPPING**: Pose-graph optimization via SLAM Toolbox creating continuous 2D occupancy and keyframe trajectory.
3. **3D RECONSTRUCTION**: Open3D-driven voxel downsampling (0.15m grid), statistical filtering, and RANSAC planar segmentation (ground floor vs. structural walls).
4. **DETECTION**: Geometric feature heuristics classifying clusters into `STORAGE_RACK`, `CHARGING_DOCK`, `PICK_STATION`, `DROP_STATION`, `CONVEYOR`, `RESTRICTED_ZONE`, and `OBSTACLE`.
5. **REVIEW & LABEL**: Human-in-the-loop uncertainty gate. Any detection with confidence $< 0.85$ is flagged as `NEEDS_CONFIRMATION` for operator review and modification.
6. **MAP GENERATED**: Dynamic generation of 4 strictly decoupled operational representations.
7. **READY FOR AUTONOMOUS OPERATION**: 1-Click activation into live Fleet Management System (FMS).

### 3.2 Dynamic Navigation Topology (No Hardcoded Grids)
Unlike legacy implementations that hardcode fixed coordinate waypoints, the synQ `AutomaticTopologyGenerator` (`backend/automap/topology_generator.py`):
- Analyzes traversable free-space corridors between detected racks and perimeter boundaries.
- Derives highway intersection nodes where longitudinal and transverse aisles meet.
- Projects entity-specific approach waypoints:
  - **Storage Racks**: Pallet pick/drop approach nodes facing rack faces with clearance buffers.
  - **Charging Docks**: Precision docking approach nodes aligned with docking approach vectors.
  - **Workstations & Conveyors**: Infeed/outfeed alignment and queuing nodes.
- Establishes collision-free bidirectional and unidirectional edges with speed limits and Euclidean distance weights.
- Guarantees complete graph connectivity for Conflict-Based Search (CBS) routing.

### 3.3 Unified World Model
The `UnifiedWorldModel` (`backend/automap/world_model.py`) maintains 4 strictly synchronized operational representations:
1. **3D Digital Twin**: Three.js WebGL scene containing meshes, bounding boxes, and visual shaders for operator inspection.
2. **2D Nav2 Costmap**: Standard ROS 2 `nav_msgs/OccupancyGrid` with origin, resolution, and inflated obstacle footprints.
3. **Semantic Scene Graph**: Hierarchical ontology with entity capabilities (`["PALLET_LIFT", "FAST_CHARGE_60KW", "ROLLER_CONVEYOR"]`), clearance envelopes, and approach node mappings.
4. **Navigation Topology Graph**: Directed `WarehouseGraph` ready for CBS pathfinding and VDA 5050 serialization.

### 3.4 Fleet Management System (FMS) Deep Integration
- **Semantic Order Resolution**: Warehouse orders can specify semantic entity targets (e.g. `pick_entity="RACK-A"`, `drop_entity="CONV-01"`), which are automatically resolved to physical approach nodes.
- **Capability & Payload Matching**: AMRs equipped with modular mechanisms (`SCISSOR_LIFT`, `ROLLER_CONVEYOR`, `TOTE_GRIPPER`) are matched against mission requirements.
- **Energy-Aware Preemptive Dispatch**: If an AMR's battery falls below $20\%$, the FMS automatically dispatches it to the nearest unreserved charging dock node.
- **Conflict-Based Search (CBS)**: Space-time $A^*$ search resolving vertex and edge conflicts across multiple AMRs.

---

## 4. Hardware Abstraction & Simulation Parity

All topic and TF contracts are identical between Gazebo Harmonic simulation and physical AMR hardware:

```
TF2 Coordinate Tree:
map
 └── odom
      └── base_footprint
           └── base_link
                ├── lidar_link (/sensors/lidar/scan)
                ├── camera_link (/camera/depth/points)
                ├── imu_link (/sensors/imu)
                ├── wheel_fl_link, wheel_fr_link, wheel_rl_link, wheel_rr_link
                └── payload_dock_link (/payload/status)
```

| Sensor / Actuator | ROS 2 Topic | Message Type | Hardware Driver | Gazebo Plugin |
| :--- | :--- | :--- | :--- | :--- |
| **2D / 3D LiDAR** | `/sensors/lidar/scan` | `sensor_msgs/LaserScan` | Ouster OS1 / Velodyne Puck | `gz-sim-sensors-system` (gpu_lidar) |
| **RGB-D Depth** | `/camera/depth/points` | `sensor_msgs/PointCloud2` | Intel RealSense D435i | `gz-sim-sensors-system` (rgbd_camera) |
| **IMU** | `/sensors/imu` | `sensor_msgs/Imu` | MicroStrain 3DM-GX5 | `gz-sim-sensors-system` (imu) |
| **Wheel Odometry** | `/odom` | `nav_msgs/Odometry` | Roboteq / CANopen Drives | `gz_ros2_control` (Mecanum drive) |
| **Velocity Command**| `/cmd_vel` | `geometry_msgs/Twist` | synQ Safety Interlock / CAN | `synq_drive` mecanum controller |
| **Battery State** | `/battery_state` | `sensor_msgs/BatteryState` | BMS CAN Bus | Gazebo Battery plugin |
| **Payload Action** | `/payload/action` | `synq_interfaces/srv/TriggerPayloadAction` | Modbus / EtherCAT Actuator | Custom Mock / Gazebo joint |
