from __future__ import annotations

import json
import os
import select
import socket
import time
from threading import Lock
from typing import Any

from fastapi import HTTPException


ROBOT_CONTROL_LOCK = Lock()
ROBOT_CONTROL_STATE: dict[str, Any] = {"connections": {}}
ROBOT_CONTROL_MAX_LINEAR = 0.4
ROBOT_CONTROL_MAX_ANGULAR = 1.2
ROBOT_CONTROL_TIMEOUT_SECONDS = 0.75
CONTROL_COMMAND_PENDING_STATUS = "pending"
CONTROL_COMMAND_DELIVERED_STATUS = "delivered"
CONTROL_COMMAND_SUCCESS_STATUS = "success"
CONTROL_COMMAND_FAILED_STATUS = "failed"


def robot_control_port() -> int:
    raw_port = os.getenv("ROBOT_CONTROL_PORT", "9000").strip() or "9000"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_PORT 必须是合法端口。") from exc
    if port < 1 or port > 65535:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_PORT 必须在 1 到 65535 之间。")
    return port


def robot_control_timeout_seconds() -> float:
    raw_timeout = os.getenv("ROBOT_CONTROL_TIMEOUT_SECONDS", str(ROBOT_CONTROL_TIMEOUT_SECONDS)).strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_TIMEOUT_SECONDS 必须是数字。") from exc
    if timeout <= 0:
        raise HTTPException(status_code=500, detail="ROBOT_CONTROL_TIMEOUT_SECONDS 必须大于 0。")
    return timeout


def robot_control_config() -> dict[str, Any]:
    host = os.getenv("ROBOT_CONTROL_HOST", "").strip()
    return {
        "host": host,
        "port": robot_control_port(),
        "maxLinear": ROBOT_CONTROL_MAX_LINEAR,
        "maxAngular": ROBOT_CONTROL_MAX_ANGULAR,
    }


def robot_control_target_key(target: dict[str, Any]) -> str:
    return f"{target['host']}:{target['port']}"


def close_robot_control_socket(target: dict[str, Any] | None = None) -> None:
    connections = ROBOT_CONTROL_STATE.setdefault("connections", {})
    keys = [robot_control_target_key(target)] if target else list(connections.keys())
    for key in keys:
        connection = connections.pop(key, None)
        if connection and connection.get("socket"):
            connection["socket"].close()


def robot_control_socket_is_closed(active_socket: socket.socket) -> bool:
    try:
        readable, _, _ = select.select([active_socket], [], [], 0)
    except (OSError, TypeError, ValueError):
        return False
    if not readable:
        return False
    try:
        return active_socket.recv(1, socket.MSG_PEEK) == b""
    except (BlockingIOError, socket.timeout):
        return False
    except OSError:
        return True


def get_robot_control_socket(target: dict[str, Any]) -> socket.socket:
    connections = ROBOT_CONTROL_STATE.setdefault("connections", {})
    key = robot_control_target_key(target)
    connection = connections.get(key)
    if connection and connection.get("socket"):
        active_socket = connection["socket"]
        if not robot_control_socket_is_closed(active_socket):
            return active_socket
        close_robot_control_socket(target)
    timeout = robot_control_timeout_seconds()
    try:
        active_socket = socket.create_connection(
            (target["host"], target["port"]),
            timeout=timeout,
        )
    except OSError as exc:
        raise HTTPException(status_code=502, detail="无人车控制服务不可达。") from exc
    active_socket.settimeout(timeout)
    connections[key] = {"socket": active_socket, "buffer": b""}
    return active_socket


def robot_control_connection(target: dict[str, Any]) -> dict[str, Any]:
    key = robot_control_target_key(target)
    connections = ROBOT_CONTROL_STATE.setdefault("connections", {})
    return connections.setdefault(key, {"socket": None, "buffer": b""})


def read_robot_control_message(active_socket: socket.socket, connection: dict[str, Any]) -> dict[str, Any]:
    while b"\n" not in connection["buffer"]:
        chunk = active_socket.recv(4096)
        if not chunk:
            raise ConnectionError("无人车控制连接已断开。")
        connection["buffer"] += chunk
    line, connection["buffer"] = connection["buffer"].split(b"\n", 1)
    return json.loads(line.decode("utf-8"))


def send_robot_control_message(
    target: dict[str, Any],
    payload: dict[str, Any],
    expected_type: str,
    *,
    close_after: bool = True,
) -> dict[str, Any]:
    encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
    with ROBOT_CONTROL_LOCK:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                active_socket = get_robot_control_socket(target)
                connection = robot_control_connection(target)
                active_socket.sendall(encoded)
                deadline = time.time() + robot_control_timeout_seconds()
                while time.time() < deadline:
                    message = read_robot_control_message(active_socket, connection)
                    if message.get("type") == expected_type:
                        if close_after:
                            close_robot_control_socket(target)
                        return message
                close_robot_control_socket(target)
                last_error = TimeoutError("无人车控制服务响应超时。")
            except (ConnectionError, OSError) as exc:
                last_error = exc
                close_robot_control_socket(target)
            except json.JSONDecodeError as exc:
                close_robot_control_socket(target)
                raise HTTPException(status_code=502, detail="无人车控制服务响应异常。") from exc
            if attempt == 0:
                continue
            if isinstance(last_error, TimeoutError):
                raise HTTPException(status_code=504, detail="无人车控制服务响应超时。") from last_error
            raise HTTPException(status_code=502, detail="无人车控制服务响应异常。") from last_error
    close_robot_control_socket(target)
    raise HTTPException(status_code=504, detail="无人车控制服务响应超时。")


def ensure_robot_control_ack_ok(response: dict[str, Any]) -> None:
    if response.get("ok", True):
        return
    error_code = str(response.get("err") or "control_rejected")
    detail_map = {
        "cmd_vel_no_subscriber": "无人车底盘未订阅 /cmd_vel，无法执行运动指令。",
        "unknown_type": "无人车控制服务不支持该指令。",
    }
    raise HTTPException(status_code=502, detail=detail_map.get(error_code, f"无人车控制服务拒绝指令：{error_code}"))


def normalize_control_value(value: Any, limit: float, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field} 必须是数字。") from exc
    return max(-limit, min(limit, parsed))
