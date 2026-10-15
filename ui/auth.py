"""
ui/auth.py — Authentication and access control gate (Decision D2).

Implements reverse-proxy header authentication (X-Forwarded-User, X-Remote-User)
and app-level shared-secret fallback (AIVARA_SHARED_SECRET).
Fails closed when AIVARA_AUTH_REQUIRED=true and credentials are missing or invalid.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

import streamlit as st

import config


@dataclass(frozen=True)
class AuthContext:
    authenticated: bool
    username: str
    auth_method: (
        str  # "proxy_header" | "shared_secret" | "session" | "dev_bypass" | "unauthenticated"
    )
    error: str | None = None


def _get_request_headers() -> dict[str, str]:
    """Retrieve HTTP request headers from Streamlit context if available."""
    try:
        ctx = getattr(st, "context", None)
        if ctx is not None and hasattr(ctx, "headers"):
            return {k.lower(): str(v) for k, v in ctx.headers.items()}
    except Exception:
        pass
    return {}


def _get_query_param(name: str) -> str | None:
    """Retrieve query parameter value safely across Streamlit versions."""
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get(name)
            if isinstance(val, list) and val:
                return str(val[0])
            if val is not None:
                return str(val)
    except Exception:
        pass
    return None


def verify_shared_secret(provided: str, secret: str) -> bool:
    """Constant-time string comparison preventing timing attacks."""
    if not provided or not secret:
        return False
    return hmac.compare_digest(provided.strip(), secret.strip())


def authenticate_request(
    headers: dict[str, str] | None = None,
    query_token: str | None = None,
    session_auth: bool | None = None,
    auth_required: bool | None = None,
    header_name: str | None = None,
    shared_secret: str | None = None,
) -> AuthContext:
    """Pure-logic resolver for authentication state. Testable without Streamlit UI."""
    is_required = auth_required if auth_required is not None else config.AIVARA_AUTH_REQUIRED
    req_header = (
        header_name if header_name is not None else config.AIVARA_AUTH_HEADER_USER
    ).lower()
    secret = shared_secret if shared_secret is not None else config.AIVARA_SHARED_SECRET

    if not is_required:
        return AuthContext(
            authenticated=True,
            username="local-dev",
            auth_method="dev_bypass",
        )

    # 1. Check existing session authorization
    if session_auth is True:
        return AuthContext(
            authenticated=True,
            username="authenticated-user",
            auth_method="session",
        )

    # 2. Check reverse-proxy header
    hdrs = headers or {}
    # Check configured header first, then standard fallbacks
    for cand in [req_header, "x-forwarded-user", "x-remote-user", "x-forwarded-email"]:
        user_val = hdrs.get(cand)
        if user_val and user_val.strip():
            return AuthContext(
                authenticated=True,
                username=user_val.strip(),
                auth_method="proxy_header",
            )

    # 3. Check shared-secret token (e.g. from query parameter or form)
    if secret and query_token and verify_shared_secret(query_token, secret):
        return AuthContext(
            authenticated=True,
            username="shared-secret-user",
            auth_method="shared_secret",
        )

    # Fail closed
    return AuthContext(
        authenticated=False,
        username="anonymous",
        auth_method="unauthenticated",
        error="Authentication required. Please log in via reverse proxy or enter the shared access secret.",
    )


def enforce_authentication() -> AuthContext:
    """Enforces authentication inside the Streamlit runtime.

    If authentication fails, displays an access gate and halts execution via st.stop().
    """
    if not config.AIVARA_AUTH_REQUIRED:
        return AuthContext(
            authenticated=True,
            username="local-dev",
            auth_method="dev_bypass",
        )

    # Check session state
    is_session_authed = st.session_state.get("_aivara_auth_ok", False)
    session_user = st.session_state.get("_aivara_auth_user", "authenticated-user")
    if is_session_authed:
        return AuthContext(
            authenticated=True,
            username=session_user,
            auth_method="session",
        )

    # Extract headers and query params
    headers = _get_request_headers()
    token_param = _get_query_param("auth") or _get_query_param("token")

    auth_ctx = authenticate_request(
        headers=headers,
        query_token=token_param,
        session_auth=False,
    )

    if auth_ctx.authenticated:
        st.session_state["_aivara_auth_ok"] = True
        st.session_state["_aivara_auth_user"] = auth_ctx.username
        return auth_ctx

    # Fail closed: render login gate and halt
    st.title("🔒 Authentication Required")
    st.info(
        "Aivara Insight Lite is running in protected mode. "
        "Access requires authentication via a corporate reverse proxy or a valid shared secret."
    )

    if config.AIVARA_SHARED_SECRET:
        with st.form("aivara_auth_form"):
            secret_input = st.text_input(
                "Access Secret / Passphrase",
                type="password",
                help="Enter the configured AIVARA_SHARED_SECRET.",
            )
            submit = st.form_submit_button("Sign In")
            if submit:
                if verify_shared_secret(secret_input, config.AIVARA_SHARED_SECRET):
                    st.session_state["_aivara_auth_ok"] = True
                    st.session_state["_aivara_auth_user"] = "shared-secret-user"
                    st.success("Authenticated successfully. Reloading...")
                    st.rerun()
                else:
                    st.error("Invalid access secret. Access denied.")

    st.caption("Contact your system administrator if you do not have access credentials.")
    st.stop()
    return auth_ctx  # pragma: no cover
