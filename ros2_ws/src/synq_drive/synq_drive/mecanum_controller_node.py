"""
synQ AMR Mecanum Controller ROS 2 Node
Subscribes to /cmd_vel, resolves kinematics, and interfaces with ros2_control or simulation.
Publishes /odom and broadcasts odom -> base_footprint TF.
"""
try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist, TransformStamped
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Float64MultiArray
    from tf2_ros import TransformBroadcaster
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

import math
from .kinematics import MecanumKinematics, Twist2D, WheelSpeeds

if ROS2_AVAILABLE:
    class MecanumControllerNode(Node):
        def __init__(self):
            super().__init__('synq_mecanum_controller')

            # Declare physical parameters
            self.declare_parameter('wheel_radius', 0.076)
            self.declare_parameter('half_wheelbase_x', 0.25)
            self.declare_parameter('half_track_y', 0.20)
            self.declare_parameter('odom_frame_id', 'odom')
            self.declare_parameter('base_frame_id', 'base_footprint')
            self.declare_parameter('publish_tf', True)

            wheel_r = self.get_parameter('wheel_radius').value
            lx = self.get_parameter('half_wheelbase_x').value
            ly = self.get_parameter('half_track_y').value
            self.odom_frame = self.get_parameter('odom_frame_id').value
            self.base_frame = self.get_parameter('base_frame_id').value
            self.publish_tf = self.get_parameter('publish_tf').value

            self.kinematics = MecanumKinematics(wheel_radius=wheel_r, half_wheelbase_x=lx, half_track_y=ly)

            # State tracking for odometry integration
            self.x = 0.0
            self.y = 0.0
            self.theta = 0.0
            self.last_time = self.get_clock().now()

            # Subscriptions
            self.cmd_vel_sub = self.create_subscription(
                Twist, '/cmd_vel', self.cmd_vel_callback, 10
            )
            self.joint_state_sub = self.create_subscription(
                JointState, '/joint_states', self.joint_state_callback, 10
            )

            # Publishers
            self.wheel_cmd_pub = self.create_publisher(
                Float64MultiArray, '/wheel_velocity_controller/commands', 10
            )
            self.odom_pub = self.create_publisher(
                Odometry, '/odom', 10
            )
            self.tf_broadcaster = TransformBroadcaster(self)

            self.get_logger().info(
                f"synQ Mecanum Controller Initialized [R={wheel_r}m, Lx={lx}m, Ly={ly}m]"
            )

        def cmd_vel_callback(self, msg: Twist):
            twist = Twist2D(vx=msg.linear.x, vy=msg.linear.y, omega=msg.angular.z)
            wheels = self.kinematics.inverse_kinematics(twist)

            # Order: [FL, FR, RL, RR]
            cmd_msg = Float64MultiArray()
            cmd_msg.data = [wheels.fl, wheels.fr, wheels.rl, wheels.rr]
            self.wheel_cmd_pub.publish(cmd_msg)

        def joint_state_callback(self, msg: JointState):
            current_time = self.get_clock().now()
            dt = (current_time - self.last_time).nanoseconds / 1e9
            if dt <= 0.0 or dt > 0.5:
                self.last_time = current_time
                return

            # Extract wheel speeds assuming names contain fl, fr, rl, rr
            speeds = {}
            for name, vel in zip(msg.name, msg.velocity):
                for key in ['wheel_fl_joint', 'wheel_fr_joint', 'wheel_rl_joint', 'wheel_rr_joint']:
                    if key in name:
                        speeds[key] = vel

            if len(speeds) < 4:
                return

            wheel_speeds = WheelSpeeds(
                fl=speeds.get('wheel_fl_joint', 0.0),
                fr=speeds.get('wheel_fr_joint', 0.0),
                rl=speeds.get('wheel_rl_joint', 0.0),
                rr=speeds.get('wheel_rr_joint', 0.0)
            )

            body_twist = self.kinematics.forward_kinematics(wheel_speeds)

            # Integrate in world frame
            delta_x = (body_twist.vx * math.cos(self.theta) - body_twist.vy * math.sin(self.theta)) * dt
            delta_y = (body_twist.vx * math.sin(self.theta) + body_twist.vy * math.cos(self.theta)) * dt
            delta_theta = body_twist.omega * dt

            self.x += delta_x
            self.y += delta_y
            self.theta += delta_theta
            self.last_time = current_time

            # Construct & publish Odometry message
            odom = Odometry()
            odom.header.stamp = current_time.to_msg()
            odom.header.frame_id = self.odom_frame
            odom.child_frame_id = self.base_frame

            odom.pose.pose.position.x = self.x
            odom.pose.pose.position.y = self.y
            odom.pose.pose.position.z = 0.0

            # Quaternion from yaw
            qz = math.sin(self.theta / 2.0)
            qw = math.cos(self.theta / 2.0)
            odom.pose.pose.orientation.z = qz
            odom.pose.pose.orientation.w = qw

            odom.twist.twist.linear.x = body_twist.vx
            odom.twist.twist.linear.y = body_twist.vy
            odom.twist.twist.angular.z = body_twist.omega

            self.odom_pub.publish(odom)

            if self.publish_tf:
                t = TransformStamped()
                t.header.stamp = current_time.to_msg()
                t.header.frame_id = self.odom_frame
                t.child_frame_id = self.base_frame
                t.transform.translation.x = self.x
                t.transform.translation.y = self.y
                t.transform.translation.z = 0.0
                t.transform.rotation.z = qz
                t.transform.rotation.w = qw
                self.tf_broadcaster.sendTransform(t)

def main(args=None):
    if not ROS2_AVAILABLE:
        print("Error: rclpy not installed in host environment. Run within ROS 2 container.")
        return
    rclpy.init(args=args)
    node = MecanumControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
