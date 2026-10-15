"""
tests/test_observability.py — Phase 10 Observability, Config, and Deployment Tests.

Validates:
1. Settings dataclass validation rules (positive bounds, env profiles).
2. Semver __version__ string integrity.
3. Structured JSON logging with active secret redaction.
4. LLM call audit trail (metadata logged, zero raw content logged).
5. Smoke test script check functions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from config import Settings, load_settings
from infra.logger import RedactingJsonFormatter, log_llm_call_audit, redact_secrets
from scripts.smoke_container import check_app_page, check_health

# ---------------------------------------------------------------------------
# 1. Config & Settings Validation
# ---------------------------------------------------------------------------


def test_settings_default_validation_passes():
    """Verify default Settings object passes validation with zero errors."""
    settings = Settings()
    errors = settings.validate()
    assert errors == []


def test_settings_invalid_parameters_rejected():
    """Verify that negative/invalid parameters produce expected error messages."""
    invalid = Settings(
        daily_budget=-5,
        max_upload_mb=0,
        max_columns=-10,
        cache_ttl_days=0,
        cache_max_entries=-1,
        session_budget=0,
        llm_timeout=-2.0,
        env="invalid_environment",
    )
    errors = invalid.validate()
    assert len(errors) == 8
    assert any("AIVARA_DAILY_BUDGET" in e for e in errors)
    assert any("AIVARA_MAX_UPLOAD_MB" in e for e in errors)
    assert any("AIVARA_MAX_COLUMNS" in e for e in errors)
    assert any("AIVARA_CACHE_TTL_DAYS" in e for e in errors)
    assert any("AIVARA_CACHE_MAX_ENTRIES" in e for e in errors)
    assert any("AIVARA_SESSION_BUDGET" in e for e in errors)
    assert any("AIVARA_LLM_TIMEOUT" in e for e in errors)
    assert any("Invalid AIVARA_ENV" in e for e in errors)


def test_load_settings_raises_on_invalid(monkeypatch):
    """Verify load_settings raises ValueError when configuration is invalid."""
    monkeypatch.setenv("AIVARA_DAILY_BUDGET", "-10")
    with pytest.raises(ValueError, match="Invalid configuration: AIVARA_DAILY_BUDGET"):
        load_settings()


def test_semver_version_format():
    """Verify __version__ follows semantic versioning format (X.Y.Z)."""
    assert hasattr(config, "__version__")
    assert re.match(r"^\d+\.\d+\.\d+$", config.__version__)


# ---------------------------------------------------------------------------
# 2. Structured JSON Logging & Secret Redaction
# ---------------------------------------------------------------------------


def test_redact_secrets_active_and_patterns(monkeypatch):
    """Verify redaction of configured keys and generic secret patterns."""
    monkeypatch.setattr("config.OPENROUTER_API_KEY", "sk-or-v1-abcdef1234567890abcdef1234567890")
    monkeypatch.setattr("config.AIVARA_SHARED_SECRET", "super-secret-passphrase-999")

    # Message containing explicit active secrets
    msg1 = (
        "Connecting using sk-or-v1-abcdef1234567890abcdef1234567890 and super-secret-passphrase-999"
    )
    redacted1 = redact_secrets(msg1)
    assert "sk-or-v1-abcdef1234567890abcdef1234567890" not in redacted1
    assert "super-secret-passphrase-999" not in redacted1
    assert "[REDACTED_API_KEY]" in redacted1
    assert "[REDACTED_SECRET]" in redacted1

    # Message containing Bearer token pattern
    msg2 = "Authorization: Bearer my_jwt_token_1234567890123456"
    redacted2 = redact_secrets(msg2)
    assert "my_jwt_token_1234567890123456" not in redacted2
    assert "[REDACTED_SECRET]" in redacted2


def test_redacting_json_formatter_structure():
    """Verify log record is properly converted to valid JSON with required metadata."""
    formatter = RedactingJsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Normal diagnostic message for user session",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "abc-123"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logger"
    assert parsed["message"] == "Normal diagnostic message for user session"
    assert parsed["correlation_id"] == "abc-123"
    assert "timestamp" in parsed


# ---------------------------------------------------------------------------
# 3. LLM Audit Trail Logging
# ---------------------------------------------------------------------------


def test_log_llm_call_audit_records_metadata(monkeypatch):
    """Verify log_llm_call_audit emits structured audit data without prompt content."""
    logged_records = []

    class MockHandler(logging.Handler):
        def emit(self, record):
            logged_records.append(record)

    audit_log = logging.getLogger("aivara.audit.llm")
    audit_log.setLevel(logging.INFO)
    handler = MockHandler()
    audit_log.addHandler(handler)

    try:
        log_llm_call_audit(
            model="meta-llama/llama-3.1-8b-instruct:free",
            prompt_tokens=420,
            completion_tokens=85,
            calls_remaining_today=15,
            correlation_id="corr-999",
        )

        assert len(logged_records) == 1
        rec = logged_records[0]
        assert hasattr(rec, "audit_event")
        audit = rec.audit_event
        assert audit["event"] == "llm_completion"
        assert audit["model"] == "meta-llama/llama-3.1-8b-instruct:free"
        assert audit["prompt_tokens"] == 420
        assert audit["completion_tokens"] == 85
        assert audit["total_tokens"] == 505
        assert audit["calls_remaining_today"] == 15
        assert rec.correlation_id == "corr-999"

        # Verify formatted output contains no secret and is valid JSON
        formatter = RedactingJsonFormatter()
        json_out = json.loads(formatter.format(rec))
        assert "audit" in json_out
        assert json_out["audit"]["prompt_tokens"] == 420
    finally:
        audit_log.removeHandler(handler)


# ---------------------------------------------------------------------------
# 4. Smoke Verification Script Unit Tests
# ---------------------------------------------------------------------------


def test_smoke_check_health_success(monkeypatch):
    """Verify check_health returns True when endpoint returns 200 'ok'."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"ok\n"
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
    assert check_health("http://localhost:8501") is True


def test_smoke_check_health_failure(monkeypatch):
    """Verify check_health returns False when endpoint returns unexpected response or error."""
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.read.return_value = b"Internal Server Error"
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
    assert check_health("http://localhost:8501") is False


def test_smoke_check_app_page_success(monkeypatch):
    """Verify check_app_page returns True on HTTP 200."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: mock_resp)
    assert check_app_page("http://localhost:8501") is True
