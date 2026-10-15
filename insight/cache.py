"""
insight/cache.py — facts-hash -> LLM response cache.

Keys the LLM response by a hash of the facts packet JSON (+ model name +
prompt version), so re-uploading the same data or re-viewing a tab never
triggers a duplicate call.

Features (Phase 6 / Audit §6):
- Multi-process safe SQLite storage with Write-Ahead Logging (WAL) and busy timeouts.
- Automatic TTL expiration and LRU capacity pruning (AIVARA_CACHE_TTL_DAYS, AIVARA_CACHE_MAX_ENTRIES).
- Zero-persistence mode via AIVARA_CACHE_ENABLED=false.
- Automatic database corruption recovery (never crashes on corrupted disk cache).
- View-level exports remain strictly scoped to in-memory session state (never written to disk).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time

import config

_lock = threading.Lock()


def _hash_key(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _get_sqlite_connection(path: str) -> sqlite3.Connection:
    """Returns a configured SQLite connection with WAL mode and busy timeout.
    Recovers automatically if the database file is corrupted."""
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    def _try_open(db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS insight_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_insight_accessed ON insight_cache(accessed_at)"
            )
            return conn
        except Exception:
            conn.close()
            raise

    try:
        return _try_open(path)
    except (sqlite3.DatabaseError, OSError):
        # Database corrupted: remove and reinitialize fresh store
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return _try_open(path)


def get(cache_key_material: str, path: str | None = None) -> dict | None:
    """Returns the cached insight dict (headline/driver/action/raw_text) or
    None if not cached or expired."""
    if not config.AIVARA_CACHE_ENABLED:
        return None

    if path is None:
        path = config.CACHE_DB_PATH

    key = _hash_key(cache_key_material)
    now = time.time()
    ttl_seconds = config.AIVARA_CACHE_TTL_DAYS * 86400

    with _lock:
        try:
            if not os.path.exists(path):
                return None
            conn = _get_sqlite_connection(path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT payload, created_at FROM insight_cache WHERE cache_key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                payload_str, created_at = row
                # Check TTL expiration
                if (now - created_at) > ttl_seconds:
                    cursor.execute("DELETE FROM insight_cache WHERE cache_key = ?", (key,))
                    return None

                # Update accessed_at for LRU
                cursor.execute(
                    "UPDATE insight_cache SET accessed_at = ? WHERE cache_key = ?",
                    (now, key),
                )
                return json.loads(payload_str)
            finally:
                conn.close()
        except Exception:
            return None


def set(cache_key_material: str, value: dict, path: str | None = None) -> None:
    """Stores a validated insight payload in the multi-process persistent cache."""
    if not config.AIVARA_CACHE_ENABLED:
        return

    if path is None:
        path = config.CACHE_DB_PATH

    key = _hash_key(cache_key_material)
    now = time.time()
    ttl_seconds = config.AIVARA_CACHE_TTL_DAYS * 86400
    max_entries = config.AIVARA_CACHE_MAX_ENTRIES
    payload_str = json.dumps(value)

    with _lock:
        try:
            conn = _get_sqlite_connection(path)
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    """
                    INSERT INTO insight_cache (cache_key, payload, created_at, accessed_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        payload = excluded.payload,
                        accessed_at = excluded.accessed_at
                    """,
                    (key, payload_str, now, now),
                )

                # Prune expired entries
                cursor.execute(
                    "DELETE FROM insight_cache WHERE created_at < ?",
                    (now - ttl_seconds,),
                )

                # Prune LRU entries if count exceeds max_entries
                cursor.execute("SELECT count(*) FROM insight_cache")
                count_row = cursor.fetchone()
                current_count = count_row[0] if count_row else 0
                if current_count > max_entries:
                    excess = current_count - max_entries
                    cursor.execute(
                        """
                        DELETE FROM insight_cache WHERE cache_key IN (
                            SELECT cache_key FROM insight_cache ORDER BY accessed_at ASC LIMIT ?
                        )
                        """,
                        (excess,),
                    )

                cursor.execute("COMMIT")
            except Exception:
                try:
                    conn.execute("ROLLBACK")
                except Exception:
                    pass
                raise
            finally:
                conn.close()
        except Exception:
            pass


def clear_disk_cache(path: str | None = None) -> None:
    """Removes the persistent disk cache file and associated SQLite WAL/SHM files."""
    if path is None:
        path = config.CACHE_DB_PATH

    with _lock:
        for suffix in ("", "-wal", "-shm"):
            target = f"{path}{suffix}"
            if os.path.exists(target):
                try:
                    os.remove(target)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# In-Memory Session-Scoped View Cache (Never persisted to shared disk)
# ---------------------------------------------------------------------------

_view_cache: dict[str, dict] = {}


def _get_effective_session_id(session_id: str | None = None) -> str:
    if session_id:
        return session_id
    try:
        import streamlit as st

        if hasattr(st, "session_state"):
            if "_session_id" not in st.session_state:
                import uuid

                st.session_state["_session_id"] = str(uuid.uuid4())
            return st.session_state["_session_id"]
    except Exception:
        pass
    return f"thread_{threading.get_ident()}"


def get_for_view(view_name: str, session_id: str | None = None) -> dict | None:
    """Convenience lookup used by export/pptx_builder.py. Scoped to session state
    or session-keyed in-memory cache to prevent cross-user data leakage across sessions.
    Never persisted to the shared disk cache."""
    if session_id:
        with _lock:
            return _view_cache.get(f"{session_id}::{view_name}")

    try:
        import streamlit as st

        if hasattr(st, "session_state") and "_view_insights" in st.session_state:
            val = st.session_state["_view_insights"].get(view_name)
            if val is not None:
                return val
    except Exception:
        pass

    eff_id = _get_effective_session_id(None)
    with _lock:
        return _view_cache.get(f"{eff_id}::{view_name}")


def set_for_view(view_name: str, value: dict, session_id: str | None = None) -> None:
    if session_id:
        with _lock:
            _view_cache[f"{session_id}::{view_name}"] = value
        return

    try:
        import streamlit as st

        if hasattr(st, "session_state"):
            st.session_state.setdefault("_view_insights", {})[view_name] = value
    except Exception:
        pass

    eff_id = _get_effective_session_id(None)
    with _lock:
        _view_cache[f"{eff_id}::{view_name}"] = value


def clear_view_cache(session_id: str | None = None) -> None:
    """Clear in-memory view cache for the given session or caller."""
    if session_id is None:
        try:
            import streamlit as st

            if hasattr(st, "session_state") and "_view_insights" in st.session_state:
                st.session_state["_view_insights"].clear()
        except Exception:
            pass

    eff_id = session_id if session_id else _get_effective_session_id()
    with _lock:
        keys_to_del = [k for k in _view_cache if k.startswith(f"{eff_id}::")]
        for k in keys_to_del:
            del _view_cache[k]
