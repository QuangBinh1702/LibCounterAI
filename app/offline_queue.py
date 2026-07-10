import sqlite3
import json
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "offline_queue.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_ops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            operation TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            retries INTEGER DEFAULT 0,
            last_error TEXT
        )
    """)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.commit()
    return conn


def enqueue(table_name: str, operation: str, data: dict):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO pending_ops (table_name, operation, data, created_at) VALUES (?, ?, ?, ?)",
            (table_name, operation, json.dumps(data, default=str), datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_pending():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, table_name, operation, data, created_at, retries, last_error FROM pending_ops ORDER BY id ASC"
        ).fetchall()
        return [
            {
                "id": r[0],
                "table_name": r[1],
                "operation": r[2],
                "data": json.loads(r[3]),
                "created_at": r[4],
                "retries": r[5],
                "last_error": r[6],
            }
            for r in rows
        ]
    finally:
        conn.close()


def remove(op_id: int):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM pending_ops WHERE id = ?", (op_id,))
        conn.commit()
    finally:
        conn.close()


def mark_error(op_id: int, error: str):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE pending_ops SET retries = retries + 1, last_error = ? WHERE id = ?",
            (str(error), op_id),
        )
        conn.commit()
    finally:
        conn.close()


def count_pending() -> int:
    conn = get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM pending_ops").fetchone()[0]
    finally:
        conn.close()


def is_postgres_alive() -> bool:
    try:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
