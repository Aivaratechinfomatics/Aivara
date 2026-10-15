"""
ui/error_boundary.py — Component error boundary for tab rendering.

Ensures that an unhandled exception in one tab renders a clean degradation notice
with a correlation ID, keeping all other tabs interactive and functional.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


def render_tab_boundary(
    tab_name: str,
    render_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Wraps a tab rendering callable with an error boundary."""
    try:
        render_fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - top-level boundary for UI stability
        correlation_id = uuid.uuid4().hex[:8]
        logger.error(
            "Unhandled exception in tab '%s' [correlation_id=%s]: %s",
            tab_name,
            correlation_id,
            exc,
            exc_info=True,
        )
        st.error(
            f"⚠️ **Unable to render {tab_name}** (Correlation ID: `{correlation_id}`). "
            "Other tabs remain interactive and functional."
        )
        with st.expander("Diagnostic Information", expanded=False):
            st.caption(f"Error: `{exc.__class__.__name__}: {exc}`")
            st.caption(
                "If this problem persists, share the correlation ID above with your system administrator."
            )
