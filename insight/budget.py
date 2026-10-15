"""
insight/budget.py — token estimation, call counting, budget enforcement.

Hard ceiling enforced in code, not just documented: tracks calls made in the
current UTC day, persisted to a multi-process safe SQLite WAL store so it survives
app restarts and prevents concurrent over-budget races across workers and processes (Audit 4.3).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

import config
from config import MAX_SESSION_LLM_CALLS

_lock = threading.Lock()
_session_calls: dict[str, int] = {}

try:
    import tiktoken

    _encoding = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken optional / model mismatch
    tiktoken = None
    _encoding = None


@dataclass
class BudgetStatus:
    calls_made_today: int
    daily_budget: int
    remaining: int
    exhausted: bool


def can_make_session_call(session_id: str = "default", limit: int = MAX_SESSION_LLM_CALLS) -> bool:
    """Checks if the given session has calls remaining under the session budget limit."""
    with _lock:
        return _session_calls.get(session_id, 0) < limit


def record_session_call(session_id: str = "default") -> int:
    """Increments and returns the session call count."""
    with _lock:
        _session_calls[session_id] = _session_calls.get(session_id, 0) + 1
        return _session_calls[session_id]


def reset_session_budget(session_id: str = "default") -> None:
    """Resets the call counter for a specific session."""
    with _lock:
        _session_calls.pop(session_id, None)


def estimate_tokens(text: str) -> int:
    """Approximate token count. OpenRouter models vary in tokenizer, so this
    is treated as an estimate only, per Section 9's token counting note."""
    if _encoding is not None:
        try:
            return len(_encoding.encode(text))
        except Exception:  # pragma: no cover - defensive
            pass
    # Rough fallback: ~4 characters per token for English-like text.
    return max(1, len(text) // 4)


def _today_key() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _get_sqlite_connection(path: str) -> sqlite3.Connection:
    """Returns a configured SQLite connection with WAL mode and busy timeout.
    Recovers from database corruption by recreating a clean store."""
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    def _try_open(db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS daily_budget (day TEXT PRIMARY KEY, calls_made INTEGER NOT NULL)"
            )
            return conn
        except Exception:
            conn.close()
            raise

    try:
        return _try_open(path)
    except (sqlite3.DatabaseError, OSError):
        # Database corrupted or non-SQLite: remove and recreate fresh store
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return _try_open(path)


def check_and_increment_daily(
    path: str | None = None, limit: int | None = None
) -> tuple[bool, int, int]:
    """Atomically checks if calls_made < limit and increments calls_made if permitted.
    Eliminates TOCTOU races in multi-process/multi-thread deployments.

    Returns:
        (allowed: bool, calls_made_today: int, remaining: int)
    """
    if path is None:
        path = config.BUDGET_DB_PATH
    if limit is None:
        limit = config.DAILY_CALL_BUDGET
    today = _today_key()

    with _lock:
        conn = _get_sqlite_connection(path)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("SELECT calls_made FROM daily_budget WHERE day = ?", (today,))
            row = cursor.fetchone()
            current_calls = row[0] if row else 0

            if current_calls >= limit:
                cursor.execute("COMMIT")
                return False, current_calls, 0

            new_calls = current_calls + 1
            cursor.execute(
                "INSERT INTO daily_budget (day, calls_made) VALUES (?, ?) "
                "ON CONFLICT(day) DO UPDATE SET calls_made = ?",
                (today, new_calls, new_calls),
            )
            # Prune previous dates to keep database tiny
            cursor.execute("DELETE FROM daily_budget WHERE day != ?", (today,))
            cursor.execute("COMMIT")
            remaining = max(0, limit - new_calls)
            return True, new_calls, remaining
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()


def get_status(path: str | None = None, daily_budget: int | None = None) -> BudgetStatus:
    """Reads current daily budget status safely from SQLite."""
    if path is None:
        path = config.BUDGET_DB_PATH
    if daily_budget is None:
        daily_budget = config.DAILY_CALL_BUDGET
    today = _today_key()

    if not os.path.exists(path):
        return BudgetStatus(
            calls_made_today=0,
            daily_budget=daily_budget,
            remaining=daily_budget,
            exhausted=daily_budget <= 0,
        )

    with _lock:
        conn = _get_sqlite_connection(path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT calls_made FROM daily_budget WHERE day = ?", (today,))
            row = cursor.fetchone()
            calls_today = row[0] if row else 0
            remaining = max(0, daily_budget - calls_today)
            return BudgetStatus(
                calls_made_today=calls_today,
                daily_budget=daily_budget,
                remaining=remaining,
                exhausted=remaining <= 0,
            )
        finally:
            conn.close()


def can_make_call(path: str | None = None, daily_budget: int | None = None) -> bool:
    """Checks whether at least one call remains under the daily budget ceiling."""
    return not get_status(path, daily_budget).exhausted


def record_call(path: str | None = None) -> BudgetStatus:
    """Increments the call counter atomically and returns updated BudgetStatus."""
    if path is None:
        path = config.BUDGET_DB_PATH
    allowed, calls_today, remaining = check_and_increment_daily(path)
    daily_budget = config.DAILY_CALL_BUDGET
    return BudgetStatus(
        calls_made_today=calls_today,
        daily_budget=daily_budget,
        remaining=remaining,
        exhausted=remaining <= 0,
    )
