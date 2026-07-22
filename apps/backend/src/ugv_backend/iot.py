from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException, Request


IOT_REPORTED_AT_MAX_SKEW_SECONDS = 24 * 60 * 60
SENSOR_MAX_IMAGE_BYTES = 5 * 1024 * 1024
SENSOR_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
SENSOR_TYPE_CAMERA = "camera"
SENSOR_TYPE_STEREO = "stereo"
SENSOR_TYPE_LIDAR = "lidar"
VALID_SENSOR_TYPES = {SENSOR_TYPE_CAMERA, SENSOR_TYPE_STEREO, SENSOR_TYPE_LIDAR}


def generate_device_token(device_id: int) -> str:
    raw = f"{device_id}-{secrets.token_hex(16)}-{datetime.now().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def resolve_device_token(
    query_one: Callable[[str, tuple[Any, ...] | None], dict[str, Any] | None],
    token_value: str,
) -> dict[str, Any] | None:
    return query_one(
        "SELECT id, device_id FROM device_tokens WHERE token = %s AND is_active = 1 LIMIT 1",
        (token_value,),
    )


def require_device_token(
    request: Request,
    resolve_device_token_fn: Callable[[str], dict[str, Any] | None],
) -> int:
    token_value = request.headers.get("X-Device-Token", "").strip()
    if not token_value:
        raise HTTPException(status_code=401, detail="缺少 X-Device-Token 请求头。")
    row = resolve_device_token_fn(token_value)
    if not row:
        raise HTTPException(status_code=403, detail="Token 无效或已被吊销。")
    return int(row["device_id"])


def map_iot_status_to_device(iot_status: str) -> str:
    return {"online": "normal", "offline": "offline", "fault": "fault"}.get(iot_status, "normal")


def sensor_file_ext(content_type: str, filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        return ext
    if "png" in (content_type or ""):
        return ".png"
    return ".jpg"
