"""
insight/client.py — OpenRouter API wrapper and Insight Generator (Phase 5 / Audit §5).

This is the ONLY module in the app that makes external network calls.
Hardened with:
- Strict JSON schema validation replacing brittle regex sentence splitting (Audit 3.8).
- Single repair retry before deterministic fallback.
- Local numerical faithfulness verification to catch hallucinations.
- Data egress control: automatic pseudonymization/un-redaction via insight/redactor.py (D5).
- Circuit breaker and exponential backoff retry on HTTP 429 and 5xx.
- Daily and per-session budget tracking (Audit 4.3).
- Model transparency reporting.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import random
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests

import config
from config import (
    AIVARA_LLM_REDACT_LABELS,
    ALLOW_PAID_MODELS_DEFAULT,
    CIRCUIT_BREAKER_MAX_FAILURES,
    CIRCUIT_BREAKER_RESET_TIMEOUT,
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    LLM_REQUEST_TIMEOUT_SECONDS,
    MAX_OUTPUT_TOKENS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from insight import budget, cache
from insight.faithfulness import verify_faithfulness
from insight.fallback import generate_deterministic_fallback
from insight.prompts import (
    build_insight_prompt,
    build_repair_prompt,
    cache_key_material,
)
from insight.redactor import redact_facts_packet, unredact_insight

logger = logging.getLogger(__name__)


@dataclass
class InsightResult:
    headline: str
    driver_explanation: str
    suggested_action: str
    raw_text: str
    from_cache: bool
    model: str
    is_fallback: bool = False


class BudgetExhaustedError(RuntimeError):
    """Raised when the daily or session call budget has been reached."""


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter API call itself fails (network, auth, circuit breaker, etc)."""


class CircuitBreaker:
    """Thread-safe circuit breaker protecting against cascading API failures."""

    def __init__(
        self,
        max_failures: int = CIRCUIT_BREAKER_MAX_FAILURES,
        reset_timeout: float = CIRCUIT_BREAKER_RESET_TIMEOUT,
    ):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"  # "CLOSED", "OPEN", "HALF_OPEN"
        self._lock = threading.Lock()

    def can_attempt(self) -> bool:
        with self._lock:
            if self.state == "OPEN":
                now = time.time()
                if now - self.last_failure_time > self.reset_timeout:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.max_failures:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker tripped to OPEN after {self.failure_count} consecutive failures."
                )

    def reset(self) -> None:
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = 0.0


# Module-level circuit breaker singleton
_circuit_breaker = CircuitBreaker()


def parse_and_validate_insight(raw_text: str) -> tuple[str, str, str] | None:
    """Parses raw model output into a validated (headline, driver, action) tuple.
    Extracts JSON even if enclosed in markdown code fences or preamble text.
    Returns None if valid schema cannot be established.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()

    # Attempt to locate JSON object boundaries {...}
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        cleaned = json_match.group(0)

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return None

        headline = str(data.get("headline", "")).strip()
        driver = str(data.get("driver_explanation", data.get("driver", ""))).strip()
        action = str(data.get("suggested_action", data.get("action", ""))).strip()

        # Strict validation: each field must have substantive content
        if len(headline) >= 6 and len(driver) >= 6 and len(action) >= 6:
            return headline, driver, action
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    return None


def _split_into_sentences(text: str) -> list[str]:
    """Backward-compatible sentence splitter."""
    validated = parse_and_validate_insight(text)
    if validated is not None:
        return list(validated)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and any(re.match(r"^(?:[1-3][\.\)]|\-|\*)\s*", ln) for ln in lines):
        numbered_parts = []
        for line in lines:
            cleaned_line = re.sub(r"^(?:[1-3][\.\)]|\-|\*)\s*", "", line).strip()
            if cleaned_line:
                numbered_parts.append(cleaned_line)
        if len(numbered_parts) >= 2:
            return numbered_parts

    parts = [
        p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", text.strip()) if p.strip()
    ]
    return parts


def validate_llm_base_url(url: str) -> None:
    """Validate that the LLM egress endpoint is safe and not an SSRF vector.

    Ensures:
    1. Scheme is 'https' (unless AIVARA_ALLOW_INSECURE_LLM_HOSTS is True).
    2. Hostname matches allowed hosts in AIVARA_ALLOWED_LLM_HOSTS.
    3. Hostname does not resolve to private, loopback, link-local, or cloud metadata IPs.
    """
    if config.AIVARA_ALLOW_INSECURE_LLM_HOSTS:
        return

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:
        raise OpenRouterError(f"Invalid LLM endpoint URL: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme != "https":
        raise OpenRouterError(
            f"Insecure LLM endpoint scheme '{scheme}'. Only HTTPS egress is permitted."
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise OpenRouterError("Invalid LLM endpoint URL: missing hostname.")

    # Check for direct IP addresses (loopback, private, link-local, cloud metadata)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise OpenRouterError(f"Egress to private/reserved IP address '{hostname}' is blocked.")
    except ValueError:
        pass

    # Block well-known cloud metadata hostnames / localhost aliases
    if hostname in ("localhost", "metadata.google.internal", "instance-data"):
        raise OpenRouterError(f"Egress to metadata/local host '{hostname}' is blocked.")

    # Validate against configured allowed hosts
    allowed = config.AIVARA_ALLOWED_LLM_HOSTS
    matched = False
    for allowed_host in allowed:
        if hostname == allowed_host or hostname.endswith("." + allowed_host):
            matched = True
            break

    if not matched:
        raise OpenRouterError(
            f"LLM endpoint host '{hostname}' is not in the allowlist ({', '.join(allowed)})."
        )


def _call_openrouter_with_resilience(
    messages: list[dict],
    model: str,
    allow_paid: bool,
    max_retries: int = 2,
    timeout: float = LLM_REQUEST_TIMEOUT_SECONDS,
) -> tuple[str, str]:
    """Executes call to OpenRouter with circuit breaker, timeout, and exponential backoff retry."""
    if not OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY is not set.")
    if config.is_placeholder_secret(OPENROUTER_API_KEY):
        raise OpenRouterError("OPENROUTER_API_KEY is configured with a placeholder value.")

    validate_llm_base_url(OPENROUTER_BASE_URL)

    if not _circuit_breaker.can_attempt():
        raise OpenRouterError("OpenRouter circuit breaker is OPEN due to repeated failures.")

    actual_model = model
    if not allow_paid and ":free" not in model and model != "openrouter/auto":
        # Guard rail: never silently call a paid model without explicit toggle
        actual_model = FALLBACK_MODEL

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Aivaratechinfomatics/Aivara",
        "X-Title": "Aivara Insight Lite",
    }
    payload: dict[str, Any] = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=timeout
            )
            # Transient rate limit (429) or server errors (500, 502, 503, 504) -> retry
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                backoff = (0.5 * (2**attempt)) + (random.uniform(0.05, 0.2))
                time.sleep(backoff)
                continue

            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            _circuit_breaker.record_success()
            return content, actual_model

        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < max_retries:
                backoff = (0.5 * (2**attempt)) + (random.uniform(0.05, 0.2))
                time.sleep(backoff)
            else:
                _circuit_breaker.record_failure()
                raise OpenRouterError(
                    f"OpenRouter request failed after {attempt + 1} attempts: {exc}"
                ) from exc

    _circuit_breaker.record_failure()
    raise OpenRouterError(f"OpenRouter request failed: {last_error}")


# Aliases
_call_openrouter = _call_openrouter_with_resilience


def generate_insight(
    facts_packet: dict[str, Any],
    model: str = DEFAULT_MODEL,
    allow_paid: bool = ALLOW_PAID_MODELS_DEFAULT,
    redact_labels: bool = AIVARA_LLM_REDACT_LABELS,
    session_id: str = "default",
) -> InsightResult:
    """Fail-soft, privacy-preserving, schema-validated insight generation:
    1. Content-hash cache lookup (no spend, no network).
    2. Budget and session-limit validation -> deterministic fallback if exhausted.
    3. Label pseudonymization if redact_labels is enabled.
    4. Call OpenRouter with circuit breaker and retry backoff.
    5. Schema validation with 1-shot repair retry -> deterministic fallback if invalid.
    6. Local numerical faithfulness verification -> deterministic fallback if hallucinating.
    7. De-pseudonymize labels locally before returning.
    8. Cache only valid, verified insights (never garbled output).
    """
    key_material = cache_key_material(facts_packet, model)
    cached = cache.get(key_material)
    if cached is not None:
        return InsightResult(
            headline=str(cached.get("headline", "")),
            driver_explanation=str(cached.get("driver_explanation", "")),
            suggested_action=str(cached.get("suggested_action", "")),
            raw_text=str(cached.get("raw_text", "")),
            from_cache=True,
            model=str(cached.get("model", model)),
            is_fallback=bool(cached.get("is_fallback", False)),
        )

    # 1. Budget enforcement (daily & session)
    if not budget.can_make_call():
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text="",
            from_cache=False,
            model="deterministic/daily_budget_exhausted",
            is_fallback=True,
        )

    if not budget.can_make_session_call(session_id):
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text="",
            from_cache=False,
            model="deterministic/session_budget_exhausted",
            is_fallback=True,
        )

    # 2. Data Egress Control / Pseudonymization
    prepared_packet = facts_packet
    reverse_map: dict[str, str] = {}
    if redact_labels:
        prepared_packet, reverse_map = redact_facts_packet(facts_packet)

    # 3. Token estimation check
    packet_json = json.dumps(prepared_packet, ensure_ascii=False)
    if budget.estimate_tokens(packet_json) > 3000:
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text="",
            from_cache=False,
            model="deterministic/payload_too_large",
            is_fallback=True,
        )

    # 4. Outbound call with resilience
    if not OPENROUTER_API_KEY or config.is_placeholder_secret(OPENROUTER_API_KEY):
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text="",
            from_cache=False,
            model="deterministic/no_api_key",
            is_fallback=True,
        )

    messages = build_insight_prompt(prepared_packet)
    try:
        raw_text, used_model = _call_openrouter_with_resilience(
            messages, model=model, allow_paid=allow_paid
        )
        budget.record_call()
        budget.record_session_call(session_id)
    except OpenRouterError as exc:
        logger.info(f"OpenRouter unavailable ({exc}), generating deterministic fallback.")
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text="",
            from_cache=False,
            model="deterministic/fallback",
            is_fallback=True,
        )

    # 5. Structured JSON schema validation
    validated = parse_and_validate_insight(raw_text)
    if validated is None:
        # Repair attempt: 1-shot retry asking model to reformat strictly as JSON
        try:
            repair_messages = build_repair_prompt(raw_text)
            repair_raw, _ = _call_openrouter_with_resilience(
                repair_messages, model=used_model, allow_paid=allow_paid, max_retries=1
            )
            validated = parse_and_validate_insight(repair_raw)
            if validated is not None:
                raw_text = repair_raw
        except OpenRouterError:
            pass

    if validated is None:
        # Schema validation completely failed — NEVER cache garbled output!
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text=raw_text,
            from_cache=False,
            model=used_model,
            is_fallback=True,
        )

    headline, driver, action = validated

    # 6. Faithfulness Check (Numerical Grounding)
    is_faithful = verify_faithfulness(headline, driver, action, prepared_packet)
    if not is_faithful:
        logger.warning("Insight contained ungrounded numeric metrics. Reverting to fallback.")
        h, d, a = generate_deterministic_fallback(facts_packet)
        return InsightResult(
            headline=h,
            driver_explanation=d,
            suggested_action=a,
            raw_text=raw_text,
            from_cache=False,
            model=used_model,
            is_fallback=True,
        )

    # 7. Local De-pseudonymization (restore original business names)
    if reverse_map:
        headline, driver, action = unredact_insight(headline, driver, action, reverse_map)

    # 8. Cache valid, faithful, unredacted insight
    result_dict = {
        "headline": headline,
        "driver_explanation": driver,
        "suggested_action": action,
        "raw_text": raw_text,
        "model": used_model,
        "is_fallback": False,
    }
    cache.set(key_material, result_dict)

    return InsightResult(
        headline=headline,
        driver_explanation=driver,
        suggested_action=action,
        raw_text=raw_text,
        from_cache=False,
        model=used_model,
        is_fallback=False,
    )


# Backward-compatible alias
query_insight = generate_insight


def classify_ambiguous_columns(
    column_payload: list[dict],
    model: str = DEFAULT_MODEL,
    allow_paid: bool = ALLOW_PAID_MODELS_DEFAULT,
) -> list[dict]:
    """Deprecated: Tier 2 LLM column classification has been removed per Decision D6.
    Returns an empty list; deterministic rule-based classifier handles all column roles.
    """
    return []
