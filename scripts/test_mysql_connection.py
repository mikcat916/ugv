from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
LEGACY_ENV_FILE = ROOT_DIR / "backend" / ".env"
PYDEPS_DIR = ROOT_DIR / ".pydeps"
LOG_DIR = ROOT_DIR / "logs"
EXPECTED_TABLES = ("users", "devices", "areas", "points", "routes", "route_points")

if PYDEPS_DIR.exists():
    sys.path.insert(0, str(PYDEPS_DIR))


class ConsoleFormatter(logging.Formatter):
    COLORS = {
        "INFO": "\033[36m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = self.COLORS.get(record.levelname)
        if not color or not sys.stdout.isatty():
            return message
        return f"{color}{message}{self.RESET}"


def configure_logger() -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"mysql_diagnose_{datetime.now():%Y%m%d_%H%M%S}.log"
    logger = logging.getLogger("mysql_diagnose")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter("%(message)s"))
    logger.addHandler(console_handler)
    return logger, log_path


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
    parser = argparse.ArgumentParser(
        description="Diagnose MySQL connectivity for this project with step-by-step logs."
    )
    parser.add_argument("--host", help="MySQL host")
    parser.add_argument("--port", type=int, help="MySQL port")
    parser.add_argument("--user", help="MySQL user")
    parser.add_argument("--password", help="MySQL password")
    parser.add_argument("--database", help="MySQL database")
    parser.add_argument("--charset", help="MySQL charset")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help=f"Default: {DEFAULT_ENV_FILE}")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket/connect timeout in seconds")
    parser.add_argument("--skip-table-check", action="store_true", help="Skip expected table checks")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(args.env_file)
    if args.env_file != LEGACY_ENV_FILE:
        load_dotenv(LEGACY_ENV_FILE)
    port_value = args.port
    if port_value is None:
        port_value = int(pick_value(None, "UAV_DB_PORT", "MYSQL_PORT", default="3306"))
    return {
        "host": pick_value(args.host, "UAV_DB_HOST", "MYSQL_HOST", default="127.0.0.1"),
        "port": int(port_value),
        "user": pick_value(args.user, "UAV_DB_USER", "MYSQL_USER", default="root"),
        "password": pick_value(args.password, "UAV_DB_PASSWORD", "MYSQL_PASSWORD", default=""),
        "database": pick_value(args.database, "UAV_DB_NAME", "MYSQL_DATABASE", default="robot_monitor"),
        "charset": pick_value(args.charset, "MYSQL_CHARSET", default="utf8mb4"),
        "env_file": args.env_file,
        "timeout": args.timeout,
    }


def mask_secret(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"


def log_step(logger: logging.Logger, index: int, title: str) -> None:
    logger.info("")
    logger.info("=" * 72)
    logger.info("STEP %s: %s", index, title)
    logger.info("=" * 72)


def log_pass(logger: logging.Logger, message: str) -> None:
    logger.info("[PASS] %s", message)


def log_warn(logger: logging.Logger, message: str) -> None:
    logger.warning("[WARN] %s", message)


def log_fail(logger: logging.Logger, message: str) -> None:
    logger.error("[FAIL] %s", message)


def get_driver():
    try:
        import pymysql as driver

        return "pymysql", driver
    except Exception:
        try:
            import mysql.connector as driver

            return "mysql.connector", driver
        except Exception:
            return None, None


def connect(driver_name: str, driver, config: dict[str, Any], database: str | None = None):
    kwargs = {
        "host": config["host"],
        "port": config["port"],
        "user": config["user"],
        "password": config["password"],
        "charset": config["charset"],
        "connect_timeout": int(max(config["timeout"], 1)),
    }
    if database:
        kwargs["database"] = database
    if driver_name == "pymysql":
        kwargs["autocommit"] = True
        return driver.connect(**kwargs)
    return driver.connect(**kwargs)


def check_tcp(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "TCP connection succeeded"
    except Exception as exc:
        return False, str(exc)


def query_scalar(cursor, sql: str, params: tuple[Any, ...] | None = None) -> Any:
    cursor.execute(sql, params or ())
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    if isinstance(row, (list, tuple)):
        return row[0]
    return row


def main() -> int:
    args = parse_args()
    logger, log_path = configure_logger()
    config = build_config(args)
    failures: list[str] = []
    warnings: list[str] = []

    logger.info("MySQL diagnose started")
    logger.info("Log file: %s", log_path)

    log_step(logger, 1, "Load configuration")
    logger.info("env_file   : %s", config["env_file"])
    logger.info("host       : %s", config["host"])
    logger.info("port       : %s", config["port"])
    logger.info("user       : %s", config["user"])
    logger.info("password   : %s", mask_secret(config["password"]))
    logger.info("database   : %s", config["database"])
    logger.info("charset    : %s", config["charset"])
    if not config["host"] or not config["user"] or not config["database"]:
        failures.append("Configuration is incomplete")
        log_fail(logger, "MYSQL_HOST / MYSQL_USER / MYSQL_DATABASE has empty values")
    else:
        log_pass(logger, "Configuration values are present")

    log_step(logger, 2, "Import MySQL driver")
    driver_name, driver = get_driver()
    if not driver:
        failures.append("MySQL driver import failed")
        log_fail(logger, "Neither pymysql nor mysql-connector-python is installed")
        log_warn(logger, "Install one of them first, for example: py -m pip install pymysql")
        logger.info("")
        logger.info("Summary")
        for item in failures:
            logger.error(" - %s", item)
        logger.info("Log file saved to: %s", log_path)
        return 1
    log_pass(logger, f"MySQL driver loaded: {driver_name}")

    log_step(logger, 3, "Resolve host and test TCP port")
    try:
        host_ip = socket.gethostbyname(config["host"])
        log_pass(logger, f"Host resolved: {config['host']} -> {host_ip}")
    except Exception as exc:
        failures.append("Host resolution failed")
        log_fail(logger, f"Cannot resolve host {config['host']}: {exc}")
        host_ip = ""
    tcp_ok, tcp_message = check_tcp(config["host"], config["port"], config["timeout"])
    if tcp_ok:
        log_pass(logger, f"TCP {config['host']}:{config['port']} is reachable")
    else:
        failures.append("TCP port is not reachable")
        log_fail(logger, f"Cannot connect to {config['host']}:{config['port']}: {tcp_message}")
        log_warn(logger, "Check MySQL service status, firewall, port mapping, and bind-address")

    log_step(logger, 4, "Connect to MySQL server")
    server_conn = None
    try:
        server_conn = connect(driver_name, driver, config, database=None)
        log_pass(logger, "Connected to MySQL server successfully")
        with server_conn.cursor() as cursor:
            version = query_scalar(cursor, "SELECT VERSION()")
            current_user = query_scalar(cursor, "SELECT CURRENT_USER()")
            log_pass(logger, f"MySQL version: {version}")
            log_pass(logger, f"Authenticated as: {current_user}")
    except Exception as exc:
        failures.append("Server connection failed")
        log_fail(logger, f"Cannot authenticate/connect to server: {exc}")
        log_warn(logger, "Typical causes: wrong username/password, host authorization, service not running")
    finally:
        if server_conn is not None:
            server_conn.close()

    log_step(logger, 5, "Connect to target database")
    db_conn = None
    try:
        db_conn = connect(driver_name, driver, config, database=config["database"])
        log_pass(logger, f"Connected to database: {config['database']}")
        with db_conn.cursor() as cursor:
            now_value = query_scalar(cursor, "SELECT NOW()")
            log_pass(logger, f"Database responds to SELECT NOW(): {now_value}")
    except Exception as exc:
        failures.append("Database connection failed")
        log_fail(logger, f"Cannot connect to database {config['database']}: {exc}")
        log_warn(logger, "If the server login works but database login fails, verify database name and privileges")
    finally:
        if db_conn is not None:
            db_conn.close()

    if not args.skip_table_check:
        log_step(logger, 6, "Check expected project tables")
        db_conn = None
        try:
            db_conn = connect(driver_name, driver, config, database=config["database"])
            with db_conn.cursor() as cursor:
                missing: list[str] = []
                for table in EXPECTED_TABLES:
                    cursor.execute("SHOW TABLES LIKE %s", (table,))
                    if cursor.fetchone():
                        log_pass(logger, f"Table exists: {table}")
                    else:
                        missing.append(table)
                        log_warn(logger, f"Table missing: {table}")
                if missing:
                    warnings.append(f"Missing tables: {', '.join(missing)}")
                    log_warn(logger, "Schema may not be initialized on this machine")
                else:
                    log_pass(logger, "All expected project tables are present")
        except Exception as exc:
            warnings.append("Skipped table check because database connection failed")
            log_warn(logger, f"Cannot inspect tables: {exc}")
        finally:
            if db_conn is not None:
                db_conn.close()

    logger.info("")
    logger.info("=" * 72)
    logger.info("SUMMARY")
    logger.info("=" * 72)
    if failures:
        for item in failures:
            logger.error("FAILED: %s", item)
    else:
        logger.info("FAILED: none")
    if warnings:
        for item in warnings:
            logger.warning("WARN  : %s", item)
    else:
        logger.info("WARN  : none")
    logger.info("Log file saved to: %s", log_path)

    if failures:
        logger.error("Diagnosis result: connection path is NOT healthy")
        return 1

    logger.info("Diagnosis result: connection path looks healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
