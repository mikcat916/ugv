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
DEFAULT_LOG_WINDOW_SECONDS = 30.0
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


def finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def bool_param(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def iso_from_epoch(value: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() if value is None else value))


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
    front_min = finite_float(status.get("frontMin", status.get("front_min")))
    if front_min is None or front_min < 0.5:
        return SafetyDecision(False, "front_blocked")
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
        dry_run: bool = False,
        log_window_seconds: float = DEFAULT_LOG_WINDOW_SECONDS,
        safety_publisher: Any | None = None,
    ) -> None:
        self.publisher = publisher
        self.twist_factory = twist_factory
        self.cmd_timeout = cmd_timeout
        self.lidar_timeout = lidar_timeout
        self.dry_run = dry_run
        self.log_window_seconds = max(1.0, float(log_window_seconds))
        self.safety_publisher = safety_publisher
        self.last_obstacle: dict[str, Any] | None = None
        self.last_obstacle_at: float | None = None
        self.last_control_at: float | None = None
        self.last_raw_cmd_at: float | None = None
        self.last_final_cmd_at: float | None = None
        self.last_raw_cmd = {"linearX": 0.0, "angularZ": 0.0}
        self.last_final_cmd = {"linearX": 0.0, "angularZ": 0.0}
        self.cmd_vel_log: list[dict[str, Any]] = []
        self.obstacle_status_log: list[dict[str, Any]] = []
        self.last_reason = "startup"

    def on_obstacle_status(self, msg: Any) -> None:
        raw = getattr(msg, "data", msg)
        try:
            self.last_obstacle = json.loads(raw)
        except (TypeError, ValueError):
            self.last_obstacle = {"online": False, "obstacleStatus": "invalid_obstacle_status"}
        self.last_obstacle_at = time.time()
        self.record_obstacle_status(self.last_obstacle, self.last_obstacle_at)
        self.publish_safety_status(self.evaluate())

    def mark_control_command(self) -> None:
        self.last_control_at = time.time()

    def on_raw_cmd(self, msg: Any) -> None:
        self.mark_control_command()
        now = time.time()
        self.last_raw_cmd_at = now
        self.last_raw_cmd = self.twist_to_cmd(msg)
        decision = self.evaluate()
        if decision.safe:
            self.last_reason = decision.reason
            self.publish_final_cmd(msg, decision.reason, "forwarded")
            self.publish_safety_status(decision)
            return
        self.publish_stop(decision.reason)
        self.publish_safety_status(decision)

    def twist_to_cmd(self, twist: Any) -> dict[str, float]:
        return {
            "linearX": float(getattr(getattr(twist, "linear", None), "x", 0.0) or 0.0),
            "angularZ": float(getattr(getattr(twist, "angular", None), "z", 0.0) or 0.0),
        }

    def stop_twist(self) -> Any:
        twist = self.twist_factory()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        return twist

    def publish_stop(self, reason: str) -> None:
        self.last_reason = reason
        self.publish_final_cmd(self.stop_twist(), reason, "stop")

    def publish_final_cmd(self, twist: Any, reason: str, source: str) -> None:
        now = time.time()
        self.last_final_cmd_at = now
        self.last_final_cmd = self.twist_to_cmd(twist)
        self.record_cmd_vel(reason, source, now)
        if self.dry_run:
            print(json.dumps({"type": "safety_dry_run", "reason": reason, "finalCmd": self.last_final_cmd}, ensure_ascii=False))
            return
        self.publisher.publish(twist)

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
        self.publish_safety_status(decision)
        return decision

    def record_cmd_vel(self, reason: str, source: str, now: float) -> None:
        entry = {
            "createdAt": iso_from_epoch(now),
            "source": source,
            "reason": reason,
            "rawCmd": dict(self.last_raw_cmd),
            "finalCmd": dict(self.last_final_cmd),
        }
        self.cmd_vel_log.insert(0, entry)
        self.prune_logs(now)

    def record_obstacle_status(self, status: dict[str, Any], now: float) -> None:
        entry = {
            "createdAt": iso_from_epoch(now),
            "online": bool(status.get("online")),
            "frontMin": status.get("frontMin", status.get("front_min")),
            "leftFrontMin": status.get("leftFrontMin", status.get("left_front_min")),
            "rightFrontMin": status.get("rightFrontMin", status.get("right_front_min")),
            "obstacleStatus": status.get("obstacleStatus", status.get("obstacle_status")),
        }
        self.obstacle_status_log.insert(0, entry)
        self.prune_logs(now)

    def with_ages(self, items: list[dict[str, Any]], now: float) -> list[dict[str, Any]]:
        result = []
        for item in items:
            entry = dict(item)
            try:
                created_epoch = time.mktime(time.strptime(str(entry.get("createdAt")), "%Y-%m-%dT%H:%M:%S"))
                entry["ageSeconds"] = round(max(0.0, now - created_epoch), 3)
            except (TypeError, ValueError, OverflowError):
                entry["ageSeconds"] = None
            result.append(entry)
        return result

    def prune_logs(self, now: float | None = None) -> None:
        current = time.time() if now is None else now

        def recent(item: dict[str, Any]) -> bool:
            try:
                created_epoch = time.mktime(time.strptime(str(item.get("createdAt")), "%Y-%m-%dT%H:%M:%S"))
            except (TypeError, ValueError, OverflowError):
                return True
            return current - created_epoch <= self.log_window_seconds

        self.cmd_vel_log = [item for item in self.cmd_vel_log if recent(item)][:100]
        self.obstacle_status_log = [item for item in self.obstacle_status_log if recent(item)][:100]

    def safety_status(self, decision: SafetyDecision | None = None) -> dict[str, Any]:
        now = time.time()
        self.prune_logs(now)
        active_decision = decision or self.evaluate()
        return {
            "dryRun": self.dry_run,
            "safe": active_decision.safe,
            "reason": active_decision.reason,
            "rawCmd": dict(self.last_raw_cmd),
            "finalCmd": dict(self.last_final_cmd),
            "lastRawCmdAt": iso_from_epoch(self.last_raw_cmd_at) if self.last_raw_cmd_at else None,
            "lastFinalCmdAt": iso_from_epoch(self.last_final_cmd_at) if self.last_final_cmd_at else None,
            "cmdVelLog": self.with_ages(self.cmd_vel_log, now),
            "obstacleStatusLog": self.with_ages(self.obstacle_status_log, now),
        }

    def publish_safety_status(self, decision: SafetyDecision | None = None) -> None:
        if not self.safety_publisher:
            return
        self.safety_publisher.publish(json.dumps(self.safety_status(decision), ensure_ascii=False))


def main() -> None:
    import rospy
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String

    rospy.init_node("project4_safety_supervisor", anonymous=False)
    cmd_topic = rospy.get_param("~cmd_topic", "/cmd_vel")
    raw_cmd_topic = rospy.get_param("~raw_cmd_topic", "/autopilot/cmd_vel_raw")
    obstacle_topic = rospy.get_param("~obstacle_topic", "/autopilot/obstacle_status")
    safety_topic = rospy.get_param("~safety_topic", "/autopilot/safety_status")
    cmd_timeout = float(rospy.get_param("~cmd_timeout", DEFAULT_CMD_TIMEOUT_SECONDS))
    lidar_timeout = float(rospy.get_param("~lidar_timeout", DEFAULT_LIDAR_TIMEOUT_SECONDS))
    log_window_seconds = float(rospy.get_param("~log_window_seconds", DEFAULT_LOG_WINDOW_SECONDS))
    dry_run = bool_param(rospy.get_param("~dry_run", False))
    publisher = rospy.Publisher(cmd_topic, Twist, queue_size=10)
    safety_publisher = rospy.Publisher(safety_topic, String, queue_size=10)
    supervisor = SafetySupervisor(
        publisher,
        Twist,
        cmd_timeout=cmd_timeout,
        lidar_timeout=lidar_timeout,
        dry_run=dry_run,
        log_window_seconds=log_window_seconds,
        safety_publisher=safety_publisher,
    )
    rospy.Subscriber(raw_cmd_topic, Twist, supervisor.on_raw_cmd, queue_size=10)
    rospy.Subscriber(obstacle_topic, String, supervisor.on_obstacle_status, queue_size=10)
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        decision = supervisor.watchdog_tick()
        if not decision.safe:
            rospy.logwarn_throttle(1.0, "autopilot safety stop: %s", decision.reason)
        rate.sleep()


if __name__ == "__main__":
    main()
