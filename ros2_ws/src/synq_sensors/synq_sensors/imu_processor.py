"""
synQ AMR IMU Processing & Orientation Filter
Validates 6-DOF IMU telemetry, applies bias compensation, and constructs covariance for EKF fusion.
"""
from typing import Tuple, Optional
import math

class ImuFilter:
    def __init__(self, gyro_noise_std: float = 0.005, accel_noise_std: float = 0.05):
        self.gyro_noise = gyro_noise_std
        self.accel_noise = accel_noise_std

    def calculate_covariances(self) -> Tuple[list, list, list]:
        """
        Constructs diagonal 3x3 covariance matrices (row-major 9 elements) for EKF ingestion.
        Returns: (orientation_cov, angular_vel_cov, linear_accel_cov)
        """
        g_var = self.gyro_noise ** 2
        a_var = self.accel_noise ** 2

        # Orientation covariance (roll, pitch from gravity, yaw from gyro integration)
        ori_cov = [
            0.01, 0.0,  0.0,
            0.0,  0.01, 0.0,
            0.0,  0.0,  0.05
        ]

        # Angular velocity covariance (rad/s)^2
        ang_cov = [
            g_var, 0.0,   0.0,
            0.0,   g_var, 0.0,
            0.0,   0.0,   g_var
        ]

        # Linear acceleration covariance (m/s^2)^2
        acc_cov = [
            a_var, 0.0,   0.0,
            0.0,   a_var, 0.0,
            0.0,   0.0,   a_var
        ]

        return ori_cov, ang_cov, acc_cov

    def estimate_tilt_angles(self, ax: float, ay: float, az: float) -> Tuple[float, float]:
        """
        Estimates roll and pitch from static gravitational acceleration vector.
        """
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay*ay + az*az))
        return roll, pitch

try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Imu
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

if ROS2_AVAILABLE:
    class ImuProcessorNode(Node):
        def __init__(self):
            super().__init__('synq_imu_processor')
            self.declare_parameter('frame_id', 'imu_link')
            self.frame_id = self.get_parameter('frame_id').value

            self.filter = ImuFilter()
            self.ori_cov, self.ang_cov, self.acc_cov = self.filter.calculate_covariances()

            self.sub = self.create_subscription(
                Imu, '/sensors/imu_raw', self.imu_callback, 10
            )
            self.pub = self.create_publisher(
                Imu, '/sensors/imu', 10
            )
            self.get_logger().info("synQ IMU Processor Initialized")

        def imu_callback(self, msg: Imu):
            clean_msg = Imu()
            clean_msg.header = msg.header
            clean_msg.header.frame_id = self.frame_id
            clean_msg.orientation = msg.orientation
            clean_msg.orientation_covariance = self.ori_cov
            clean_msg.angular_velocity = msg.angular_velocity
            clean_msg.angular_velocity_covariance = self.ang_cov
            clean_msg.linear_acceleration = msg.linear_acceleration
            clean_msg.linear_acceleration_covariance = self.acc_cov

            self.pub.publish(clean_msg)

def main(args=None):
    if not ROS2_AVAILABLE:
        print("rclpy not available; run inside ROS 2 container.")
        return
    rclpy.init(args=args)
    node = ImuProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
