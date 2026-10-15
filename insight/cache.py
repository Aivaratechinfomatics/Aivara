"""
insight/cache.py — facts-hash -> LLM response cache.

Keys the LLM response by a hash of the facts packet JSON (+ model name +
prompt version), so re-uploading the same data or re-viewing a tab never
triggers a duplicate call. This is also the module export/pptx_builder.py
reads from directly — it must never import insight/client.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading

import config

_lock = threading.Lock()


def _hash_key(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _read_cache(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache(path: str, cache: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    os.replace(tmp_path, path)


def get(cache_key_material: str, path: str | None = None) -> dict | None:
    """Returns the cached insight dict (headline/driver/action/raw_text) or
    None if not cached."""
    if path is None:
        path = config.INSIGHT_CACHE_PATH
    key = _hash_key(cache_key_material)
    with _lock:
        cache = _read_cache(path)
        return cache.get(key)


def set(cache_key_material: str, value: dict, path: str | None = None) -> None:
    if path is None:
        path = config.INSIGHT_CACHE_PATH
    key = _hash_key(cache_key_material)
    with _lock:
        cache = _read_cache(path)
        cache[key] = value
        _write_cache(path, cache)


def clear_disk_cache(path: str | None = None) -> None:
    """Removes the persistent disk cache file."""
    if path is None:
        path = config.INSIGHT_CACHE_PATH
    with _lock:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


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
