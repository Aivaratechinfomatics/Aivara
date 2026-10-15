"""
tests/test_safety_harness.py — verifies the test harness safeguards work.
"""

import socket

import pytest


def test_socket_blocking_prevents_external_connection():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="Unauthorized external network call blocked"):
            s.connect(("8.8.8.8", 53))
    finally:
        s.close()


def test_budget_and_cache_isolated_in_temp_dir():
    import os

    import config

    assert "test_budget_state.json" in config.BUDGET_STATE_PATH
    assert "test_insight_cache.json" in config.INSIGHT_CACHE_PATH
    assert os.path.exists(os.path.dirname(config.BUDGET_STATE_PATH))
