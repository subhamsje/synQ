.PHONY: all test test-kinematics test-sensors build clean sim-docker help

PYTHON ?= python3
COLCON ?= colcon

all: test

help:
	@echo "synQ AMR Platform Build & Test Automation"
	@echo "  make test             - Run all unit, kinematics, and sensor test suites"
	@echo "  make test-kinematics  - Run Mecanum kinematics test suite"
	@echo "  make test-sensors     - Run LiDAR, IMU, and TF test suite"
	@echo "  make build            - Build ROS 2 workspace using colcon"
	@echo "  make sim-docker       - Build and launch Gazebo simulation container"
	@echo "  make clean            - Remove temporary build artifacts and test caches"

test:
	$(PYTHON) -m pytest tests/ -v

test-kinematics:
	$(PYTHON) -m pytest tests/unit/ -v

test-sensors:
	$(PYTHON) -m pytest tests/ros2/ -v

build:
	cd ros2_ws && $(COLCON) build --symlink-install

clean:
	rm -rf ros2_ws/build ros2_ws/install ros2_ws/log .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

sim-docker:
	docker compose up --build
