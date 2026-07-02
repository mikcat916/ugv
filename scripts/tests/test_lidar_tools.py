from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_fake_ros_modules(monkeypatch):
    rospy = types.ModuleType("rospy")
    rospy.logwarn_throttle = lambda *args, **kwargs: None
    rospy.loginfo = lambda *args, **kwargs: None
    rospy.logwarn = lambda *args, **kwargs: None
    rospy.init_node = lambda *args, **kwargs: None
    rospy.is_shutdown = lambda: True
    rospy.sleep = lambda seconds: None
    rospy.Rate = lambda hz: types.SimpleNamespace(sleep=lambda: None)
    rospy.Subscriber = lambda *args, **kwargs: types.SimpleNamespace(unregister=lambda: None)

    nav_msgs = types.ModuleType("nav_msgs")
    nav_msgs_msg = types.ModuleType("nav_msgs.msg")
    sensor_msgs = types.ModuleType("sensor_msgs")
    sensor_msgs_msg = types.ModuleType("sensor_msgs.msg")
    std_msgs = types.ModuleType("std_msgs")
    std_msgs_msg = types.ModuleType("std_msgs.msg")

    nav_msgs_msg.Odometry = type("Odometry", (), {})
    for name in ["CompressedImage", "Image", "Imu", "LaserScan", "NavSatFix", "PointCloud2"]:
        setattr(sensor_msgs_msg, name, type(name, (), {}))
    std_msgs_msg.Float32 = type("Float32", (), {})

    monkeypatch.setitem(sys.modules, "rospy", rospy)
    monkeypatch.setitem(sys.modules, "nav_msgs", nav_msgs)
    monkeypatch.setitem(sys.modules, "nav_msgs.msg", nav_msgs_msg)
    monkeypatch.setitem(sys.modules, "sensor_msgs", sensor_msgs)
    monkeypatch.setitem(sys.modules, "sensor_msgs.msg", sensor_msgs_msg)
    monkeypatch.setitem(sys.modules, "std_msgs", std_msgs)
    monkeypatch.setitem(sys.modules, "std_msgs.msg", std_msgs_msg)


def test_ros_iot_bridge_lidar_payload_uses_scan_stamp_and_extra(monkeypatch):
    install_fake_ros_modules(monkeypatch)
    bridge = load_module("ros_iot_bridge_test_module", ROOT / "ros_iot_bridge.py")
    config = bridge.BridgeConfig(
        server="http://127.0.0.1:8000",
        token="token",
        interval=60,
        wifi_interface="wlan0",
        lidar_topic="/scan",
    )
    stamp = 1_700_000_000.0
    scan = {"timestamp": stamp, "rangeStride": 4, "ranges": [1.0, None, 2.0]}

    payload = bridge.build_lidar_payload(config, scan)

    assert payload["reportedAt"] == datetime.fromtimestamp(stamp).isoformat(timespec="seconds")
    assert payload["extra"]["sourceTopic"] == "/scan"
    assert payload["extra"]["rangeStride"] == 4
    assert payload["extra"]["uploadTime"]
    assert payload["data"] is scan


def test_diagnose_lidar_samples_pass_when_frequency_and_ranges_are_valid():
    diagnose = load_module("diagnose_lidar_ros_test_module", ROOT / "diagnose_lidar_ros.py")
    samples = [
        {"receivedAt": 10.0, "ranges": [1.0, None, float("inf")]},
        {"receivedAt": 11.0, "ranges": [2.5, 0, -1]},
        {"receivedAt": 12.0, "ranges": [3.0]},
    ]

    ok, messages, summary = diagnose.evaluate_lidar_samples(samples, duration=3, min_hz=0.5)

    assert ok is True
    assert summary["samples"] == 3
    assert summary["validRanges"] == 3
    assert any("Received 3 scans" in message for message in messages)


def test_diagnose_lidar_samples_fails_without_valid_ranges():
    diagnose = load_module("diagnose_lidar_ros_test_module_2", ROOT / "diagnose_lidar_ros.py")
    samples = [{"receivedAt": 10.0, "ranges": [None, 0, float("inf")]}]

    ok, messages, summary = diagnose.evaluate_lidar_samples(samples, duration=2, min_hz=1)

    assert ok is False
    assert summary["validRanges"] == 0
    assert "No positive finite ranges found." in messages
