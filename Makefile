.PHONY: all test build clean sim-docker help

PYTHON ?= python3
COLCON ?= colcon

all: test

help:
	@echo "synQ AMR Platform Build & Test Automation"
	@echo "  make test        - Run kinematics and unit test suites"
	@echo "  make build       - Build ROS 2 workspace using colcon"
	@echo "  make sim-docker  - Build and launch Gazebo simulation container"
	@echo "  make clean       - Remove temporary build artifacts and test caches"

test:
	$(PYTHON) -m pytest tests/unit/ -v

build:
	cd ros2_ws && $(COLCON) build --symlink-install

clean:
	rm -rf ros2_ws/build ros2_ws/install ros2_ws/log .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

sim-docker:
	docker compose up --build
