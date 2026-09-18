"""
synQ AMR Localization Launch Script
Launches robot_localization EKF (wheel odom + IMU fusion) and Nav2 AMCL.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_localization = get_package_share_directory('synq_localization')
    
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_yaml_file = LaunchConfiguration('map', default=os.path.join(
        get_package_share_directory('synq_simulation'), 'maps', 'warehouse_map.yaml'
    ))

    ekf_config_file = os.path.join(pkg_localization, 'config', 'ekf.yaml')
    amcl_config_file = os.path.join(pkg_localization, 'config', 'amcl.yaml')

    # robot_localization EKF Node
    node_ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_file, {'use_sim_time': use_sim_time}]
    )

    # Nav2 Map Server
    node_map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_yaml_file}, {'use_sim_time': use_sim_time}]
    )

    # Nav2 AMCL Node
    node_amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[amcl_config_file, {'use_sim_time': use_sim_time}]
    )

    # Nav2 Lifecycle Manager
    node_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server', 'amcl']
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('map', default_value=map_yaml_file),
        node_ekf,
        node_map_server,
        node_amcl,
        node_lifecycle_manager
    ])
