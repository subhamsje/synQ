# synQ Autonomous Mobile Robot Platform
# ROS 2 Jazzy + Gazebo Sim Harmonic Development Container
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive

# Install Gazebo Harmonic integration, ros2_control, Nav2, and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-controller-manager \
    ros-jazzy-joint-state-broadcaster \
    ros-jazzy-velocity-controllers \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-xacro \
    python3-colcon-common-extensions \
    python3-pip \
    python3-pytest \
    git \
    curl \
    tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Source ROS 2 environment in bashrc
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc

CMD ["/bin/bash"]
