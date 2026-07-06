from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
import asyncio
import bcrypt
import httpx
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

import auth as auth_helpers
import autopilot as autopilot_helpers
import iot as iot_helpers
import robot_control as robot_control_helpers
from config import (
    BASE_DIR,
    DEFAULT_SITE,
    PAGES,
    PROTOTYPES,
    PROTOTYPE_DIR,
    ROOT_DIR,
    SCHEMA_FILE,
    STATIC_DIR,
    TEMPLATES_DIR,
    admin_username,
    asset_version,
    debug_enabled,
    mysql_configured,
    mysql_settings,
    self_registration_allowed,
    session_secret,
)
from db import (
    clear_table,
    ensure_database,
    ensure_autonomy_tables,
    ensure_iot_tables,
    ensure_management_system_tables,
    ensure_mysql_configured,
    ensure_robot_device_column,
    ensure_robot_ip_column,
    execute_insert,
    execute_schema,
    execute_write,
    query_all,
    query_one,
)

MAX_ID_VALUE = 2_147_483_647
logger = logging.getLogger("ugv.backend")
logging.getLogger("uvicorn.access").disabled = True

# Global runtime state shared by startup and health checks.
APP_STATE = {
    "db_ready": False,
    "db_error": "",
}
# In-memory websocket registry for dashboard realtime updates.
WS_CLIENTS: set[WebSocket] = set()
WS_LOCK = asyncio.Lock()
ROBOT_DISCOVERY_TTL_SECONDS = 300
ROBOT_DISCOVERY_TIMEOUT_SECONDS = 0.18
ROBOT_IDENTITY_TTL_HOURS = 24
ROBOT_DISCOVERY_PORTS = (22, 80, 443, 8000)
ROBOT_TELEMETRY_OFFLINE_SECONDS = 180
IOT_REPORTED_AT_MAX_SKEW_SECONDS = iot_helpers.IOT_REPORTED_AT_MAX_SKEW_SECONDS
ROBOT_WEAK_SIGNAL_THRESHOLD = 35
ROBOT_CAMERA_PORT = 8080
ROBOT_CAMERA_STALE_SECONDS = float(os.getenv("ROBOT_CAMERA_STALE_SECONDS", "5") or "5")
ROBOT_STEREO_STALE_SECONDS = float(os.getenv("ROBOT_STEREO_STALE_SECONDS", "10") or "10")
ROBOT_LIDAR_STALE_SECONDS = float(os.getenv("ROBOT_LIDAR_STALE_SECONDS", "3") or "3")
ROBOT_DISCOVERY_HOST_HINTS = ("raspberry", "robot", "agv", "car", "rover", "pi", "wheeltec")
RASPBERRY_PI_MAC_PREFIXES = {
    "28CDC1",
    "2CCF67",
    "B827EB",
    "D83ADD",
    "DCA632",
    "E45F01",
}
ROBOT_DISCOVERY_CACHE: dict[str, Any] = {"items": [], "scanned_at": 0.0, "subnets": []}
ROBOT_DISCOVERY_LOCK = Lock()
IOT_INGEST_THROTTLE_STATE: dict[tuple[str, str, str], float] = {}
IOT_INGEST_THROTTLE_LOCK = Lock()
ROBOT_CONTROL_PRIORITY_STATE: dict[str, float] = {"ingest_pause_until": 0.0}
ROBOT_CONTROL_PRIORITY_LOCK = Lock()
ROBOT_CONTROL_LOCK = robot_control_helpers.ROBOT_CONTROL_LOCK
ROBOT_CONTROL_STATE = robot_control_helpers.ROBOT_CONTROL_STATE
ROBOT_CONTROL_MAX_LINEAR = robot_control_helpers.ROBOT_CONTROL_MAX_LINEAR
ROBOT_CONTROL_MAX_ANGULAR = robot_control_helpers.ROBOT_CONTROL_MAX_ANGULAR
ROBOT_CONTROL_TIMEOUT_SECONDS = robot_control_helpers.ROBOT_CONTROL_TIMEOUT_SECONDS
CONTROL_COMMAND_PENDING_STATUS = robot_control_helpers.CONTROL_COMMAND_PENDING_STATUS
CONTROL_COMMAND_DELIVERED_STATUS = robot_control_helpers.CONTROL_COMMAND_DELIVERED_STATUS
CONTROL_COMMAND_SUCCESS_STATUS = robot_control_helpers.CONTROL_COMMAND_SUCCESS_STATUS
CONTROL_COMMAND_FAILED_STATUS = robot_control_helpers.CONTROL_COMMAND_FAILED_STATUS
ROBOT_CONTROL_MODE = os.getenv("ROBOT_CONTROL_MODE", "direct").strip().lower() or "direct"
AUTOPILOT_RUNTIME = autopilot_helpers.AutopilotRuntime(
    lidar_timeout_seconds=float(os.getenv("AUTOPILOT_LIDAR_TIMEOUT_SECONDS", "2") or "2"),
    control_timeout_seconds=float(os.getenv("AUTOPILOT_CONTROL_TIMEOUT_SECONDS", "10") or "10"),
    deadman_timeout_seconds=float(os.getenv("AUTOPILOT_DEADMAN_TIMEOUT_SECONDS", "5") or "5"),
    max_runtime_seconds=float(os.getenv("AUTOPILOT_MAX_RUNTIME_SECONDS", "0") or "0"),
    debug_log_window_seconds=float(os.getenv("AUTOPILOT_DEBUG_LOG_WINDOW_SECONDS", "30") or "30"),
)
AUTOPILOT_MODES = autopilot_helpers.AUTOPILOT_MODES
AUTOPILOT_CONTROL_PRIORITY = autopilot_helpers.CONTROL_PRIORITY


def mysql_ready() -> bool:
    return mysql_configured() and APP_STATE["db_ready"]


def robot_control_mode() -> str:
    return str(globals().get("ROBOT_CONTROL_MODE") or os.getenv("ROBOT_CONTROL_MODE", "direct")).strip().lower() or "direct"


def hash_password(password: str) -> str:
    return auth_helpers.hash_password(password)


def is_legacy_password_hash(password_hash: Any) -> bool:
    return auth_helpers.is_legacy_password_hash(password_hash)


def verify_password(password: str, password_hash: str) -> bool:
    return auth_helpers.verify_password(password, password_hash)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    return auth_helpers.get_user_by_username(query_one, username)


def validate_auth_user_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    return auth_helpers.validate_auth_user_payload(payload)

def ensure_admin_user() -> None:
    auth_helpers.ensure_admin_user(get_user_by_username, execute_write, hash_password)


def current_user(request: Request) -> dict[str, Any] | None:
    return auth_helpers.current_user(request, mysql_ready, get_user_by_username, verify_session_auth_token)


def template_user(user: dict[str, Any] | None) -> dict[str, str] | None:
    return auth_helpers.template_user(user)


def user_session_signature(user: dict[str, Any]) -> str:
    return auth_helpers.user_session_signature(user)


def create_session_auth_token(user: dict[str, Any]) -> str:
    return auth_helpers.create_session_auth_token(user)


def verify_session_auth_token(user: dict[str, Any], token: str) -> bool:
    return auth_helpers.verify_session_auth_token(user, token)


def issue_login_token(request: Request) -> str:
    return auth_helpers.issue_login_token(request)


def verify_login_token(request: Request, payload: dict[str, Any]) -> None:
    auth_helpers.verify_login_token(request, payload)


def establish_user_session(request: Request, user: dict[str, Any]) -> None:
    auth_helpers.establish_user_session(request, user, create_session_auth_token)


def visible_pages_for_user(user: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    return auth_helpers.visible_pages_for_user(user)


def vnc_config() -> dict[str, Any]:
    target_port = int(os.getenv("ROBOT_VNC_PORT", "5900") or "5900")
    proxy_port = int(os.getenv("NOVNC_PROXY_PORT", "6080") or "6080")
    return {
        "targetHost": os.getenv("ROBOT_VNC_HOST", "192.168.137.70").strip() or "192.168.137.70",
        "targetPort": target_port,
        "proxyHost": os.getenv("NOVNC_PROXY_HOST", "").strip(),
        "proxyPort": proxy_port,
        "viewOnly": os.getenv("NOVNC_VIEW_ONLY", "1").strip() != "0",
        "password": os.getenv("NOVNC_PASSWORD", "").strip(),
    }


def camera_config() -> dict[str, Any]:
    mjpeg_url = os.getenv("ROBOT_CAMERA_MJPEG_URL", "").strip()
    snapshot_url = os.getenv("ROBOT_CAMERA_SNAPSHOT_URL", "").strip()
    inferred_mode = "mjpeg" if mjpeg_url else "snapshot" if snapshot_url else "none"
    return {
        "label": os.getenv("ROBOT_CAMERA_LABEL", "前置摄像头").strip() or "前置摄像头",
        "mjpegUrl": mjpeg_url,
        "snapshotUrl": snapshot_url,
        "mode": os.getenv("ROBOT_CAMERA_MODE", inferred_mode).strip() or inferred_mode,
        "status": os.getenv("ROBOT_CAMERA_STATUS", "unavailable").strip() or "unavailable",
        "statusText": os.getenv("ROBOT_CAMERA_STATUS_TEXT", "").strip(),
        "reason": os.getenv("ROBOT_CAMERA_STATUS_REASON", "").strip(),
    }


def video_config() -> dict[str, Any]:
    return {
        "camera": camera_config(),
        "vnc": vnc_config(),
    }


def robot_control_port() -> int:
    return robot_control_helpers.robot_control_port()


def robot_control_config() -> dict[str, Any]:
    return robot_control_helpers.robot_control_config()


def robot_control_target_key(target: dict[str, Any]) -> str:
    return robot_control_helpers.robot_control_target_key(target)


def close_robot_control_socket(target: dict[str, Any] | None = None) -> None:
    robot_control_helpers.close_robot_control_socket(target)


def get_robot_control_socket(target: dict[str, Any]) -> socket.socket:
    return robot_control_helpers.get_robot_control_socket(target)


def robot_control_connection(target: dict[str, Any]) -> dict[str, Any]:
    return robot_control_helpers.robot_control_connection(target)


def read_robot_control_message(active_socket: socket.socket, connection: dict[str, Any]) -> dict[str, Any]:
    return robot_control_helpers.read_robot_control_message(active_socket, connection)


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
                deadline = time.time() + robot_control_helpers.robot_control_timeout_seconds()
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
    robot_control_helpers.ensure_robot_control_ack_ok(response)


def send_robot_control_command(
    target: dict[str, Any],
    payload: dict[str, Any],
    expected_type: str,
    *,
    close_after: bool = True,
) -> dict[str, Any]:
    try:
        return send_robot_control_message(target, payload, expected_type, close_after=close_after)
    except TypeError as exc:
        if "close_after" not in str(exc):
            raise
        return send_robot_control_message(target, payload, expected_type)


def insert_control_command(record: dict[str, Any]) -> int:
    return execute_insert(
        """
        INSERT INTO control_commands
            (scope, target_type, target_id, command_type, params_json, status, error, response_json, created_at, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record["scope"],
            record["targetType"],
            record["targetId"],
            record["commandType"],
            json.dumps(record.get("params") or {}, ensure_ascii=False),
            record.get("status", CONTROL_COMMAND_PENDING_STATUS),
            record.get("error") or None,
            json.dumps(record.get("response"), ensure_ascii=False) if record.get("response") is not None else None,
            record.get("createdAt") or datetime.now(),
            record.get("completedAt"),
        ),
    )


def update_control_command(
    command_id: int,
    status: str,
    response: Any = None,
    error: str = "",
    completed: bool = True,
) -> int:
    return execute_write(
        """
        UPDATE control_commands
        SET status = %s, response_json = %s, error = %s, completed_at = %s
        WHERE id = %s
        """,
        (
            status,
            json.dumps(response, ensure_ascii=False) if response is not None else None,
            error or None,
            datetime.now() if completed else None,
            command_id,
        ),
    )


def validate_control_command_payload(payload: dict[str, Any]) -> dict[str, Any]:
    scope = str(payload.get("scope") or "device").strip().lower()
    target_type = str(payload.get("targetType") or "").strip()
    target_id = parse_strict_id(payload.get("targetId"), "targetId")
    command_type = str(payload.get("commandType") or "").strip()
    if not target_type:
        raise HTTPException(status_code=422, detail="targetType 不能为空。")
    if not command_type:
        raise HTTPException(status_code=422, detail="commandType 不能为空。")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    return {"scope": scope, "targetType": target_type, "targetId": target_id, "commandType": command_type, "params": params}


def control_target_exists(target_type: str, target_id: int) -> bool:
    table_map = {
        "robot": "robots",
        "sensor": "devices",
        "device": "devices",
        "network": "network_channels",
        "network_channel": "network_channels",
        "onboard_unit": "onboard_units",
        "cluster_node": "cluster_nodes",
    }
    table = table_map.get(target_type)
    if not table:
        return False
    return bool(query_one(f"SELECT id FROM {table} WHERE id = %s LIMIT 1", (target_id,)))


def execute_direct_robot_control(record: dict[str, Any]) -> dict[str, Any]:
    command_type = record["commandType"]
    params = record.get("params") or {}
    target = load_robot_control_target(record["targetId"])
    if command_type == "cmd_vel":
        if AUTOPILOT_RUNTIME.is_estopped():
            raise HTTPException(status_code=423, detail="急停已触发，必须先解除急停。")
        AUTOPILOT_RUNTIME.note_manual_override(robot_id=target.get("robotId"), source="control_command")
        linear = normalize_control_value(params.get("linear", 0.0), ROBOT_CONTROL_MAX_LINEAR, "linear")
        angular = normalize_control_value(params.get("angular", 0.0), ROBOT_CONTROL_MAX_ANGULAR, "angular")
        response = send_robot_control_command(target, {"type": "cmd_vel", "v": linear, "w": angular}, "ack", close_after=False)
        ensure_robot_control_ack_ok(response)
        return {"type": "cmd_vel", "linear": linear, "angular": angular, "response": response}
    if command_type in {"stop", "emergency_stop"}:
        response = send_robot_control_message(target, {"type": "stop"}, "ack")
        ensure_robot_control_ack_ok(response)
        return {"type": "stop", "response": response}
    if command_type == "connectivity_test":
        response = send_robot_control_message(target, {"type": "ping"}, "pong")
        ensure_robot_control_ack_ok(response)
        return {"type": "connectivity_test", "response": response}
    raise HTTPException(status_code=422, detail=f"不支持的机器人控制指令：{command_type}")


def apply_control_success_side_effect(record: dict[str, Any]) -> None:
    if record.get("targetType") == "cluster_node" and record.get("commandType") == "node_exit":
        execute_write("UPDATE cluster_nodes SET status = 'disconnected', joined_at = NULL WHERE id = %s", (record["targetId"],))


def create_control_command(record: dict[str, Any]) -> dict[str, Any]:
    command_id = insert_control_command({**record, "status": CONTROL_COMMAND_PENDING_STATUS, "createdAt": datetime.now()})
    try:
        if record["targetType"] == "robot":
            if robot_control_mode() == "queue":
                return {"ok": True, "queued": True, "commandId": command_id}
            result = execute_direct_robot_control(record)
            update_control_command(command_id, CONTROL_COMMAND_SUCCESS_STATUS, response=result)
            apply_control_success_side_effect(record)
            return {"ok": True, "commandId": command_id, "response": result}
        if not control_target_exists(record["targetType"], record["targetId"]):
            raise HTTPException(status_code=404, detail="未找到对应控制目标。")
        gateway_url = os.getenv("CONTROL_GATEWAY_URL", "").strip()
        if not gateway_url:
            raise HTTPException(status_code=502, detail="真实控制网关未配置，无法下发该控制命令。")
        raise HTTPException(status_code=502, detail="真实控制网关暂未接入当前后端。")
    except HTTPException as exc:
        update_control_command(command_id, CONTROL_COMMAND_FAILED_STATUS, error=str(exc.detail))
        raise


def normalize_control_value(value: Any, limit: float, field: str) -> float:
    return robot_control_helpers.normalize_control_value(value, limit, field)


def forbidden_page(detail: str = "仅管理员可访问当前页面。") -> HTMLResponse:
    return auth_helpers.forbidden_page(detail)


def require_page_login(request: Request):
    return auth_helpers.require_page_login(request, current_user)


def require_api_login(request: Request) -> dict[str, Any]:
    return auth_helpers.require_api_login(request, current_user)


def is_admin_user(user: dict[str, Any] | None) -> bool:
    return auth_helpers.is_admin_user(user)


def require_admin_login(request: Request) -> dict[str, Any]:
    user = require_api_login(request)
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作。")
    return user


def to_iso_date(value: Any) -> str:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value or "")


def to_iso_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat(timespec="seconds")
    return str(value or "")


def record_autonomy_event(event: dict[str, Any]) -> int | None:
    if not mysql_ready():
        return None
    robot_id = event.get("robotId")
    try:
        robot_id_value = int(robot_id) if robot_id else None
    except (TypeError, ValueError):
        robot_id_value = None
    return execute_insert(
        """
        INSERT INTO autonomy_events
            (robot_id, level, event_type, message, data_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            robot_id_value,
            str(event.get("level") or "info")[:20],
            str(event.get("eventType") or "event")[:64],
            str(event.get("message") or ""),
            json.dumps(event.get("data") or {}, ensure_ascii=False),
            coerce_datetime(event.get("createdAt")) or datetime.now(),
        ),
    )


def load_autonomy_events(limit: int = 20, robot_id: int | None = None) -> list[dict[str, Any]]:
    if not mysql_ready():
        return []
    limit = max(1, min(int(limit or 20), 100))
    where = ""
    params: list[Any] = []
    if robot_id is not None:
        where = "WHERE robot_id = %s"
        params.append(int(robot_id))
    rows = query_all(
        f"""
        SELECT id, robot_id, level, event_type, message, data_json, created_at
        FROM autonomy_events
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT {limit}
        """,
        tuple(params),
    )
    return [
        {
            "id": row["id"],
            "robotId": row["robot_id"],
            "level": row["level"],
            "eventType": row["event_type"],
            "message": row["message"] or "",
            "data": json.loads(row["data_json"]) if row["data_json"] else {},
            "createdAt": to_iso_datetime(row["created_at"]),
        }
        for row in rows
    ]


AUTOPILOT_RUNTIME.configure_persistence(record_autonomy_event, load_autonomy_events)


def parse_datetime(value: Any, field_name: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise HTTPException(status_code=422, detail=f"{field_name} 不能为空。")
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是合法的日期时间格式。") from exc


def coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_date(value: Any, field_name: str) -> date:
    raw = str(value or "").strip()
    if not raw:
        raise HTTPException(status_code=422, detail=f"{field_name} 不能为空。")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是合法的日期格式。") from exc


def parse_int_range(value: Any, field_name: str, min_value: int = 0, max_value: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是整数。") from exc
    if number < min_value or number > max_value:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须在 {min_value} 到 {max_value} 之间。")
    return number


def parse_strict_id(value: Any, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是整数。") from exc
    if number < 1 or number > MAX_ID_VALUE:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须在 1 到 {MAX_ID_VALUE} 之间。")
    return number


def normalize_entity_name(value: Any) -> str:
    return str(value or "").strip()


def normalized_name_key(value: Any) -> str:
    return normalize_entity_name(value).lower()


def normalize_pagination(page: int = 1, size: int = 20) -> tuple[int, int, int]:
    normalized_size = min(max(int(size or 20), 1), 100)
    normalized_page = max(int(page or 1), 1)
    offset = (normalized_page - 1) * normalized_size
    return normalized_page, normalized_size, offset


def parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是数字。") from exc


def parse_ipv4(value: Any, field_name: str = "ipAddress") -> str:
    raw = str(value or "").strip()
    if not raw:
        raise HTTPException(status_code=422, detail=f"{field_name} 不能为空。")
    try:
        parsed = ipaddress.ip_address(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是合法的 IPv4 地址。") from exc
    if parsed.version != 4:
        raise HTTPException(status_code=422, detail=f"{field_name} 必须是合法的 IPv4 地址。")
    return str(parsed)


def format_window(start_at: Any, end_at: Any) -> str:
    start_value = to_iso_datetime(start_at)
    end_value = to_iso_datetime(end_at)
    if not start_value and not end_value:
        return "未排期"
    if start_value and end_value:
        return f"{start_value} - {end_value}"
    return start_value or end_value


def robot_exists(robot_id: Any) -> bool:
    if robot_id is None:
        return False
    return bool(query_one("SELECT id FROM robots WHERE id = %s LIMIT 1", (robot_id,)))


def resolve_robot_device(robot_id: Any) -> dict[str, Any]:
    parsed_id = parse_strict_id(robot_id, "robot_id")
    robot = query_one("SELECT id, ip_address, device_id FROM robots WHERE id = %s LIMIT 1", (parsed_id,))
    if not robot:
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    device_id = robot.get("device_id")
    if device_id:
        return {"robot": robot, "deviceId": int(device_id), "deviceMatchSource": "robots.device_id"}

    dev_row = query_one(
        """
        SELECT id
        FROM devices
        WHERE robot_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (parsed_id,),
    )
    if dev_row and dev_row.get("id"):
        return {"robot": robot, "deviceId": int(dev_row["id"]), "deviceMatchSource": "devices.robot_id"}

    ip = str(robot.get("ip_address") or "").strip()
    if ip:
        telemetry_row = query_one(
            "SELECT device_id FROM device_telemetry WHERE source_ip = %s ORDER BY reported_at DESC, id DESC LIMIT 1",
            (ip,),
        )
        if telemetry_row and telemetry_row.get("device_id"):
            return {
                "robot": robot,
                "deviceId": int(telemetry_row["device_id"]),
                "deviceMatchSource": "device_telemetry.source_ip",
            }
    return {"robot": robot, "deviceId": None, "deviceMatchSource": ""}


def set_robot_primary_device(robot_id: int | None, device_id: int | None) -> None:
    if not robot_id:
        return
    execute_write("UPDATE robots SET device_id = %s WHERE id = %s", (device_id, robot_id))


def refresh_robot_primary_device(robot_id: int | None) -> None:
    if not robot_id:
        return
    row = query_one(
        """
        SELECT id
        FROM devices
        WHERE robot_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (robot_id,),
    )
    set_robot_primary_device(robot_id, int(row["id"]) if row and row.get("id") else None)


def load_robot_camera_target(robot_id: Any) -> dict[str, Any]:
    parsed_id = parse_strict_id(robot_id, "robot_id")
    row = query_one(
        "SELECT id, model, ip_address FROM robots WHERE id = %s LIMIT 1",
        (parsed_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    raw_ip = str(row.get("ip_address") or "").strip()
    if not raw_ip:
        raise HTTPException(status_code=422, detail="机器人未配置 IP 地址，无法读取摄像头。")
    row["ip_address"] = parse_ipv4(raw_ip, "ipAddress")
    return row


def env_robot_control_target() -> dict[str, Any]:
    config = robot_control_config()
    if not config["host"]:
        raise HTTPException(status_code=422, detail="请选择要控制的机器人。")
    return {
        "robotId": None,
        "model": "环境变量控制目标",
        "ipAddress": config["host"],
        "host": config["host"],
        "port": config["port"],
        "maxLinear": config["maxLinear"],
        "maxAngular": config["maxAngular"],
    }


def load_robot_control_target(robot_id: Any) -> dict[str, Any]:
    parsed_id = parse_strict_id(robot_id, "robotId")
    row = query_one(
        "SELECT id, model, ip_address FROM robots WHERE id = %s LIMIT 1",
        (parsed_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    raw_ip = str(row.get("ip_address") or "").strip()
    if not raw_ip:
        raise HTTPException(status_code=422, detail="机器人未配置 IP 地址，无法控制。")
    ip_address = parse_ipv4(raw_ip, "ipAddress")
    return {
        "robotId": parsed_id,
        "model": row.get("model") or f"机器人 {parsed_id}",
        "ipAddress": ip_address,
        "host": ip_address,
        "port": robot_control_port(),
        "maxLinear": ROBOT_CONTROL_MAX_LINEAR,
        "maxAngular": ROBOT_CONTROL_MAX_ANGULAR,
    }


def resolve_robot_control_target(robot_id: Any = None) -> dict[str, Any]:
    if robot_id is None or str(robot_id).strip() == "":
        return env_robot_control_target()
    return load_robot_control_target(robot_id)


def robot_camera_url(ip_address: str, action: str) -> str:
    return f"http://{ip_address}:{ROBOT_CAMERA_PORT}/?action={action}"


def robot_camera_upload_path(robot_id: Any) -> Path:
    return CAMERA_UPLOAD_DIR / "robot_cameras" / f"robot-{parse_strict_id(robot_id, 'robot_id')}.jpg"


def camera_stale_seconds() -> float:
    raw = os.getenv("ROBOT_CAMERA_STALE_SECONDS", str(ROBOT_CAMERA_STALE_SECONDS)).strip()
    try:
        value = float(raw)
    except ValueError:
        value = ROBOT_CAMERA_STALE_SECONDS
    return max(0.5, value)


def sensor_stale_seconds(sensor_type: Any) -> float:
    normalized = str(sensor_type or iot_helpers.SENSOR_TYPE_CAMERA).strip().lower()
    defaults = {
        iot_helpers.SENSOR_TYPE_CAMERA: ROBOT_CAMERA_STALE_SECONDS,
        iot_helpers.SENSOR_TYPE_STEREO: ROBOT_STEREO_STALE_SECONDS,
        iot_helpers.SENSOR_TYPE_LIDAR: ROBOT_LIDAR_STALE_SECONDS,
    }
    env_names = {
        iot_helpers.SENSOR_TYPE_CAMERA: "ROBOT_CAMERA_STALE_SECONDS",
        iot_helpers.SENSOR_TYPE_STEREO: "ROBOT_STEREO_STALE_SECONDS",
        iot_helpers.SENSOR_TYPE_LIDAR: "ROBOT_LIDAR_STALE_SECONDS",
    }
    default = defaults.get(normalized, ROBOT_CAMERA_STALE_SECONDS)
    raw = os.getenv(env_names.get(normalized, "ROBOT_CAMERA_STALE_SECONDS"), str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        value = default
    return max(0.5, value)


def sensor_stale_thresholds() -> dict[str, float]:
    return {
        iot_helpers.SENSOR_TYPE_CAMERA: sensor_stale_seconds(iot_helpers.SENSOR_TYPE_CAMERA),
        iot_helpers.SENSOR_TYPE_STEREO: sensor_stale_seconds(iot_helpers.SENSOR_TYPE_STEREO),
        iot_helpers.SENSOR_TYPE_LIDAR: sensor_stale_seconds(iot_helpers.SENSOR_TYPE_LIDAR),
    }


def snapshot_age_seconds(reported_at: datetime | None, now: datetime | None = None) -> float | None:
    if not reported_at:
        return None
    current = now or datetime.now()
    return max(0.0, (current - reported_at).total_seconds())


def snapshot_is_stale(
    reported_at: datetime | None,
    now: datetime | None = None,
    sensor_type: Any = iot_helpers.SENSOR_TYPE_CAMERA,
) -> bool:
    age = snapshot_age_seconds(reported_at, now)
    return age is None or age > sensor_stale_seconds(sensor_type)


def latest_uploaded_camera_snapshot(robot_id: Any) -> dict[str, Any] | None:
    path = robot_camera_upload_path(robot_id)
    if not path.exists():
        return None
    content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    reported_at = datetime.fromtimestamp(path.stat().st_mtime)
    return {
        "content": path.read_bytes(),
        "contentType": content_type,
        "reportedAt": reported_at,
        "stale": snapshot_is_stale(reported_at),
        "source": "uploaded",
    }


def camera_response_headers(source: str, reported_at: datetime | None = None, stale: bool = False) -> dict[str, str]:
    headers = {
        "Cache-Control": "no-store",
        "X-Camera-Source": source,
        "X-Camera-Stale": "1" if stale else "0",
    }
    if reported_at:
        headers["X-Camera-Reported-At"] = to_iso_datetime(reported_at)
    return headers


async def fetch_robot_camera_snapshot(ip_address: str) -> tuple[bytes, str]:
    url = robot_camera_url(ip_address, "snapshot")
    timeout = httpx.Timeout(4.0, connect=1.5)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="摄像头快照不可达。") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"摄像头快照返回异常状态：{response.status_code}。")
    return response.content, response.headers.get("content-type") or "image/jpeg"


async def open_robot_camera_stream(ip_address: str) -> StreamingResponse:
    url = robot_camera_url(ip_address, "stream")
    timeout = httpx.Timeout(connect=2.0, read=None, write=5.0, pool=5.0)
    client = httpx.AsyncClient(timeout=timeout)
    try:
        request = client.build_request("GET", url)
        response = await client.send(request, stream=True)
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail="摄像头实时流不可达。") from exc
    if response.status_code != 200:
        await response.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"摄像头实时流返回异常状态：{response.status_code}。")

    async def stream_chunks():
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_chunks(),
        media_type=response.headers.get("content-type") or "multipart/x-mixed-replace;boundary=boundarydonotcross",
        headers={"Cache-Control": "no-store"},
    )


def local_ipv4_networks() -> list[ipaddress.IPv4Network]:
    networks: list[ipaddress.IPv4Network] = []
    seen: set[str] = set()
    try:
        output = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "scope", "global"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        for raw_line in output.splitlines():
            parts = raw_line.split()
            if "inet" not in parts:
                continue
            cidr = parts[parts.index("inet") + 1]
            interface = ipaddress.ip_interface(cidr)
            network = interface.network
            if network.version != 4 or interface.ip.is_loopback:
                continue
            if network.num_addresses > 256:
                network = ipaddress.ip_interface(f"{interface.ip}/24").network
            key = str(network)
            if key not in seen:
                seen.add(key)
                networks.append(network)
    except Exception:
        pass

    if networks:
        return networks

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip_text = sock.getsockname()[0]
        fallback = ipaddress.ip_interface(f"{ip_text}/24").network
        return [fallback]
    except Exception:
        return []


def local_ipv4_addresses() -> set[str]:
    addresses: set[str] = set()
    try:
        output = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "scope", "global"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        for raw_line in output.splitlines():
            parts = raw_line.split()
            if "inet" not in parts:
                continue
            cidr = parts[parts.index("inet") + 1]
            interface = ipaddress.ip_interface(cidr)
            if interface.version == 4 and not interface.ip.is_loopback:
                addresses.add(str(interface.ip))
    except Exception:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except Exception:
        pass
    return {item for item in addresses if item}


def probe_tcp_ports(ip_address: str, ports: tuple[int, ...] = ROBOT_DISCOVERY_PORTS) -> list[int]:
    open_ports: list[int] = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(ROBOT_DISCOVERY_TIMEOUT_SECONDS)
                if sock.connect_ex((ip_address, port)) == 0:
                    open_ports.append(port)
        except OSError:
            continue
    return open_ports


def reverse_lookup_host(ip_address: str) -> str:
    try:
        host_name, _, _ = socket.gethostbyaddr(ip_address)
        return host_name
    except OSError:
        return ""


def read_arp_mac(ip_address: str) -> str:
    arp_path = Path("/proc/net/arp")
    if not arp_path.exists():
        return ""
    try:
        for raw_line in arp_path.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
            columns = raw_line.split()
            if len(columns) >= 4 and columns[0] == ip_address:
                return columns[3].upper()
    except Exception:
        return ""
    return ""


def normalize_mac_prefix(mac_address: str) -> str:
    return "".join(char for char in mac_address.upper() if char.isalnum())[:6]


def load_recent_iot_identity_map() -> dict[str, dict[str, Any]]:
    if not mysql_ready():
        return {}
    rows = query_all(
        f"""
        SELECT t.source_ip, t.device_id, d.name AS device_name, d.model AS device_model, t.reported_at
        FROM device_telemetry t
        JOIN devices d ON d.id = t.device_id
        WHERE t.source_ip IS NOT NULL
          AND t.source_ip <> ''
          AND t.reported_at >= DATE_SUB(NOW(), INTERVAL {ROBOT_IDENTITY_TTL_HOURS} HOUR)
        ORDER BY t.reported_at DESC, t.id DESC
        """
    )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        source_ip = str(row.get("source_ip") or "").strip()
        if source_ip and source_ip not in result:
            result[source_ip] = {
                "deviceId": int(row["device_id"]),
                "deviceName": row.get("device_name") or "",
                "deviceModel": row.get("device_model") or "",
                "reportedAt": to_iso_datetime(row["reported_at"]),
            }
    return result


def load_recent_iot_log_identity_map() -> dict[str, dict[str, Any]]:
    if not mysql_ready():
        return {}
    rows = query_all(
        f"""
        SELECT t.device_id, d.name AS device_name, d.model AS device_model, MAX(t.reported_at) AS reported_at
        FROM device_telemetry t
        JOIN devices d ON d.id = t.device_id
        WHERE (t.source_ip IS NULL OR t.source_ip = '')
          AND t.reported_at >= DATE_SUB(NOW(), INTERVAL {ROBOT_IDENTITY_TTL_HOURS} HOUR)
        GROUP BY t.device_id, d.name, d.model
        ORDER BY reported_at DESC
        """
    )
    device_rows = [row for row in rows if row.get("device_id") is not None]
    if len(device_rows) != 1:
        return {}

    try:
        output = subprocess.check_output(
            ["journalctl", "-u", "project4-backend.service", "-n", "400", "--no-pager"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except Exception:
        return {}

    ip_matches = re.findall(r'(\d+\.\d+\.\d+\.\d+):\d+\s+-\s+"POST /api/iot/telemetry', output)
    unique_ips: list[str] = []
    for ip_text in ip_matches:
        try:
            normalized = parse_ipv4(ip_text, "source_ip")
        except HTTPException:
            continue
        if normalized not in unique_ips:
            unique_ips.append(normalized)

    if not unique_ips:
        return {}

    device = device_rows[0]
    payload = {
        "deviceId": int(device["device_id"]),
        "deviceName": device.get("device_name") or "",
        "deviceModel": device.get("device_model") or "",
        "reportedAt": to_iso_datetime(device["reported_at"]),
    }
    return {ip_text: dict(payload) for ip_text in unique_ips}


def classify_robot_candidate(
    host_name: str,
    mac_address: str,
    open_ports: list[int],
    iot_identity: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    host_token = host_name.lower()
    host_match = any(token in host_token for token in ROBOT_DISCOVERY_HOST_HINTS)
    mac_match = normalize_mac_prefix(mac_address) in RASPBERRY_PI_MAC_PREFIXES
    clues: list[str] = []
    if iot_identity:
        clues.append(
            f"iot={iot_identity.get('deviceName') or iot_identity.get('deviceModel') or iot_identity.get('deviceId')}"
        )
    if host_match and host_name:
        clues.append(f"hostname={host_name}")
    if mac_match and mac_address:
        clues.append(f"mac={mac_address}")
    if 22 in open_ports:
        clues.append("ssh")
    if any(port in open_ports for port in (80, 443, 8000)):
        clues.append("web")
    confirmed = bool(iot_identity or host_match or mac_match or ("ssh" in clues and host_token in ROBOT_DISCOVERY_HOST_HINTS))
    summary = ", ".join(clues) if clues else "reachable host"
    return confirmed, summary


def scan_robot_candidate(ip_address: str, iot_identity_map: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    open_ports = probe_tcp_ports(ip_address)
    if not open_ports:
        return None
    host_name = reverse_lookup_host(ip_address)
    mac_address = read_arp_mac(ip_address)
    iot_identity = iot_identity_map.get(ip_address)
    confirmed, summary = classify_robot_candidate(host_name, mac_address, open_ports, iot_identity)
    return {
        "ipAddress": ip_address,
        "hostName": host_name,
        "macAddress": mac_address,
        "openPorts": open_ports,
        "confirmed": confirmed,
        "summary": summary,
        "deviceId": iot_identity.get("deviceId") if iot_identity else None,
        "deviceName": iot_identity.get("deviceName") if iot_identity else "",
        "deviceModel": iot_identity.get("deviceModel") if iot_identity else "",
        "reportedAt": iot_identity.get("reportedAt") if iot_identity else "",
    }


def discover_robot_candidates(force: bool = False) -> dict[str, Any]:
    now = time.time()
    with ROBOT_DISCOVERY_LOCK:
        if (
            not force
            and ROBOT_DISCOVERY_CACHE["items"]
            and now - float(ROBOT_DISCOVERY_CACHE["scanned_at"] or 0.0) < ROBOT_DISCOVERY_TTL_SECONDS
        ):
            scanned_at = float(ROBOT_DISCOVERY_CACHE["scanned_at"])
            return {
                "items": list(ROBOT_DISCOVERY_CACHE["items"]),
                "scannedAt": datetime.fromtimestamp(scanned_at).isoformat(timespec="seconds"),
                "expiresAt": datetime.fromtimestamp(scanned_at + ROBOT_DISCOVERY_TTL_SECONDS).isoformat(
                    timespec="seconds"
                ),
                "subnets": list(ROBOT_DISCOVERY_CACHE["subnets"]),
            }

    networks = local_ipv4_networks()
    local_ips = local_ipv4_addresses()
    iot_identity_map = load_recent_iot_identity_map()
    if not iot_identity_map:
        iot_identity_map = load_recent_iot_log_identity_map()
    items: list[dict[str, Any]] = []
    futures = []
    with ThreadPoolExecutor(max_workers=48) as executor:
        for network in networks:
            for host in network.hosts():
                ip_text = str(host)
                if ip_text in local_ips:
                    continue
                futures.append(executor.submit(scan_robot_candidate, ip_text, iot_identity_map))
        for future in as_completed(futures):
            candidate = future.result()
            if candidate:
                items.append(candidate)

    items.sort(key=lambda item: (not item["confirmed"], item["hostName"] or item["ipAddress"], item["ipAddress"]))
    with ROBOT_DISCOVERY_LOCK:
        ROBOT_DISCOVERY_CACHE["items"] = items
        ROBOT_DISCOVERY_CACHE["scanned_at"] = now
        ROBOT_DISCOVERY_CACHE["subnets"] = [str(network) for network in networks]

    return {
        "items": list(items),
        "scannedAt": datetime.fromtimestamp(now).isoformat(timespec="seconds"),
        "expiresAt": datetime.fromtimestamp(now + ROBOT_DISCOVERY_TTL_SECONDS).isoformat(timespec="seconds"),
        "subnets": [str(network) for network in networks],
    }


def get_discovered_robot(ip_address: str) -> dict[str, Any] | None:
    with ROBOT_DISCOVERY_LOCK:
        scanned_at = float(ROBOT_DISCOVERY_CACHE["scanned_at"] or 0.0)
        if time.time() - scanned_at > ROBOT_DISCOVERY_TTL_SECONDS:
            return None
        for item in ROBOT_DISCOVERY_CACHE["items"]:
            if item.get("ipAddress") == ip_address:
                return dict(item)
    return None


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def derive_robot_network_status(telemetry_status: Any, signal: Any, reported_at: Any) -> str:
    reported_dt = _coerce_datetime(reported_at)
    status = str(telemetry_status or "").strip().lower()
    if status == "offline":
        return "offline"
    if status == "fault":
        return "warning"
    if reported_dt is None:
        return "offline"
    if (datetime.now() - reported_dt).total_seconds() > ROBOT_TELEMETRY_OFFLINE_SECONDS:
        return "offline"
    if signal is not None and int(signal) < ROBOT_WEAK_SIGNAL_THRESHOLD:
        return "warning"
    return "online"


def load_robots() -> list[dict[str, Any]]:
    rows = query_all(
        """
        SELECT r.id, r.model, r.ip_address, r.device_id, linked_device.id AS linked_device_id,
               r.status, r.health, r.battery, r.speed,
               r.`signal` AS signal_value, r.latency, r.lng, r.lat, r.heading, r.created_at,
               (
                   SELECT dt.battery
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                     AND dt.battery IS NOT NULL
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_battery,
               (
                   SELECT dt.`signal`
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                     AND dt.`signal` IS NOT NULL
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_signal,
               (
                   SELECT dt.status
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                     AND dt.status IS NOT NULL
                     AND dt.status <> ''
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_status,
               (
                   SELECT dt.lat
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                     AND dt.lat IS NOT NULL
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_lat,
               (
                   SELECT dt.lng
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                     AND dt.lng IS NOT NULL
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_lng,
               (
                   SELECT dt.reported_at
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_reported_at,
               (
                   SELECT dt.created_at
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_received_at,
               (
                   SELECT dt.source_ip
                   FROM device_telemetry dt
                   WHERE (
                       dt.device_id = COALESCE(r.device_id, linked_device.id)
                       OR (COALESCE(r.device_id, linked_device.id) IS NULL AND dt.source_ip = r.ip_address)
                   )
                   ORDER BY dt.created_at DESC, dt.id DESC
                   LIMIT 1
               ) AS telemetry_source_ip
        FROM robots r
        LEFT JOIN (
            SELECT id, robot_id
            FROM (
                SELECT d.id, d.robot_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY d.robot_id
                           ORDER BY d.created_at DESC, d.id DESC
                       ) AS rn
                FROM devices d
                WHERE d.robot_id IS NOT NULL
            ) ranked_devices
            WHERE rn = 1
        ) linked_device ON linked_device.robot_id = r.id
        ORDER BY r.created_at DESC, r.id DESC
        """
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        battery_value = row["telemetry_battery"] if row.get("telemetry_battery") is not None else row["battery"]
        signal_value = row["telemetry_signal"] if row.get("telemetry_signal") is not None else row["signal_value"]
        lng_value = row["telemetry_lng"] if row.get("telemetry_lng") is not None else row["lng"]
        lat_value = row["telemetry_lat"] if row.get("telemetry_lat") is not None else row["lat"]
        telemetry_seen_at = row.get("telemetry_received_at") or row.get("telemetry_reported_at")
        last_seen_at = telemetry_seen_at or row["created_at"]
        network_status = derive_robot_network_status(row.get("telemetry_status"), signal_value, telemetry_seen_at)
        items.append(
            {
                "id": row["id"],
                "model": row["model"],
                "ipAddress": row.get("ip_address") or "",
                "deviceId": row.get("device_id") or row.get("linked_device_id"),
                "status": row["status"],
                "health": int(row["health"]),
                "battery": int(battery_value),
                "speed": float(row["speed"]),
                "signal": int(signal_value),
                "latency": int(row["latency"]),
                "location": [float(lng_value), float(lat_value)],
                "heading": int(row["heading"]),
                "networkStatus": network_status,
                "telemetryStatus": str(row.get("telemetry_status") or ""),
                "lastSeenAt": to_iso_datetime(last_seen_at),
                "locationUpdatedAt": to_iso_datetime(last_seen_at),
                "isRealtime": telemetry_seen_at is not None,
                "createdAt": to_iso_datetime(row["created_at"]),
            }
        )
    return items




def load_alerts() -> list[dict[str, Any]]:
    rows = query_all(
        """
        SELECT id, level, title, detail, happened_at, created_at
        FROM alerts
        ORDER BY happened_at DESC, id DESC
        """
    )
    return [
        {
            "id": row["id"],
            "level": row["level"],
            "title": row["title"],
            "detail": row["detail"] or "",
            "happenedAt": to_iso_datetime(row["happened_at"]),
            "createdAt": to_iso_datetime(row["created_at"]),
        }
        for row in rows
    ]


def build_maintenance_items(robots: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for robot in robots:
        network_status = str(robot.get("networkStatus") or "").lower()
        battery = int(robot.get("battery") or 0)
        health = int(robot.get("health") or 0)
        if network_status == "offline":
            state = "critical"
            summary = f"{robot.get('model', '机器人')} 网络已离线，最近上报 {robot.get('lastSeenAt') or '-'}。"
        elif battery <= 20 or health < 60:
            state = "warning"
            summary = f"{robot.get('model', '机器人')} 电量或健康度偏低，请检查设备状态。"
        else:
            state = "normal"
            summary = f"{robot.get('model', '机器人')} 状态正常。"
        items.append({"id": robot.get("id"), "state": state, "summary": summary, "source": "robot"})
    for alert in alerts:
        level = str(alert.get("level") or "").lower()
        items.append({
            "id": alert.get("id"),
            "state": "critical" if level == "critical" else "warning",
            "summary": alert.get("title") or "告警待处理。",
            "source": "alert",
        })
    return items



def empty_dashboard_payload() -> dict[str, Any]:
    return {
        "site": DEFAULT_SITE,
        "counts": {"robots": 0, "tasks": 0, "alerts": 0},
        "robots": [],
        "alerts": [],
        "maintenance": [],
        "generatedAt": datetime.now().isoformat(timespec="minutes"),
    }


def build_dashboard_payload() -> dict[str, Any]:
    if not mysql_ready():
        return empty_dashboard_payload()
    robots = load_robots()
    alerts = load_alerts()
    tasks_count = 0
    try:
        row = query_one("SELECT COUNT(*) AS cnt FROM tasks")
        if row:
            tasks_count = row["cnt"]
    except Exception:
        pass
    return {
        "site": DEFAULT_SITE,
        "counts": {
            "robots": len(robots),
            "tasks": tasks_count,
            "alerts": len(alerts),
        },
        "robots": robots,
        "alerts": alerts,
        "maintenance": build_maintenance_items(robots, alerts),
        "generatedAt": datetime.now().isoformat(timespec="minutes"),
    }


def ws_dashboard_message(event: str) -> dict[str, Any]:
    # Unified websocket payload shape used by all push events.
    return {
        "type": "dashboard_update",
        "event": event,
        "pages": PAGES,
        "data": build_dashboard_payload(),
        "serverTime": datetime.now().isoformat(timespec="seconds"),
    }


async def ws_register(websocket: WebSocket) -> None:
    async with WS_LOCK:
        WS_CLIENTS.add(websocket)


async def ws_unregister(websocket: WebSocket) -> None:
    async with WS_LOCK:
        WS_CLIENTS.discard(websocket)


async def ws_broadcast(event: str) -> None:
    # Broadcast full dashboard snapshot and prune dead connections.
    async with WS_LOCK:
        clients = list(WS_CLIENTS)
    if not clients:
        return
    message = ws_dashboard_message(event)
    stale: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_json(message)
        except Exception:
            stale.append(client)
    if stale:
        async with WS_LOCK:
            for client in stale:
                WS_CLIENTS.discard(client)






def build_alert_record(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    if not title:
        raise HTTPException(status_code=422, detail="告警标题不能为空。")
    level = str(payload.get("level", "warning")).strip() or "warning"
    if level not in {"info", "warning", "critical"}:
        raise HTTPException(status_code=422, detail="告警等级必须是 info、warning 或 critical。")
    happened_at = payload.get("happenedAt")
    return {
        "level": level,
        "title": title,
        "detail": str(payload.get("detail", "")).strip(),
        "happened_at": parse_datetime(happened_at, "happenedAt") if happened_at else datetime.now(),
        "created_at": datetime.now(),
    }




def insert_robot(record: dict[str, Any]) -> None:
    execute_write(
        """
        INSERT INTO robots (
            model, ip_address, device_id, status, health, battery, speed, `signal`, latency, lng, lat, heading, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record["model"],
            record["ip_address"],
            record["device_id"],
            record["status"],
            record["health"],
            record["battery"],
            record["speed"],
            record["signal"],
            record["latency"],
            record["lng"],
            record["lat"],
            record["heading"],
            record["created_at"],
        ),
    )




def insert_alert(record: dict[str, Any]) -> None:
    execute_write(
        """
        INSERT INTO alerts (level, title, detail, happened_at, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            record["level"],
            record["title"],
            record["detail"],
            record["happened_at"],
            record["created_at"],
        ),
    )




def build_robot_record(payload: dict[str, Any]) -> dict[str, Any]:
    model = str(payload.get("model", "")).strip()
    if not model:
        raise HTTPException(status_code=422, detail="机器人名称不能为空。")
    ip_address = parse_ipv4(payload.get("ipAddress"), "ipAddress")
    discovered = get_discovered_robot(ip_address)
    if not payload.get("manualConfirm") and (not discovered or not discovered.get("confirmed")):
        raise HTTPException(status_code=422, detail="请先扫描当前 Wi-Fi 网络，并选择已确认的机器人后再添加。")
    device_id: int | None = None
    if payload.get("deviceId") not in {None, ""}:
        device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
        if not query_one("SELECT id FROM devices WHERE id = %s LIMIT 1", (device_id,)):
            raise HTTPException(status_code=404, detail="未找到对应设备。")
    elif discovered and discovered.get("deviceId"):
        device_id = int(discovered["deviceId"])
    return {
        "model": model,
        "ip_address": ip_address,
        "device_id": device_id,
        "status": str(payload.get("status", "idle")).strip() or "idle",
        "health": parse_int_range(payload.get("health", 92), "health"),
        "battery": parse_int_range(payload.get("battery", 78), "battery"),
        "speed": parse_float(payload.get("speed", 1.2), "speed"),
        "signal": parse_int_range(payload.get("signal", 88), "signal"),
        "latency": parse_int_range(payload.get("latency", 28), "latency", 0, 1000),
        "lng": parse_float(payload.get("lng", DEFAULT_SITE["center"][0]), "lng"),
        "lat": parse_float(payload.get("lat", DEFAULT_SITE["center"][1]), "lat"),
        "heading": parse_int_range(payload.get("heading", 0), "heading", 0, 359),
        "created_at": datetime.now(),
    }
def amap_script_tag() -> str:
    amap_key = os.getenv("AMAP_WEB_KEY", "").strip()
    if not amap_key:
        return ""
    return (
        '<script src="https://webapi.amap.com/maps?v=2.0&key='
        f"{amap_key}"
        '&plugin=AMap.Scale,AMap.ToolBar,AMap.PolygonEditor,AMap.Geolocation,AMap.Geocoder"></script>'
    )


def render_page(request: Request, page_id: str) -> HTMLResponse | RedirectResponse:
    # Common page renderer for all protected web pages.
    user = require_page_login(request)
    if isinstance(user, RedirectResponse):
        return user
    if page_id in {"control", "autopilot", "users", "clusters", "formations"} and not is_admin_user(user):
        return forbidden_page("仅管理员可访问当前管理页面。")
    safe_user = template_user(user)
    page = PAGES[page_id]
    return templates.TemplateResponse(
        request,
        "app.html",
        {
            "page_id": page_id,
            "page_title": page["title"],
            "page_route": page["route"],
            "page_kicker": page["kicker"],
            "amap_key": os.getenv("AMAP_WEB_KEY", "").strip(),
            "amap_script": amap_script_tag(),
            "current_user": safe_user,
            "pages": visible_pages_for_user(user),
            "site": DEFAULT_SITE,
            "mysql_ready": mysql_ready(),
            "asset_version": asset_version(),
            "video_config": video_config(),
            "vnc_config": vnc_config(),
            "robot_control_config": robot_control_config(),
        },
    )


def redirect_legacy_page(request: Request, page_id: str) -> RedirectResponse:
    user = require_page_login(request)
    if isinstance(user, RedirectResponse):
        return user
    return RedirectResponse(url=PAGES[page_id]["route"], status_code=302)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Application startup bootstrap: DB + schema + admin seed.
    if mysql_configured():
        try:
            logger.info("Initializing local MySQL database and schema.")
            ensure_database()
            execute_schema()
            ensure_iot_tables()
            try:
                ensure_autonomy_tables()
            except Exception as exc:  # pragma: no cover - optional migration resilience
                logger.exception("Autonomy event table migration failed: %s", exc)
            ensure_robot_ip_column()
            ensure_robot_device_column()
            ensure_management_system_tables()
            ensure_admin_user()
            APP_STATE["db_ready"] = True
            APP_STATE["db_error"] = ""
            logger.info("Database bootstrap complete; local admin account is available.")
        except Exception as exc:  # pragma: no cover - startup resilience
            APP_STATE["db_ready"] = False
            APP_STATE["db_error"] = str(exc)
            logger.exception("Database bootstrap failed: %s", exc)
    else:
        APP_STATE["db_ready"] = False
        APP_STATE["db_error"] = "MySQL 未配置。"
        logger.warning(APP_STATE["db_error"])
    yield


app = FastAPI(title="机器人巡检平台", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-local-secret"))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def env_float_setting(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return float(raw_value)
    except ValueError:
        return default


def iot_ingest_throttle_interval(request: Request) -> tuple[str, str, float] | None:
    if request.method != "POST":
        return None
    path = request.url.path
    if path == "/api/iot/camera/snapshot":
        interval = env_float_setting("IOT_CAMERA_SNAPSHOT_MIN_INTERVAL_SECONDS", 2.0)
        channel = request.query_params.get("channel", "mono").strip().lower() or "mono"
        return "camera", channel, interval
    if path == "/api/iot/sensor/data":
        interval = env_float_setting("IOT_SENSOR_DATA_MIN_INTERVAL_SECONDS", 1.0)
        return "sensor", "data", interval
    return None


def mark_robot_control_priority_window() -> None:
    duration = env_float_setting("ROBOT_CONTROL_INGEST_PAUSE_SECONDS", 5.0)
    if duration <= 0:
        return
    pause_until = time.monotonic() + duration
    with ROBOT_CONTROL_PRIORITY_LOCK:
        ROBOT_CONTROL_PRIORITY_STATE["ingest_pause_until"] = max(
            ROBOT_CONTROL_PRIORITY_STATE.get("ingest_pause_until", 0.0),
            pause_until,
        )


def robot_control_priority_active() -> bool:
    with ROBOT_CONTROL_PRIORITY_LOCK:
        return time.monotonic() < ROBOT_CONTROL_PRIORITY_STATE.get("ingest_pause_until", 0.0)


@app.middleware("http")
async def prioritize_robot_control(request: Request, call_next):
    throttle = iot_ingest_throttle_interval(request)
    if throttle is not None:
        group, channel, interval = throttle
        if robot_control_priority_active():
            return JSONResponse({
                "ok": True,
                "skipped": True,
                "reason": "robot_control_active",
                "retryAfter": round(max(0.0, ROBOT_CONTROL_PRIORITY_STATE.get("ingest_pause_until", 0.0) - time.monotonic()), 3),
            }, status_code=202)
        if interval > 0:
            source = request.client.host if request.client else ""
            key = (source, group, channel)
            now = time.monotonic()
            with IOT_INGEST_THROTTLE_LOCK:
                last_seen = IOT_INGEST_THROTTLE_STATE.get(key, 0.0)
                if now - last_seen < interval:
                    return JSONResponse({
                        "ok": True,
                        "skipped": True,
                        "reason": "rate_limited",
                        "retryAfter": round(interval - (now - last_seen), 3),
                    }, status_code=202)
                IOT_INGEST_THROTTLE_STATE[key] = now
    return await call_next(request)


# Auth + page routes
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    login_token = issue_login_token(request)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "mysql_ready": mysql_ready(),
            "mysql_error": APP_STATE["db_error"],
            "allow_self_register": self_registration_allowed(),
            "current_user": template_user(current_user(request)),
            "login_token": login_token,
            "asset_version": asset_version(),
        },
    )


@app.post("/auth/login")
async def login(request: Request) -> JSONResponse:
    if not mysql_ready():
        raise HTTPException(status_code=503, detail=APP_STATE["db_error"] or "MySQL 当前不可用。")
    payload = await request.json()
    verify_login_token(request, payload)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    if not username or not password:
        raise HTTPException(status_code=422, detail="用户名和密码不能为空。")
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误。")
    if str(user.get("status", "active")).strip().lower() == "disabled":
        raise HTTPException(status_code=403, detail="当前账号已被禁用。")
    if is_legacy_password_hash(user.get("password_hash")):
        user["password_hash"] = hash_password(password)
        execute_write(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (user["password_hash"], user["id"]),
        )
    establish_user_session(request, user)
    return JSONResponse(
        {
            "ok": True,
            "user": {"username": user["username"], "displayName": user["display_name"]},
            "redirect": PAGES["overview"]["route"],
        }
    )


@app.post("/auth/register")
async def register(request: Request) -> JSONResponse:
    if not mysql_ready():
        raise HTTPException(status_code=503, detail=APP_STATE["db_error"] or "MySQL 当前不可用。")
    if not self_registration_allowed():
        raise HTTPException(status_code=403, detail="当前环境未开放注册。")
    payload = await request.json()
    verify_login_token(request, payload)
    username, password, display_name = validate_auth_user_payload(payload)
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="用户名已存在。")
    password_hash = hash_password(password)
    execute_write(
        "INSERT INTO users (username, password_hash, display_name, status, created_at) VALUES (%s, %s, %s, 'active', %s)",
        (username, password_hash, display_name, datetime.now()),
    )
    establish_user_session(
        request,
        {"username": username, "password_hash": password_hash, "display_name": display_name, "status": "active"},
    )
    return JSONResponse(
        {
            "ok": True,
            "user": {"username": username, "displayName": display_name},
            "redirect": PAGES["overview"]["route"],
        }
    )


@app.post("/auth/logout")
async def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"ok": True, "redirect": "/login"})


@app.get("/", response_class=HTMLResponse)
async def root_page(request: Request):
    return redirect_legacy_page(request, "overview")


@app.get("/overview", response_class=HTMLResponse)
async def overview_page(request: Request):
    return render_page(request, "overview")






@app.get("/monitoring_dashboard", response_class=HTMLResponse)
async def legacy_status_page(request: Request):
    return redirect_legacy_page(request, "status")


@app.get("/robots", response_class=HTMLResponse)
async def status_page(request: Request):
    return render_page(request, "status")


@app.get("/video", response_class=HTMLResponse)
async def video_page(request: Request):
    return render_page(request, "video")


@app.get("/control", response_class=HTMLResponse)
async def control_page(request: Request):
    return render_page(request, "control")


@app.get("/autopilot", response_class=HTMLResponse)
async def autopilot_page(request: Request):
    return render_page(request, "autopilot")


@app.get("/perception", response_class=HTMLResponse)
async def perception_page(request: Request):
    return render_page(request, "perception")


@app.get("/sensors", response_class=HTMLResponse)
async def sensors_page(request: Request):
    return render_page(request, "sensors")


@app.get("/maps", response_class=HTMLResponse)
async def maps_page(request: Request):
    return render_page(request, "maps")



@app.get("/device-management", response_class=HTMLResponse)
async def device_management_page(request: Request):
    return render_page(request, "device_management")


@app.get("/clusters", response_class=HTMLResponse)
async def clusters_page(request: Request):
    return render_page(request, "clusters")


@app.get("/formations", response_class=HTMLResponse)
async def formations_page(request: Request):
    return render_page(request, "formations")



@app.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    return render_page(request, "devices")


@app.get("/api/dashboard")
async def api_dashboard(request: Request) -> JSONResponse:
    require_api_login(request)
    return JSONResponse({"pages": PAGES, "data": build_dashboard_payload()})


@app.get("/api/robot-maps")
async def api_robot_maps(request: Request) -> JSONResponse:
    require_api_login(request)
    return JSONResponse(
        {
            "items": load_robot_map_catalog(),
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.post("/api/robot-maps/sync")
async def api_sync_robot_maps(request: Request) -> JSONResponse:
    require_api_login(request)
    payload = await request.json()
    robot_id = payload.get("robotId")
    robot_ip = str(payload.get("sourceHost") or "").strip()
    if robot_id not in (None, "") and mysql_ready():
        parsed_robot_id = parse_strict_id(robot_id, "robotId")
        robot = query_one("SELECT id, model, ip_address FROM robots WHERE id = %s", (parsed_robot_id,))
        if not robot:
            raise HTTPException(status_code=404, detail="未找到对应机器人。")
        robot_ip = str(robot.get("ip_address") or robot_ip).strip()
    if not robot_ip:
        robot_ip = str(os.getenv("ROBOT_MAP_SYNC_HOST", "")).strip()
    if not robot_ip:
        raise HTTPException(status_code=422, detail="未找到可同步地图的机器人 IP。")
    loop = asyncio.get_running_loop()
    synced = await loop.run_in_executor(None, sync_robot_map_from_host, robot_ip, payload)
    return JSONResponse(
        {
            "ok": True,
            "synced": synced,
            "items": load_robot_map_catalog(),
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
        }
    )


# Health + realtime routes
@app.get("/api/health")
async def api_health() -> JSONResponse:
    configured = mysql_configured()
    ready = mysql_ready()
    status = "ok" if ready else "degraded"
    payload = {
        "status": status,
        "mysqlConfigured": configured,
        "mysqlReady": ready,
        "detail": APP_STATE["db_error"] if APP_STATE["db_error"] else "",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return JSONResponse(payload, status_code=200 if ready else 503)


@app.get("/health")
async def health() -> JSONResponse:
    return await api_health()


@app.get("/debug/config")
async def debug_config() -> JSONResponse:
    if not debug_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    mysql = mysql_settings()
    payload = {
        "debug": True,
        "backend": {
            "host": os.getenv("BACKEND_HOST", "127.0.0.1"),
            "port": int(os.getenv("BACKEND_PORT", "8000") or "8000"),
        },
        "mysql": {
            "host": mysql["host"],
            "port": mysql["port"],
            "user": mysql["user"],
            "database": mysql["database"],
            "charset": mysql["charset"],
            "passwordConfigured": bool(mysql["password"]),
            "ready": mysql_ready(),
        },
        "auth": {
            "adminUsername": admin_username(),
            "allowSelfRegister": self_registration_allowed(),
            "sessionSecretConfigured": bool(os.getenv("SESSION_SECRET", "")),
        },
        "paths": {
            "root": str(ROOT_DIR),
            "backend": str(BASE_DIR),
            "schema": str(SCHEMA_FILE),
        },
    }
    return JSONResponse(payload)


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    session = websocket.scope.get("session") or {}
    if not session.get("username"):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    await ws_register(websocket)
    try:
        await websocket.send_json(ws_dashboard_message("connected"))
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() in {"ping", "heartbeat"}:
                await websocket.send_json({"type": "pong", "serverTime": datetime.now().isoformat(timespec="seconds")})
            elif message.strip().lower() == "refresh":
                await websocket.send_json(ws_dashboard_message("refresh"))
    except WebSocketDisconnect:
        pass
    finally:
        await ws_unregister(websocket)


# CRUD API routes
@app.get("/api/robots")
async def api_robots(request: Request) -> JSONResponse:
    require_api_login(request)
    return JSONResponse({"items": load_robots() if mysql_ready() else []})


@app.get("/api/robots/discovery")
async def api_robot_discovery(request: Request, refresh: int = 0) -> JSONResponse:
    require_api_login(request)
    return JSONResponse(discover_robot_candidates(force=bool(refresh)))


def optional_robot_id_from_payload(payload: dict[str, Any]) -> int | None:
    value = payload.get("robotId")
    if value in (None, ""):
        return None
    return parse_strict_id(value, "robotId")


def autopilot_payload_with_robot_id(payload: dict[str, Any], robot_id: int | None) -> dict[str, Any]:
    if robot_id is None:
        return dict(payload)
    return {**payload, "robotId": robot_id}


def try_autopilot_stop(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return robot_control_stop_result(payload)
    except HTTPException as exc:
        return {"ok": False, "statusCode": exc.status_code, "detail": exc.detail}


def autopilot_response(status: dict[str, Any], stop_result: dict[str, Any] | None = None) -> dict[str, Any]:
    response = {"ok": True, **status}
    if stop_result is not None:
        response["stopResult"] = stop_result
    response["controlPriority"] = list(AUTOPILOT_CONTROL_PRIORITY)
    return response


def handle_autopilot_state_error(exc: ValueError) -> None:
    if str(exc) == "estop_active":
        raise HTTPException(status_code=409, detail="急停已触发，必须手动解除后才能启动或继续自动驾驶。") from exc
    raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/autopilot/status")
async def api_autopilot_status(limit: int = 20) -> JSONResponse:
    return JSONResponse(autopilot_response(AUTOPILOT_RUNTIME.status(event_limit=limit)))


@app.get("/api/autopilot/events")
async def api_autopilot_events(request: Request, limit: int = 20, robotId: Optional[int] = None) -> JSONResponse:
    require_api_login(request)
    return JSONResponse({"items": AUTOPILOT_RUNTIME.events(limit, robot_id=robotId)})


@app.get("/api/autopilot/debug-log")
async def api_autopilot_debug_log(request: Request, limit: int = 50) -> Response:
    require_admin_login(request)
    payload = AUTOPILOT_RUNTIME.debug_log(event_limit=limit)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="autopilot-debug-{stamp}.json"'},
    )


@app.post("/api/autopilot/start")
async def api_autopilot_start(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    try:
        status = AUTOPILOT_RUNTIME.start(robot_id=robot_id)
    except ValueError as exc:
        handle_autopilot_state_error(exc)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status))


@app.post("/api/autopilot/deadman")
async def api_autopilot_deadman(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    source = str(payload.get("source") or "web").strip() or "web"
    status = AUTOPILOT_RUNTIME.renew_deadman(source=source, robot_id=robot_id)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status))


@app.post("/api/autopilot/pause")
async def api_autopilot_pause(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    payload = autopilot_payload_with_robot_id(payload, robot_id)
    status = AUTOPILOT_RUNTIME.pause(robot_id=robot_id)
    stop_result = await run_in_threadpool(try_autopilot_stop, payload)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status, stop_result))


@app.post("/api/autopilot/resume")
async def api_autopilot_resume(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    try:
        status = AUTOPILOT_RUNTIME.resume(robot_id=robot_id)
    except ValueError as exc:
        handle_autopilot_state_error(exc)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status))


@app.post("/api/autopilot/stop")
async def api_autopilot_stop(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    payload = autopilot_payload_with_robot_id(payload, robot_id)
    status = AUTOPILOT_RUNTIME.stop(robot_id=robot_id)
    stop_result = await run_in_threadpool(try_autopilot_stop, payload)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status, stop_result))


@app.post("/api/autopilot/estop")
async def api_autopilot_estop(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    payload = autopilot_payload_with_robot_id(payload, robot_id)
    status = AUTOPILOT_RUNTIME.estop(robot_id=robot_id)
    stop_result = await run_in_threadpool(try_autopilot_stop, payload)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status, stop_result))


@app.post("/api/autopilot/clear-estop")
async def api_autopilot_clear_estop(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    robot_id = optional_robot_id_from_payload(payload)
    status = AUTOPILOT_RUNTIME.clear_estop(robot_id=robot_id)
    await ws_broadcast("autopilot")
    return JSONResponse(autopilot_response(status))


@app.post("/api/iot/autopilot/status")
async def api_iot_autopilot_status(request: Request) -> JSONResponse:
    device_id = await run_in_threadpool(require_device_token, request)
    payload = await request.json()
    robot_id = payload.get("robotId")
    if robot_id in (None, "") and mysql_ready():
        row = await run_in_threadpool(query_one, "SELECT robot_id FROM devices WHERE id = %s LIMIT 1", (device_id,))
        robot_id = row.get("robot_id") if row else None
    status = AUTOPILOT_RUNTIME.update_report(payload, device_id=device_id, robot_id=robot_id)
    await ws_broadcast("autopilot")
    return JSONResponse({"ok": True, "status": status})


def robot_control_status_result(robot_id: Optional[str] = None) -> dict[str, Any]:
    target = resolve_robot_control_target(robot_id)
    response = send_robot_control_command(target, {"type": "ping"}, "pong")
    ensure_robot_control_ack_ok(response)
    return {"ok": True, "target": target, "response": response}


def robot_control_cmd_vel_result(payload: dict[str, Any]) -> dict[str, Any]:
    target = resolve_robot_control_target(payload.get("robotId"))
    if AUTOPILOT_RUNTIME.is_estopped():
        raise HTTPException(status_code=423, detail="急停已触发，必须先解除急停。")
    linear = normalize_control_value(payload.get("linear", 0.0), ROBOT_CONTROL_MAX_LINEAR, "linear")
    angular = normalize_control_value(payload.get("angular", 0.0), ROBOT_CONTROL_MAX_ANGULAR, "angular")
    AUTOPILOT_RUNTIME.note_manual_override(robot_id=target.get("robotId"), source="robot_control")
    if robot_control_mode() == "queue":
        command_id = insert_control_command(
            {
                "scope": "robot",
                "targetType": "robot",
                "targetId": target["robotId"],
                "commandType": "cmd_vel",
                "params": {"linear": linear, "angular": angular},
                "status": CONTROL_COMMAND_PENDING_STATUS,
                "createdAt": datetime.now(),
            }
        )
        return {"ok": True, "queued": True, "commandId": command_id, "target": target, "linear": linear, "angular": angular}
    response = send_robot_control_command(
        target,
        {"type": "cmd_vel", "v": linear, "w": angular},
        "ack",
        close_after=False,
    )
    ensure_robot_control_ack_ok(response)
    return {
        "ok": True,
        "target": target,
        "linear": linear,
        "angular": angular,
        "response": response,
    }


def robot_control_stop_result(payload: dict[str, Any]) -> dict[str, Any]:
    target = resolve_robot_control_target(payload.get("robotId"))
    if not AUTOPILOT_RUNTIME.is_estopped():
        AUTOPILOT_RUNTIME.note_manual_override(robot_id=target.get("robotId"), source="robot_control_stop")
    if robot_control_mode() == "queue":
        command_id = insert_control_command(
            {
                "scope": "robot",
                "targetType": "robot",
                "targetId": target["robotId"],
                "commandType": "stop",
                "params": {},
                "status": CONTROL_COMMAND_PENDING_STATUS,
                "createdAt": datetime.now(),
            }
        )
        close_robot_control_socket(target)
        return {"ok": True, "queued": True, "commandId": command_id, "target": target}
    response = send_robot_control_command(target, {"type": "stop"}, "ack")
    ensure_robot_control_ack_ok(response)
    return {"ok": True, "target": target, "response": response}


@app.get("/api/robot-control/status")
async def api_robot_control_status(request: Request, robotId: Optional[str] = None) -> JSONResponse:
    require_admin_login(request)
    mark_robot_control_priority_window()
    return JSONResponse(await run_in_threadpool(robot_control_status_result, robotId))


@app.post("/api/robot-control/cmd_vel")
async def api_robot_control_cmd_vel(request: Request) -> JSONResponse:
    require_admin_login(request)
    mark_robot_control_priority_window()
    payload = await request.json()
    return JSONResponse(await run_in_threadpool(robot_control_cmd_vel_result, payload))


@app.post("/api/robot-control/stop")
async def api_robot_control_stop(request: Request) -> JSONResponse:
    require_admin_login(request)
    mark_robot_control_priority_window()
    payload = await request.json()
    return JSONResponse(await run_in_threadpool(robot_control_stop_result, payload))


@app.post("/api/control/commands")
async def api_create_control_command(request: Request) -> JSONResponse:
    require_admin_login(request)
    record = validate_control_command_payload(await request.json())
    result = create_control_command(record)
    return JSONResponse(result)


@app.get("/api/iot/control/commands")
async def api_iot_next_control_command(request: Request) -> JSONResponse:
    device_id = await run_in_threadpool(require_device_token, request)
    robot_row = await run_in_threadpool(query_one, "SELECT robot_id FROM devices WHERE id = %s LIMIT 1", (device_id,))
    robot_id = robot_row.get("robot_id") if robot_row else None
    if not robot_id:
        return JSONResponse({"command": None})
    command = await run_in_threadpool(
        query_one,
        """
        SELECT id, command_type, params_json
        FROM control_commands
        WHERE target_type = 'robot' AND target_id = %s AND status = %s
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """,
        (robot_id, CONTROL_COMMAND_PENDING_STATUS),
    )
    if not command:
        return JSONResponse({"command": None})
    await run_in_threadpool(update_control_command, command["id"], CONTROL_COMMAND_DELIVERED_STATUS, completed=False)
    params = json.loads(command.get("params_json") or "{}")
    return JSONResponse({"command": {"id": command["id"], "type": command["command_type"], "params": params}})


@app.post("/api/iot/control/commands/{command_id}/ack")
async def api_iot_ack_control_command(command_id: int, request: Request) -> JSONResponse:
    await run_in_threadpool(require_device_token, request)
    command_id = parse_strict_id(command_id, "command_id")
    payload = await request.json()
    ok = bool(payload.get("ok"))
    response = payload.get("response")
    error = str(payload.get("error") or "").strip()
    await run_in_threadpool(
        update_control_command,
        command_id,
        CONTROL_COMMAND_SUCCESS_STATUS if ok else CONTROL_COMMAND_FAILED_STATUS,
        response=response,
        error=error,
        completed=True,
    )
    return JSONResponse({"ok": True})


@app.get("/api/robots/{robot_id}/camera/snapshot")
async def api_robot_camera_snapshot(robot_id: int, request: Request) -> Response:
    require_api_login(request)
    robot = load_robot_camera_target(robot_id)
    try:
        content, media_type = await fetch_robot_camera_snapshot(robot["ip_address"])
        return Response(content=content, media_type=media_type, headers=camera_response_headers("live", datetime.now(), False))
    except HTTPException:
        pass

    uploaded = latest_uploaded_camera_snapshot(robot_id)
    if uploaded and not uploaded["stale"]:
        return Response(
            content=uploaded["content"],
            media_type=uploaded["contentType"],
            headers=camera_response_headers("uploaded", uploaded["reportedAt"], False),
        )

    fallback = _fallback_iot_snapshot(robot_id, robot["ip_address"])
    if fallback:
        file_path = STATIC_DIR / fallback["file_path"].lstrip("/static/")
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                media_type=fallback.get("content_type") or "image/jpeg",
                headers=camera_response_headers("iot", coerce_datetime(fallback.get("reported_at")), False),
            )
    raise HTTPException(status_code=502, detail="摄像头快照不可达，且没有新鲜的上传画面。")


def _fallback_iot_snapshot(robot_id: Any, ip_address: str) -> dict[str, Any] | None:
    """通过机器人关联设备查找最新摄像头快照，旧数据回退到 source_ip。"""
    if not mysql_ready():
        return None
    resolution = resolve_robot_device(robot_id)
    device_id = resolution.get("deviceId")
    if not device_id:
        return None
    # 查找该设备最新的摄像头快照
    snap = query_one(
        """
        SELECT file_path, content_type, reported_at FROM device_sensor_data
        WHERE device_id = %s AND sensor_type IN ('camera', 'stereo') AND file_path IS NOT NULL
        ORDER BY reported_at DESC, id DESC LIMIT 1
        """,
        (device_id,),
    )
    if snap and snapshot_is_stale(coerce_datetime(snap.get("reported_at")), sensor_type=SENSOR_TYPE_CAMERA):
        return None
    return snap


@app.get("/api/robots/{robot_id}/camera/stream")
async def api_robot_camera_stream(robot_id: int, request: Request) -> StreamingResponse:
    require_api_login(request)
    robot = load_robot_camera_target(robot_id)
    return await open_robot_camera_stream(robot["ip_address"])


@app.post("/api/robots")
async def api_create_robot(request: Request) -> JSONResponse:
    require_api_login(request)
    record = build_robot_record(await request.json())
    insert_robot(record)
    await ws_broadcast("robot_created")
    return JSONResponse({"ok": True})


@app.delete("/api/robots/{robot_id}")
async def api_delete_robot(robot_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    robot_id = parse_strict_id(robot_id, "robot_id")
    if clear_table("robots", robot_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    await ws_broadcast("robot_deleted")
    return JSONResponse({"ok": True})


@app.get("/api/alerts")
async def api_alerts(request: Request) -> JSONResponse:
    require_api_login(request)
    return JSONResponse({"items": load_alerts() if mysql_ready() else []})


@app.post("/api/alerts")
async def api_create_alert(request: Request) -> JSONResponse:
    require_api_login(request)
    record = build_alert_record(await request.json())
    insert_alert(record)
    await ws_broadcast("alert_created")
    return JSONResponse({"ok": True})


@app.delete("/api/alerts/{alert_id}")
async def api_delete_alert(alert_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    alert_id = parse_strict_id(alert_id, "alert_id")
    if clear_table("alerts", alert_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应告警。")
    await ws_broadcast("alert_deleted")
    return JSONResponse({"ok": True})


UPLOAD_DIR = STATIC_DIR / "uploads" / "devices"
SENSOR_UPLOAD_DIR = STATIC_DIR / "uploads" / "sensors"
CAMERA_UPLOAD_DIR = STATIC_DIR / "uploads" / "cameras"
MAP_UPLOAD_DIR = STATIC_DIR / "uploads" / "maps"


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SENSOR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CAMERA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    MAP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def load_robot_map_catalog() -> list[dict[str, Any]]:
    if not MAP_UPLOAD_DIR.exists():
        return []
    items: list[dict[str, Any]] = []
    for metadata_path in sorted(MAP_UPLOAD_DIR.glob("**/metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(metadata, dict):
            continue
        image_url = str(metadata.get("imageUrl") or "").strip()
        if not image_url:
            image_path = metadata_path.with_suffix(".png")
            if image_path.exists():
                try:
                    image_url = f"/static/{image_path.relative_to(STATIC_DIR).as_posix()}"
                except ValueError:
                    image_url = ""
        item = {
            "id": str(metadata.get("id") or metadata_path.parent.name),
            "name": str(metadata.get("name") or metadata_path.parent.name),
            "robotId": metadata.get("robotId"),
            "robotName": metadata.get("robotName") or "",
            "sourceHost": metadata.get("sourceHost") or "",
            "sourceYamlPath": metadata.get("sourceYamlPath") or "",
            "sourceImagePath": metadata.get("sourceImagePath") or "",
            "yamlUrl": metadata.get("yamlUrl") or "",
            "pgmUrl": metadata.get("pgmUrl") or "",
            "imageUrl": image_url,
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "resolution": metadata.get("resolution"),
            "origin": metadata.get("origin") if isinstance(metadata.get("origin"), list) else [],
            "occupiedThresh": metadata.get("occupiedThresh"),
            "freeThresh": metadata.get("freeThresh"),
            "negate": metadata.get("negate"),
            "sizeMeters": metadata.get("sizeMeters") if isinstance(metadata.get("sizeMeters"), dict) else {},
            "sourceMtime": metadata.get("sourceMtime") or "",
            "syncedAt": metadata.get("syncedAt") or "",
        }
        items.append(item)
    return sorted(items, key=lambda item: (str(item.get("syncedAt") or ""), str(item.get("name") or "")), reverse=True)


def static_url_for_path(path: Path) -> str:
    return f"/static/{quote(path.relative_to(STATIC_DIR).as_posix(), safe='/')}"


def find_robot_map_metadata_path(map_id: str) -> Path | None:
    if not map_id or not MAP_UPLOAD_DIR.exists():
        return None
    for metadata_path in MAP_UPLOAD_DIR.glob("**/metadata.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(metadata.get("id") or "") == str(map_id):
            return metadata_path
    return None


def slugify_robot_map(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def pick_robot_map_file(local_dir: Path, suffix: str) -> Path:
    existing = sorted(local_dir.glob(f"*{suffix}"))
    if existing:
        return existing[0]
    return local_dir / f"{local_dir.name}{suffix}"


def robot_map_sync_credentials() -> dict[str, Any]:
    return {
        "user": os.getenv("ROBOT_MAP_SYNC_USER", "wheeltec").strip() or "wheeltec",
        "password": os.getenv("ROBOT_MAP_SYNC_PASSWORD", "").strip(),
        "port": int(os.getenv("ROBOT_MAP_SYNC_PORT", "22").strip() or "22"),
        "timeout": float(os.getenv("ROBOT_MAP_SYNC_TIMEOUT", "12").strip() or "12"),
        "defaultYaml": os.getenv("ROBOT_MAP_SYNC_DEFAULT_YAML", "").strip(),
    }


def sync_robot_map_from_host(host: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        import paramiko
        import yaml
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"地图同步依赖缺失：{exc.name}。") from exc

    import posixpath

    credentials = robot_map_sync_credentials()
    if not credentials["password"]:
        raise HTTPException(status_code=503, detail="未配置 ROBOT_MAP_SYNC_PASSWORD，无法连接无人车同步地图。")

    selected_id = str(payload.get("id") or "").strip()
    remote_yaml = str(payload.get("sourceYamlPath") or credentials["defaultYaml"] or "").strip()
    if not remote_yaml:
        raise HTTPException(status_code=422, detail="未找到车端地图 YAML 路径。")

    metadata_path = find_robot_map_metadata_path(selected_id)
    local_dir = metadata_path.parent if metadata_path else None
    existing_metadata: dict[str, Any] = {}
    if metadata_path:
        try:
            existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_metadata = {}

    map_name = str(payload.get("name") or existing_metadata.get("name") or Path(remote_yaml).stem or "SLAM 地图")
    robot_id = payload.get("robotId") or existing_metadata.get("robotId")
    robot_folder = f"robot-{robot_id}" if robot_id not in (None, "") else f"host-{host.replace('.', '-')}"
    if local_dir is None:
        fallback_slug = hashlib.sha1(remote_yaml.encode("utf-8")).hexdigest()[:8]
        local_dir = MAP_UPLOAD_DIR / robot_folder / slugify_robot_map(map_name, f"map-{fallback_slug}")
    local_dir.mkdir(parents=True, exist_ok=True)
    local_yaml = pick_robot_map_file(local_dir, ".yaml")
    local_pgm = pick_robot_map_file(local_dir, ".pgm")
    local_png = pick_robot_map_file(local_dir, ".png")
    metadata_path = local_dir / "metadata.json"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            host,
            port=credentials["port"],
            username=credentials["user"],
            password=credentials["password"],
            timeout=credentials["timeout"],
            banner_timeout=credentials["timeout"],
            auth_timeout=credentials["timeout"],
        )
        sftp = ssh.open_sftp()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_yaml = temp_path / "map.yaml"
                temp_pgm = temp_path / "map.pgm"
                temp_png = temp_path / "map.png"
                sftp.get(remote_yaml, str(temp_yaml))
                raw_meta = yaml.safe_load(temp_yaml.read_text(encoding="utf-8")) or {}
                remote_image = str(payload.get("sourceImagePath") or raw_meta.get("image") or "").strip()
                if not remote_image:
                    raise HTTPException(status_code=422, detail="地图 YAML 中未找到 image 字段。")
                if not remote_image.startswith("/"):
                    remote_image = posixpath.normpath(posixpath.join(posixpath.dirname(remote_yaml), remote_image))
                sftp.get(remote_image, str(temp_pgm))
                yaml_stat = sftp.stat(remote_yaml)
                pgm_stat = sftp.stat(remote_image)
                with Image.open(temp_pgm) as image:
                    gray = image.convert("L")
                    width, height = gray.size
                    gray.save(temp_png, optimize=True)
                shutil.move(str(temp_yaml), local_yaml)
                shutil.move(str(temp_pgm), local_pgm)
                shutil.move(str(temp_png), local_png)
        finally:
            sftp.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步车端地图失败：{exc}") from exc
    finally:
        ssh.close()

    resolution = float(raw_meta.get("resolution") or 0)
    size_meters = {
        "width": round(width * resolution, 3) if resolution else None,
        "height": round(height * resolution, 3) if resolution else None,
    }
    map_id = selected_id or str(existing_metadata.get("id") or f"{robot_folder}-{local_dir.name}")
    metadata = {
        "id": map_id,
        "name": map_name,
        "robotId": robot_id,
        "robotName": payload.get("robotName") or existing_metadata.get("robotName") or "",
        "sourceHost": host,
        "sourceYamlPath": remote_yaml,
        "sourceImagePath": remote_image,
        "yamlUrl": static_url_for_path(local_yaml),
        "pgmUrl": static_url_for_path(local_pgm),
        "imageUrl": static_url_for_path(local_png),
        "width": width,
        "height": height,
        "resolution": resolution,
        "origin": raw_meta.get("origin") if isinstance(raw_meta.get("origin"), list) else [],
        "occupiedThresh": raw_meta.get("occupied_thresh"),
        "freeThresh": raw_meta.get("free_thresh"),
        "negate": raw_meta.get("negate"),
        "sizeMeters": size_meters,
        "sourceMtime": datetime.fromtimestamp(max(pgm_stat.st_mtime, yaml_stat.st_mtime)).isoformat(timespec="seconds"),
        "syncedAt": datetime.now().isoformat(timespec="seconds"),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def ensure_device_exists(device_id: int | None) -> None:
    if device_id is None:
        return
    if not query_one("SELECT id FROM devices WHERE id = %s", (device_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备。")


# 鈹€鈹€ 璁惧绠＄悊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
def ensure_unique_table_name(table_name: str, name: str, label: str, record_id: int | None = None) -> None:
    normalized = normalized_name_key(name)
    if not normalized:
        raise HTTPException(status_code=422, detail=f"{label}名称不能为空。")
    sql = f"SELECT id FROM {table_name} WHERE LOWER(TRIM(name)) = %s"
    params: list[Any] = [normalized]
    if record_id is not None:
        sql += " AND id <> %s"
        params.append(record_id)
    sql += " LIMIT 1"
    if query_one(sql, tuple(params)):
        raise HTTPException(status_code=409, detail=f"{label}名称已存在。")


def ensure_no_related_records(table_name: str, where_clause: str, params: tuple[Any, ...], detail: str) -> None:
    row = query_one(f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE {where_clause}", params)
    if int(row.get("cnt", 0) if row else 0) > 0:
        raise HTTPException(status_code=409, detail=detail)


def ensure_unique_cluster_node(cluster_id: int, robot_id: int, record_id: int | None = None) -> None:
    sql = "SELECT id FROM cluster_nodes WHERE cluster_id = %s AND robot_id = %s"
    params: list[Any] = [cluster_id, robot_id]
    if record_id is not None:
        sql += " AND id <> %s"
        params.append(record_id)
    sql += " LIMIT 1"
    if query_one(sql, tuple(params)):
        raise HTTPException(status_code=409, detail="该机器人已接入当前集群。")


def build_formation_member_record(payload: dict[str, Any]) -> dict[str, Any]:
    formation_id = parse_strict_id(payload.get("formationId"), "formationId")
    robot_id = parse_strict_id(payload.get("robotId"), "robotId")
    formation = query_one("SELECT cluster_id FROM formations WHERE id = %s LIMIT 1", (formation_id,))
    if not formation:
        raise HTTPException(status_code=404, detail="未找到对应编队。")
    if not query_one("SELECT id FROM robots WHERE id = %s LIMIT 1", (robot_id,)):
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    if not query_one("SELECT id FROM cluster_nodes WHERE cluster_id = %s AND robot_id = %s LIMIT 1", (formation["cluster_id"], robot_id)):
        raise HTTPException(status_code=409, detail="机器人未加入编队所属集群。")
    return {
        "formationId": formation_id,
        "robotId": robot_id,
        "slotIndex": parse_strict_id(payload.get("slotIndex") or 1, "slotIndex"),
        "role": str(payload.get("role") or "member").strip() or "member",
        "offsetX": parse_float(payload.get("offsetX") or 0, "offsetX"),
        "offsetY": parse_float(payload.get("offsetY") or 0, "offsetY"),
        "offsetYaw": parse_float(payload.get("offsetYaw") or 0, "offsetYaw"),
    }


def paged_response(rows: list[dict[str, Any]], total: int, page: int, size: int) -> dict[str, Any]:
    return {"items": rows, "total": total, "page": page, "size": size}


def load_devices(status: Optional[str] = None) -> list[dict[str, Any]]:
    where_sql = """
        WHERE 1=1
    """
    params: list[Any] = []
    if status:
        where_sql += " AND d.status = %s"
        params.append(status)
    sql = f"""
        SELECT d.id, d.name, d.model, d.image_path, d.status, d.notes, d.created_at
        FROM devices d
        {where_sql}
        ORDER BY d.created_at DESC, d.id DESC
    """
    rows = query_all(sql, tuple(params) if params else None)
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "model": r["model"],
            "imagePath": r["image_path"] or "",
            "status": r["status"],
            "notes": r["notes"] or "",
            "createdAt": to_iso_datetime(r["created_at"]),
        }
        for r in rows
    ]


def load_devices_page(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
) -> dict[str, Any]:
    page, size, offset = normalize_pagination(page, size)
    params: list[Any] = []
    where_sql = "WHERE 1=1"
    keyword = str(keyword or "").strip()
    if status:
        where_sql += " AND d.status = %s"
        params.append(status)
    if keyword:
        keyword_like = f"%{keyword}%"
        where_sql += " AND (d.name LIKE %s OR d.model LIKE %s OR d.notes LIKE %s OR d.code LIKE %s OR c.name LIKE %s)"
        params.extend([keyword_like, keyword_like, keyword_like, keyword_like, keyword_like])
    total_row = query_one(
        f"""
        SELECT COUNT(*) AS cnt
        FROM devices d
        LEFT JOIN device_categories c ON c.id = d.category_id
        {where_sql}
        """,
        tuple(params) if params else None,
    )
    total = int(total_row["cnt"]) if total_row else 0
    rows = query_all(
        f"""
        SELECT d.id, d.name, d.code, d.model, d.manufacturer, d.serial_number,
               d.image_path, d.status, d.category_id, c.name AS category_name,
               d.robot_id, r.model AS robot_name, d.notes, d.created_at
        FROM devices d
        LEFT JOIN device_categories c ON c.id = d.category_id
        LEFT JOIN robots r ON r.id = d.robot_id
        {where_sql}
        ORDER BY d.created_at DESC, d.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "code": r.get("code") or "",
                "model": r["model"],
                "manufacturer": r.get("manufacturer") or "",
                "serialNumber": r.get("serial_number") or "",
                "imagePath": r["image_path"] or "",
                "status": r["status"],
                "categoryId": r.get("category_id"),
                "categoryName": r.get("category_name") or "",
                "robotId": r.get("robot_id"),
                "robotName": r.get("robot_name") or "",
                "notes": r["notes"] or "",
                "createdAt": to_iso_datetime(r["created_at"]),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


def load_users(page: int = 1, size: int = 20) -> dict[str, Any]:
    page, size, offset = normalize_pagination(page, size)
    total_row = query_one("SELECT COUNT(*) AS cnt FROM users")
    rows = query_all(
        """
        SELECT id, username, display_name, status, created_at
        FROM users
        ORDER BY id ASC
        LIMIT %s OFFSET %s
        """,
        (size, offset),
    )
    return paged_response(
        [
            {
                "id": row["id"],
                "username": row["username"],
                "displayName": row.get("display_name") or row["username"],
                "status": row.get("status") or "active",
                "createdAt": to_iso_datetime(row.get("created_at")),
            }
            for row in rows
        ],
        int(total_row.get("cnt", 0) if total_row else 0),
        page,
        size,
    )


def load_device_categories_page(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict[str, Any]:
    page, size, offset = normalize_pagination(page, size)
    conditions: list[str] = []
    params: list[Any] = []
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append("(name LIKE %s OR description LIKE %s)")
        params.extend([like, like])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    total = int((query_one(f"SELECT COUNT(*) AS cnt FROM device_categories {where}", tuple(params)) or {}).get("cnt", 0) or 0)
    rows = query_all(
        f"""
        SELECT id, name, description, status, created_at
        FROM device_categories
        {where}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return paged_response(
        [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row.get("description") or "",
                "status": row.get("status") or "active",
                "createdAt": to_iso_datetime(row.get("created_at")),
            }
            for row in rows
        ],
        total,
        page,
        size,
    )


def load_onboard_units_page(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict[str, Any]:
    page, size, offset = normalize_pagination(page, size)
    params: list[Any] = []
    where = ""
    if keyword:
        like = f"%{keyword.strip()}%"
        where = """
        WHERE (u.name LIKE %s OR u.unit_type LIKE %s OR u.model LIKE %s
               OR u.protocol LIKE %s OR u.notes LIKE %s OR d.name LIKE %s)
        """
        params.extend([like, like, like, like, like, like])
    total = int((query_one(
        f"""
        SELECT COUNT(*) AS cnt
        FROM onboard_units u
        JOIN devices d ON d.id = u.device_id
        {where}
        """,
        tuple(params),
    ) or {}).get("cnt", 0) or 0)
    rows = query_all(
        f"""
        SELECT u.id, u.device_id, d.name AS device_name, u.name, u.unit_type,
               u.model, u.protocol, u.status, u.notes, u.created_at
        FROM onboard_units u
        JOIN devices d ON d.id = u.device_id
        {where}
        ORDER BY u.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return paged_response(
        [
            {
                "id": row["id"],
                "deviceId": row["device_id"],
                "deviceName": row.get("device_name") or "",
                "name": row["name"],
                "unitType": row.get("unit_type") or "",
                "model": row.get("model") or "",
                "protocol": row.get("protocol") or "",
                "status": row.get("status") or "active",
                "notes": row.get("notes") or "",
                "createdAt": to_iso_datetime(row.get("created_at")),
            }
            for row in rows
        ],
        total,
        page,
        size,
    )


def load_network_channels_page(page: int = 1, size: int = 20, keyword: Optional[str] = None) -> dict[str, Any]:
    page, size, offset = normalize_pagination(page, size)
    params: list[Any] = []
    where = ""
    if keyword:
        like = f"%{keyword.strip()}%"
        where = """
        WHERE (n.name LIKE %s OR n.channel_type LIKE %s OR n.host LIKE %s
               OR n.protocol LIKE %s OR n.notes LIKE %s OR d.name LIKE %s)
        """
        params.extend([like, like, like, like, like, like])
    total = int((query_one(
        f"""
        SELECT COUNT(*) AS cnt
        FROM network_channels n
        JOIN devices d ON d.id = n.device_id
        {where}
        """,
        tuple(params),
    ) or {}).get("cnt", 0) or 0)
    rows = query_all(
        f"""
        SELECT n.id, n.device_id, d.name AS device_name, n.name, n.channel_type,
               n.host, n.port, n.protocol, n.status, n.notes, n.created_at
        FROM network_channels n
        JOIN devices d ON d.id = n.device_id
        {where}
        ORDER BY n.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return paged_response(
        [
            {
                "id": row["id"],
                "deviceId": row["device_id"],
                "deviceName": row.get("device_name") or "",
                "name": row["name"],
                "channelType": row.get("channel_type") or "",
                "host": row.get("host") or "",
                "port": row.get("port"),
                "protocol": row.get("protocol") or "",
                "status": row.get("status") or "active",
                "notes": row.get("notes") or "",
                "createdAt": to_iso_datetime(row.get("created_at")),
            }
            for row in rows
        ],
        total,
        page,
        size,
    )


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return render_page(request, "users")


@app.get("/api/users")
async def api_users(request: Request, page: int = 1, size: int = 20) -> JSONResponse:
    require_admin_login(request)
    page, size, _ = normalize_pagination(page, size)
    return JSONResponse(load_users(page, size) if mysql_ready() else {"items": [], "total": 0, "page": page, "size": size})


@app.post("/api/users")
async def api_create_user(request: Request) -> JSONResponse:
    require_admin_login(request)
    payload = await request.json()
    username, password, display_name = validate_auth_user_payload(payload)
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="用户名已存在。")
    user_id = execute_insert(
        """
        INSERT INTO users (username, password_hash, display_name, status, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (username, hash_password(password), display_name, str(payload.get("status") or "active"), datetime.now()),
    )
    return JSONResponse({"ok": True, "userId": user_id})


@app.put("/api/users/{user_id}")
async def api_update_user(user_id: int, request: Request) -> JSONResponse:
    require_admin_login(request)
    user_id = parse_strict_id(user_id, "user_id")
    payload = await request.json()
    existing = query_one("SELECT id FROM users WHERE id = %s LIMIT 1", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="未找到对应用户。")
    updates: list[str] = []
    params: list[Any] = []
    if "displayName" in payload:
        display_name = str(payload.get("displayName") or "").strip()
        if len(display_name) > 128:
            raise HTTPException(status_code=422, detail="显示名称长度不能超过 128 个字符。")
        updates.append("display_name = %s")
        params.append(display_name)
    if "password" in payload:
        password = str(payload.get("password") or "")
        if len(password) < 6:
            raise HTTPException(status_code=422, detail="密码长度至少为 6 位。")
        updates.append("password_hash = %s")
        params.append(hash_password(password))
    if "status" in payload:
        updates.append("status = %s")
        params.append(str(payload.get("status") or "active").strip() or "active")
    if not updates:
        return JSONResponse({"ok": True})
    params.append(user_id)
    execute_write(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", tuple(params))
    return JSONResponse({"ok": True})


@app.patch("/api/users/{user_id}/status")
async def api_update_user_status(user_id: int, request: Request) -> JSONResponse:
    require_admin_login(request)
    user_id = parse_strict_id(user_id, "user_id")
    payload = await request.json()
    status = str(payload.get("status") or "").strip()
    if status not in {"active", "disabled"}:
        raise HTTPException(status_code=422, detail="status 必须是 active 或 disabled。")
    if execute_write("UPDATE users SET status = %s WHERE id = %s", (status, user_id)) == 0:
        raise HTTPException(status_code=404, detail="未找到对应用户。")
    return JSONResponse({"ok": True})


@app.get("/api/device-categories")
async def api_device_categories(request: Request, page: int = 1, size: int = 20, keyword: Optional[str] = None) -> JSONResponse:
    require_api_login(request)
    page, size, _ = normalize_pagination(page, size)
    return JSONResponse(load_device_categories_page(page, size, keyword) if mysql_ready() else {"items": [], "total": 0, "page": page, "size": size})


@app.post("/api/device-categories")
async def api_create_device_category(request: Request) -> JSONResponse:
    require_api_login(request)
    payload = await request.json()
    name = normalize_entity_name(payload.get("name"))
    ensure_unique_table_name("device_categories", name, "设备类别")
    category_id = execute_insert(
        "INSERT INTO device_categories (name, description, status, created_at) VALUES (%s, %s, %s, %s)",
        (name, str(payload.get("description") or "").strip(), str(payload.get("status") or "active").strip() or "active", datetime.now()),
    )
    return JSONResponse({"ok": True, "categoryId": category_id})


@app.put("/api/device-categories/{category_id}")
async def api_update_device_category(category_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    category_id = parse_strict_id(category_id, "category_id")
    payload = await request.json()
    if not query_one("SELECT id FROM device_categories WHERE id = %s LIMIT 1", (category_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备类别。")
    name = normalize_entity_name(payload.get("name"))
    ensure_unique_table_name("device_categories", name, "设备类别", category_id)
    execute_write(
        "UPDATE device_categories SET name = %s, description = %s, status = %s WHERE id = %s",
        (name, str(payload.get("description") or "").strip(), str(payload.get("status") or "active").strip() or "active", category_id),
    )
    return JSONResponse({"ok": True})


@app.delete("/api/device-categories/{category_id}")
async def api_delete_device_category(category_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    category_id = parse_strict_id(category_id, "category_id")
    ensure_no_related_records("devices", "category_id = %s", (category_id,), "该设备类别下还有设备，不能删除。")
    if clear_table("device_categories", category_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应设备类别。")
    return JSONResponse({"ok": True})


@app.get("/api/onboard-units")
async def api_onboard_units(request: Request, page: int = 1, size: int = 20, keyword: Optional[str] = None) -> JSONResponse:
    require_api_login(request)
    page, size, _ = normalize_pagination(page, size)
    return JSONResponse(load_onboard_units_page(page, size, keyword) if mysql_ready() else {"items": [], "total": 0, "page": page, "size": size})


@app.post("/api/onboard-units")
async def api_create_onboard_unit(request: Request) -> JSONResponse:
    require_api_login(request)
    payload = await request.json()
    device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
    ensure_device_exists(device_id)
    name = normalize_entity_name(payload.get("name"))
    unit_type = normalize_entity_name(payload.get("unitType"))
    unit_id = execute_insert(
        """
        INSERT INTO onboard_units (device_id, name, unit_type, model, protocol, status, notes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            device_id, name, unit_type, str(payload.get("model") or "").strip(),
            str(payload.get("protocol") or "").strip(), str(payload.get("status") or "active").strip() or "active",
            str(payload.get("notes") or "").strip(), datetime.now(),
        ),
    )
    return JSONResponse({"ok": True, "unitId": unit_id})


@app.put("/api/onboard-units/{unit_id}")
async def api_update_onboard_unit(unit_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    unit_id = parse_strict_id(unit_id, "unit_id")
    payload = await request.json()
    if not query_one("SELECT id FROM onboard_units WHERE id = %s LIMIT 1", (unit_id,)):
        raise HTTPException(status_code=404, detail="未找到对应机载单元。")
    device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
    ensure_device_exists(device_id)
    execute_write(
        """
        UPDATE onboard_units
        SET device_id = %s, name = %s, unit_type = %s, model = %s, protocol = %s, status = %s, notes = %s
        WHERE id = %s
        """,
        (
            device_id, normalize_entity_name(payload.get("name")), normalize_entity_name(payload.get("unitType")),
            str(payload.get("model") or "").strip(), str(payload.get("protocol") or "").strip(),
            str(payload.get("status") or "active").strip() or "active", str(payload.get("notes") or "").strip(), unit_id,
        ),
    )
    return JSONResponse({"ok": True})


@app.delete("/api/onboard-units/{unit_id}")
async def api_delete_onboard_unit(unit_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    unit_id = parse_strict_id(unit_id, "unit_id")
    if clear_table("onboard_units", unit_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应机载单元。")
    return JSONResponse({"ok": True})


@app.get("/api/network-channels")
async def api_network_channels(request: Request, page: int = 1, size: int = 20, keyword: Optional[str] = None) -> JSONResponse:
    require_api_login(request)
    page, size, _ = normalize_pagination(page, size)
    return JSONResponse(load_network_channels_page(page, size, keyword) if mysql_ready() else {"items": [], "total": 0, "page": page, "size": size})


@app.post("/api/network-channels")
async def api_create_network_channel(request: Request) -> JSONResponse:
    require_api_login(request)
    payload = await request.json()
    device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
    ensure_device_exists(device_id)
    port = parse_int_range(payload.get("port"), "port", 1, 65535) if payload.get("port") not in {None, ""} else None
    channel_id = execute_insert(
        """
        INSERT INTO network_channels (device_id, name, channel_type, host, port, protocol, status, notes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            device_id, normalize_entity_name(payload.get("name")), normalize_entity_name(payload.get("channelType")),
            str(payload.get("host") or "").strip(), port, str(payload.get("protocol") or "").strip(),
            str(payload.get("status") or "active").strip() or "active", str(payload.get("notes") or "").strip(), datetime.now(),
        ),
    )
    return JSONResponse({"ok": True, "channelId": channel_id})


@app.put("/api/network-channels/{channel_id}")
async def api_update_network_channel(channel_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    channel_id = parse_strict_id(channel_id, "channel_id")
    payload = await request.json()
    if not query_one("SELECT id FROM network_channels WHERE id = %s LIMIT 1", (channel_id,)):
        raise HTTPException(status_code=404, detail="未找到对应通信通道。")
    device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
    ensure_device_exists(device_id)
    port = parse_int_range(payload.get("port"), "port", 1, 65535) if payload.get("port") not in {None, ""} else None
    execute_write(
        """
        UPDATE network_channels
        SET device_id = %s, name = %s, channel_type = %s, host = %s, port = %s,
            protocol = %s, status = %s, notes = %s
        WHERE id = %s
        """,
        (
            device_id, normalize_entity_name(payload.get("name")), normalize_entity_name(payload.get("channelType")),
            str(payload.get("host") or "").strip(), port, str(payload.get("protocol") or "").strip(),
            str(payload.get("status") or "active").strip() or "active", str(payload.get("notes") or "").strip(), channel_id,
        ),
    )
    return JSONResponse({"ok": True})


@app.delete("/api/network-channels/{channel_id}")
async def api_delete_network_channel(channel_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    channel_id = parse_strict_id(channel_id, "channel_id")
    if clear_table("network_channels", channel_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应通信通道。")
    return JSONResponse({"ok": True})


@app.delete("/api/cluster-nodes/{node_id}")
async def api_delete_cluster_node(node_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    node_id = parse_strict_id(node_id, "node_id")
    node = query_one("SELECT cluster_id, robot_id FROM cluster_nodes WHERE id = %s LIMIT 1", (node_id,))
    if not node:
        raise HTTPException(status_code=404, detail="未找到对应集群节点。")
    if query_one(
        """
        SELECT fm.id
        FROM formation_members fm
        JOIN formations f ON f.id = fm.formation_id
        WHERE f.cluster_id = %s AND fm.robot_id = %s
        LIMIT 1
        """,
        (node["cluster_id"], node["robot_id"]),
    ):
        raise HTTPException(status_code=409, detail="该节点仍被编队成员引用，不能删除。")
    if clear_table("cluster_nodes", node_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应集群节点。")
    return JSONResponse({"ok": True})


@app.put("/api/cluster-nodes/{node_id}")
async def api_update_cluster_node(node_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    node_id = parse_strict_id(node_id, "node_id")
    payload = await request.json()
    existing = query_one("SELECT cluster_id, robot_id FROM cluster_nodes WHERE id = %s LIMIT 1", (node_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="未找到对应集群节点。")
    cluster_id = parse_strict_id(payload.get("clusterId"), "clusterId")
    robot_id = parse_strict_id(payload.get("robotId"), "robotId")
    if not query_one("SELECT id FROM clusters WHERE id = %s LIMIT 1", (cluster_id,)):
        raise HTTPException(status_code=404, detail="未找到对应集群。")
    if not query_one("SELECT id FROM robots WHERE id = %s LIMIT 1", (robot_id,)):
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    ensure_unique_cluster_node(cluster_id, robot_id, node_id)
    changed_identity = cluster_id != existing["cluster_id"] or robot_id != existing["robot_id"]
    if changed_identity and query_one(
        """
        SELECT fm.id
        FROM formation_members fm
        JOIN formations f ON f.id = fm.formation_id
        WHERE f.cluster_id = %s AND fm.robot_id = %s
        LIMIT 1
        """,
        (existing["cluster_id"], existing["robot_id"]),
    ):
        raise HTTPException(status_code=409, detail="该节点已被编队成员引用，不能迁移。")
    execute_write(
        "UPDATE cluster_nodes SET cluster_id = %s, robot_id = %s, role = %s, status = %s WHERE id = %s",
        (
            cluster_id,
            robot_id,
            str(payload.get("role") or "member").strip() or "member",
            str(payload.get("status") or "standby").strip() or "standby",
            node_id,
        ),
    )
    return JSONResponse({"ok": True})


@app.put("/api/formations/{formation_id}")
async def api_update_formation(formation_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    formation_id = parse_strict_id(formation_id, "formation_id")
    payload = await request.json()
    cluster_id = parse_strict_id(payload.get("clusterId"), "clusterId")
    if not query_one("SELECT id FROM clusters WHERE id = %s LIMIT 1", (cluster_id,)):
        raise HTTPException(status_code=404, detail="未找到对应集群。")
    existing = query_one("SELECT id FROM formations WHERE id = %s LIMIT 1", (formation_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="未找到对应编队。")
    missing = query_one(
        """
        SELECT fm.robot_id
        FROM formation_members fm
        LEFT JOIN cluster_nodes cn
          ON cn.cluster_id = %s AND cn.robot_id = fm.robot_id
        WHERE fm.formation_id = %s AND cn.id IS NULL
        LIMIT 1
        """,
        (cluster_id, formation_id),
    )
    if missing:
        raise HTTPException(status_code=409, detail="目标集群未包含当前编队的全部机器人。")
    execute_write(
        """
        UPDATE formations
        SET cluster_id = %s, name = %s, formation_type = %s, status = %s, description = %s
        WHERE id = %s
        """,
        (
            cluster_id,
            normalize_entity_name(payload.get("name")),
            str(payload.get("formationType") or "line").strip() or "line",
            str(payload.get("status") or "draft").strip() or "draft",
            str(payload.get("description") or "").strip(),
            formation_id,
        ),
    )
    return JSONResponse({"ok": True})


@app.get("/api/formation-members")
async def api_formation_members(request: Request, formationId: Optional[int] = None) -> JSONResponse:
    require_api_login(request)
    formation_id = parse_strict_id(formationId, "formationId")
    if not query_one("SELECT id FROM formations WHERE id = %s LIMIT 1", (formation_id,)):
        raise HTTPException(status_code=404, detail="未找到对应编队。")
    rows = query_all(
        """
        SELECT id, formation_id, robot_id, slot_index, role, offset_x, offset_y, offset_yaw, created_at
        FROM formation_members
        WHERE formation_id = %s
        ORDER BY slot_index ASC, id ASC
        """,
        (formation_id,),
    )
    return JSONResponse({"items": rows})


@app.put("/api/formation-members/{member_id}")
async def api_update_formation_member(member_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    member_id = parse_strict_id(member_id, "member_id")
    payload = await request.json()
    record = build_formation_member_record(payload)
    if not query_one("SELECT id FROM formation_members WHERE id = %s LIMIT 1", (member_id,)):
        raise HTTPException(status_code=404, detail="未找到对应编队成员。")
    duplicate = query_one(
        "SELECT id FROM formation_members WHERE formation_id = %s AND robot_id = %s AND id <> %s LIMIT 1",
        (record["formationId"], record["robotId"], member_id),
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="该机器人已在当前编队中。")
    execute_write(
        """
        UPDATE formation_members
        SET formation_id = %s, robot_id = %s, slot_index = %s, role = %s,
            offset_x = %s, offset_y = %s, offset_yaw = %s
        WHERE id = %s
        """,
        (
            record["formationId"], record["robotId"], record["slotIndex"], record["role"],
            record["offsetX"], record["offsetY"], record["offsetYaw"], member_id,
        ),
    )
    return JSONResponse({"ok": True})


@app.get("/api/devices")
async def api_devices(
    request: Request,
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
) -> JSONResponse:
    require_api_login(request)
    page, size, _ = normalize_pagination(page, size)
    return JSONResponse(
        load_devices_page(page, size, status, keyword)
        if mysql_ready()
        else {"items": [], "total": 0, "page": page, "size": size}
    )


@app.post("/api/devices")
async def api_create_device(request: Request) -> JSONResponse:
    require_api_login(request)
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    model = str(payload.get("model", "")).strip()
    if not name or not model:
        raise HTTPException(status_code=422, detail="设备名称和型号不能为空。")
    category_id = parse_strict_id(payload.get("categoryId"), "categoryId") if payload.get("categoryId") not in {None, ""} else None
    robot_id = parse_strict_id(payload.get("robotId"), "robotId") if payload.get("robotId") not in {None, ""} else None
    if category_id and not query_one("SELECT id FROM device_categories WHERE id = %s LIMIT 1", (category_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备类别。")
    if robot_id and not query_one("SELECT id FROM robots WHERE id = %s LIMIT 1", (robot_id,)):
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    device_id = execute_insert(
        """
        INSERT INTO devices
            (name, code, model, manufacturer, serial_number, image_path, status, category_id, robot_id, notes, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            name, str(payload.get("code") or "").strip(), model, str(payload.get("manufacturer") or "").strip(),
            str(payload.get("serialNumber") or "").strip(), str(payload.get("imagePath", "")),
            str(payload.get("status", "normal")).strip() or "normal", category_id, robot_id,
            str(payload.get("notes", "")).strip(), datetime.now(),
        ),
    )
    if robot_id:
        set_robot_primary_device(robot_id, device_id)
    return JSONResponse({"ok": True, "deviceId": device_id})


@app.put("/api/devices/{device_id}")
async def api_update_device(device_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    device_id = parse_strict_id(device_id, "device_id")
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    model = str(payload.get("model", "")).strip()
    if not name or not model:
        raise HTTPException(status_code=422, detail="设备名称和型号不能为空。")
    category_id = parse_strict_id(payload.get("categoryId"), "categoryId") if payload.get("categoryId") not in {None, ""} else None
    robot_id = parse_strict_id(payload.get("robotId"), "robotId") if payload.get("robotId") not in {None, ""} else None
    if category_id and not query_one("SELECT id FROM device_categories WHERE id = %s LIMIT 1", (category_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备类别。")
    if robot_id and not query_one("SELECT id FROM robots WHERE id = %s LIMIT 1", (robot_id,)):
        raise HTTPException(status_code=404, detail="未找到对应机器人。")
    existing = query_one("SELECT robot_id FROM devices WHERE id = %s LIMIT 1", (device_id,))
    affected = execute_write(
        """
        UPDATE devices
        SET name=%s, code=%s, model=%s, manufacturer=%s, serial_number=%s,
            status=%s, category_id=%s, robot_id=%s, notes=%s
        WHERE id=%s
        """,
        (
            name, str(payload.get("code") or "").strip(), model, str(payload.get("manufacturer") or "").strip(),
            str(payload.get("serialNumber") or "").strip(), str(payload.get("status", "normal")).strip() or "normal",
            category_id, robot_id, str(payload.get("notes", "")).strip(), device_id,
        ),
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="未找到对应设备。")
    old_robot_id = existing.get("robot_id") if existing else None
    if robot_id:
        set_robot_primary_device(robot_id, device_id)
    if old_robot_id and old_robot_id != robot_id:
        refresh_robot_primary_device(int(old_robot_id))
    return JSONResponse({"ok": True})


@app.delete("/api/devices/{device_id}")
async def api_delete_device(device_id: int, request: Request) -> JSONResponse:
    require_api_login(request)
    device_id = parse_strict_id(device_id, "device_id")
    existing = query_one("SELECT robot_id FROM devices WHERE id = %s LIMIT 1", (device_id,))
    if clear_table("devices", device_id) == 0:
        raise HTTPException(status_code=404, detail="未找到对应设备。")
    if existing and existing.get("robot_id"):
        refresh_robot_primary_device(int(existing["robot_id"]))
    return JSONResponse({"ok": True})


@app.post("/api/devices/{device_id}/image")
async def api_upload_device_image(
    device_id: int, request: Request, file: UploadFile = File(...)
) -> JSONResponse:
    require_api_login(request)
    device_id = parse_strict_id(device_id, "device_id")
    if not query_one("SELECT id FROM devices WHERE id = %s", (device_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备。")
    ensure_upload_dir()
    ext = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    filename = f"device_{device_id}{ext}"
    dest = UPLOAD_DIR / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/static/uploads/devices/{filename}"
    execute_write("UPDATE devices SET image_path = %s WHERE id = %s", (url, device_id))
    return JSONResponse({"ok": True, "url": url})




# 设备通信（物联网对接）
#
# 鉴权方案：
# 1. 设备上报接口使用 X-Device-Token 请求头，不依赖 Session。
# 2. 管理接口（创建、吊销 Token、查询记录）仍然要求后台登录。
#
# 接口一览：
#   POST   /api/iot/tokens               管理员为设备创建 Token
#   DELETE /api/iot/tokens/{id}          管理员吊销 Token
#   GET    /api/iot/tokens               管理员查看 Token 列表
#   POST   /api/iot/checkin              设备上报巡检打卡（X-Device-Token 鉴权）
#   POST   /api/iot/telemetry            设备上报遥测状态（X-Device-Token 鉴权）
#   GET    /api/iot/checkins             管理员查询打卡记录
#   GET    /api/iot/telemetry            管理员查询遥测记录
#   GET    /api/iot/devices/{id}/status  查询指定设备的最新遥测状态

def _generate_device_token(device_id: int) -> str:
    return iot_helpers.generate_device_token(device_id)


def _resolve_device_token(token_value: str) -> dict[str, Any] | None:
    return iot_helpers.resolve_device_token(query_one, token_value)


def require_device_token(request: Request) -> int:
    return iot_helpers.require_device_token(request, _resolve_device_token)


# Token 管理接口（仅管理员）

@app.get("/api/iot/tokens")
async def api_iot_list_tokens(request: Request) -> JSONResponse:
    """获取设备 Token 列表。"""
    require_admin_login(request)
    rows = query_all(
        """
        SELECT dt.id, dt.device_id, d.name AS device_name, dt.token,
               dt.note, dt.is_active, dt.created_at
        FROM device_tokens dt
        JOIN devices d ON d.id = dt.device_id
        ORDER BY dt.created_at DESC
        """
    ) if mysql_ready() else []
    return JSONResponse({
        "items": [
            {
                "id": r["id"],
                "deviceId": r["device_id"],
                "deviceName": r["device_name"],
                "token": r["token"],
                "note": r["note"] or "",
                "isActive": bool(r["is_active"]),
                "createdAt": to_iso_datetime(r["created_at"]),
            }
            for r in rows
        ]
    })


@app.post("/api/iot/tokens")
async def api_iot_create_token(request: Request) -> JSONResponse:
    """为指定设备创建新的 Token。"""
    require_admin_login(request)
    payload = await request.json()
    device_id = parse_strict_id(payload.get("deviceId"), "deviceId")
    if not query_one("SELECT id FROM devices WHERE id = %s", (device_id,)):
        raise HTTPException(status_code=404, detail="未找到对应设备。")
    note = str(payload.get("note", "")).strip()
    token_value = _generate_device_token(device_id)
    token_id = execute_insert(
        "INSERT INTO device_tokens (device_id, token, note, is_active, created_at) VALUES (%s,%s,%s,1,%s)",
        (device_id, token_value, note, datetime.now()),
    )
    return JSONResponse({"ok": True, "tokenId": token_id, "token": token_value})


@app.delete("/api/iot/tokens/{token_id}")
async def api_iot_revoke_token(token_id: int, request: Request) -> JSONResponse:
    """吊销指定 Token。"""
    require_admin_login(request)
    token_id = parse_strict_id(token_id, "token_id")
    affected = execute_write(
        "UPDATE device_tokens SET is_active = 0 WHERE id = %s", (token_id,)
    )
    if affected == 0:
        raise HTTPException(status_code=404, detail="未找到对应 Token。")
    return JSONResponse({"ok": True})


# 设备打卡上报接口

@app.post("/api/iot/checkin")
async def api_iot_checkin(request: Request) -> JSONResponse:
    """
    设备到达巡检点后主动上报打卡记录。
    请求头：
        X-Device-Token: <token>

    请求体（JSON）：
        {
          "lat": 22.349433,
          "lng": 113.584411,
          "note": "设备打卡",
          "checkedAt": "2026-03-30T10:00:00"
        }
    """
    device_id = await run_in_threadpool(require_device_token, request)
    payload = await request.json()

    lat_raw = payload.get("lat")
    lng_raw = payload.get("lng")
    note = str(payload.get("note", "")).strip()
    checked_at_raw = payload.get("checkedAt")

    lat = parse_float(lat_raw, "lat") if lat_raw is not None else None
    lng = parse_float(lng_raw, "lng") if lng_raw is not None else None
    checked_at = parse_datetime(checked_at_raw, "checkedAt") if checked_at_raw else datetime.now()

    checkin_id = await run_in_threadpool(
        execute_insert,
        """
        INSERT INTO device_checkins
            (device_id, lat, lng, note, checked_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (device_id, lat, lng, note, checked_at, datetime.now()),
    )
    await ws_broadcast("device_checkin")
    return JSONResponse({"ok": True, "checkinId": checkin_id})


# 设备遥测上报接口

@app.post("/api/iot/telemetry")
async def api_iot_telemetry(request: Request) -> JSONResponse:
    """
    设备遥测状态上报接口，设备定期调用并写入历史记录。
    请求头：
        X-Device-Token: <token>

    请求体（JSON）：
        {
          "battery": 85,
          "signal": 72,
          "status": "online",
          "lat": 22.349433,
          "lng": 113.584411,
          "reportedAt": "2026-03-30T10:00:00",
          "extra": {"temp": 25.3}
        }
    """
    device_id = await run_in_threadpool(require_device_token, request)
    payload = await request.json()

    battery_raw = payload.get("battery")
    signal_raw = payload.get("signal")
    status_raw = str(payload.get("status", "")).strip() or None
    lat_raw = payload.get("lat")
    lng_raw = payload.get("lng")
    extra = payload.get("extra")
    reported_at_raw = payload.get("reportedAt")

    battery = parse_int_range(battery_raw, "battery", 0, 100) if battery_raw is not None else None
    signal = parse_int_range(signal_raw, "signal", 0, 100) if signal_raw is not None else None
    if status_raw and status_raw not in {"online", "offline", "fault"}:
        raise HTTPException(status_code=422, detail="status 必须是 online、offline 或 fault。")
    lat = parse_float(lat_raw, "lat") if lat_raw is not None else None
    lng = parse_float(lng_raw, "lng") if lng_raw is not None else None
    received_at = datetime.now()
    reported_at = parse_datetime(reported_at_raw, "reportedAt") if reported_at_raw else received_at
    if abs((received_at - reported_at).total_seconds()) > IOT_REPORTED_AT_MAX_SKEW_SECONDS:
        reported_at = received_at
    extra_json = json.dumps(extra, ensure_ascii=False) if extra is not None else None
    source_ip = ""
    if request.client and request.client.host:
        try:
            source_ip = parse_ipv4(request.client.host, "source_ip")
        except HTTPException:
            source_ip = str(request.client.host).strip()

    # 写入遥测历史
    await run_in_threadpool(
        execute_insert,
        """
        INSERT INTO device_telemetry
            (device_id, battery, `signal`, status, lat, lng, source_ip, extra_json, reported_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (device_id, battery, signal, status_raw, lat, lng, source_ip or None, extra_json, reported_at, datetime.now()),
    )

    # 同步更新设备当前状态，仅在状态字段有值时覆盖
    if status_raw:
        await run_in_threadpool(
            execute_write,
            "UPDATE devices SET status = %s WHERE id = %s",
            (_map_iot_status_to_device(status_raw), device_id),
        )

    await ws_broadcast("device_telemetry")
    return JSONResponse({"ok": True})


def _map_iot_status_to_device(iot_status: str) -> str:
    return iot_helpers.map_iot_status_to_device(iot_status)


# 管理端查询接口（Session 鉴权）

@app.get("/api/iot/checkins")
async def api_iot_list_checkins(
    request: Request,
    device_id: Optional[int] = None,
    limit: int = 50,
) -> JSONResponse:
    """查询设备打卡记录。"""
    require_api_login(request)
    limit = min(max(limit, 1), 200)
    sql = """
        SELECT ci.id, ci.device_id, d.name AS device_name,
               ci.lat, ci.lng, ci.note, ci.checked_at, ci.created_at
        FROM device_checkins ci
        JOIN devices d ON d.id = ci.device_id
        WHERE 1=1
    """
    params: list[Any] = []
    if device_id is not None:
        sql += " AND ci.device_id = %s"
        params.append(device_id)
    sql += " ORDER BY ci.checked_at DESC, ci.id DESC LIMIT %s"
    params.append(limit)

    rows = query_all(sql, tuple(params)) if mysql_ready() else []
    return JSONResponse({
        "items": [
            {
                "id": r["id"],
                "deviceId": r["device_id"],
                "deviceName": r["device_name"],
                "lat": float(r["lat"]) if r["lat"] is not None else None,
                "lng": float(r["lng"]) if r["lng"] is not None else None,
                "note": r["note"] or "",
                "checkedAt": to_iso_datetime(r["checked_at"]),
                "createdAt": to_iso_datetime(r["created_at"]),
            }
            for r in rows
        ]
    })


@app.get("/api/iot/telemetry")
async def api_iot_list_telemetry(
    request: Request,
    device_id: Optional[int] = None,
    limit: int = 100,
) -> JSONResponse:
    """查询设备遥测记录。"""
    require_api_login(request)
    limit = min(max(limit, 1), 500)
    sql = """
        SELECT t.id, t.device_id, d.name AS device_name,
               t.battery, t.`signal` AS signal_value, t.status, t.lat, t.lng,
               t.extra_json, t.reported_at, t.created_at
        FROM device_telemetry t
        JOIN devices d ON d.id = t.device_id
        WHERE 1=1
    """
    params: list[Any] = []
    if device_id is not None:
        sql += " AND t.device_id = %s"
        params.append(device_id)
    sql += " ORDER BY t.reported_at DESC, t.id DESC LIMIT %s"
    params.append(limit)

    rows = query_all(sql, tuple(params)) if mysql_ready() else []
    return JSONResponse({
        "items": [
            {
                "id": r["id"],
                "deviceId": r["device_id"],
                "deviceName": r["device_name"],
                "battery": r["battery"],
                "signal": r["signal_value"],
                "status": r["status"] or "",
                "lat": float(r["lat"]) if r["lat"] is not None else None,
                "lng": float(r["lng"]) if r["lng"] is not None else None,
                "extra": json.loads(r["extra_json"]) if r["extra_json"] else None,
                "reportedAt": to_iso_datetime(r["reported_at"]),
                "createdAt": to_iso_datetime(r["created_at"]),
            }
            for r in rows
        ]
    })


@app.get("/api/iot/devices/{device_id}/status")
async def api_iot_device_latest_status(device_id: int, request: Request) -> JSONResponse:
    """获取指定设备的最新遥测状态。"""
    require_api_login(request)
    device_id = parse_strict_id(device_id, "device_id")
    device = query_one("SELECT id, name, status FROM devices WHERE id = %s", (device_id,))
    if not device:
        raise HTTPException(status_code=404, detail="未找到对应设备。")
    latest = query_one(
        """
        SELECT battery, `signal` AS signal_value, status, lat, lng, extra_json, reported_at
        FROM device_telemetry
        WHERE device_id = %s
        ORDER BY reported_at DESC, id DESC
        LIMIT 1
        """,
        (device_id,),
    ) if mysql_ready() else None
    return JSONResponse({
        "deviceId": device_id,
        "deviceName": device["name"],
        "deviceStatus": device["status"],
        "telemetry": {
            "battery": latest["battery"] if latest else None,
            "signal": latest["signal_value"] if latest else None,
            "status": latest["status"] if latest else None,
            "lat": float(latest["lat"]) if latest and latest["lat"] is not None else None,
            "lng": float(latest["lng"]) if latest and latest["lng"] is not None else None,
            "extra": json.loads(latest["extra_json"]) if latest and latest["extra_json"] else None,
            "reportedAt": to_iso_datetime(latest["reported_at"]) if latest else None,
        } if latest else None,
    })


# ── IoT 传感器数据上报接口 ─────────────────────────────────────────────────────
#
# 接口一览：
#   POST   /api/iot/camera/snapshot    设备上传摄像头快照（单目/双目）
#   POST   /api/iot/sensor/data        设备上传传感器数据（雷达/点云等）
#   GET    /api/iot/sensor/data        管理员查询传感器数据记录
#   GET    /api/iot/sensor/latest       管理员查询设备最新传感器快照

SENSOR_MAX_IMAGE_BYTES = iot_helpers.SENSOR_MAX_IMAGE_BYTES
SENSOR_ALLOWED_IMAGE_TYPES = iot_helpers.SENSOR_ALLOWED_IMAGE_TYPES
SENSOR_TYPE_CAMERA = iot_helpers.SENSOR_TYPE_CAMERA
SENSOR_TYPE_STEREO = iot_helpers.SENSOR_TYPE_STEREO
SENSOR_TYPE_LIDAR = iot_helpers.SENSOR_TYPE_LIDAR
VALID_SENSOR_TYPES = iot_helpers.VALID_SENSOR_TYPES
SENSOR_MAX_JSON_BYTES = 1024 * 1024
MAX_LIDAR_RANGES = 4096
LIDAR_NUMERIC_FIELDS = {
    "angleMin",
    "angleMax",
    "angleIncrement",
    "sourceAngleMax",
    "sourceAngleIncrement",
    "rangeMin",
    "rangeMax",
    "minRange",
    "maxRange",
    "meanRange",
    "displayRange",
    "timestamp",
}


def _sensor_file_ext(content_type: str, filename: str) -> str:
    return iot_helpers.sensor_file_ext(content_type, filename)


def validate_lidar_payload(data: Any) -> None:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="lidar data 必须是 JSON 对象。")
    ranges = data.get("ranges")
    if not isinstance(ranges, list):
        raise HTTPException(status_code=422, detail="lidar data.ranges 必须是数组。")
    if not 1 <= len(ranges) <= MAX_LIDAR_RANGES:
        raise HTTPException(status_code=422, detail=f"lidar data.ranges 长度必须在 1..{MAX_LIDAR_RANGES} 之间。")
    for index, value in enumerate(ranges):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(status_code=422, detail=f"lidar data.ranges[{index}] 必须是正有限数字或 null。")
        try:
            numeric = float(value)
        except OverflowError:
            numeric = math.inf
        if not math.isfinite(numeric) or numeric <= 0:
            raise HTTPException(status_code=422, detail=f"lidar data.ranges[{index}] 必须是正有限数字或 null。")
    for field in LIDAR_NUMERIC_FIELDS:
        if field not in data or data[field] is None:
            continue
        value = data[field]
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError):
            numeric = math.inf
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(numeric):
            raise HTTPException(status_code=422, detail=f"lidar data.{field} 必须是有限数字。")


def latest_sensor_rows(
    device_id: int | None = None,
    sensor_type: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if device_id is not None:
        conditions.append("s.device_id = %s")
        params.append(device_id)
    if sensor_type:
        conditions.append("s.sensor_type = %s")
        params.append(sensor_type.strip().lower())
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    limit = max(1, min(int(limit or 200), 500))
    return query_all(
        f"""
        SELECT id, device_id, sensor_type, channel, file_path, data_json, content_type,
               size_bytes, extra_json, reported_at
        FROM (
            SELECT s.device_id, s.sensor_type, s.channel, s.file_path, s.data_json, s.content_type,
                   s.size_bytes, s.extra_json, s.reported_at, s.id,
                   ROW_NUMBER() OVER (
                       PARTITION BY s.device_id, s.sensor_type, COALESCE(s.channel, '')
                       ORDER BY s.reported_at DESC, s.id DESC
                   ) AS rn
            FROM device_sensor_data s
            {where}
        ) ranked
        WHERE rn = 1
        ORDER BY reported_at DESC, id DESC
        LIMIT {limit}
        """,
        tuple(params),
    )


def unique_sensor_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for row in rows:
        key = f"{row.get('device_id')}:{row.get('sensor_type')}:{row.get('channel') or ''}"
        if key in seen:
            continue
        seen.add(key)
        items.append(row)
    return items


def sensor_row_to_response_item(
    row: dict[str, Any],
    now: datetime | None = None,
    include_device_id: bool = True,
    include_stale: bool = False,
) -> dict[str, Any]:
    sensor_type = row["sensor_type"]
    reported_at = coerce_datetime(row.get("reported_at"))
    item: dict[str, Any] = {
        "sensorType": sensor_type,
        "channel": row["channel"],
        "filePath": row["file_path"],
        "data": json.loads(row["data_json"]) if row["data_json"] else None,
        "contentType": row["content_type"],
        "sizeBytes": row["size_bytes"],
        "extra": json.loads(row["extra_json"]) if row["extra_json"] else None,
        "reportedAt": to_iso_datetime(reported_at or row["reported_at"]),
    }
    if include_device_id:
        item["deviceId"] = row["device_id"]
    if include_stale:
        threshold = sensor_stale_seconds(sensor_type)
        age = snapshot_age_seconds(reported_at, now)
        item["stale"] = snapshot_is_stale(reported_at, now, sensor_type)
        item["staleAfterSeconds"] = threshold
        item["ageSeconds"] = round(age, 3) if age is not None else None
    return item


@app.post("/api/iot/camera/snapshot")
async def api_iot_camera_snapshot(
    request: Request,
    file: UploadFile = File(...),
    channel: str = "mono",
) -> JSONResponse:
    """
    设备上传摄像头快照图片。
    支持单目、双目左右路、深度图等不同通道。

    请求头：X-Device-Token
    表单参数：
        file: JPEG/PNG 图片文件（≤ 5 MB）
        channel: 通道标签（mono | left | right | depth）
    """
    device_id = await run_in_threadpool(require_device_token, request)
    await run_in_threadpool(ensure_upload_dir)

    # 确定 sensor_type
    channel_norm = (channel or "mono").strip().lower()
    if channel_norm in {"left", "right", "depth"}:
        sensor_type = SENSOR_TYPE_STEREO
    else:
        sensor_type = SENSOR_TYPE_CAMERA
        channel_norm = "mono"

    # 读取文件
    content = await file.read()
    if len(content) > SENSOR_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"图片大小超过限制（最大 {SENSOR_MAX_IMAGE_BYTES // 1024 // 1024} MB）")
    content_type = (file.content_type or "image/jpeg").strip().lower()
    if content_type not in SENSOR_ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="仅支持 JPEG/PNG 图片格式")

    # 存储文件
    ext = _sensor_file_ext(content_type, file.filename or "")
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{device_id}_{sensor_type}_{channel_norm}_{ts}{ext}"
    dest = CAMERA_UPLOAD_DIR / filename
    await run_in_threadpool(dest.write_bytes, content)
    file_url = f"/static/uploads/cameras/{filename}"
    robot_id: int | None = None
    if sensor_type == SENSOR_TYPE_CAMERA and channel_norm == "mono":
        robot_row = await run_in_threadpool(query_one, "SELECT robot_id FROM devices WHERE id = %s LIMIT 1", (device_id,))
        if robot_row and robot_row.get("robot_id"):
            robot_id = int(robot_row["robot_id"])
            robot_path = robot_camera_upload_path(robot_id)
            await run_in_threadpool(robot_path.parent.mkdir, parents=True, exist_ok=True)
            await run_in_threadpool(robot_path.write_bytes, content)

    # 写入数据库
    reported_at_raw = request.query_params.get("reportedAt", "")
    reported_at = parse_datetime(reported_at_raw, "reportedAt") if reported_at_raw else now
    extra_meta: dict[str, Any] = {"channel": channel_norm}
    try:
        await run_in_threadpool(
            execute_insert,
            """
            INSERT INTO device_sensor_data
                (device_id, sensor_type, channel, file_path, content_type, size_bytes, extra_json, reported_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (device_id, sensor_type, channel_norm, file_url, content_type, len(content),
             json.dumps(extra_meta, ensure_ascii=False), reported_at, datetime.now()),
        )
    except Exception:
        if robot_id is None:
            raise

    await ws_broadcast("device_sensor")
    return JSONResponse({"ok": True, "url": file_url, "size": len(content), "sensorType": sensor_type, "channel": channel_norm, "robotId": robot_id})


@app.post("/api/iot/sensor/data")
async def api_iot_sensor_data(request: Request) -> JSONResponse:
    """
    设备上传传感器结构化数据（雷达扫描、点云摘要等）。

    请求头：X-Device-Token
    请求体（JSON）：
        {
          "sensorType": "lidar",
          "channel": "scan",
          "data": { "ranges": [...], "angleMin": -1.57, ... },
          "reportedAt": "2026-06-25T12:00:00",
          "extra": {}
        }
    """
    device_id = await run_in_threadpool(require_device_token, request)
    payload = await request.json()

    sensor_type = str(payload.get("sensorType") or "").strip().lower()
    if sensor_type not in VALID_SENSOR_TYPES:
        raise HTTPException(status_code=422, detail=f"sensorType 必须是 {', '.join(sorted(VALID_SENSOR_TYPES))} 之一。")
    channel = str(payload.get("channel") or "").strip().lower() or None
    data = payload.get("data")
    if data is None:
        raise HTTPException(status_code=422, detail="缺少 data 字段。")
    if sensor_type == SENSOR_TYPE_LIDAR:
        validate_lidar_payload(data)
    reported_at_raw = payload.get("reportedAt")
    reported_at = parse_datetime(reported_at_raw, "reportedAt") if reported_at_raw else datetime.now()
    extra = payload.get("extra")

    data_json = json.dumps(data, ensure_ascii=False)
    # 限制数据大小（JSON ≤ 1 MB）
    data_size = len(data_json.encode("utf-8"))
    if data_size > SENSOR_MAX_JSON_BYTES:
        raise HTTPException(status_code=413, detail="data 字段超过 1 MB 限制。")
    extra_json = json.dumps(extra, ensure_ascii=False) if extra is not None else None

    try:
        await run_in_threadpool(
            execute_insert,
            """
            INSERT INTO device_sensor_data
                (device_id, sensor_type, channel, data_json, content_type, size_bytes, extra_json, reported_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (device_id, sensor_type, channel, data_json, "application/json", data_size,
             extra_json, reported_at, datetime.now()),
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"数据库写入失败: {exc}")

    await ws_broadcast("device_sensor")
    return JSONResponse({"ok": True, "sensorType": sensor_type, "channel": channel})


@app.get("/api/iot/sensor/data")
async def api_iot_list_sensor_data(
    request: Request,
    device_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
) -> JSONResponse:
    """管理员查询传感器数据记录。"""
    require_api_login(request)
    if not mysql_ready():
        return JSONResponse({"items": []})

    conditions: list[str] = []
    params: list[Any] = []
    if device_id is not None:
        conditions.append("s.device_id = %s")
        params.append(parse_strict_id(device_id, "device_id"))
    if sensor_type:
        conditions.append("s.sensor_type = %s")
        params.append(sensor_type.strip().lower())
    if channel:
        conditions.append("s.channel = %s")
        params.append(channel.strip().lower())
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    limit = max(1, min(int(limit or 50), 200))
    rows = query_all(
        f"""
        SELECT s.id, s.device_id, d.name AS device_name, s.sensor_type, s.channel,
               s.file_path, s.data_json, s.content_type, s.size_bytes, s.extra_json,
               s.reported_at, s.created_at
        FROM device_sensor_data s
        JOIN devices d ON d.id = s.device_id
        {where}
        ORDER BY s.reported_at DESC, s.id DESC
        LIMIT {limit}
        """,
        tuple(params),
    )
    return JSONResponse({
        "items": [
            {
                "id": r["id"],
                "deviceId": r["device_id"],
                "deviceName": r["device_name"],
                "sensorType": r["sensor_type"],
                "channel": r["channel"],
                "filePath": r["file_path"],
                "data": json.loads(r["data_json"]) if r["data_json"] else None,
                "contentType": r["content_type"],
                "sizeBytes": r["size_bytes"],
                "extra": json.loads(r["extra_json"]) if r["extra_json"] else None,
                "reportedAt": to_iso_datetime(r["reported_at"]),
                "createdAt": to_iso_datetime(r["created_at"]),
            }
            for r in rows
        ]
    })


@app.get("/api/iot/sensor/latest")
async def api_iot_sensor_latest(
    request: Request,
    device_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
) -> JSONResponse:
    """获取设备最新传感器快照（每种类型+通道各取最新一条）。device_id 可选，不传则返回全部。"""
    require_api_login(request)
    if not mysql_ready():
        return JSONResponse({"sensors": []})
    did = parse_strict_id(device_id, "device_id") if device_id is not None else None
    rows = unique_sensor_rows(latest_sensor_rows(device_id=did, sensor_type=sensor_type, limit=200))
    items = [sensor_row_to_response_item(r, include_device_id=True) for r in rows]
    return JSONResponse({"sensors": items})


@app.get("/api/robots/{robot_id}/sensors/latest")
async def api_robot_sensors_latest(robot_id: int, request: Request) -> JSONResponse:
    """通过机器人 ID 获取关联设备的最新传感器数据。"""
    require_api_login(request)
    robot_id = parse_strict_id(robot_id, "robot_id")
    if not mysql_ready():
        return JSONResponse({"robotId": robot_id, "sensors": []})
    resolution = resolve_robot_device(robot_id)
    device_id = resolution.get("deviceId")
    if not device_id:
        return JSONResponse({
            "robotId": robot_id,
            "deviceId": None,
            "deviceMatchSource": resolution.get("deviceMatchSource") or "",
            "staleAfterSeconds": camera_stale_seconds(),
            "staleAfterSecondsByType": sensor_stale_thresholds(),
            "sensors": [],
        })
    rows = unique_sensor_rows(latest_sensor_rows(device_id=device_id, limit=50))
    now = datetime.now()
    items = [
        sensor_row_to_response_item(r, now=now, include_device_id=False, include_stale=True)
        for r in rows
    ]
    return JSONResponse({
        "robotId": robot_id,
        "deviceId": device_id,
        "deviceMatchSource": resolution.get("deviceMatchSource") or "",
        "staleAfterSeconds": camera_stale_seconds(),
        "staleAfterSecondsByType": sensor_stale_thresholds(),
        "sensors": items,
    })


# Utility + prototype routes
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/prototype/{prototype_name}", response_class=HTMLResponse)
async def prototype_page(prototype_name: str) -> HTMLResponse:
    if prototype_name not in PROTOTYPES:
        raise HTTPException(status_code=404, detail="未找到原型页面。")
    html_file = PROTOTYPE_DIR / prototype_name / "code.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="原型文件不存在。")
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


@app.get("/prototype/{prototype_name}/screen.png", include_in_schema=False)
async def prototype_screen(prototype_name: str):
    if prototype_name not in PROTOTYPES:
        raise HTTPException(status_code=404, detail="未找到原型页面。")
    png_file = PROTOTYPE_DIR / prototype_name / "screen.png"
    if not png_file.exists():
        raise HTTPException(status_code=404, detail="原型截图不存在。")
    return FileResponse(path=png_file)
