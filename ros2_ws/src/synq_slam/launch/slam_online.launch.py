"""
synQ AMR Online Asynchronous 2D SLAM Launch Script
Executes SLAM Toolbox mapping and graph-based loop closure.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_slam = get_package_share_directory('synq_slam')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    slam_config_file = os.path.join(pkg_slam, 'config', 'slam_toolbox_async.yaml')

    node_slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_config_file, {'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        node_slam_toolbox
    ])
