from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
LEGACY_ENV_FILE = ROOT_DIR / "backend" / ".env"
PYDEPS_DIR = ROOT_DIR / ".pydeps"

if PYDEPS_DIR.exists():
    sys.path.insert(0, str(PYDEPS_DIR))

import pymysql


DEVICE_TOKENS_SQL = """
CREATE TABLE IF NOT EXISTS device_tokens (
    id         BIGINT       PRIMARY KEY AUTO_INCREMENT,
    device_id  BIGINT       NOT NULL,
    token      VARCHAR(128) NOT NULL UNIQUE,
    note       VARCHAR(256) NULL,
    is_active  TINYINT(1)   NOT NULL DEFAULT 1,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dt_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='Device auth tokens'
"""

DEVICE_CHECKINS_SQL = """
CREATE TABLE IF NOT EXISTS device_checkins (
    id         BIGINT        PRIMARY KEY AUTO_INCREMENT,
    device_id  BIGINT        NOT NULL,
    point_id   BIGINT        NULL,
    route_id   BIGINT        NULL,
    lat        DECIMAL(10,7) NULL,
    lng        DECIMAL(10,7) NULL,
    note       TEXT          NULL,
    checked_at DATETIME      NOT NULL,
    created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ci_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT fk_ci_point  FOREIGN KEY (point_id)  REFERENCES points(id)  ON DELETE SET NULL,
    CONSTRAINT fk_ci_route  FOREIGN KEY (route_id)  REFERENCES routes(id)  ON DELETE SET NULL
) COMMENT='Device check-in records'
"""

DEVICE_TELEMETRY_SQL = """
CREATE TABLE IF NOT EXISTS device_telemetry (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT,
    device_id   BIGINT        NOT NULL,
    battery     TINYINT       NULL,
    `signal`    TINYINT       NULL,
    status      VARCHAR(32)   NULL,
    lat         DECIMAL(10,7) NULL,
    lng         DECIMAL(10,7) NULL,
    extra_json  JSON          NULL,
    reported_at DATETIME      NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_telemetry_device_time (device_id, reported_at DESC),
    CONSTRAINT fk_tel_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) COMMENT='Device telemetry records'
"""


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def pick_value(cli_value: str | None, *env_keys: str, default: str = "") -> str:
    if cli_value is not None:
        return cli_value
    for key in env_keys:
        value = os.getenv(key)
        if value is not None and value.strip():
            return value.strip()
    return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap IoT backend tables and optionally mint a device token.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--database")
    parser.add_argument("--device-id", type=int, default=2, help="Device id to mint a token for")
    parser.add_argument("--note", default="raspberrypi car deploy")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> dict[str, object]:
    load_dotenv(args.env_file)
    if args.env_file != LEGACY_ENV_FILE:
        load_dotenv(LEGACY_ENV_FILE)
    return {
        "host": pick_value(args.host, "UAV_DB_HOST", "MYSQL_HOST", default="127.0.0.1"),
        "port": int(args.port or pick_value(None, "UAV_DB_PORT", "MYSQL_PORT", default="3306")),
        "user": pick_value(args.user, "UAV_DB_USER", "MYSQL_USER", default="root"),
        "password": pick_value(args.password, "UAV_DB_PASSWORD", "MYSQL_PASSWORD", default=""),
        "database": pick_value(args.database, "UAV_DB_NAME", "MYSQL_DATABASE", default="robot_monitor"),
        "device_id": args.device_id,
        "note": args.note,
    }


def main() -> int:
    args = parse_args()
    config = build_config(args)
    conn = pymysql.connect(
        host=str(config["host"]),
        port=int(config["port"]),
        user=str(config["user"]),
        password=str(config["password"]),
        database=str(config["database"]),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(DEVICE_TOKENS_SQL)
            cur.execute(DEVICE_CHECKINS_SQL)
            cur.execute(DEVICE_TELEMETRY_SQL)
            cur.execute("SELECT id, name FROM devices WHERE id = %s", (int(config["device_id"]),))
            device = cur.fetchone()
            if not device:
                print(f"Device not found: {config['device_id']}", file=sys.stderr)
                return 1
            cur.execute(
                "SELECT token FROM device_tokens WHERE device_id = %s AND is_active = 1 ORDER BY id DESC LIMIT 1",
                (int(config["device_id"]),),
            )
            row = cur.fetchone()
            if row:
                token = row["token"]
                created = False
            else:
                raw = f"{config['device_id']}-{secrets.token_hex(16)}-{datetime.now().isoformat()}"
                token = hashlib.sha256(raw.encode()).hexdigest()
                cur.execute(
                    "INSERT INTO device_tokens (device_id, token, note, is_active, created_at) VALUES (%s,%s,%s,1,%s)",
                    (int(config["device_id"]), token, str(config["note"]), datetime.now()),
                )
                created = True
    finally:
        conn.close()

    print(f"device_id={config['device_id']}")
    print(f"token_created={created}")
    print(f"token={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
