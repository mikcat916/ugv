from __future__ import annotations

import importlib.util
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def scan(ranges, angle_min_deg=-90, angle_step_deg=10, range_min=0.1, range_max=10.0):
    return SimpleNamespace(
        ranges=ranges,
        angle_min=math.radians(angle_min_deg),
        angle_increment=math.radians(angle_step_deg),
        angle_max=math.radians(angle_min_deg + angle_step_deg * (len(ranges) - 1)),
        range_min=range_min,
        range_max=range_max,
    )


def test_lidar_filters_invalid_ranges():
    lidar = load_module("lidar_obstacle_test_filters", ROOT / "lidar_obstacle.py")

    assert lidar.finite_distance(float("inf"), 0.1, 10.0) is None
    assert lidar.finite_distance(float("nan"), 0.1, 10.0) is None
    assert lidar.finite_distance(0, 0.1, 10.0) is None
    assert lidar.finite_distance(0.05, 0.1, 10.0) is None
    assert lidar.finite_distance(11.0, 0.1, 10.0) is None
    assert lidar.finite_distance(1.2, 0.1, 10.0) == 1.2


def test_front_under_half_meter_stops():
    lidar = load_module("lidar_obstacle_test_front_stop", ROOT / "lidar_obstacle.py")
    ranges = [2.0] * 19
    ranges[9] = 0.4

    status = lidar.build_obstacle_status(scan(ranges))

    assert status["frontMin"] == 0.4
    assert status["obstacleStatus"] == "front_blocked"
    assert status["linearX"] == 0.0
    assert status["safe"] is False


def test_left_near_right_far_turns_right():
    lidar = load_module("lidar_obstacle_test_avoid", ROOT / "lidar_obstacle.py")
    ranges = [2.0] * 19
    ranges[12] = 0.55

    status = lidar.build_obstacle_status(scan(ranges))

    assert status["leftFrontMin"] == 0.55
    assert status["obstacleStatus"] == "avoid_right"
    assert status["angularZ"] < 0
    assert status["safe"] is True


def test_lidar_timeout_status_stops():
    lidar = load_module("lidar_obstacle_test_timeout", ROOT / "lidar_obstacle.py")

    status = lidar.timeout_status(last_seen=10.0, now=12.5)

    assert status["online"] is False
    assert status["ageSeconds"] == 2.5
    assert status["linearX"] == 0.0
    assert status["obstacleStatus"] == "lidar_timeout"


def test_autopilot_node_clamps_safe_forward_speed():
    node = load_module("autopilot_node_test_clamp", ROOT / "autopilot_node.py")

    assert node.clamp_linear(9.0) == 0.1
    assert node.clamp_linear(0.02) == 0.02
    assert node.clamp_linear(0.0) == 0.0
    assert node.obstacle_safe({"online": True, "frontMin": 1.2, "obstacleStatus": "front_clear"}) is True
    assert node.obstacle_safe({"online": True, "frontMin": 0.4, "obstacleStatus": "front_blocked"}) is False


def test_autopilot_node_does_not_block_on_slow_backend():
    autopilot = load_module("autopilot_node_test_nonblocking", ROOT / "autopilot_node.py")

    class Publisher:
        def __init__(self):
            self.messages = []

        def publish(self, msg):
            self.messages.append(msg)

    class Twist:
        def __init__(self):
            self.linear = SimpleNamespace(x=0.0)
            self.angular = SimpleNamespace(z=0.0)

    class SlowBackend:
        def __init__(self):
            self.config = SimpleNamespace(robot_id=7)
            self.polls = 0
            self.reports = 0

        def get_status(self):
            time.sleep(0.2)
            self.polls += 1
            return {"mode": "manual", "estop": False, "manualOverride": False}

        def report_status(self, payload):
            time.sleep(0.2)
            self.reports += 1
            return {"ok": True}

    backend = SlowBackend()
    node = autopilot.AutopilotNode(Publisher(), Twist, backend)

    started = time.monotonic()
    _linear, _angular, safe, reason = node.tick()

    assert time.monotonic() - started < 0.1
    assert safe is False
    assert reason == "manual"
    time.sleep(0.35)
    assert backend.polls == 1
    assert backend.reports == 1
