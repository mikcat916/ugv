from __future__ import annotations

try:
    from loguru import logger
except Exception:
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from MICCProject1.scripts.Config import load_config


def _load_driver():
    try:
        import mysql.connector as driver

        return "mysql.connector", driver
    except Exception:
        try:
            import pymysql as driver

            return "pymysql", driver
        except Exception:
            return None, None


class DBHelper:
    def __init__(self):
        self.conn = None
        self.driver_name, self.driver = _load_driver()

        cfg = load_config()
        self.db_config = {
            "host": cfg.get("DB_HOST", "127.0.0.1"),
            "port": int(cfg.get("DB_PORT", "3306") or 3306),
            "user": cfg.get("DB_USER", "root"),
            "password": cfg.get("DB_PASS", "123456"),
            "db_name": cfg.get("DB_NAME", "UGV_DB"),
            "mysqldump_path": cfg.get("mysqldump_path") or "mysqldump",
            "mysql_path": cfg.get("mysql_path") or "mysql",
        }

        if not self.driver:
            logger.error("数据库连接失败: 未安装 mysql-connector-python 或 pymysql")
            return

        try:
            if self.driver_name == "mysql.connector":
                self.conn = self.driver.connect(
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    user=self.db_config["user"],
                    password=self.db_config["password"],
                    database=self.db_config["db_name"],
                    connection_timeout=2,
                    charset="utf8mb4",
                )
            else:
                self.conn = self.driver.connect(
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    user=self.db_config["user"],
                    password=self.db_config["password"],
                    database=self.db_config["db_name"],
                    connect_timeout=2,
                    charset="utf8mb4",
                    autocommit=False,
                    cursorclass=self.driver.cursors.DictCursor,
                )
            logger.info("数据库连接成功")
        except Exception as exc:
            logger.error(f"数据库连接失败: {exc}")
            self.conn = None

    def _is_connected(self) -> bool:
        if self.conn is None:
            return False
        if self.driver_name == "mysql.connector":
            try:
                return self.conn.is_connected()
            except Exception:
                return False
        return True

    def _get_cursor(self):
        if not self._is_connected():
            raise RuntimeError("数据库未连接")
        if self.driver_name == "mysql.connector":
            return self.conn.cursor(dictionary=True)
        return self.conn.cursor()

    def execute_query(self, query, params=None):
        cursor = None
        try:
            cursor = self._get_cursor()
            cursor.execute(query, params or ())

            if query.strip().lower().startswith("select"):
                return cursor.fetchall()

            self.conn.commit()
            return cursor.rowcount
        except Exception as exc:
            logger.error(f"执行SQL失败: {exc}")
            if self.conn is not None:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            return None
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    def fetch_all(self, query, params=None):
        result = self.execute_query(query, params)
        return result if result is not None else []

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
