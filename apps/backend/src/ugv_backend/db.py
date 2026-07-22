from __future__ import annotations

from typing import Any

import pymysql
from fastapi import HTTPException
from pymysql.cursors import DictCursor

from .config import SCHEMA_FILE, mysql_configured, mysql_settings


def get_server_db():
    settings = mysql_settings()
    return pymysql.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
        charset=settings["charset"],
        cursorclass=DictCursor,
        autocommit=False,
    )


def get_db():
    settings = mysql_settings()
    return pymysql.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
        charset=settings["charset"],
        cursorclass=DictCursor,
        autocommit=False,
    )


def ensure_mysql_configured() -> None:
    if mysql_configured():
        return
    raise HTTPException(
        status_code=503,
        detail="MySQL 未配置，请先在 .env 中设置 MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DATABASE。",
    )


def ensure_database() -> None:
    # Create database if missing before schema execution.
    if not mysql_configured():
        return
    settings = mysql_settings()
    connection = get_server_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings['database']}` CHARACTER SET {settings['charset']}"
            )
        connection.commit()
    finally:
        connection.close()


def schema_tables_ready(table_names: tuple[str, ...]) -> bool:
    if not mysql_configured():
        return False
    settings = mysql_settings()
    connection = get_server_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name IN %s
                """,
                (settings["database"], table_names),
            )
            row = cursor.fetchone() or {}
        return int(row.get("total", 0) or 0) == len(table_names)
    finally:
        connection.close()


def execute_schema() -> None:
    # Execute SQL bootstrap script in an idempotent way.
    if not mysql_configured() or not SCHEMA_FILE.exists():
        return
    if schema_tables_ready(("users", "robots", "tasks", "alerts", "reports")):
        return
    statements = [item.strip() for item in SCHEMA_FILE.read_text(encoding="utf-8").split(";") if item.strip()]
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


def ensure_iot_tables() -> None:
    if not mysql_configured():
        return
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS device_tokens (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    device_id BIGINT NOT NULL,
                    token VARCHAR(128) NOT NULL UNIQUE,
                    note VARCHAR(256) NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_dt_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS device_checkins (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    device_id BIGINT NOT NULL,
                    lat DECIMAL(10,7) NULL,
                    lng DECIMAL(10,7) NULL,
                    note TEXT NULL,
                    checked_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_ci_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS device_telemetry (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    device_id BIGINT NOT NULL,
                    battery TINYINT NULL,
                    `signal` TINYINT NULL,
                    status VARCHAR(32) NULL,
                    lat DECIMAL(10,7) NULL,
                    lng DECIMAL(10,7) NULL,
                    source_ip VARCHAR(64) NULL,
                    extra_json JSON NULL,
                    reported_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_tel_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("SHOW COLUMNS FROM device_telemetry LIKE 'source_ip'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE device_telemetry ADD COLUMN source_ip VARCHAR(64) NULL AFTER lng")
            cursor.execute("SHOW INDEX FROM device_telemetry WHERE Key_name = 'idx_telemetry_device_time'")
            if not cursor.fetchone():
                cursor.execute("CREATE INDEX idx_telemetry_device_time ON device_telemetry (device_id, reported_at DESC)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS device_sensor_data (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    device_id BIGINT NOT NULL,
                    sensor_type VARCHAR(32) NOT NULL COMMENT 'camera|stereo|lidar',
                    channel VARCHAR(32) NULL COMMENT 'mono|left|right|depth|scan|pointcloud',
                    file_path VARCHAR(512) NULL COMMENT '文件存储路径（图片类）',
                    data_json JSON NULL COMMENT '结构化数据（雷达/点云）',
                    content_type VARCHAR(64) NULL COMMENT 'MIME 类型',
                    size_bytes BIGINT NULL DEFAULT 0 COMMENT '文件大小',
                    extra_json JSON NULL COMMENT '附加元数据',
                    reported_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_sensor_device FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute("SHOW INDEX FROM device_sensor_data WHERE Key_name = 'idx_sensor_device_time'")
            if not cursor.fetchone():
                cursor.execute("CREATE INDEX idx_sensor_device_time ON device_sensor_data (device_id, sensor_type, reported_at DESC)")
            cursor.execute("SHOW INDEX FROM device_sensor_data WHERE Key_name = 'idx_sensor_device_type_channel_time'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    CREATE INDEX idx_sensor_device_type_channel_time
                    ON device_sensor_data (device_id, sensor_type, channel, reported_at DESC)
                    """
                )
        connection.commit()
    finally:
        connection.close()


def ensure_autonomy_tables() -> None:
    if not mysql_configured():
        return
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS autonomy_events (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    robot_id BIGINT NULL,
                    level VARCHAR(20) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    message TEXT,
                    data_json JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute("SHOW COLUMNS FROM autonomy_events LIKE 'robot_id'")
            column = cursor.fetchone()
            if column and str(column.get("Null", "")).upper() == "NO":
                cursor.execute("ALTER TABLE autonomy_events MODIFY robot_id BIGINT NULL")
            cursor.execute("SHOW INDEX FROM autonomy_events WHERE Key_name = 'idx_autonomy_events_robot_time'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    CREATE INDEX idx_autonomy_events_robot_time
                    ON autonomy_events (robot_id, created_at DESC)
                    """
                )
        connection.commit()
    finally:
        connection.close()


def ensure_management_system_tables() -> None:
    # Management tables are currently created by the canonical schema file.
    # Keep this hook so startup and tests can exercise the migration boundary.
    return None


def ensure_robot_ip_column() -> None:
    if not mysql_configured():
        return
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM robots LIKE 'ip_address'")
            if cursor.fetchone():
                connection.commit()
                return
            cursor.execute("ALTER TABLE robots ADD COLUMN ip_address VARCHAR(64) NULL AFTER model")
        connection.commit()
    finally:
        connection.close()


def ensure_robot_device_column() -> None:
    if not mysql_configured():
        return
    settings = mysql_settings()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM robots LIKE 'device_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE robots ADD COLUMN device_id BIGINT NULL AFTER ip_address")

            cursor.execute("SHOW INDEX FROM robots WHERE Key_name = 'idx_robots_device'")
            if not cursor.fetchone():
                cursor.execute("CREATE INDEX idx_robots_device ON robots (device_id)")

            cursor.execute(
                """
                UPDATE robots r
                JOIN (
                    SELECT id, robot_id
                    FROM (
                        SELECT d.id, d.robot_id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY d.robot_id
                                   ORDER BY d.created_at DESC, d.id DESC
                               ) AS rn
                        FROM devices d
                        WHERE d.robot_id IS NOT NULL
                    ) ranked
                    WHERE rn = 1
                ) latest ON latest.robot_id = r.id
                SET r.device_id = latest.id
                WHERE r.device_id IS NULL
                """
            )

            cursor.execute(
                """
                SELECT CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'robots'
                  AND COLUMN_NAME = 'device_id'
                  AND REFERENCED_TABLE_NAME = 'devices'
                LIMIT 1
                """,
                (settings["database"],),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    ALTER TABLE robots
                    ADD CONSTRAINT fk_robots_device
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
                    """
                )
        connection.commit()
    finally:
        connection.close()


def query_all(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    ensure_mysql_configured()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return list(cursor.fetchall())
    finally:
        connection.close()


def query_one(sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    ensure_mysql_configured()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    finally:
        connection.close()


def execute_write(sql: str, params: tuple[Any, ...] | None = None) -> int:
    ensure_mysql_configured()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            affected = cursor.execute(sql, params or ())
        connection.commit()
        return affected
    finally:
        connection.close()


def execute_insert(sql: str, params: tuple[Any, ...] | None = None) -> int:
    ensure_mysql_configured()
    connection = get_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            inserted_id = int(cursor.lastrowid or 0)
        connection.commit()
        return inserted_id
    finally:
        connection.close()


def clear_table(table_name: str, record_id: int) -> int:
    return execute_write(f"DELETE FROM {table_name} WHERE id = %s", (record_id,))
