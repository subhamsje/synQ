"""
synQ AMR Gazebo Sim & ROS 2 Control Launch Script
Spawns synQ-AMR into Gazebo Harmonic and brings up the Mecanum kinematic control stack.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_description = get_package_share_directory('synq_description')
    pkg_bringup = get_package_share_directory('synq_bringup')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Path to Xacro URDF
    xacro_file = os.path.join(pkg_description, 'urdf', 'synq_amr.urdf.xacro')
    robot_description_content = Command(['xacro ', xacro_file])

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': use_sim_time
        }]
    )

    # Gazebo Sim Launcher
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # Spawn AMR in Gazebo
    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'synq_amr', '-z', '0.1']
    )

    # ros2_control Spawners
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager']
    )

    wheel_velocity_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['wheel_velocity_controller', '--controller-manager', '/controller_manager']
    )

    # synQ Mecanum Controller Node (bridges /cmd_vel to wheel_velocity_controller)
    mecanum_controller_node = Node(
        package='synq_drive',
        executable='mecanum_controller',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true', description='Use simulation time'),
        node_robot_state_publisher,
        gz_sim,
        gz_spawn_entity,
        joint_state_broadcaster_spawner,
        wheel_velocity_controller_spawner,
        mecanum_controller_node
    ])
