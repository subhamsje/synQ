"""
FLTX Autonomous Mobile Robot (AMR) Core Controller Node
Manages robot state transitions, battery dynamics, payload constraints, and Mecanum odometry.
"""
from typing import Dict, Any, Optional
import math
import time

class FLTXAmrCore:
    def __init__(self, robot_id: str = "FLTX-AMR-01"):
        self.robot_id = robot_id
        self.state = "IDLE"
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.omega = 0.0
        self.battery_soc = 100.0
        self.active_payload = "NONE"
        self.max_speed = 1.5  # m/s default bare chassis
        self.estop_active = False

    def attach_payload(self, payload_type: str):
        """Attaches modular payload and reconfigures kinematic constraints."""
        valid_payloads = {
            "SCISSOR_LIFT": {"max_speed": 0.8, "tare_kg": 18.5},
            "ROLLER_CONVEYOR": {"max_speed": 1.0, "tare_kg": 14.0},
            "TOTE_GRIPPER": {"max_speed": 1.2, "tare_kg": 10.0},
            "NONE": {"max_speed": 1.5, "tare_kg": 0.0}
        }
        if payload_type not in valid_payloads:
            raise ValueError(f"Unknown payload type: {payload_type}")
        
        self.active_payload = payload_type
        self.max_speed = valid_payloads[payload_type]["max_speed"]

    def set_estop(self, active: bool):
        self.estop_active = active
        if active:
            self.state = "ESTOP"
            self.vx = 0.0
            self.vy = 0.0
            self.omega = 0.0
        else:
            self.state = "IDLE"

    def apply_velocity(self, vx: float, vy: float, omega: float):
        if self.estop_active:
            return
        
        # Clamp velocity to payload-aware limits
        speed = math.sqrt(vx*vx + vy*vy)
        if speed > self.max_speed and speed > 0:
            scale = self.max_speed / speed
            vx *= scale
            vy *= scale

        self.vx = vx
        self.vy = vy
        self.omega = omega

        if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(omega) > 0.01:
            self.state = "NAVIGATING"
        else:
            self.state = "IDLE"

    def update_step(self, dt: float):
        """Integrates kinematics and updates battery consumption."""
        if self.estop_active or dt <= 0:
            return

        delta_x = (self.vx * math.cos(self.theta) - self.vy * math.sin(self.theta)) * dt
        delta_y = (self.vx * math.sin(self.theta) + self.vy * math.cos(self.theta)) * dt
        delta_theta = self.omega * dt

        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta

        # Battery drain model: idle = 0.01%/s, driving = 0.05%/s
        drain_rate = 0.05 if self.state == "NAVIGATING" else 0.01
        self.battery_soc = max(0.0, self.battery_soc - drain_rate * dt)

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "robot_id": self.robot_id,
            "state": self.state,
            "position": {"x": round(self.x, 3), "y": round(self.y, 3), "theta": round(self.theta, 3)},
            "velocity": {"vx": round(self.vx, 3), "vy": round(self.vy, 3), "omega": round(self.omega, 3)},
            "battery_soc": round(self.battery_soc, 1),
            "payload": self.active_payload,
            "max_speed": self.max_speed,
            "estop": self.estop_active
        }

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import BatteryState
    from std_msgs.msg import String, Bool
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

if ROS2_AVAILABLE:
    class FLTXAmrNode(Node):
        def __init__(self):
            super().__init__('fltx_amr_core_node')
            self.declare_parameter('robot_id', 'FLTX-AMR-01')
            self.declare_parameter('update_rate_hz', 20.0)

            robot_id = self.get_parameter('robot_id').value
            rate = self.get_parameter('update_rate_hz').value

            self.core = FLTXAmrCore(robot_id=robot_id)
            self.last_time = self.get_clock().now()

            # Subscriptions
            self.cmd_vel_sub = self.create_subscription(
                Twist, '/cmd_vel', self.cmd_vel_callback, 10
            )
            self.payload_sub = self.create_subscription(
                String, '/fltx/payload_attach', self.payload_callback, 10
            )
            self.estop_sub = self.create_subscription(
                Bool, '/fltx/estop', self.estop_callback, 10
            )

            # Publishers
            self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
            self.battery_pub = self.create_publisher(BatteryState, '/battery_state', 10)
            self.status_pub = self.create_publisher(String, '/fltx/amr_status', 10)

            self.timer = self.create_timer(1.0 / rate, self.timer_callback)
            self.get_logger().info(f"FLTX AMR Core Node initialized: {robot_id}")

        def cmd_vel_callback(self, msg: Twist):
            self.core.apply_velocity(msg.linear.x, msg.linear.y, msg.angular.z)

        def payload_callback(self, msg: String):
            try:
                self.core.attach_payload(msg.data.upper())
                self.get_logger().info(f"Payload updated: {self.core.active_payload} (Max speed: {self.core.max_speed} m/s)")
            except ValueError as e:
                self.get_logger().error(str(e))

        def estop_callback(self, msg: Bool):
            self.core.set_estop(msg.data)
            self.get_logger().warn(f"Emergency Stop active: {msg.data}")

        def timer_callback(self):
            now = self.get_clock().now()
            dt = (now - self.last_time).nanoseconds / 1e9
            self.last_time = now

            self.core.update_step(dt)

            # Publish Odometry
            odom = Odometry()
            odom.header.stamp = now.to_msg()
            odom.header.frame_id = 'odom'
            odom.child_frame_id = 'base_footprint'
            odom.pose.pose.position.x = self.core.x
            odom.pose.pose.position.y = self.core.y
            odom.pose.pose.orientation.z = math.sin(self.core.theta / 2.0)
            odom.pose.pose.orientation.w = math.cos(self.core.theta / 2.0)
            odom.twist.twist.linear.x = self.core.vx
            odom.twist.twist.linear.y = self.core.vy
            odom.twist.twist.angular.z = self.core.omega
            self.odom_pub.publish(odom)

            # Publish Battery State
            bat = BatteryState()
            bat.header.stamp = now.to_msg()
            bat.percentage = self.core.battery_soc / 100.0
            bat.voltage = 25.6
            self.battery_pub.publish(bat)

            # Publish Status JSON String
            status_msg = String()
            import json
            status_msg.data = json.dumps(self.core.get_telemetry())
            self.status_pub.publish(status_msg)

def main(args=None):
    if not ROS2_AVAILABLE:
        print("Error: rclpy not available on host. Run inside ROS 2 container.")
        return
    rclpy.init(args=args)
    node = FLTXAmrNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
