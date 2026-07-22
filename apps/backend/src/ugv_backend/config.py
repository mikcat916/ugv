from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


# Runtime paths and bootstrap file locations.
PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PACKAGE_DIR.parents[1]
ROOT_DIR = PACKAGE_DIR.parents[3]
PROTOTYPE_DIR = BASE_DIR / "stitch_monitoring_dashboard"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
ROOT_ENV_FILE = ROOT_DIR / ".env"
SCHEMA_FILE = BASE_DIR / "db" / "mysql_schema.sql"
UPLOAD_ROOT_DIR = ROOT_DIR / "var" / "uploads"


def load_local_env(path: Path, overwrite: bool = True) -> None:
    # Minimal .env loader to keep deployment dependency-free.
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if overwrite or key not in os.environ:
            os.environ[key] = value


load_local_env(ROOT_ENV_FILE, overwrite=False)


def asset_version() -> str:
    candidates = (
        STATIC_DIR / "dashboard.css",
        STATIC_DIR / "api.js",
        STATIC_DIR / "ui.js",
        STATIC_DIR / "websocket.js",
        STATIC_DIR / "sim_autopilot.js",
        STATIC_DIR / "sim_safety.js",
        STATIC_DIR / "simulator.js",
        STATIC_DIR / "dashboard.js",
        STATIC_DIR / "login.js",
        TEMPLATES_DIR / "app.html",
        TEMPLATES_DIR / "login.html",
    )
    mtimes = [path.stat().st_mtime for path in candidates if path.exists()]
    return str(int(max(mtimes, default=time.time())))


# Legacy prototype routes are kept for compatibility/debug pages.
PROTOTYPES = {
    "_2": "总览",
    "monitoring_dashboard": "机器人状态",
}


# Canonical page map: used by template navigation and redirects.
PAGES = {
    "overview": {"route": "/overview", "title": "总览", "kicker": "系统概览"},
    "status": {"route": "/robots", "title": "机器人状态", "kicker": "设备状态"},
    "video": {"route": "/video", "title": "实时画面", "kicker": "摄像头"},
    "perception": {"route": "/perception", "title": "智能感知", "kicker": "Orin AI"},
    "maps": {"route": "/maps", "title": "地图展示", "kicker": "SLAM 地图"},
    "control": {"route": "/control", "title": "远程遥控", "kicker": "车辆控制"},
    "autopilot": {"route": "/autopilot", "title": "自动驾驶", "kicker": "安全自动模式"},
    "simulator": {"route": "/simulator", "title": "仿真", "kicker": "Simulator MVP"},
    "device_management": {"route": "/device-management", "title": "设备管理", "kicker": "设备体系"},
    "users": {"route": "/users", "title": "用户管理", "kicker": "本地账号"},
    "clusters": {"route": "/clusters", "title": "集群管理", "kicker": "节点编队"},
    "formations": {"route": "/formations", "title": "编队管理", "kicker": "队形方案"},
    "devices": {"route": "/devices", "title": "设备管理", "kicker": "设备信息"},
    "sensors": {"route": "/sensors", "title": "传感器数据", "kicker": "深度图 / 雷达"},
}


REQUIRED_MYSQL_ENV = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)


DEFAULT_SITE = {
    "name": "机器人巡检指挥中心",
    "subtitle": "巡检作业控制台",
    "city": "中山大学珠海校区瀚林2号",
    "center": [113.584411, 22.349433],
    "zoom": 17.2,
}


def mysql_configured() -> bool:
    return all(os.getenv(key, "").strip() for key in REQUIRED_MYSQL_ENV)


def mysql_settings() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "").strip(),
        "port": int(os.getenv("MYSQL_PORT", "3306").strip() or "3306"),
        "user": os.getenv("MYSQL_USER", "").strip(),
        "password": os.getenv("MYSQL_PASSWORD", "").strip(),
        "database": os.getenv("MYSQL_DATABASE", "").strip(),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4").strip() or "utf8mb4",
    }


def debug_enabled() -> bool:
    return os.getenv("DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}


def self_registration_allowed() -> bool:
    raw = os.getenv("ALLOW_SELF_REGISTER", "0").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"


def session_secret() -> str:
    return os.getenv("SESSION_SECRET", "dev-local-secret")
