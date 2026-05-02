import sqlite3
from datetime import datetime
import os
import logging
from contextlib import closing
from typing import Literal, Optional
from pydantic import BaseModel, field_validator

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "feedback_loop.sqlite")


from pydantic import BaseModel, Field, field_validator

class UserFeedback(BaseModel):
    query: str = Field(..., max_length=1000)
    original_truth_score: float = 0.0
    user_flag: Literal["correct", "incorrect", "bias_disagreement"]
    user_corrected_score: Optional[float] = None
    comments: str = Field("", max_length=5000)

    @field_validator("original_truth_score", "user_corrected_score", mode="before")
    @classmethod
    def normalize_scores(cls, value: Optional[float]) -> Optional[float]:
        if value is None or value == "":
            return 0.0
        numeric_value = float(value)
        if 1.0 < numeric_value <= 100.0:
            numeric_value = numeric_value / 100.0
        return max(0.0, min(numeric_value, 1.0))


def _get_connection(retries: int = 5, delay: float = 0.5) -> sqlite3.Connection:
    for i in range(retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except sqlite3.OperationalError as e:
            if i == retries - 1:
                raise
            logging.getLogger(__name__).warning(f"SQLite connection attempt {i+1} failed: {e}. Retrying...")
            import time
            time.sleep(delay * (2 ** i))
    return sqlite3.connect(DB_PATH)


def init_feedback_database():
    try:
        with closing(_get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback_loop (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    query TEXT,
                    original_truth_score REAL,
                    user_flag TEXT,
                    user_corrected_score REAL,
                    comments TEXT,
                    pipeline_status TEXT,
                    owner_email TEXT NOT NULL DEFAULT 'public'
                )
            """)
            conn.commit()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to init feedback DB: {e}")


def process_and_log_feedback(
    feedback: UserFeedback, owner_email: str = "public"
) -> dict:
    try:
        ts = datetime.now().isoformat()
        with closing(_get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO feedback_loop 
                (timestamp, query, original_truth_score, user_flag, user_corrected_score, comments, owner_email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    ts,
                    feedback.query,
                    feedback.original_truth_score,
                    feedback.user_flag,
                    feedback.user_corrected_score,
                    feedback.comments,
                    owner_email,
                ),
            )
            conn.commit()
            return {"status": "success", "id": cursor.lastrowid}
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to log feedback: {e}")
        return {"status": "error", "message": str(e)}
