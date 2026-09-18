#include "fltx_navigation/navigation_node.hpp"

namespace fltx {

FLTXNavigationNode::FLTXNavigationNode(const rclcpp::NodeOptions & options)
: Node("fltx_navigation_node", options) {
    this->declare_parameter("max_linear_speed", 1.0);
    this->declare_parameter("max_angular_speed", 1.0);
    this->declare_parameter("goal_tolerance_m", 0.05);
    this->declare_parameter("obstacle_safety_distance", 0.45);

    max_linear_speed_ = this->get_parameter("max_linear_speed").as_double();
    max_angular_speed_ = this->get_parameter("max_angular_speed").as_double();
    goal_tolerance_m_ = this->get_parameter("goal_tolerance_m").as_double();
    obstacle_safety_distance_ = this->get_parameter("obstacle_safety_distance").as_double();

    // Subscriptions
    sub_goal_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
        "/goal_pose", 10,
        std::bind(&FLTXNavigationNode::onGoalPose, this, std::placeholders::_1)
    );

    sub_odom_ = this->create_subscription<nav_msgs::msg::Odometry>(
        "/odom", 10,
        std::bind(&FLTXNavigationNode::onOdometry, this, std::placeholders::_1)
    );

    sub_scan_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
        "/sensors/lidar/scan", 10,
        std::bind(&FLTXNavigationNode::onLaserScan, this, std::placeholders::_1)
    );

    // Publishers
    pub_cmd_vel_ = this->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
    pub_status_ = this->create_publisher<std_msgs::msg::String>("/fltx/nav_status", 10);

    // 20 Hz Control Loop
    timer_control_ = this->create_wall_timer(
        std::chrono::milliseconds(50),
        std::bind(&FLTXNavigationNode::controlLoop, this)
    );

    RCLCPP_INFO(this->get_logger(), "FLTX C++ Navigation Node Initialized. Ready for goals.");
}

void FLTXNavigationNode::onGoalPose(const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
    target_x_ = msg->pose.position.x;
    target_y_ = msg->pose.position.y;

    // Convert quaternion to yaw
    double qz = msg->pose.orientation.z;
    double qw = msg->pose.orientation.w;
    target_yaw_ = 2.0 * std::atan2(qz, qw);

    has_active_goal_ = true;
    state_ = NavState::NAVIGATING;

    RCLCPP_INFO(this->get_logger(), "New navigation goal received: (X=%.2f, Y=%.2f, Yaw=%.2f rad)",
                target_x_, target_y_, target_yaw_);
}

void FLTXNavigationNode::onOdometry(const nav_msgs::msg::Odometry::SharedPtr msg) {
    current_x_ = msg->pose.pose.position.x;
    current_y_ = msg->pose.pose.position.y;

    double qz = msg->pose.pose.orientation.z;
    double qw = msg->pose.pose.orientation.w;
    current_yaw_ = 2.0 * std::atan2(qz, qw);
}

void FLTXNavigationNode::onLaserScan(const sensor_msgs::msg::LaserScan::SharedPtr msg) {
    latest_scan_ = *msg;
    has_scan_ = true;
    obstacle_in_front_ = checkObstacleCollision();
}

bool FLTXNavigationNode::checkObstacleCollision() {
    if (!has_scan_ || latest_scan_.ranges.empty()) {
        return false;
    }

    // Check front sector: -45 deg to +45 deg
    double angle = latest_scan_.angle_min;
    for (size_t i = 0; i < latest_scan_.ranges.size(); ++i, angle += latest_scan_.angle_increment) {
        if (angle >= -0.785398 && angle <= 0.785398) {
            double r = latest_scan_.ranges[i];
            if (r > 0.05 && r < obstacle_safety_distance_) {
                return true; // Obstacle inside safety zone
            }
        }
    }
    return false;
}

void FLTXNavigationNode::stopRobot() {
    geometry_msgs::msg::Twist stop_twist;
    stop_twist.linear.x = 0.0;
    stop_twist.linear.y = 0.0;
    stop_twist.angular.z = 0.0;
    pub_cmd_vel_->publish(stop_twist);
}

void FLTXNavigationNode::controlLoop() {
    std_msgs::msg::String status_msg;

    if (!has_active_goal_) {
        state_ = NavState::IDLE;
        status_msg.data = "IDLE";
        pub_status_->publish(status_msg);
        return;
    }

    if (obstacle_in_front_) {
        state_ = NavState::OBSTACLE_DETECTED;
        stopRobot();
        status_msg.data = "OBSTACLE_DETECTED";
        pub_status_->publish(status_msg);
        RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 1000,
                             "Navigation paused: obstacle detected in front clearance zone.");
        return;
    }

    // Position error in global frame
    double dx_global = target_x_ - current_x_;
    double dy_global = target_y_ - current_y_;
    double distance = std::sqrt(dx_global * dx_global + dy_global * dy_global);

    if (distance < goal_tolerance_m_) {
        // Position reached; align orientation
        double yaw_error = target_yaw_ - current_yaw_;
        while (yaw_error > M_PI) yaw_error -= 2.0 * M_PI;
        while (yaw_error < -M_PI) yaw_error += 2.0 * M_PI;

        if (std::abs(yaw_error) < 0.05) {
            has_active_goal_ = false;
            state_ = NavState::GOAL_REACHED;
            stopRobot();
            status_msg.data = "GOAL_REACHED";
            pub_status_->publish(status_msg);
            RCLCPP_INFO(this->get_logger(), "Navigation goal successfully reached.");
            return;
        }

        // Align yaw in place
        geometry_msgs::msg::Twist cmd;
        cmd.angular.z = std::clamp(1.5 * yaw_error, -max_angular_speed_, max_angular_speed_);
        pub_cmd_vel_->publish(cmd);
        status_msg.data = "ALIGNING_ORIENTATION";
        pub_status_->publish(status_msg);
        return;
    }

    // Transform translation error into robot local frame for holonomic Mecanum driving
    double cos_yaw = std::cos(current_yaw_);
    double sin_yaw = std::sin(current_yaw_);

    double dx_robot =  cos_yaw * dx_global + sin_yaw * dy_global;
    double dy_robot = -sin_yaw * dx_global + cos_yaw * dy_global;

    // Proportional control
    double kp = 1.2;
    double cmd_vx = kp * dx_robot;
    double cmd_vy = kp * dy_robot;

    // Clamp to max velocity
    double speed = std::sqrt(cmd_vx * cmd_vx + cmd_vy * cmd_vy);
    if (speed > max_linear_speed_) {
        double scale = max_linear_speed_ / speed;
        cmd_vx *= scale;
        cmd_vy *= scale;
    }

    // Heading towards movement direction
    double heading_error = std::atan2(dy_global, dx_global) - current_yaw_;
    while (heading_error > M_PI) heading_error -= 2.0 * M_PI;
    while (heading_error < -M_PI) heading_error += 2.0 * M_PI;
    double cmd_omega = std::clamp(1.0 * heading_error, -max_angular_speed_, max_angular_speed_);

    geometry_msgs::msg::Twist cmd;
    cmd.linear.x = cmd_vx;
    cmd.linear.y = cmd_vy;
    cmd.angular.z = cmd_omega;
    pub_cmd_vel_->publish(cmd);

    status_msg.data = "NAVIGATING";
    pub_status_->publish(status_msg);
}

} // namespace fltx

int main(int argc, char ** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<fltx::FLTXNavigationNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
