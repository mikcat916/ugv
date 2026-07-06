from __future__ import annotations

import os
import re
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


def _backend_credentials() -> tuple[str, str]:
    env_values = _load_env_file(ENV_FILE)
    username = (
        _env_value("UGV_BACKEND_USERNAME", env_values)
        or _env_value("ADMIN_USERNAME", env_values)
        or "admin"
    )
    password = (
        _env_value("UGV_BACKEND_PASSWORD", env_values)
        or _env_value("ADMIN_PASSWORD", env_values)
        or "admin123"
    )
    return username, password


def _login_session(target: str, timeout: float) -> requests.Session:
    session = requests.Session()
    login_page = session.get(f"{target}/login", timeout=timeout)
    login_page.raise_for_status()
    match = re.search(r'loginToken:\s*"([^"]+)"', login_page.text)
    if not match:
        raise RuntimeError("后端登录页未返回 loginToken。")
    username, password = _backend_credentials()
    response = session.post(
        f"{target}/auth/login",
        json={"username": username, "password": password, "loginToken": match.group(1)},
        timeout=timeout,
    )
    response.raise_for_status()
    return session


def get_autopilot_status(url: str | None = None, timeout: float = 2.5) -> dict[str, Any]:
    target = (url or backend_url()).rstrip("/")
    try:
        response = requests.get(f"{target}/api/autopilot/status", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {"ok": False, "url": target, "message": str(exc)}
    except ValueError as exc:
        return {"ok": False, "url": target, "message": f"后端返回非 JSON 响应：{exc}"}
    payload["ok"] = True
    payload["url"] = target
    return payload


def post_autopilot_action(action: str, payload: dict[str, Any] | None = None, url: str | None = None, timeout: float = 3.5) -> dict[str, Any]:
    target = (url or backend_url()).rstrip("/")
    try:
        session = _login_session(target, timeout)
        response = session.post(f"{target}/api/autopilot/{action}", json=payload or {}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return {"ok": False, "url": target, "message": str(exc)}
    except (RuntimeError, ValueError) as exc:
        return {"ok": False, "url": target, "message": str(exc)}
    data["ok"] = bool(data.get("ok", True))
    data["url"] = target
    return data


def post_autopilot_deadman(url: str | None = None, timeout: float = 3.5) -> dict[str, Any]:
    return post_autopilot_action("deadman", {"source": "desktop"}, url=url, timeout=timeout)
