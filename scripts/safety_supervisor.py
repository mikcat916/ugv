#!/usr/bin/env python3
"""Safety supervisor for the Project4 autopilot MVP."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_CMD_TIMEOUT_SECONDS = 0.75
DEFAULT_LIDAR_TIMEOUT_SECONDS = 2.0
STOP_REASONS = {"front_blocked", "both_front_blocked", "lidar_timeout", "control_timeout", "estop"}


@dataclass
class SafetyDecision:
    safe: bool
    reason: str
    linear_x: float = 0.0
    angular_z: float = 0.0


def clamp(value: Any, limit: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        parsed = 0.0
    if not math.isfinite(parsed):
        parsed = 0.0
    return max(-abs(limit), min(abs(limit), parsed))


def obstacle_is_safe(status: dict[str, Any], now: float | None = None, lidar_timeout: float = DEFAULT_LIDAR_TIMEOUT_SECONDS) -> SafetyDecision:
    current = time.time() if now is None else float(now)
    obstacle_status = str(status.get("obstacleStatus") or status.get("obstacle_status") or "").strip()
    online = bool(status.get("online"))
    age = status.get("ageSeconds", status.get("age_seconds"))
    try:
        age_value = float(age)
    except (TypeError, ValueError):
        updated_at = status.get("updatedAt")
        try:
            age_value = current - float(updated_at)
        except (TypeError, ValueError):
            age_value = math.inf

    if not online or age_value > lidar_timeout:
        return SafetyDecision(False, "lidar_timeout")
    if obstacle_status in STOP_REASONS:
        return SafetyDecision(False, obstacle_status)
    return SafetyDecision(
        True,
        obstacle_status or "front_clear",
        float(status.get("linearX", status.get("linear_x", 0.0)) or 0.0),
        float(status.get("angularZ", status.get("angular_z", 0.0)) or 0.0),
    )


class SafetySupervisor:
    def __init__(
        self,
        publisher: Any,
        twist_factory: Any,
        *,
        cmd_timeout: float = DEFAULT_CMD_TIMEOUT_SECONDS,
        lidar_timeout: float = DEFAULT_LIDAR_TIMEOUT_SECONDS,
    ) -> None:
        self.publisher = publisher
        self.twist_factory = twist_factory
        self.cmd_timeout = cmd_timeout
        self.lidar_timeout = lidar_timeout
        self.last_obstacle: dict[str, Any] | None = None
        self.last_obstacle_at: float | None = None
        self.last_control_at: float | None = None
        self.last_reason = "startup"

    def on_obstacle_status(self, msg: Any) -> None:
        raw = getattr(msg, "data", msg)
        try:
            self.last_obstacle = json.loads(raw)
        except (TypeError, ValueError):
            self.last_obstacle = {"online": False, "obstacleStatus": "invalid_obstacle_status"}
        self.last_obstacle_at = time.time()

    def mark_control_command(self) -> None:
        self.last_control_at = time.time()

    def stop_twist(self) -> Any:
        twist = self.twist_factory()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        return twist

    def publish_stop(self, reason: str) -> None:
        self.last_reason = reason
        self.publisher.publish(self.stop_twist())

    def evaluate(self) -> SafetyDecision:
        now = time.time()
        if self.last_obstacle is None or self.last_obstacle_at is None:
            return SafetyDecision(False, "lidar_timeout")
        obstacle_status = dict(self.last_obstacle)
        obstacle_status["ageSeconds"] = now - self.last_obstacle_at
        obstacle_decision = obstacle_is_safe(obstacle_status, now=now, lidar_timeout=self.lidar_timeout)
        if not obstacle_decision.safe:
            return obstacle_decision
        if self.last_control_at is not None and now - self.last_control_at > self.cmd_timeout:
            return SafetyDecision(False, "control_timeout")
        return obstacle_decision

    def watchdog_tick(self) -> SafetyDecision:
        decision = self.evaluate()
        if not decision.safe:
            self.publish_stop(decision.reason)
        return decision


def main() -> None:
    import rospy
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String

    rospy.init_node("project4_safety_supervisor", anonymous=False)
    cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel")
    obstacle_topic = rospy.get_param("~obstacle_topic", "/autopilot/obstacle_status")
    cmd_timeout = float(rospy.get_param("~cmd_timeout", DEFAULT_CMD_TIMEOUT_SECONDS))
    lidar_timeout = float(rospy.get_param("~lidar_timeout", DEFAULT_LIDAR_TIMEOUT_SECONDS))
    publisher = rospy.Publisher(cmd_topic, Twist, queue_size=10)
    supervisor = SafetySupervisor(publisher, Twist, cmd_timeout=cmd_timeout, lidar_timeout=lidar_timeout)
    rospy.Subscriber(obstacle_topic, String, supervisor.on_obstacle_status, queue_size=10)
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        decision = supervisor.watchdog_tick()
        if not decision.safe:
            rospy.logwarn_throttle(1.0, "autopilot safety stop: %s", decision.reason)
        rate.sleep()


if __name__ == "__main__":
    main()
