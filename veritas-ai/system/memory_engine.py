"""
Friday System — Context & Memory Engine (Phase 40)
====================================================
Persistent memory layer that stores:
  - Previous commands and their outcomes
  - User preferences (voice, volume, default apps)
  - Frequent workflows for prediction
  - Session context for multi-turn conversations

Uses SQLite for durability across restarts.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, List
from collections import Counter

logger = logging.getLogger("friday.memory")

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "friday_memory.sqlite")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db():
    """Create tables on first run."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            action TEXT,
            kwargs TEXT,
            status TEXT,
            speech_response TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Friday memory database initialized.")


# Initialize on import
init_memory_db()


# ---------------------------------------------------------------------------
# Command History
# ---------------------------------------------------------------------------

def log_command(raw_text: str, action: Optional[str], kwargs: dict,
                status: str, speech_response: str):
    """Log a processed command to history."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO command_history (timestamp, raw_text, action, kwargs, status, speech_response) VALUES (?,?,?,?,?,?)",
        (
            datetime.utcnow().isoformat() + "Z",
            raw_text,
            action or "",
            json.dumps(kwargs),
            status,
            speech_response,
        ),
    )
    conn.commit()
    conn.close()


def get_recent_commands(limit: int = 20) -> List[dict]:
    """Retrieve the most recent commands."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM command_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_most_frequent_actions(top_n: int = 5) -> List[tuple]:
    """Return the most commonly executed action types."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT action FROM command_history WHERE action != ''"
    ).fetchall()
    conn.close()

    actions = [row["action"] for row in rows]
    return Counter(actions).most_common(top_n)


def predict_next_action() -> Optional[str]:
    """
    Simple prediction: if the user frequently follows action A with action B,
    suggest B after A is completed.
    """
    conn = _get_connection()
    rows = conn.execute(
        "SELECT action FROM command_history WHERE action != '' ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    # Build bigram frequencies
    actions = [row["action"] for row in reversed(rows)]
    bigrams = Counter()
    for i in range(len(actions) - 1):
        bigrams[(actions[i], actions[i + 1])] += 1

    last_action = actions[-1]
    candidates = [(pair, count) for pair, count in bigrams.items() if pair[0] == last_action]

    if candidates:
        best = max(candidates, key=lambda x: x[1])
        if best[1] >= 2:  # Only predict if pattern seen at least twice
            return best[0][1]

    return None


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------

def set_preference(key: str, value: str):
    """Set or update a user preference."""
    conn = _get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?,?,?)",
        (key, value, datetime.utcnow().isoformat() + "Z"),
    )
    conn.commit()
    conn.close()
    logger.info(f"Preference set: {key} = {value}")


def get_preference(key: str, default: str = "") -> str:
    """Get a user preference."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT value FROM user_preferences WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row else default


def get_all_preferences() -> dict:
    """Get all preferences as a dict."""
    conn = _get_connection()
    rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# ---------------------------------------------------------------------------
# Session Context (multi-turn conversation memory)
# ---------------------------------------------------------------------------

class SessionContext:
    """Tracks conversation turns within a single activation session."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.utcnow().strftime("session_%Y%m%d_%H%M%S")
        self._turns: List[dict] = []

    def add_turn(self, role: str, content: str):
        """Add a conversation turn (role: 'user' or 'assistant')."""
        turn = {"role": role, "content": content}
        self._turns.append(turn)

        # Persist
        conn = _get_connection()
        conn.execute(
            "INSERT INTO session_context (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (self.session_id, role, content, datetime.utcnow().isoformat() + "Z"),
        )
        conn.commit()
        conn.close()

    def get_context_window(self, max_turns: int = 10) -> List[dict]:
        """Return the last N turns for context injection."""
        return self._turns[-max_turns:]

    def clear(self):
        self._turns = []
