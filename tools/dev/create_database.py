from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT_DIR / ".env"
DEFAULT_SCHEMA_FILE = ROOT_DIR / "apps" / "backend" / "db" / "mysql_schema.sql"


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
        description="Create a MySQL database for this project and execute schema SQL."
    )
    parser.add_argument("--host", help="MySQL host")
    parser.add_argument("--port", type=int, help="MySQL port")
    parser.add_argument("--user", help="MySQL user")
    parser.add_argument("--password", help="MySQL password")
    parser.add_argument("--database", help="Target database name")
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=DEFAULT_SCHEMA_FILE,
        help=f"Schema SQL path. Default: {DEFAULT_SCHEMA_FILE}",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f".env path used as fallback. Default: {DEFAULT_ENV_FILE}",
    )
    parser.add_argument(
        "--charset",
        default=None,
        help="Database charset. Default comes from env or utf8mb4.",
    )
    parser.add_argument(
        "--collation",
        default="utf8mb4_unicode_ci",
        help="Database collation. Default: utf8mb4_unicode_ci",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved configuration without connecting to MySQL.",
    )
    return parser.parse_args()


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


def connect(driver_name: str, driver, config: dict, database: str | None = None):
    kwargs = {
        "host": config["host"],
        "port": config["port"],
        "user": config["user"],
        "password": config["password"],
        "charset": config["charset"],
    }
    if database:
        kwargs["database"] = database
    if driver_name == "pymysql":
        kwargs["autocommit"] = True
        return driver.connect(**kwargs)
    return driver.connect(**kwargs)


def strip_schema_preamble(sql: str) -> str:
    sql = re.sub(
        r"^\s*CREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\s+`?[\w-]+`?.*?;\s*",
        "",
        sql,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    sql = re.sub(
        r"^\s*USE\s+`?[\w-]+`?\s*;\s*",
        "",
        sql,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return sql


def split_sql_statements(sql: str) -> Iterable[str]:
    current: list[str] = []
    in_single = False
    in_double = False
    escape = False
    for ch in sql:
        current.append(ch)
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                yield statement[:-1].strip()
            current = []
    tail = "".join(current).strip()
    if tail:
        yield tail


def execute_statements(conn, statements: Iterable[str]) -> None:
    cursor = conn.cursor()
    try:
        for statement in statements:
            if statement:
                cursor.execute(statement)
        try:
            conn.commit()
        except Exception:
            pass
    finally:
        cursor.close()


def create_database(conn, database: str, charset: str, collation: str) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database}` "
            f"DEFAULT CHARACTER SET {charset} COLLATE {collation}"
        )
        try:
            conn.commit()
        except Exception:
            pass
    finally:
        cursor.close()


def build_config(args: argparse.Namespace) -> dict:
    load_dotenv(args.env_file)
    port_value = args.port
    if port_value is None:
        port_value = int(pick_value(None, "MYSQL_PORT", default="3306"))
    return {
        "host": pick_value(args.host, "MYSQL_HOST", default="127.0.0.1"),
        "port": int(port_value),
        "user": pick_value(args.user, "MYSQL_USER", default="root"),
        "password": pick_value(args.password, "MYSQL_PASSWORD", default=""),
        "database": pick_value(args.database, "MYSQL_DATABASE", default="robot_monitor"),
        "charset": pick_value(args.charset, "MYSQL_CHARSET", default="utf8mb4"),
        "collation": args.collation,
        "schema_file": args.schema_file,
    }


def main() -> int:
    args = parse_args()
    config = build_config(args)

    if args.dry_run:
        print("Resolved MySQL configuration:")
        print(f"  host: {config['host']}")
        print(f"  port: {config['port']}")
        print(f"  user: {config['user']}")
        print(f"  password: {'*' * len(config['password']) if config['password'] else '(empty)'}")
        print(f"  database: {config['database']}")
        print(f"  charset: {config['charset']}")
        print(f"  collation: {config['collation']}")
        print(f"  schema_file: {config['schema_file']}")
        return 0

    if not config["schema_file"].exists():
        print(f"Schema file not found: {config['schema_file']}", file=sys.stderr)
        return 1

    driver_name, driver = get_driver()
    if not driver:
        print(
            "MySQL driver not found. Install pymysql or mysql-connector-python first.",
            file=sys.stderr,
        )
        return 1

    schema_sql = config["schema_file"].read_text(encoding="utf-8-sig")
    schema_sql = strip_schema_preamble(schema_sql)
    statements = list(split_sql_statements(schema_sql))

    try:
        server_conn = connect(driver_name, driver, config, database=None)
        create_database(server_conn, config["database"], config["charset"], config["collation"])
        server_conn.close()

        db_conn = connect(driver_name, driver, config, database=config["database"])
        execute_statements(db_conn, statements)
        db_conn.close()
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        return 1

    print(f"Database initialized successfully: {config['database']}")
    print(f"Schema applied from: {config['schema_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
