"""
insight/budget.py — token estimation, call counting, budget enforcement.

Hard ceiling enforced in code, not just documented: tracks calls made in the
current UTC day, persisted to a small local file so it survives app
restarts, and refuses to call the LLM past the configured ceiling.
"""

from __future__ import annotations

import json
import os
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


def _read_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(path: str, state: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp_path, path)


def get_status(path: str | None = None, daily_budget: int | None = None) -> BudgetStatus:
    if path is None:
        path = config.BUDGET_STATE_PATH
    if daily_budget is None:
        daily_budget = config.DAILY_CALL_BUDGET
    with _lock:
        state = _read_state(path)
        today = _today_key()
        calls_today = int(state.get(today, 0))
        remaining = max(0, daily_budget - calls_today)
        return BudgetStatus(
            calls_made_today=calls_today,
            daily_budget=daily_budget,
            remaining=remaining,
            exhausted=remaining <= 0,
        )


def can_make_call(path: str | None = None, daily_budget: int | None = None) -> bool:
    return not get_status(path, daily_budget).exhausted


def record_call(path: str | None = None) -> BudgetStatus:
    """Increment today's call counter and persist it. Call this only after a
    call actually succeeds (or is attempted) — never speculatively."""
    if path is None:
        path = config.BUDGET_STATE_PATH
    with _lock:
        state = _read_state(path)
        today = _today_key()
        state[today] = int(state.get(today, 0)) + 1
        # Keep the state file small: drop any days other than today.
        state = {today: state[today]}
        _write_state(path, state)
        daily_budget = config.DAILY_CALL_BUDGET
        calls_today = state[today]
        remaining = max(0, daily_budget - calls_today)
        return BudgetStatus(
            calls_made_today=calls_today,
            daily_budget=daily_budget,
            remaining=remaining,
            exhausted=remaining <= 0,
        )
