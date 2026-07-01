from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env()


def load_db_config() -> dict:
    """
    数据库连接配置：
    - 优先读取环境变量
    - 没有则使用默认值（本机开发）
    """
    return {
        "host": os.getenv("UAV_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("UAV_DB_PORT", "3306")),
        "user": os.getenv("UAV_DB_USER", "root1"),
        "password": os.getenv("UAV_DB_PASSWORD", "123456"),
        "database": os.getenv("UAV_DB_NAME", "robot_monitor"),
    }
