"""
insight/client.py — OpenRouter API wrapper.

This is the ONLY module in the app that makes network calls. Everything to
the left of this module (ingestion, analytics, facts_builder) runs fully
offline. export/pptx_builder.py must never import this module (enforced by
convention + a unit test — see tests/test_export_no_network.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests

from config import (
    ALLOW_PAID_MODELS_DEFAULT,
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    MAX_OUTPUT_TOKENS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from insight import budget, cache
from insight.prompts import build_column_classification_prompt, build_insight_prompt, cache_key_material


@dataclass
class InsightResult:
    headline: str
    driver_explanation: str
    suggested_action: str
    raw_text: str
    from_cache: bool
    model: str


class BudgetExhaustedError(RuntimeError):
    """Raised when the daily call budget has been exhausted."""


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter API call itself fails (network, auth, etc)."""


def _split_into_sentences(text: str) -> list[str]:
    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "headline" in data:
            return [
                data.get("headline", ""),
                data.get("driver_explanation", data.get("driver", "")),
                data.get("suggested_action", data.get("action", "")),
            ]
    except Exception:
        pass

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and any(re.match(r"^(?:[1-3][\.\)]|\-|\*)\s*", l) for l in lines):
        numbered_parts = []
        for line in lines:
            cleaned_line = re.sub(r"^(?:[1-3][\.\)]|\-|\*)\s*", "", line).strip()
            if cleaned_line:
                numbered_parts.append(cleaned_line)
        if len(numbered_parts) >= 2:
            return numbered_parts

    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", text.strip()) if p.strip()]
    return parts


def _call_openrouter(messages: list[dict], model: str, allow_paid: bool) -> tuple[str, str]:
    if not OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY is not set.")

    actual_model = model
    if not allow_paid and ":free" not in model and model != "openrouter/auto":
        # Guard rail: never silently call a paid model.
        actual_model = FALLBACK_MODEL

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }

    try:
        resp = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"], actual_model
    except requests.RequestException as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise OpenRouterError(f"Unexpected OpenRouter response shape: {exc}") from exc


def generate_insight(
    facts_packet: dict,
    model: str = DEFAULT_MODEL,
    allow_paid: bool = ALLOW_PAID_MODELS_DEFAULT,
) -> InsightResult:
    """Fail-soft insight generation:
      1. Check cache by content hash -> return cached hit, no network call, no budget spend.
      2. Check budget -> if exhausted, raise BudgetExhaustedError (caller shows a neutral
         placeholder, per Section 9.2.7 — the dashboard must still render fully).
      3. Call OpenRouter, parse the 3-sentence structure, cache it.
    """
    key_material = cache_key_material(facts_packet, model)
    cached = cache.get(key_material)
    if cached is not None:
        return InsightResult(**cached, from_cache=True)

    if not budget.can_make_call():
        raise BudgetExhaustedError("Daily LLM call budget has been reached.")

    # Guard: estimate token size of facts packet
    packet_json = json.dumps(facts_packet, ensure_ascii=False)
    if budget.estimate_tokens(packet_json) > 3000:
        raise OpenRouterError("Facts packet exceeds safe token budget.")

    messages = build_insight_prompt(facts_packet)
    raw_text, used_model = _call_openrouter(messages, model=model, allow_paid=allow_paid)
    budget.record_call()

    sentences = _split_into_sentences(raw_text)
    headline = sentences[0] if len(sentences) > 0 else raw_text.strip()
    driver = sentences[1] if len(sentences) > 1 else ""
    action = sentences[2] if len(sentences) > 2 else ""

    result_dict = {
        "headline": headline,
        "driver_explanation": driver,
        "suggested_action": action,
        "raw_text": raw_text,
        "model": used_model,
    }
    if headline and len(headline) >= 5:
        cache.set(key_material, result_dict)

    return InsightResult(**result_dict, from_cache=False)


def classify_ambiguous_columns(
    column_payload: list[dict],
    model: str = DEFAULT_MODEL,
    allow_paid: bool = ALLOW_PAID_MODELS_DEFAULT,
) -> list[dict]:
    """Tier 2 classification fallback (Section 8.2). Budget-aware like
    insight generation; callers should treat a BudgetExhaustedError as "keep
    the Tier 1 guess" rather than a hard failure."""
    if not column_payload:
        return []

    key_material = cache_key_material({"columns": column_payload}, model)
    cached = cache.get(key_material)
    if cached is not None:
        return cached.get("classifications", [])

    if not budget.can_make_call():
        raise BudgetExhaustedError("Daily LLM call budget has been reached.")

    messages = build_column_classification_prompt(column_payload)
    raw_text, _ = _call_openrouter(messages, model=model, allow_paid=allow_paid)
    budget.record_call()

    try:
        cleaned = raw_text.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        classifications = json.loads(cleaned)
    except json.JSONDecodeError:
        classifications = []

    cache.set(key_material, {"classifications": classifications})
    return classifications
