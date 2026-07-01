#!/usr/bin/env python3
"""TCP bridge from Project4 robot-control protocol to ROS /cmd_vel."""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any

import rospy
from geometry_msgs.msg import Twist


HOST = "0.0.0.0"
PORT = 9000
CMD_TIMEOUT_SEC = 0.5
SOCKET_TIMEOUT_SEC = 2.0
STOP_REPEAT = 3
STOP_REPEAT_DELAY_SEC = 0.05
MAX_LINEAR = 0.6
MAX_ANGULAR = 2.0


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    port: int
    max_linear: float
    max_angular: float
    cmd_timeout: float


class RosControlBridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.publisher = rospy.Publisher("/cmd_vel", Twist, queue_size=10)
        self.lock = Lock()
        self.last_cmd_time = 0.0
        self.current_linear = 0.0
        self.current_angular = 0.0

    def subscriber_count(self) -> int:
        return int(self.publisher.get_num_connections())

    def status_payload(self) -> dict[str, Any]:
        return {
            "rosOk": not rospy.is_shutdown(),
            "cmdVelSubscribers": self.subscriber_count(),
            "v": self.current_linear,
            "w": self.current_angular,
        }

    def publish_velocity(self, linear: float, angular: float) -> None:
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)

    def stop(self) -> None:
        with self.lock:
            self.last_cmd_time = 0.0
            self.current_linear = 0.0
            self.current_angular = 0.0
        for _ in range(STOP_REPEAT):
            self.publish_velocity(0.0, 0.0)
            time.sleep(STOP_REPEAT_DELAY_SEC)

    def command_velocity(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.subscriber_count() <= 0:
            return {"type": "ack", "ok": False, "err": "cmd_vel_no_subscriber", **self.status_payload()}
        linear = clamp(float(payload.get("v", 0.0)), self.config.max_linear)
        angular = clamp(float(payload.get("w", 0.0)), self.config.max_angular)
        with self.lock:
            self.last_cmd_time = time.time()
            self.current_linear = linear
            self.current_angular = angular
        self.publish_velocity(linear, angular)
        return {"type": "ack", "ok": True, **self.status_payload(), "ts": int(time.time())}

    def watchdog_loop(self) -> None:
        while not rospy.is_shutdown():
            time.sleep(0.05)
            with self.lock:
                expired = self.last_cmd_time > 0 and (time.time() - self.last_cmd_time) > self.config.cmd_timeout
                if not expired:
                    continue
                self.last_cmd_time = 0.0
            rospy.logwarn("cmd_vel timeout -> stop")
            self.stop()

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_type = str(payload.get("type", "")).strip()
        if message_type == "ping":
            return {"type": "pong", **self.status_payload(), "ts": int(time.time())}
        if message_type == "stop":
            self.stop()
            return {"type": "ack", "ok": True, **self.status_payload(), "ts": int(time.time())}
        if message_type == "cmd_vel":
            return self.command_velocity(payload)
        return {"type": "ack", "ok": False, "err": "unknown_type", "ts": int(time.time())}


def clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def send_json_line(conn: socket.socket, payload: dict[str, Any]) -> None:
    conn.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def handle_client(conn: socket.socket, addr: tuple[str, int], bridge: RosControlBridge) -> None:
    rospy.loginfo("control client connected: %s", addr)
    conn.settimeout(SOCKET_TIMEOUT_SEC)
    buffer = b""
    try:
        while not rospy.is_shutdown():
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk
            buffer = process_buffer(conn, buffer, bridge)
    except Exception as exc:
        rospy.logerr("control client error: %s", exc)
    finally:
        bridge.stop()
        conn.close()
        rospy.loginfo("control client disconnected: %s", addr)


def process_buffer(conn: socket.socket, buffer: bytes, bridge: RosControlBridge) -> bytes:
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        if not line.strip():
            continue
        response = bridge.handle_message(json.loads(line.decode("utf-8")))
        send_json_line(conn, response)
    return buffer


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else default


def load_config() -> BridgeConfig:
    return BridgeConfig(
        host=os.getenv("PROJECT4_CONTROL_HOST", HOST).strip() or HOST,
        port=int(os.getenv("PROJECT4_CONTROL_PORT", str(PORT))),
        max_linear=env_float("PROJECT4_MAX_LINEAR", MAX_LINEAR),
        max_angular=env_float("PROJECT4_MAX_ANGULAR", MAX_ANGULAR),
        cmd_timeout=env_float("PROJECT4_CMD_TIMEOUT", CMD_TIMEOUT_SEC),
    )


def main() -> None:
    rospy.init_node("project4_ros_control_bridge", anonymous=False)
    config = load_config()
    bridge = RosControlBridge(config)
    Thread(target=bridge.watchdog_loop, daemon=True).start()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.host, config.port))
    server.listen(4)
    rospy.loginfo("Project4 ROS control bridge listening on %s:%s", config.host, config.port)
    while not rospy.is_shutdown():
        conn, addr = server.accept()
        Thread(target=handle_client, args=(conn, addr, bridge), daemon=True).start()


if __name__ == "__main__":
    main()
