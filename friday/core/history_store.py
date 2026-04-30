import os
import sqlite3
from contextlib import closing
from typing import List, Optional
from app.core.config import settings
from models.schemas import HistoryEntry, QueryResponse

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "query_history.sqlite")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_history_database() -> None:
    with closing(_get_connection()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                query TEXT,
                status TEXT,
                truth_score REAL,
                confidence_score REAL,
                summary TEXT,
                owner_email TEXT NOT NULL DEFAULT 'public'
            )
        """)
        try:
            conn.execute(
                "ALTER TABLE query_history ADD COLUMN owner_email TEXT NOT NULL DEFAULT 'public'"
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()


def log_query_result(payload: QueryResponse, owner_email: str = "public") -> None:
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO query_history (timestamp, query, status, truth_score, confidence_score, summary, owner_email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                payload.timestamp,
                payload.query,
                payload.status,
                payload.truth_score,
                payload.confidence_score,
                payload.summary,
                owner_email,
            ),
        )
        conn.commit()


def fetch_recent_history(
    limit: Optional[int] = None, owner_email: str = None
) -> List[HistoryEntry]:
    effective_limit = limit or settings.HISTORY_MAX_ITEMS
    with closing(_get_connection()) as conn:
        if owner_email:
            rows = conn.execute(
                "SELECT * FROM query_history WHERE owner_email = ? ORDER BY timestamp DESC LIMIT ?",
                (
                    owner_email,
                    effective_limit,
                ),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM query_history ORDER BY timestamp DESC LIMIT ?",
                (effective_limit,),
            ).fetchall()
    return [
        HistoryEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            query=row["query"],
            status=row["status"],
            truth_score=row["truth_score"],
            summary=row["summary"],
        )
        for row in rows
    ]


init_history_database()
