"""
infra/logger.py — Structured JSON logging and LLM call audit trail (Phase 10).

Features:
- Structured JSON output format for log aggregators (Elasticsearch, Datadog, CloudWatch).
- Active secret redaction: intercepts OpenRouter API keys, bearer tokens, and shared secrets.
- Dedicated LLM audit logger (aivara.audit.llm) tracking timestamps, models, token counts,
  and budget balance without logging any prompt, facts, or business data content.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import config

# Patterns to sanitize from all log messages
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{16,}", re.I),
    re.compile(
        r"(api[_-]?key|secret|password|token)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?", re.I
    ),
]


def redact_secrets(message: str) -> str:
    """Sanitize secrets, API keys, and bearer tokens from a log string."""
    if not message:
        return message

    redacted = message
    # 1. Redact known active secrets if configured
    if config.OPENROUTER_API_KEY and len(config.OPENROUTER_API_KEY) > 6:
        redacted = redacted.replace(config.OPENROUTER_API_KEY, "[REDACTED_API_KEY]")
    if config.AIVARA_SHARED_SECRET and len(config.AIVARA_SHARED_SECRET) > 6:
        redacted = redacted.replace(config.AIVARA_SHARED_SECRET, "[REDACTED_SECRET]")

    # 2. Redact regex patterns
    for pat in _SECRET_PATTERNS:
        redacted = pat.sub(lambda m: "[REDACTED_SECRET]", redacted)

    return redacted


class RedactingJsonFormatter(logging.Formatter):
    """JSON formatter that redacts secrets and provides structured metadata."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the base message
        raw_message = record.getMessage()
        safe_message = redact_secrets(raw_message)

        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_message,
        }

        # Include correlation ID if present on record
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_data["correlation_id"] = str(record.correlation_id)

        # Include extra payload data if passed in record.__dict__
        if hasattr(record, "audit_event") and record.audit_event:
            log_data["audit"] = record.audit_event

        if record.exc_info:
            log_data["exception"] = redact_secrets(self.formatException(record.exc_info))

        return json.dumps(log_data)


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
    logger_name: str = "aivara",
) -> logging.Logger:
    """Configure root / package logger with structured redacting formatter."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers on re-configuration
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        if json_format:
            handler.setFormatter(RedactingJsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s in %(name)s: %(message)s")
            )
        logger.addHandler(handler)

    return logger


# Audit logger specifically for tracking LLM token consumption and call counts
audit_logger = logging.getLogger("aivara.audit.llm")


def log_llm_call_audit(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    calls_remaining_today: int,
    correlation_id: str | None = None,
) -> None:
    """Audit log an LLM call with metadata.

    Guarantees that ZERO prompt text, facts packets, or completion contents are logged.
    """
    audit_data = {
        "event": "llm_completion",
        "model": model,
        "prompt_tokens": max(0, prompt_tokens),
        "completion_tokens": max(0, completion_tokens),
        "total_tokens": max(0, prompt_tokens) + max(0, completion_tokens),
        "calls_remaining_today": calls_remaining_today,
    }
    msg = f"LLM Call: model={model} prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} remaining={calls_remaining_today}"
    audit_logger.info(
        msg,
        extra={
            "audit_event": audit_data,
            "correlation_id": correlation_id,
        },
    )
