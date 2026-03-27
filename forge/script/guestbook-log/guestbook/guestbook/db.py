from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "migrations/schema.sql"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat(timespec="seconds")


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def record_entry(conn: sqlite3.Connection, entry: dict) -> int:
    cur = conn.execute(
        """
        INSERT INTO entries (
            created_utc, updated_utc, status, display_name, comment_raw, comment_rendered,
            page_url, page_path, page_title, referrer, ip_address, ip_hash, user_agent,
            accept_language, submission_token, honeypot_value, filter_score, filter_flags,
            source_kind, notes_internal, is_deleted
        ) VALUES (
            :created_utc, :updated_utc, :status, :display_name, :comment_raw, :comment_rendered,
            :page_url, :page_path, :page_title, :referrer, :ip_address, :ip_hash, :user_agent,
            :accept_language, :submission_token, :honeypot_value, :filter_score, :filter_flags,
            :source_kind, :notes_internal, :is_deleted
        )
        """,
        {
            **entry,
            "filter_flags": json.dumps(entry["filter_flags"], sort_keys=True),
        },
    )
    return int(cur.lastrowid)


def add_moderation_event(conn: sqlite3.Connection, entry_id: int, action: str, actor: str, notes: str = "") -> None:
    conn.execute(
        """
        INSERT INTO moderation_events (entry_id, event_utc, action, actor, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entry_id, utc_now_text(), action, actor, notes),
    )


def set_status(conn: sqlite3.Connection, entry_id: int, status: str, actor: str, notes: str = "") -> None:
    conn.execute(
        "UPDATE entries SET status = ?, updated_utc = ? WHERE id = ?",
        (status, utc_now_text(), entry_id),
    )
    add_moderation_event(conn, entry_id, status, actor, notes)


def fetch_public_entries(conn: sqlite3.Connection, page_path: str | None = None, limit: int = 50, order: str = "newest") -> list[sqlite3.Row]:
    order_clause = "DESC" if order == "newest" else "ASC"
    if page_path:
        cur = conn.execute(
            f"""
            SELECT id, created_utc, display_name, comment_rendered, page_path, page_title
            FROM entries
            WHERE status = 'approved' AND is_deleted = 0 AND page_path = ?
            ORDER BY created_utc {order_clause}
            LIMIT ?
            """,
            (page_path, limit),
        )
    else:
        cur = conn.execute(
            f"""
            SELECT id, created_utc, display_name, comment_rendered, page_path, page_title
            FROM entries
            WHERE status = 'approved' AND is_deleted = 0
            ORDER BY created_utc {order_clause}
            LIMIT ?
            """,
            (limit,),
        )
    return list(cur.fetchall())


def count_public_entries(conn: sqlite3.Connection, page_path: str) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE status = 'approved' AND is_deleted = 0 AND page_path = ?",
        (page_path,),
    )
    return int(cur.fetchone()[0])


def list_entries(conn: sqlite3.Connection, status: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
    if status:
        cur = conn.execute(
            """
            SELECT id, created_utc, status, display_name, page_path, filter_score, filter_flags
            FROM entries
            WHERE status = ?
            ORDER BY created_utc DESC
            LIMIT ?
            """,
            (status, limit),
        )
    else:
        cur = conn.execute(
            """
            SELECT id, created_utc, status, display_name, page_path, filter_score, filter_flags
            FROM entries
            ORDER BY created_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
    return list(cur.fetchall())


def get_entry(conn: sqlite3.Connection, entry_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    return cur.fetchone()


def recent_count(conn: sqlite3.Connection, ip_address: str, since: datetime) -> int:
    cur = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE ip_address = ? AND created_utc >= ?",
        (ip_address, since.isoformat(timespec="seconds")),
    )
    return int(cur.fetchone()[0])


def last_submission_time(conn: sqlite3.Connection, ip_address: str) -> datetime | None:
    cur = conn.execute(
        "SELECT created_utc FROM entries WHERE ip_address = ? ORDER BY created_utc DESC LIMIT 1",
        (ip_address,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return datetime.fromisoformat(row["created_utc"])


def build_stats(conn: sqlite3.Connection) -> dict:
    total = int(conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
    pending = int(conn.execute("SELECT COUNT(*) FROM entries WHERE status = 'pending'").fetchone()[0])
    approved = int(conn.execute("SELECT COUNT(*) FROM entries WHERE status = 'approved'").fetchone()[0])
    spam = int(conn.execute("SELECT COUNT(*) FROM entries WHERE status = 'spam'").fetchone()[0])
    pages = list(
        conn.execute(
            """
            SELECT page_path, COUNT(*) AS total
            FROM entries
            GROUP BY page_path
            ORDER BY total DESC, page_path ASC
            LIMIT 20
            """
        ).fetchall()
    )
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "spam": spam,
        "pages": pages,
    }


def export_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM entries ORDER BY created_utc DESC").fetchall())


def search_entries(conn: sqlite3.Connection, term: str, limit: int = 50) -> list[sqlite3.Row]:
    like = f"%{term}%"
    return list(
        conn.execute(
            """
            SELECT id, created_utc, status, display_name, page_path, comment_raw
            FROM entries
            WHERE display_name LIKE ? OR comment_raw LIKE ? OR page_path LIKE ?
            ORDER BY created_utc DESC
            LIMIT ?
            """,
            (like, like, like, limit),
        ).fetchall()
    )


def rate_limit_snapshot(conn: sqlite3.Connection, ip_address: str) -> dict[str, int]:
    now = utc_now()
    return {
        "hour": recent_count(conn, ip_address, now - timedelta(hours=1)),
        "day": recent_count(conn, ip_address, now - timedelta(days=1)),
    }

