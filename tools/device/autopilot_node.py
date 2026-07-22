#!/usr/bin/env python3
"""Autopilot main loop for the Project4 MVP."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any


DEFAULT_LINEAR = 0.1
MAX_LINEAR = 0.1
MAX_ANGULAR = 0.6
BACKEND_TIMEOUT = 8.0
STATUS_POLL_SECONDS = 1.0
REPORT_SECONDS = 1.0
STOP_REASONS = {"front_blocked", "both_front_blocked", "lidar_timeout", "control_timeout", "estop"}


@dataclass
class BackendConfig:
    server: str
    token: str
    robot_id: int | None
    timeout: float


def clamp(value: Any, limit: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        parsed = 0.0
    if not math.isfinite(parsed):
        parsed = 0.0
    return max(-abs(limit), min(abs(limit), parsed))


def clamp_linear(value: Any) -> float:
    parsed = clamp(value, MAX_LINEAR)
    if parsed <= 0:
        return 0.0
    return min(MAX_LINEAR, parsed)


def obstacle_safe(status: dict[str, Any]) -> bool:
    if not status or not status.get("online"):
        return False
    obstacle_status = str(status.get("obstacleStatus") or "").strip()
    if obstacle_status in STOP_REASONS:
        return False
    try:
        front = float(status.get("frontMin"))
    except (TypeError, ValueError):
        return False
    return math.isfinite(front) and front >= 0.5


def action_reason(obstacle: dict[str, Any], backend_status: dict[str, Any]) -> str:
    if backend_status.get("estop"):
        return "estop"
    if backend_status.get("manualOverride"):
        return "manual_override"
    if not obstacle:
        return "lidar_timeout"
    return str(obstacle.get("obstacleStatus") or backend_status.get("reason") or "front_clear")


def env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class BackendClient:
    def __init__(self, config: BackendConfig) -> None:
        self.config = config

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.config.server.rstrip('/')}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if self.config.token:
            headers["X-Device-Token"] = self.config.token
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_status(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/autopilot/status?limit=1")

    def report_status(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.config.token:
            return None
        return self._request_json("POST", "/api/iot/autopilot/status", payload)


class AutopilotNode:
    def __init__(self, publisher: Any, twist_factory: Any, backend: BackendClient, *, dry_run: bool = False) -> None:
        self.publisher = publisher
        self.twist_factory = twist_factory
        self.backend = backend
        self.dry_run = dry_run
        self.lock = Lock()
        self.backend_status: dict[str, Any] = {"mode": "manual", "estop": False, "manualOverride": False}
        self.obstacle_status: dict[str, Any] = {}
        self.safety_status: dict[str, Any] = {}
        self.last_backend_poll = 0.0
        self.last_report = 0.0
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.last_reason = "startup"
        self.poll_inflight = False
        self.report_inflight = False

    def on_obstacle_status(self, msg: Any) -> None:
        raw = getattr(msg, "data", msg)
        try:
            status = json.loads(raw)
        except (TypeError, ValueError):
            status = {"online": False, "obstacleStatus": "invalid_obstacle_status"}
        with self.lock:
            self.obstacle_status = status

    def on_safety_status(self, msg: Any) -> None:
        raw = getattr(msg, "data", msg)
        try:
            status = json.loads(raw)
        except (TypeError, ValueError):
            status = {"safe": False, "reason": "invalid_safety_status"}
        with self.lock:
            self.safety_status = status

    def make_twist(self, linear: float, angular: float) -> Any:
        twist = self.twist_factory()
        twist.linear.x = float(linear)
        twist.angular.z = float(angular)
        return twist

    def publish_velocity(self, linear: float, angular: float) -> None:
        with self.lock:
            self.last_linear = float(linear)
            self.last_angular = float(angular)
        if self.dry_run:
            print(json.dumps({"type": "autopilot_dry_run", "linearX": float(linear), "angularZ": float(angular)}, ensure_ascii=False))
            return
        self.publisher.publish(self.make_twist(linear, angular))

    def stop(self, reason: str) -> None:
        self.last_reason = reason
        self.publish_velocity(0.0, 0.0)

    def poll_backend(self) -> None:
        now = time.time()
        with self.lock:
            if self.poll_inflight or now - self.last_backend_poll < STATUS_POLL_SECONDS:
                return
            self.last_backend_poll = now
            self.poll_inflight = True

        def worker() -> None:
            try:
                status = self.backend.get_status()
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                status = {"mode": "fault", "safe": False, "reason": "backend_unreachable"}
            with self.lock:
                self.backend_status = status
                self.poll_inflight = False

        Thread(target=worker, daemon=True).start()

    def snapshot_inputs(self) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.lock:
            return dict(self.backend_status), dict(self.obstacle_status)

    def decide(self) -> tuple[float, float, bool, str]:
        backend_status, obstacle_status = self.snapshot_inputs()
        mode = str(backend_status.get("mode") or "manual")
        if backend_status.get("estop") or mode == "estop":
            return 0.0, 0.0, False, "estop"
        if backend_status.get("manualOverride"):
            return 0.0, 0.0, False, "manual_override"
        if mode != "auto_running":
            return 0.0, 0.0, False, mode
        if not obstacle_safe(obstacle_status):
            return 0.0, 0.0, False, action_reason(obstacle_status, backend_status)
        linear = clamp_linear(obstacle_status.get("linearX", DEFAULT_LINEAR))
        angular = clamp(obstacle_status.get("angularZ", 0.0), MAX_ANGULAR)
        return linear, angular, True, action_reason(obstacle_status, backend_status)

    def maybe_report(self, safe: bool, reason: str) -> None:
        now = time.time()
        with self.lock:
            if self.report_inflight or now - self.last_report < REPORT_SECONDS:
                return
            self.last_report = now
            self.report_inflight = True
            backend_status = dict(self.backend_status)
            obstacle_status = dict(self.obstacle_status)
            safety_status = dict(self.safety_status)
            last_linear = self.last_linear
            last_angular = self.last_angular
        if safety_status:
            safety_status["autopilotDryRun"] = self.dry_run
        else:
            safety_status = {
                "dryRun": self.dry_run,
                "safe": safe,
                "reason": reason,
                "rawCmd": {"linearX": last_linear, "angularZ": last_angular},
                "finalCmd": {"linearX": last_linear if not self.dry_run else 0.0, "angularZ": last_angular if not self.dry_run else 0.0},
            }
        payload = {
            "robotId": self.backend.config.robot_id,
            "mode": backend_status.get("mode", "manual"),
            "safe": safe,
            "reason": reason,
            "linearX": last_linear,
            "angularZ": last_angular,
            "manualOverride": bool(backend_status.get("manualOverride")),
            "estop": bool(backend_status.get("estop")),
            "lidar": obstacle_status or {"online": False, "obstacleStatus": "lidar_timeout"},
            "safety": safety_status,
        }

        def worker() -> None:
            try:
                self.backend.report_status(payload)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                pass
            finally:
                with self.lock:
                    self.report_inflight = False

        Thread(target=worker, daemon=True).start()

    def tick(self) -> tuple[float, float, bool, str]:
        self.poll_backend()
        linear, angular, safe, reason = self.decide()
        if safe:
            self.last_reason = reason
            self.publish_velocity(linear, angular)
        else:
            self.stop(reason)
        self.maybe_report(safe, reason)
        return linear, angular, safe, reason


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project4 autopilot node.")
    parser.add_argument("--server", default=os.getenv("PROJECT4_AUTOPILOT_SERVER", "http://127.0.0.1:8000"), help="Backend server URL.")
    parser.add_argument("--token", default=os.getenv("PROJECT4_AUTOPILOT_TOKEN", ""), help="Device token for /api/iot/autopilot/status reports.")
    parser.add_argument("--robot-id", type=int, default=int(os.getenv("PROJECT4_AUTOPILOT_ROBOT_ID", "0") or "0"), help="Robot ID to include in reports.")
    parser.add_argument("--obstacle-topic", default="/autopilot/obstacle_status", help="Obstacle JSON topic.")
    parser.add_argument("--safety-topic", default="/autopilot/safety_status", help="Safety supervisor JSON topic.")
    parser.add_argument("--cmd-topic", default="/autopilot/cmd_vel_raw", help="Raw velocity command topic for safety supervision.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_bool("PROJECT4_AUTOPILOT_DRY_RUN"),
        help="Print decisions without publishing raw velocity commands.",
    )
    parser.add_argument("--rate", type=float, default=10.0, help="Main loop frequency.")
    return parser.parse_args()


def main() -> None:
    import rospy
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String

    args = parse_args()
    rospy.init_node("project4_autopilot_node", anonymous=False)
    backend = BackendClient(
        BackendConfig(
            server=args.server,
            token=args.token,
            robot_id=args.robot_id or None,
            timeout=BACKEND_TIMEOUT,
        )
    )
    publisher = rospy.Publisher(args.cmd_topic, Twist, queue_size=10)
    node = AutopilotNode(publisher, Twist, backend, dry_run=args.dry_run)
    rospy.Subscriber(args.obstacle_topic, String, node.on_obstacle_status, queue_size=10)
    rospy.Subscriber(args.safety_topic, String, node.on_safety_status, queue_size=10)
    rate = rospy.Rate(max(args.rate, 1.0))
    while not rospy.is_shutdown():
        _linear, _angular, safe, reason = node.tick()
        if not safe:
            rospy.logwarn_throttle(1.0, "autopilot stop: %s", reason)
        rate.sleep()


if __name__ == "__main__":
    main()
