import os
import sqlite3
from contextlib import closing
from typing import List, Optional

from config.settings import settings
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                status TEXT NOT NULL,
                truth_score REAL NOT NULL,
                confidence_score REAL NOT NULL,
                summary TEXT NOT NULL
            )
            """
        )
        conn.commit()


def log_query_result(payload: QueryResponse) -> None:
    with closing(_get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO query_history (timestamp, query, status, truth_score, confidence_score, summary)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.timestamp,
                payload.query,
                payload.status,
                payload.truth_score,
                payload.confidence_score,
                payload.summary,
            ),
        )
        conn.commit()


def fetch_recent_history(limit: Optional[int] = None) -> List[HistoryEntry]:
    effective_limit = limit or settings.HISTORY_MAX_ITEMS
    with closing(_get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, query, status, truth_score, summary
            FROM query_history
            ORDER BY id DESC
            LIMIT ?
            """,
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
