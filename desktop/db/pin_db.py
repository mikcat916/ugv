from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import pymysql

from db.db_config import load_db_config


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _hash_pin_pbkdf2(pin: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 120000)
    return dk.hex()


class PinStore:
    def __init__(self) -> None:
        cfg = load_db_config()
        self.host = cfg["host"]
        self.port = cfg["port"]
        self.user = cfg["user"]
        self.password = cfg["password"]
        self.database = cfg["database"]

    def _connect(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    def init_db(self, default_pin: str = "123456", pinlen: int = 6) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_pin (
                        id INT PRIMARY KEY CHECK(id=1),
                        pinhash VARCHAR(255) NOT NULL,
                        salt VARCHAR(64) NOT NULL,
                        pinalgo VARCHAR(32) NOT NULL DEFAULT 'bcrypt',
                        pinlen INT NOT NULL DEFAULT 6,
                        failedcount INT NOT NULL DEFAULT 0,
                        maxfailed INT NOT NULL DEFAULT 5,
                        lastfailat DATETIME NULL,
                        lockuntil DATETIME NULL,
                        lockminutes INT NOT NULL DEFAULT 10,
                        updatedat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )

                cur.execute("SELECT id FROM device_pin WHERE id=1;")
                if cur.fetchone() is None:
                    salt = secrets.token_hex(8)
                    pinhash = _hash_pin_pbkdf2(default_pin, salt)
                    cur.execute(
                        """
                        INSERT INTO device_pin
                        (id, pinhash, salt, pinalgo, pinlen, failedcount, maxfailed, lastfailat, lockuntil, lockminutes)
                        VALUES (1, %s, %s, %s, %s, 0, 5, NULL, NULL, 10);
                        """,
                        (pinhash, salt, "pbkdf2", pinlen),
                    )

    def _get_row(self) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM device_pin WHERE id=1;")
                return cur.fetchone()

    def _update(self, **fields) -> None:
        if not fields:
            return
        fields["updatedat"] = _now_iso()
        sets = ", ".join(f"{k}=%s" for k in fields.keys())
        values = list(fields.values())
        values.append(1)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE device_pin SET {sets} WHERE id=%s;", values)

    def is_locked(self) -> bool:
        row = self._get_row()
        if not row:
            return False
        until = _parse_iso(row.get("lockuntil"))
        if not until:
            return False
        return datetime.now() < until

    def get_lock_info(self) -> tuple[bool, Optional[datetime]]:
        row = self._get_row()
        if not row:
            return False, None
        until = _parse_iso(row.get("lockuntil"))
        if not until:
            return False, None
        return datetime.now() < until, until

    def verify(self, pin: str) -> bool:
        row = self._get_row()
        if not row:
            return False
        if self.is_locked():
            return False

        salt = row.get("salt")
        algo = row.get("pinalgo")
        if algo == "pbkdf2":
            pinhash = _hash_pin_pbkdf2(pin, salt)
        else:
            # fallback to pbkdf2 if unknown algo
            pinhash = _hash_pin_pbkdf2(pin, salt)

        if pinhash == row["pinhash"]:
            self._update(failedcount=0, lastfailat=None, lockuntil=None)
            return True

        failed = int(row.get("failedcount", 0)) + 1
        maxfailed = int(row.get("maxfailed", 5))
        lockminutes = int(row.get("lockminutes", 10))
        lockuntil = None
        if failed >= maxfailed:
            lockuntil = (datetime.now() + timedelta(minutes=lockminutes)).replace(microsecond=0).isoformat()
            failed = maxfailed

        self._update(
            failedcount=failed,
            lastfailat=_now_iso(),
            lockuntil=lockuntil,
        )
        return False
