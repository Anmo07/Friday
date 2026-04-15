import sqlite3
from datetime import datetime
import os
import logging
from contextlib import closing
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

# Ensure absolute SQLite storage mapping structurally resolving Docker volumes properly natively
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "feedback_loop.sqlite")

class UserFeedback(BaseModel):
    query: str
    original_truth_score: float
    user_flag: Literal["correct", "incorrect", "bias_disagreement"]
    user_corrected_score: Optional[float] = None
    comments: str = ""

    @field_validator("original_truth_score", "user_corrected_score", mode="before")
    @classmethod
    def normalize_scores(cls, value: Optional[float]) -> Optional[float]:
        if value is None or value == "":
            return None
        numeric_value = float(value)
        if 1.0 < numeric_value <= 100.0:
            numeric_value = numeric_value / 100.0
        return max(0.0, min(numeric_value, 1.0))


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_feedback_database():
    """ Structurally scaffolds the localized proprietary dataset tables intelligently mapping limits natively """
    try:
        with closing(_get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback_loop (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    query TEXT,
                    original_truth_score REAL,
                    user_flag TEXT,
                    user_corrected_score REAL,
                    comments TEXT,
                    pipeline_status TEXT
                )
            ''')
            conn.commit()
        logging.info("Feedback SQLite Array intrinsically provisioned safely.")
    except Exception as e:
        logging.error(f"Failed propagating local SQL Database bounds organically: {e}")

init_feedback_database()

def process_and_log_feedback(feedback: UserFeedback):
    """
    Ingests explicit user disagreement signals.
    Passively flags them as PENDING_VALIDATION for the Model Improvement cycles (Phase 30).
    """
    try:
        with closing(_get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback_loop 
                (timestamp, query, original_truth_score, user_flag, user_corrected_score, comments, pipeline_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat() + "Z",
                feedback.query.strip(),
                feedback.original_truth_score,
                feedback.user_flag,
                feedback.user_corrected_score,
                feedback.comments.strip(),
                "PENDING_VALIDATION"
            ))
            conn.commit()
        return {"status": "success", "tracking_stage": "PENDING_VALIDATION"}
    except Exception as e:
        return {"status": "error", "message": f"Database ingestion crash intelligently avoided: {e}"}
