from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _env_value(key: str, env_values: dict[str, str]) -> str:
    return os.getenv(key, "").strip() or env_values.get(key, "").strip()


def backend_url() -> str:
    env_values = _load_env_file(ENV_FILE)
    explicit = _env_value("UGV_BACKEND_URL", env_values) or _env_value("BACKEND_URL", env_values)
    if explicit:
        return explicit.rstrip("/")
    host = _env_value("BACKEND_HOST", env_values) or "127.0.0.1"
    port = _env_value("BACKEND_PORT", env_values) or "8000"
    return f"http://{host}:{port}".rstrip("/") if host and port else DEFAULT_BACKEND_URL


def check_backend_health(url: str | None = None, timeout: float = 2.5) -> dict[str, Any]:
    target = (url or backend_url()).rstrip("/")
    try:
        response = requests.get(f"{target}/health", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"ok": False, "url": target, "message": str(exc)}
    except ValueError as exc:
        return {"ok": False, "url": target, "message": f"后端返回非 JSON 响应：{exc}"}
    status = str(payload.get("status") or "").lower()
    return {
        "ok": status == "ok",
        "url": target,
        "status": status or "unknown",
        "mysqlReady": bool(payload.get("mysqlReady")),
        "message": payload.get("detail") or ("后端在线" if status == "ok" else f"后端状态异常：{status or 'unknown'}"),
    }
