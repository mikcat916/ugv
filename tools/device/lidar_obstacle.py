#!/usr/bin/env python3
"""LiDAR obstacle segmentation for the Project4 autopilot MVP."""

from __future__ import annotations

import json
import math
import time
from typing import Any


FRONT_STOP_M = 0.5
FRONT_SLOW_M = 1.0
SIDE_NEAR_M = 0.8
DEFAULT_LINEAR_MPS = 0.1
SLOW_LINEAR_MPS = 0.08
AVOID_ANGULAR_RADPS = 0.35
LIDAR_TIMEOUT_SECONDS = 2.0


def finite_distance(value: Any, range_min: float, range_max: float) -> float | None:
    try:
        distance = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(distance) or distance == 0:
        return None
    if distance < range_min or distance > range_max:
        return None
    return distance


def scan_to_data(scan: Any) -> dict[str, Any]:
    ranges = list(getattr(scan, "ranges", []) or [])
    angle_min = float(getattr(scan, "angle_min", -math.pi))
    angle_increment = float(getattr(scan, "angle_increment", 0.0) or 0.0)
    angle_max = float(getattr(scan, "angle_max", angle_min + angle_increment * max(len(ranges) - 1, 0)))
    if not angle_increment and len(ranges) > 1:
        angle_increment = (angle_max - angle_min) / max(len(ranges) - 1, 1)
    return {
        "ranges": ranges,
        "angleMin": angle_min,
        "angleMax": angle_max,
        "angleIncrement": angle_increment,
        "rangeMin": float(getattr(scan, "range_min", 0.0) or 0.0),
        "rangeMax": float(getattr(scan, "range_max", 30.0) or 30.0),
    }


def sector_min(scan_data: dict[str, Any], min_deg: float, max_deg: float) -> float | None:
    ranges = scan_data.get("ranges") or []
    angle = float(scan_data.get("angleMin") or 0.0)
    step = float(scan_data.get("angleIncrement") or 0.0)
    range_min = float(scan_data.get("rangeMin") or 0.0)
    range_max = float(scan_data.get("rangeMax") or 30.0)
    values: list[float] = []
    for raw in ranges:
        degrees = math.degrees(angle)
        if min_deg <= degrees <= max_deg:
            distance = finite_distance(raw, range_min, range_max)
            if distance is not None:
                values.append(distance)
        angle += step
    return min(values) if values else None


def decide_obstacle_status(left_front: float | None, front: float | None, right_front: float | None) -> dict[str, Any]:
    left_near = left_front is not None and left_front < SIDE_NEAR_M
    right_near = right_front is not None and right_front < SIDE_NEAR_M
    front_blocked = front is None or front < FRONT_STOP_M
    front_slow = front is not None and FRONT_STOP_M <= front < FRONT_SLOW_M

    if left_near and right_near:
        return {"obstacleStatus": "both_front_blocked", "linearX": 0.0, "angularZ": 0.0, "safe": False}
    if front_blocked:
        return {"obstacleStatus": "front_blocked", "linearX": 0.0, "angularZ": 0.0, "safe": False}
    if left_near and not right_near:
        return {"obstacleStatus": "avoid_right", "linearX": SLOW_LINEAR_MPS, "angularZ": -AVOID_ANGULAR_RADPS, "safe": True}
    if right_near and not left_near:
        return {"obstacleStatus": "avoid_left", "linearX": SLOW_LINEAR_MPS, "angularZ": AVOID_ANGULAR_RADPS, "safe": True}
    if front_slow:
        turn = 0.0
        if left_front is not None and right_front is not None:
            turn = -AVOID_ANGULAR_RADPS if right_front > left_front else AVOID_ANGULAR_RADPS
        return {"obstacleStatus": "front_slow", "linearX": SLOW_LINEAR_MPS, "angularZ": turn, "safe": True}
    return {"obstacleStatus": "front_clear", "linearX": DEFAULT_LINEAR_MPS, "angularZ": 0.0, "safe": True}


def build_obstacle_status(scan: Any, received_at: float | None = None) -> dict[str, Any]:
    scan_data = scan_to_data(scan)
    left_front_min = sector_min(scan_data, 20.0, 80.0)
    front_min = sector_min(scan_data, -20.0, 20.0)
    right_front_min = sector_min(scan_data, -80.0, -20.0)
    decision = decide_obstacle_status(left_front_min, front_min, right_front_min)
    now = time.time() if received_at is None else float(received_at)
    return {
        "online": True,
        "ageSeconds": 0.0,
        "updatedAt": now,
        "leftFrontMin": round(left_front_min, 3) if left_front_min is not None else None,
        "frontMin": round(front_min, 3) if front_min is not None else None,
        "rightFrontMin": round(right_front_min, 3) if right_front_min is not None else None,
        **decision,
    }


def timeout_status(last_seen: float | None, now: float | None = None) -> dict[str, Any]:
    current = time.time() if now is None else float(now)
    age = None if last_seen is None else max(0.0, current - float(last_seen))
    return {
        "online": False,
        "ageSeconds": round(age, 3) if age is not None else None,
        "leftFrontMin": None,
        "frontMin": None,
        "rightFrontMin": None,
        "obstacleStatus": "lidar_timeout",
        "linearX": 0.0,
        "angularZ": 0.0,
        "safe": False,
    }


class LidarObstacleNode:
    def __init__(self, rospy: Any, output_topic: Any) -> None:
        self.rospy = rospy
        self.output_topic = output_topic
        self.last_seen: float | None = None
        self.last_status = timeout_status(None)

    def on_scan(self, msg: Any) -> None:
        self.last_seen = time.time()
        self.last_status = build_obstacle_status(msg, self.last_seen)
        self.publish(self.last_status)

    def publish(self, status: dict[str, Any]) -> None:
        self.output_topic.publish(json.dumps(status, ensure_ascii=False, separators=(",", ":")))

    def watchdog_tick(self) -> None:
        if self.last_seen is None or time.time() - self.last_seen > LIDAR_TIMEOUT_SECONDS:
            self.last_status = timeout_status(self.last_seen)
            self.publish(self.last_status)


def main() -> None:
    import rospy
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String

    rospy.init_node("project4_lidar_obstacle", anonymous=False)
    scan_topic = rospy.get_param("~scan_topic", "/scan")
    status_topic = rospy.get_param("~status_topic", "/autopilot/obstacle_status")
    publisher = rospy.Publisher(status_topic, String, queue_size=10)
    node = LidarObstacleNode(rospy, publisher)
    rospy.Subscriber(scan_topic, LaserScan, node.on_scan, queue_size=10)
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        node.watchdog_tick()
        rate.sleep()


if __name__ == "__main__":
    main()
