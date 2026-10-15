"""
tests/conftest.py — test safety harness and shared fixtures.

Guarantees:
1. Socket-blocking fixture: prevents tests from making unmocked external network calls.
2. Isolated environment fixture: points cache and budget state paths to a per-session temp dir.
3. Fake OpenRouter fixture: allows mocking LLM responses without network calls.
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Socket Blocker Fixture (Blocks all external network egress)
# ---------------------------------------------------------------------------

_ORIGINAL_SOCKET_CONNECT = socket.socket.connect


def _blocked_connect(self, address):
    host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
    port = address[1] if isinstance(address, tuple) and len(address) > 1 else None

    # Allow localhost and loopback interfaces for in-memory or local test servers
    if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        return _ORIGINAL_SOCKET_CONNECT(self, address)

    raise RuntimeError(
        f"Unauthorized external network call blocked during tests! "
        f"Attempted connection to {host}:{port}. "
        "All tests must be fully offline or use mocks."
    )


@pytest.fixture(autouse=True)
def block_external_sockets(request):
    """Autouse fixture that intercepts socket connections and blocks external network calls."""
    if "live" in request.keywords:
        yield
        return

    with patch.object(socket.socket, "connect", _blocked_connect):
        yield


# ---------------------------------------------------------------------------
# 2. Temp-dir Isolation for Budget and Cache Files
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolate_budget_and_cache(tmp_path, monkeypatch):
    """Ensures each test gets clean, isolated state files in a temporary directory."""
    test_budget_path = str(tmp_path / "test_budget_state.json")
    test_cache_path = str(tmp_path / "test_insight_cache.json")

    monkeypatch.setenv("AIVARA_BUDGET_STATE_PATH", test_budget_path)
    monkeypatch.setenv("AIVARA_INSIGHT_CACHE_PATH", test_cache_path)
    monkeypatch.setenv("AIVARA_BUDGET_DB_PATH", test_budget_path)
    monkeypatch.setenv("AIVARA_CACHE_DB_PATH", test_cache_path)

    import config

    monkeypatch.setattr(config, "BUDGET_STATE_PATH", test_budget_path)
    monkeypatch.setattr(config, "INSIGHT_CACHE_PATH", test_cache_path)
    monkeypatch.setattr(config, "BUDGET_DB_PATH", test_budget_path)
    monkeypatch.setattr(config, "CACHE_DB_PATH", test_cache_path)

    yield {
        "budget_path": test_budget_path,
        "cache_path": test_cache_path,
    }


# ---------------------------------------------------------------------------
# 3. Fake OpenRouter LLM Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_openrouter():
    """Provides a mocked OpenRouter API client responding with valid structured JSON."""
    canned_response = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{\n  "headline": "Revenue grew by 24.5% driven by Enterprise segment.",\n'
                        '  "driver_explanation": "North region contributed $45k in new enterprise contracts.",\n'
                        '  "suggested_action": "Expand sales capacity in high-performing regions."\n}'
                    )
                }
            }
        ],
        "usage": {"total_tokens": 85},
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = canned_response
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        yield mock_post
