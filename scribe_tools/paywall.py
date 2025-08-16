from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "paywall.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                customer_id TEXT PRIMARY KEY,
                email TEXT,
                status TEXT,
                current_period_end INTEGER
            )
            """
        )
        con.commit()


def set_subscription(customer_id: str, email: Optional[str], status: str, current_period_end: Optional[int]) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO users (customer_id, email, status, current_period_end)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
              email=excluded.email,
              status=excluded.status,
              current_period_end=excluded.current_period_end
            """,
            (customer_id, email, status, current_period_end or 0),
        )
        con.commit()


def get_user(customer_id: str) -> Optional[Tuple[str, str, str, int]]:
    with _conn() as con:
        cur = con.execute("SELECT customer_id, email, status, current_period_end FROM users WHERE customer_id=?", (customer_id,))
        row = cur.fetchone()
        return row if row else None


def is_active(customer_id: str) -> bool:
    row = get_user(customer_id)
    if not row:
        return False
    _, _, status, period_end = row
    now = int(time.time())
    return status in ("active", "trialing") and (period_end == 0 or period_end > now)
