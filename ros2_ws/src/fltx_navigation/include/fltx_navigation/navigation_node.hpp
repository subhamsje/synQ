#ifndef FLTX_NAVIGATION_NODE_HPP_
#define FLTX_NAVIGATION_NODE_HPP_

#include <memory>
#include <string>
#include <vector>
#include <cmath>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "std_msgs/msg/string.hpp"

namespace fltx {

enum class NavState {
    IDLE,
    NAVIGATING,
    OBSTACLE_DETECTED,
    GOAL_REACHED
};

class FLTXNavigationNode : public rclcpp::Node {
public:
    explicit FLTXNavigationNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
    virtual ~FLTXNavigationNode() = default;

private:
    void onGoalPose(const geometry_msgs::msg::PoseStamped::SharedPtr msg);
    void onOdometry(const nav_msgs::msg::Odometry::SharedPtr msg);
    void onLaserScan(const sensor_msgs::msg::LaserScan::SharedPtr msg);
    void controlLoop();

    bool checkObstacleCollision();
    void stopRobot();

    // Node Parameters
    double max_linear_speed_{1.0};
    double max_angular_speed_{1.0};
    double goal_tolerance_m_{0.05};
    double obstacle_safety_distance_{0.45}; // meters

    // Runtime State
    NavState state_{NavState::IDLE};
    double current_x_{0.0};
    double current_y_{0.0};
    double current_yaw_{0.0};
    double target_x_{0.0};
    double target_y_{0.0};
    double target_yaw_{0.0};
    bool has_active_goal_{false};
    bool obstacle_in_front_{false};

    sensor_msgs::msg::LaserScan latest_scan_;
    bool has_scan_{false};

    // ROS 2 Interfaces
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr sub_goal_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_odom_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr sub_scan_;

    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_cmd_vel_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_status_;

    rclcpp::TimerBase::SharedPtr timer_control_;
};

} // namespace fltx

#endif // FLTX_NAVIGATION_NODE_HPP_
