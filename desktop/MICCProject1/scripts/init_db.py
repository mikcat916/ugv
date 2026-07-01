from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path


def load_config(path: Path) -> dict:
    config = configparser.ConfigParser()
    if not path.exists():
        raise FileNotFoundError(f"config.ini not found: {path}")
    config.read(path, encoding="utf-8")
    if "mysql" not in config:
        raise KeyError("[mysql] section not found in config.ini")
    section = config["mysql"]
    cfg = {
        "host": section.get("db_host", "127.0.0.1"),
        "port": section.getint("db_port", 3306),
        "user": section.get("db_user", "root"),
        "password": section.get("db_pass", ""),
        "db_name": section.get("db_name", "device_management"),
    }
    cfg["host"] = os.getenv("UAV_DB_HOST", os.getenv("MYSQL_HOST", cfg["host"]))
    cfg["port"] = int(os.getenv("UAV_DB_PORT", os.getenv("MYSQL_PORT", str(cfg["port"]))))
    cfg["user"] = os.getenv("UAV_DB_USER", os.getenv("MYSQL_USER", cfg["user"]))
    cfg["password"] = os.getenv("UAV_DB_PASSWORD", os.getenv("MYSQL_PASSWORD", cfg["password"]))
    cfg["db_name"] = os.getenv("UAV_DB_NAME", os.getenv("MYSQL_DATABASE", cfg["db_name"]))
    return cfg


def get_driver():
    try:
        import mysql.connector as driver

        return "mysql.connector", driver
    except Exception:
        try:
            import pymysql as driver

            return "pymysql", driver
        except Exception:
            return None, None


def connect(driver_name: str, driver, cfg: dict, database: str | None = None):
    if driver_name == "mysql.connector":
        return driver.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=database,
            charset="utf8mb4",
        )
    return driver.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=database,
        charset="utf8mb4",
        autocommit=True,
    )


def exec_schema(conn, sql: str) -> None:
    cursor = conn.cursor()
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        cursor.execute(stmt)
    try:
        conn.commit()
    except Exception:
        pass
    cursor.close()


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    cfg_path = base / "config.ini"
    schema_path = base / "sql" / "schema.sql"

    cfg = load_config(cfg_path)
    if not schema_path.exists():
        print(f"schema.sql not found: {schema_path}")
        return 1

    driver_name, driver = get_driver()
    if not driver:
        print("MySQL driver not found. Install mysql-connector-python or pymysql.")
        return 1

    db_name = cfg["db_name"]

    conn = connect(driver_name, driver, cfg, database=None)
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    try:
        conn.commit()
    except Exception:
        pass
    cur.close()
    conn.close()

    conn = connect(driver_name, driver, cfg, database=db_name)
    sql = schema_path.read_text(encoding="utf-8-sig")
    exec_schema(conn, sql)
    conn.close()

    print("Schema initialized OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
