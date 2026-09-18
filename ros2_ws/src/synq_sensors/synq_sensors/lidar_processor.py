"""
synQ AMR LiDAR Data Preprocessor & Health Supervisor
Cleans raw laser scan data, filters chassis self-reflection artifacts, and monitors sensor dropouts.
"""
from typing import List, Tuple, Optional
import math
import time

class LidarFilter:
    def __init__(self, min_valid_range: float = 0.12, max_valid_range: float = 25.0, timeout_sec: float = 0.25):
        self.min_range = min_valid_range
        self.max_range = max_valid_range
        self.timeout_sec = timeout_sec
        self.last_scan_time: Optional[float] = None

    def filter_ranges(self, raw_ranges: List[float]) -> Tuple[List[float], dict]:
        """
        Cleans scan ranges. Returns filtered ranges and metrics dictionary.
        """
        self.last_scan_time = time.time()
        filtered = []
        valid_count = 0
        min_detected = float('inf')

        for r in raw_ranges:
            if math.isnan(r) or math.isinf(r):
                filtered.append(float('inf'))
            elif r < self.min_range:
                # Self-chassis reflection or blind zone: mark as invalid
                filtered.append(float('inf'))
            elif r > self.max_range:
                filtered.append(float('inf'))
            else:
                filtered.append(r)
                valid_count += 1
                if r < min_detected:
                    min_detected = r

        stats = {
            "total_points": len(raw_ranges),
            "valid_points": valid_count,
            "valid_ratio": valid_count / len(raw_ranges) if raw_ranges else 0.0,
            "min_distance_m": min_detected if min_detected != float('inf') else None,
            "healthy": valid_count > 0
        }
        return filtered, stats

    def is_timed_out(self, current_time: Optional[float] = None) -> bool:
        if self.last_scan_time is None:
            return True
        now = current_time if current_time is not None else time.time()
        return (now - self.last_scan_time) > self.timeout_sec

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import Bool
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

if ROS2_AVAILABLE:
    class LidarProcessorNode(Node):
        def __init__(self):
            super().__init__('synq_lidar_processor')
            self.declare_parameter('min_range', 0.12)
            self.declare_parameter('max_range', 25.0)
            self.declare_parameter('frame_id', 'lidar_link')

            min_r = self.get_parameter('min_range').value
            max_r = self.get_parameter('max_range').value
            self.frame_id = self.get_parameter('frame_id').value

            self.filter = LidarFilter(min_valid_range=min_r, max_valid_range=max_r)

            self.sub = self.create_subscription(
                LaserScan, '/sensors/lidar/scan_raw', self.scan_callback, 10
            )
            self.pub = self.create_publisher(
                LaserScan, '/sensors/lidar/scan', 10
            )
            self.health_pub = self.create_publisher(
                Bool, '/sensors/lidar/healthy', 10
            )

            # Watchdog timer at 10 Hz
            self.timer = self.create_timer(0.1, self.watchdog_check)
            self.get_logger().info("synQ LiDAR Processor Initialized")

        def scan_callback(self, msg: LaserScan):
            filtered_ranges, stats = self.filter.filter_ranges(list(msg.ranges))
            
            clean_msg = LaserScan()
            clean_msg.header = msg.header
            clean_msg.header.frame_id = self.frame_id
            clean_msg.angle_min = msg.angle_min
            clean_msg.angle_max = msg.angle_max
            clean_msg.angle_increment = msg.angle_increment
            clean_msg.time_increment = msg.time_increment
            clean_msg.scan_time = msg.scan_time
            clean_msg.range_min = self.filter.min_range
            clean_msg.range_max = self.filter.max_range
            clean_msg.ranges = filtered_ranges

            self.pub.publish(clean_msg)

            health_msg = Bool()
            health_msg.data = stats["healthy"]
            self.health_pub.publish(health_msg)

        def watchdog_check(self):
            if self.filter.is_timed_out():
                health_msg = Bool()
                health_msg.data = False
                self.health_pub.publish(health_msg)

def main(args=None):
    if not ROS2_AVAILABLE:
        print("rclpy not available; run inside ROS 2 container.")
        return
    rclpy.init(args=args)
    node = LidarProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
