#!/usr/bin/env python3
"""Diagnose a ROS LaserScan topic before connecting it to Project4."""

from __future__ import annotations

import argparse
import math
import sys
import time
from typing import Any


def positive_finite_ranges(ranges: Any) -> list[float]:
    if not isinstance(ranges, (list, tuple)):
        return []
    values: list[float] = []
    for value in ranges:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric) and numeric > 0:
            values.append(numeric)
    return values


def summarize_lidar_samples(samples: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    count = len(samples)
    first_seen = samples[0]["receivedAt"] if samples else None
    last_seen = samples[-1]["receivedAt"] if samples else None
    elapsed = max(0.0, float(last_seen - first_seen)) if count > 1 else max(float(duration), 0.001)
    hz = (count - 1) / elapsed if count > 1 and elapsed > 0 else count / max(float(duration), 0.001)
    valid_ranges: list[float] = []
    valid_scans = 0
    total_ranges = 0
    for sample in samples:
        ranges = sample.get("ranges") or []
        total_ranges += len(ranges) if isinstance(ranges, (list, tuple)) else 0
        scan_valid = positive_finite_ranges(ranges)
        if scan_valid:
            valid_scans += 1
            valid_ranges.extend(scan_valid)
    return {
        "samples": count,
        "hz": round(hz, 3),
        "validScans": valid_scans,
        "totalRanges": total_ranges,
        "validRanges": len(valid_ranges),
        "minRange": round(min(valid_ranges), 3) if valid_ranges else None,
        "maxRange": round(max(valid_ranges), 3) if valid_ranges else None,
    }


def evaluate_lidar_samples(samples: list[dict[str, Any]], duration: float, min_hz: float) -> tuple[bool, list[str], dict[str, Any]]:
    summary = summarize_lidar_samples(samples, duration)
    messages: list[str] = []
    ok = True
    if summary["samples"] <= 0:
        ok = False
        messages.append("No LaserScan messages received.")
    else:
        messages.append(f"Received {summary['samples']} scans at {summary['hz']} Hz.")
    if summary["hz"] < min_hz:
        ok = False
        messages.append(f"Frequency below threshold: {summary['hz']} Hz < {min_hz} Hz.")
    if summary["validRanges"] <= 0:
        ok = False
        messages.append("No positive finite ranges found.")
    else:
        messages.append(
            f"Valid ranges: {summary['validRanges']}/{summary['totalRanges']} "
            f"(min={summary['minRange']} m, max={summary['maxRange']} m)."
        )
    return ok, messages, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose a ROS LaserScan topic.")
    parser.add_argument("--topic", default="/scan", help="LaserScan topic to inspect.")
    parser.add_argument("--duration", type=float, default=5.0, help="Sampling duration in seconds.")
    parser.add_argument("--min-hz", type=float, default=1.0, help="Minimum acceptable scan frequency.")
    return parser.parse_args()


def topic_exists(rospy: Any, topic: str) -> bool:
    return any(name == topic for name, _type_name in rospy.get_published_topics())


def main() -> int:
    args = parse_args()
    try:
        import rospy
        from sensor_msgs.msg import LaserScan
    except Exception as exc:
        print(f"ROS imports failed: {exc}", file=sys.stderr)
        return 2

    rospy.init_node("project4_lidar_diagnose", anonymous=True)
    if not topic_exists(rospy, args.topic):
        print(f"Topic not found: {args.topic}", file=sys.stderr)
        return 1

    samples: list[dict[str, Any]] = []

    def on_scan(msg: Any) -> None:
        samples.append({
            "receivedAt": time.monotonic(),
            "frameId": getattr(msg.header, "frame_id", ""),
            "ranges": list(msg.ranges),
        })

    subscriber = rospy.Subscriber(args.topic, LaserScan, on_scan, queue_size=10)
    deadline = time.monotonic() + max(args.duration, 0.1)
    rate = rospy.Rate(20)
    while not rospy.is_shutdown() and time.monotonic() < deadline:
        rate.sleep()
    subscriber.unregister()

    ok, messages, summary = evaluate_lidar_samples(samples, args.duration, args.min_hz)
    for message in messages:
        print(message)
    print(f"Summary: {summary}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
