#!/usr/bin/env python3
"""Post ROS robot telemetry + sensor data to Project4 backend."""

from __future__ import annotations

import argparse
import configparser
import json
import math
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Any

import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import (
    CompressedImage,
    Image,
    Imu,
    LaserScan,
    NavSatFix,
    PointCloud2,
)
from std_msgs.msg import Float32


CONFIG_FILE = Path(__file__).resolve().parent / "iot_client.conf"
HTTP_TIMEOUT_SEC = 10
WIFI_SIGNAL_RE = re.compile(r"Signal level=(-?\\d+) dBm")
MAX_LIDAR_RANGES = 4096


@dataclass(frozen=True)
class BridgeConfig:
    server: str
    token: str
    interval: int
    wifi_interface: str
    # 传感器话题配置
    camera_topic: str = ""
    stereo_left_topic: str = ""
    stereo_right_topic: str = ""
    depth_topic: str = ""
    lidar_topic: str = ""
    camera_interval: int = 10
    lidar_interval: int = 15


class TelemetryState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.gps: NavSatFix | None = None
        self.odom: Odometry | None = None
        self.imu: Imu | None = None
        self.imu_on_board: Imu | None = None
        self.voltage: Float32 | None = None
        # 传感器数据（摄像头、雷达）
        self.camera_jpeg: bytes | None = None
        self.stereo_left_jpeg: bytes | None = None
        self.stereo_right_jpeg: bytes | None = None
        self.depth_jpeg: bytes | None = None
        self.depth_last_encoded_at = 0.0
        self.lidar_scan: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "gps": navsat_to_dict(self.gps),
                "odom": odom_to_dict(self.odom),
                "imu": imu_to_dict(self.imu),
                "imuOnBoard": imu_to_dict(self.imu_on_board),
                "powerVoltage": round(float(self.voltage.data), 3) if self.voltage else None,
            }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project4 ROS telemetry bridge")
    parser.add_argument("--config", default=str(CONFIG_FILE))
    return parser.parse_args()


def load_config(path: str) -> BridgeConfig:
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    server = cfg.get("client", "server", fallback="").strip().rstrip("/")
    token = cfg.get("client", "token", fallback="").strip()
    interval = cfg.getint("client", "interval", fallback=15)
    wifi_interface = cfg.get("client", "network_interface", fallback="wlan0").strip() or "wlan0"
    if not server:
        raise RuntimeError("missing server in config")
    if not token:
        raise RuntimeError("missing token in config")
    # 传感器配置
    camera_topic = cfg.get("sensors", "camera_topic", fallback="").strip()
    stereo_left_topic = cfg.get("sensors", "stereo_left_topic", fallback="").strip()
    stereo_right_topic = cfg.get("sensors", "stereo_right_topic", fallback="").strip()
    depth_topic = cfg.get("sensors", "depth_topic", fallback="").strip()
    lidar_topic = cfg.get("sensors", "lidar_topic", fallback="").strip()
    camera_interval = max(2, cfg.getint("sensors", "camera_interval", fallback=10))
    lidar_interval = max(1, cfg.getint("sensors", "lidar_interval", fallback=15))
    return BridgeConfig(
        server=server,
        token=token,
        interval=max(5, interval),
        wifi_interface=wifi_interface,
        camera_topic=camera_topic,
        stereo_left_topic=stereo_left_topic,
        stereo_right_topic=stereo_right_topic,
        depth_topic=depth_topic,
        lidar_topic=lidar_topic,
        camera_interval=camera_interval,
        lidar_interval=lidar_interval,
    )


def vector3_to_dict(value: Any) -> dict[str, float]:
    return {"x": round(float(value.x), 6), "y": round(float(value.y), 6), "z": round(float(value.z), 6)}


def quaternion_to_dict(value: Any) -> dict[str, float]:
    return {
        "x": round(float(value.x), 6),
        "y": round(float(value.y), 6),
        "z": round(float(value.z), 6),
        "w": round(float(value.w), 6),
    }


def navsat_to_dict(msg: NavSatFix | None) -> dict[str, Any]:
    if msg is None:
        return {"available": False}
    lat = float(msg.latitude)
    lng = float(msg.longitude)
    has_fix = int(msg.status.status) >= 0 and math.isfinite(lat) and math.isfinite(lng)
    return {
        "available": True,
        "hasFix": has_fix,
        "status": int(msg.status.status),
        "service": int(msg.status.service),
        "lat": round(lat, 7) if math.isfinite(lat) else None,
        "lng": round(lng, 7) if math.isfinite(lng) else None,
        "altitude": round(float(msg.altitude), 3) if math.isfinite(float(msg.altitude)) else None,
    }


def odom_to_dict(msg: Odometry | None) -> dict[str, Any]:
    if msg is None:
        return {"available": False}
    return {
        "available": True,
        "frameId": msg.header.frame_id,
        "childFrameId": msg.child_frame_id,
        "position": vector3_to_dict(msg.pose.pose.position),
        "orientation": quaternion_to_dict(msg.pose.pose.orientation),
        "linear": vector3_to_dict(msg.twist.twist.linear),
        "angular": vector3_to_dict(msg.twist.twist.angular),
    }


def imu_to_dict(msg: Imu | None) -> dict[str, Any]:
    if msg is None:
        return {"available": False}
    return {
        "available": True,
        "frameId": msg.header.frame_id,
        "orientation": quaternion_to_dict(msg.orientation),
        "angularVelocity": vector3_to_dict(msg.angular_velocity),
        "linearAcceleration": vector3_to_dict(msg.linear_acceleration),
    }


def read_signal(interface: str) -> int | None:
    result = subprocess.run(["iwconfig", interface], capture_output=True, text=True, timeout=3, check=False)
    output = result.stdout + result.stderr
    match = WIFI_SIGNAL_RE.search(output)
    if not match:
        return None
    dbm = int(match.group(1))
    return max(0, min(100, int(2 * (dbm + 100))))


def build_payload(config: BridgeConfig, state: TelemetryState) -> dict[str, Any]:
    snapshot = state.snapshot()
    payload: dict[str, Any] = {"status": "online", "reportedAt": datetime.now().isoformat(timespec="seconds")}
    signal = read_signal(config.wifi_interface)
    if signal is not None:
        payload["signal"] = signal
    gps = snapshot["gps"]
    if gps.get("hasFix"):
        payload["lat"] = gps["lat"]
        payload["lng"] = gps["lng"]
    payload["extra"] = {"ros": snapshot, "locationSource": "ros:/gps/fix" if gps.get("hasFix") else "none"}
    return payload


def post_payload(config: BridgeConfig, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{config.server}/api/iot/telemetry",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Device-Token": config.token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def start_subscribers(state: TelemetryState, config: BridgeConfig) -> None:
    rospy.Subscriber("/gps/fix", NavSatFix, lambda msg: assign(state, "gps", msg), queue_size=1)
    rospy.Subscriber("/odom", Odometry, lambda msg: assign(state, "odom", msg), queue_size=1)
    rospy.Subscriber("/imu", Imu, lambda msg: assign(state, "imu", msg), queue_size=1)
    rospy.Subscriber("/imu_on_board", Imu, lambda msg: assign(state, "imu_on_board", msg), queue_size=1)
    rospy.Subscriber("/PowerVoltage", Float32, lambda msg: assign(state, "voltage", msg), queue_size=1)
    # 摄像头订阅（CompressedImage 格式，已经是 JPEG 编码）
    if config.camera_topic:
        rospy.Subscriber(
            config.camera_topic, CompressedImage,
            lambda msg: assign_jpeg(state, "camera_jpeg", msg), queue_size=1,
        )
        rospy.loginfo("subscribed camera: %s", config.camera_topic)
    if config.stereo_left_topic:
        rospy.Subscriber(
            config.stereo_left_topic, CompressedImage,
            lambda msg: assign_jpeg(state, "stereo_left_jpeg", msg), queue_size=1,
        )
        rospy.loginfo("subscribed stereo left: %s", config.stereo_left_topic)
    if config.stereo_right_topic:
        rospy.Subscriber(
            config.stereo_right_topic, CompressedImage,
            lambda msg: assign_jpeg(state, "stereo_right_jpeg", msg), queue_size=1,
        )
        rospy.loginfo("subscribed stereo right: %s", config.stereo_right_topic)
    if config.depth_topic:
        rospy.Subscriber(
            config.depth_topic, Image,
            lambda msg: assign_depth_image(state, msg), queue_size=1,
        )
        rospy.loginfo("subscribed depth image: %s", config.depth_topic)
    # 雷达订阅
    if config.lidar_topic:
        rospy.Subscriber(
            config.lidar_topic, LaserScan,
            lambda msg: assign_lidar(state, msg), queue_size=1,
        )
        rospy.loginfo("subscribed lidar: %s", config.lidar_topic)


def assign_jpeg(state: TelemetryState, field: str, msg: CompressedImage) -> None:
    """Extract JPEG bytes from CompressedImage and store in state."""
    data = msg.data
    if not data:
        return
    raw = bytes(data)
    # CompressedImage 可能是 jpeg/png 格式
    fmt = (msg.format or "").lower()
    if "jpeg" in fmt or "jpg" in fmt or raw[:2] == b"\xff\xd8":
        with state.lock:
            setattr(state, field, raw)
    elif "png" in fmt:
        # 尝试用 cv2 转换为 JPEG
        try:
            import cv2
            import numpy as np
            arr = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                with state.lock:
                    setattr(state, field, buf.tobytes())
        except Exception:
            pass


def assign_depth_image(state: TelemetryState, msg: Image) -> None:
    """Convert a raw ROS depth Image into a visual JPEG preview."""
    now = time.monotonic()
    with state.lock:
        if now - state.depth_last_encoded_at < 1.0:
            return
        state.depth_last_encoded_at = now
    try:
        import cv2
        import numpy as np
        from cv_bridge import CvBridge

        image = CvBridge().imgmsg_to_cv2(msg, desired_encoding="passthrough")
        depth = np.asarray(image)
        if depth.ndim == 3:
            depth = depth[:, :, 0]
        depth_float = depth.astype(np.float32, copy=False)
        valid_mask = np.isfinite(depth_float) & (depth_float > 0)
        valid_values = depth_float[valid_mask]
        if valid_values.size:
            lower, upper = np.percentile(valid_values, [2, 98])
            if not np.isfinite(lower):
                lower = float(valid_values.min())
            if not np.isfinite(upper) or upper <= lower:
                upper = float(valid_values.max())
            if upper <= lower:
                upper = lower + 1.0
            normalized = (np.clip(depth_float, lower, upper) - lower) * (255.0 / (upper - lower))
            normalized[~valid_mask] = 0
            depth_u8 = normalized.astype(np.uint8)
        else:
            depth_u8 = np.zeros(depth_float.shape[:2], dtype=np.uint8)
            valid_mask = np.zeros(depth_float.shape[:2], dtype=bool)
        color_map = cv2.COLORMAP_TURBO if hasattr(cv2, "COLORMAP_TURBO") else cv2.COLORMAP_JET
        preview = cv2.applyColorMap(depth_u8, color_map)
        preview[~valid_mask] = (0, 0, 0)
        ok, buf = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok:
            with state.lock:
                state.depth_jpeg = buf.tobytes()
    except Exception as exc:
        rospy.logwarn_throttle(30, "depth image conversion failed: %s", exc)


def _safe_float(value: float, digits: int = 3) -> float | None:
    """Return rounded float, or None if not finite (avoids NaN/Infinity in JSON)."""
    f = float(value)
    return round(f, digits) if math.isfinite(f) else None


def assign_lidar(state: TelemetryState, msg: LaserScan) -> None:
    """Extract key LiDAR scan data and store in state."""
    ranges = list(msg.ranges)
    intensities = list(msg.intensities) if msg.intensities else []
    range_stride = max(1, math.ceil(len(ranges) / MAX_LIDAR_RANGES))
    rendered_ranges = ranges[::range_stride]
    rendered_intensities = intensities[::range_stride] if intensities else []
    angle_increment = float(msg.angle_increment) * range_stride
    angle_max = float(msg.angle_min) + angle_increment * max(len(rendered_ranges) - 1, 0)
    # 过滤无效值
    valid_ranges = [r for r in ranges if math.isfinite(r) and r > 0]
    stamp_sec = msg.header.stamp.to_sec() if msg.header.stamp else None
    if stamp_sec is not None and not math.isfinite(stamp_sec):
        stamp_sec = None
    summary: dict[str, Any] = {
        "frameId": msg.header.frame_id,
        "angleMin": _safe_float(msg.angle_min, 4),
        "angleMax": _safe_float(angle_max, 4),
        "angleIncrement": _safe_float(angle_increment, 6),
        "sourceAngleMax": _safe_float(msg.angle_max, 4),
        "sourceAngleIncrement": _safe_float(msg.angle_increment, 6),
        "rangeMin": _safe_float(msg.range_min, 3),
        "rangeMax": _safe_float(msg.range_max, 3),
        "numBeams": len(ranges),
        "renderedBeams": len(rendered_ranges),
        "rangeStride": range_stride,
        "validBeams": len(valid_ranges),
        "timestamp": stamp_sec,
    }
    if valid_ranges:
        summary["minRange"] = round(min(valid_ranges), 3)
        summary["maxRange"] = round(max(valid_ranges), 3)
        summary["meanRange"] = round(sum(valid_ranges) / len(valid_ranges), 3)
    summary["ranges"] = [round(r, 3) if math.isfinite(r) else None for r in rendered_ranges]
    if rendered_intensities:
        summary["intensities"] = [round(i, 2) if math.isfinite(i) else None for i in rendered_intensities]
    with state.lock:
        state.lidar_scan = summary


def assign(state: TelemetryState, field: str, value: Any) -> None:
    with state.lock:
        setattr(state, field, value)


def main() -> None:
    config = load_config(parse_args().config)
    rospy.init_node("project4_ros_iot_bridge", anonymous=False)
    state = TelemetryState()
    start_subscribers(state, config)
    rospy.loginfo(
        "Project4 ROS IoT bridge started | interval=%ss | camera_interval=%ss | lidar_interval=%ss",
        config.interval, config.camera_interval, config.lidar_interval,
    )
    # 启动传感器上传线程
    if config.camera_topic or config.stereo_left_topic or config.stereo_right_topic or config.depth_topic:
        cam_thread = Thread(target=camera_upload_loop, args=(config, state), daemon=True)
        cam_thread.start()
    if config.lidar_topic:
        lidar_thread = Thread(target=lidar_upload_loop, args=(config, state), daemon=True)
        lidar_thread.start()
    # 主循环：遥测上报
    rate = rospy.Rate(1.0 / config.interval)
    while not rospy.is_shutdown():
        payload = build_payload(config, state)
        try:
            result = post_payload(config, payload)
            rospy.loginfo("telemetry posted: ok=%s", result.get("ok"))
        except Exception as exc:
            rospy.logwarn("telemetry post failed: %s", exc)
        rate.sleep()


# ── 传感器数据上传 ──────────────────────────────────────────────────────────────


def _post_image(config: BridgeConfig, jpeg_data: bytes, channel: str) -> dict[str, Any]:
    """Upload JPEG image to /api/iot/camera/snapshot."""
    boundary = f"project4-{int(time.time() * 1000)}"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="snapshot.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = head + jpeg_data + tail
    url = f"{config.server}/api/iot/camera/snapshot?channel={channel}"
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "X-Device-Token": config.token,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_sensor_data(config: BridgeConfig, payload: dict[str, Any]) -> dict[str, Any]:
    """Upload sensor data to /api/iot/sensor/data."""
    request = urllib.request.Request(
        f"{config.server}/api/iot/sensor/data",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Device-Token": config.token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
        return json.loads(response.read().decode("utf-8"))


def camera_upload_loop(config: BridgeConfig, state: TelemetryState) -> None:
    """Periodically upload camera snapshots."""
    while not rospy.is_shutdown():
        with state.lock:
            cam = state.camera_jpeg
            left = state.stereo_left_jpeg
            right = state.stereo_right_jpeg
            depth = state.depth_jpeg
        if cam:
            try:
                result = _post_image(config, cam, "mono")
                rospy.loginfo("camera mono uploaded: %s bytes, ok=%s", len(cam), result.get("ok"))
            except Exception as exc:
                rospy.logwarn("camera mono upload failed: %s", exc)
        if left:
            try:
                result = _post_image(config, left, "left")
                rospy.loginfo("camera left uploaded: %s bytes, ok=%s", len(left), result.get("ok"))
            except Exception as exc:
                rospy.logwarn("camera left upload failed: %s", exc)
        if right:
            try:
                result = _post_image(config, right, "right")
                rospy.loginfo("camera right uploaded: %s bytes, ok=%s", len(right), result.get("ok"))
            except Exception as exc:
                rospy.logwarn("camera right upload failed: %s", exc)
        if depth:
            try:
                result = _post_image(config, depth, "depth")
                rospy.loginfo("camera depth uploaded: %s bytes, ok=%s", len(depth), result.get("ok"))
            except Exception as exc:
                rospy.logwarn("camera depth upload failed: %s", exc)
        rospy.sleep(config.camera_interval)


def lidar_upload_loop(config: BridgeConfig, state: TelemetryState) -> None:
    """Periodically upload LiDAR scan data."""
    while not rospy.is_shutdown():
        with state.lock:
            scan = state.lidar_scan
        if scan:
            payload = {
                "sensorType": "lidar",
                "channel": "scan",
                "data": scan,
                "reportedAt": datetime.now().isoformat(timespec="seconds"),
            }
            try:
                result = _post_sensor_data(config, payload)
                rospy.loginfo("lidar scan uploaded: %s beams, ok=%s", scan.get("validBeams"), result.get("ok"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:500] if hasattr(exc, "read") else ""
                rospy.logwarn("lidar upload failed: %s | body: %s", exc, body)
            except Exception as exc:
                rospy.logwarn("lidar upload failed: %s", exc)
        rospy.sleep(config.lidar_interval)


if __name__ == "__main__":
    main()
