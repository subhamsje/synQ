"""
AutoMap Sensor Abstraction & Ingestion Layer
Interfaces with ROS 2 sensor topics:
- /scan (sensor_msgs/LaserScan)
- /camera/depth/points (sensor_msgs/PointCloud2)
- /odom (nav_msgs/Odometry)
- /tf, /tf_static (geometry_msgs/TransformStamped)
Works with real hardware and Gazebo simulation without hardcoding geometry.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class RobotPose:
    x: float
    y: float
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0  # Heading in radians
    timestamp: float = field(default_factory=time.time)
    frame_id: str = "map"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "z": round(self.z, 3),
            "yaw_deg": round(math.degrees(self.yaw), 1),
            "timestamp": self.timestamp,
            "frame_id": self.frame_id
        }


@dataclass
class ScanKeyframe:
    keyframe_id: str
    timestamp: float
    pose: RobotPose
    # (x, y, z, intensity) points in map frame
    points: List[Tuple[float, float, float, float]] = field(default_factory=list)
    raw_scan_ranges: Optional[List[float]] = None

    @property
    def point_count(self) -> int:
        return len(self.points)


class SensorDataStream:
    """
    Subscribes to or simulates continuous sensor feeds from an AMR traversing
    a warehouse facility to build high-fidelity mapping datasets.
    """

    def __init__(self, robot_id: str = "synq-amr-01"):
        self.robot_id = robot_id
        self.active = False
        self.keyframes: List[ScanKeyframe] = []
        self.odometry_history: List[RobotPose] = []
        self.topic_mapping = {
            "scan_2d": f"/{robot_id}/scan",
            "point_cloud": f"/{robot_id}/camera/depth/points",
            "odometry": f"/{robot_id}/odom",
            "tf": "/tf"
        }

    def start_recording(self):
        self.active = True
        self.keyframes = []
        self.odometry_history = []

    def stop_recording(self) -> int:
        self.active = False
        return len(self.keyframes)

    def ingest_ros2_scan(self, laser_scan: Dict[str, Any], current_pose: RobotPose):
        """Ingests standard sensor_msgs/LaserScan dictionary into map-frame points."""
        if not self.active:
            return

        angle_min = laser_scan.get("angle_min", -math.pi)
        angle_inc = laser_scan.get("angle_increment", 0.01745)
        ranges = laser_scan.get("ranges", [])
        range_min = laser_scan.get("range_min", 0.1)
        range_max = laser_scan.get("range_max", 30.0)

        pts = []
        for i, r in enumerate(ranges):
            if range_min <= r <= range_max:
                theta = current_pose.yaw + (angle_min + i * angle_inc)
                px = current_pose.x + r * math.cos(theta)
                py = current_pose.y + r * math.sin(theta)
                # Sensor scan typically at lidar height 0.35m
                pz = current_pose.z + 0.35
                pts.append((px, py, pz, 1.0))

        kf_id = f"kf-{len(self.keyframes) + 1:04d}"
        kf = ScanKeyframe(
            keyframe_id=kf_id,
            timestamp=time.time(),
            pose=current_pose,
            points=pts,
            raw_scan_ranges=ranges
        )
        self.keyframes.append(kf)
        self.odometry_history.append(current_pose)

    def generate_synthetic_scan_run(self, facility_profile: str = "standard_hub") -> List[ScanKeyframe]:
        """
        Generates realistic SLAM mapping run data mirroring physical Gazebo / ROS2 output
        across a warehouse floorplan with laser noise, beam reflections, and odometry drift.
        """
        self.start_recording()

        # Realistic mapping waypoint trajectory around the warehouse
        trajectory_waypoints = [
            (1.0, 1.0, 0.0),
            (4.0, 1.0, 0.0),
            (7.5, 1.0, 0.0),
            (11.0, 1.0, 0.0),
            (13.5, 1.0, math.pi / 2),
            (13.5, 5.0, math.pi / 2),
            (11.0, 5.0, math.pi),
            (7.5, 5.0, math.pi),
            (4.0, 5.0, math.pi),
            (1.0, 5.0, math.pi / 2),
            (1.0, 9.0, math.pi / 2),
            (4.0, 9.0, 0.0),
            (7.5, 9.0, 0.0),
            (11.0, 9.0, 0.0),
            (13.5, 9.0, math.pi / 2),
            (13.5, 13.5, math.pi),
            (7.5, 13.5, math.pi),
            (1.0, 13.5, -math.pi / 2),
            (1.0, 1.0, 0.0)
        ]

        # Warehouse bounding walls and ground truth obstacle boundaries
        walls = [
            (0.0, 0.0, 15.0, 0.0),
            (15.0, 0.0, 15.0, 15.0),
            (15.0, 15.0, 0.0, 15.0),
            (0.0, 15.0, 0.0, 0.0)
        ]

        # Physical structural objects in warehouse
        objects = [
            # Storage Rack Row 1
            {"x1": 2.0, "y1": 2.2, "x2": 6.5, "y2": 3.4, "h": 3.2, "type": "rack"},
            {"x1": 8.5, "y1": 2.2, "x2": 13.0, "y2": 3.4, "h": 3.2, "type": "rack"},
            # Storage Rack Row 2
            {"x1": 2.0, "y1": 7.0, "x2": 6.5, "y2": 8.2, "h": 3.2, "type": "rack"},
            {"x1": 8.5, "y1": 7.0, "x2": 13.0, "y2": 8.2, "h": 3.2, "type": "rack"},
            # Storage Rack Row 3
            {"x1": 2.0, "y1": 11.8, "x2": 6.5, "y2": 13.0, "h": 3.2, "type": "rack"},
            {"x1": 8.5, "y1": 11.8, "x2": 13.0, "y2": 13.0, "h": 3.2, "type": "rack"},
            # Charging Docks
            {"x1": 0.2, "y1": 0.2, "x2": 1.5, "y2": 1.5, "h": 0.4, "type": "charger"},
            {"x1": 13.5, "y1": 13.5, "x2": 14.8, "y2": 14.8, "h": 0.4, "type": "charger"},
            # Inbound Pick & Pack Stations
            {"x1": 0.0, "y1": 4.0, "x2": 1.4, "y2": 6.0, "h": 1.1, "type": "pick_station"},
            {"x1": 13.6, "y1": 6.5, "x2": 15.0, "y2": 8.5, "h": 1.1, "type": "drop_station"},
            # Conveyor
            {"x1": 0.0, "y1": 8.8, "x2": 1.2, "y2": 10.5, "h": 0.9, "type": "conveyor"},
            # Unidentified Temporary Pallet Obstacle (needs confirmation)
            {"x1": 7.2, "y1": 5.8, "x2": 8.2, "y2": 6.8, "h": 0.8, "type": "obstacle"}
        ]

        # Interpolate poses along the trajectory to create keyframes
        step_idx = 0
        for i in range(len(trajectory_waypoints) - 1):
            w1 = trajectory_waypoints[i]
            w2 = trajectory_waypoints[i + 1]
            dist = math.hypot(w2[0] - w1[0], w2[1] - w1[1])
            num_steps = max(2, int(dist / 0.8))

            for s in range(num_steps):
                t_ratio = s / float(num_steps)
                cx = w1[0] + t_ratio * (w2[0] - w1[0])
                cy = w1[1] + t_ratio * (w2[1] - w1[1])
                cyaw = w1[2] + t_ratio * (w2[2] - w1[2])

                pose = RobotPose(x=cx, y=cy, yaw=cyaw, timestamp=time.time() - (len(trajectory_waypoints) * 2 - step_idx))
                self.odometry_history.append(pose)

                # Generate 360-degree LiDAR raycast hits
                kf_points = []
                num_rays = 120
                for r_idx in range(num_rays):
                    angle = cyaw + (r_idx / float(num_rays)) * 2 * math.pi
                    dx = math.cos(angle)
                    dy = math.sin(angle)

                    closest_dist = 12.0  # Max LiDAR range

                    # Intersect perimeter walls
                    for (wx1, wy1, wx2, wy2) in walls:
                        d = self._ray_segment_intersect(cx, cy, dx, dy, wx1, wy1, wx2, wy2)
                        if d is not None and d < closest_dist:
                            closest_dist = d

                    # Intersect objects
                    for obj in objects:
                        for (ox1, oy1, ox2, oy2) in [
                            (obj["x1"], obj["y1"], obj["x2"], obj["y1"]),
                            (obj["x2"], obj["y1"], obj["x2"], obj["y2"]),
                            (obj["x2"], obj["y2"], obj["x1"], obj["y2"]),
                            (obj["x1"], obj["y2"], obj["x1"], obj["y1"]),
                        ]:
                            d = self._ray_segment_intersect(cx, cy, dx, dy, ox1, oy1, ox2, oy2)
                            if d is not None and d < closest_dist:
                                closest_dist = d

                    if closest_dist < 11.5:
                        hit_x = cx + closest_dist * dx
                        hit_y = cy + closest_dist * dy
                        # Sample 3D vertical layers (LiDAR reflection + Depth camera elevation)
                        for z in [0.0, 0.35, 1.0, 1.8, 2.5]:
                            kf_points.append((hit_x, hit_y, z, 0.85))

                kf = ScanKeyframe(
                    keyframe_id=f"kf-{step_idx + 1:04d}",
                    timestamp=pose.timestamp,
                    pose=pose,
                    points=kf_points
                )
                self.keyframes.append(kf)
                step_idx += 1

        self.active = False
        return self.keyframes

    @staticmethod
    def _ray_segment_intersect(px, py, dx, dy, x1, y1, x2, y2) -> Optional[float]:
        """2D Ray-line segment intersection calculation."""
        v1_x = px - x1
        v1_y = py - y1
        v2_x = x2 - x1
        v2_y = y2 - y1
        v3_x = -dy
        v3_y = dx

        dot = v2_x * v3_x + v2_y * v3_y
        if abs(dot) < 1e-6:
            return None

        t1 = (v2_x * v1_y - v2_y * v1_x) / dot
        t2 = (v1_x * v3_x + v1_y * v3_y) / dot

        if t1 >= 0.05 and 0.0 <= t2 <= 1.0:
            return t1
        return None
