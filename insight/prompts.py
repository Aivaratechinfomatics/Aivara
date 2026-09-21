"""
insight/prompts.py — prompt templates (system + per-insight-type).
"""

from __future__ import annotations

import json

from config import PROMPT_VERSION

INSIGHT_SYSTEM_PROMPT = """\
You turn pre-computed business analytics into one short insight. You are
given only aggregated numbers, never raw records. Respond in exactly this
structure, 3 short sentences total, no preamble:
1) What changed (the headline number and direction).
2) What explains it (name the top driver(s) from the data given).
3) One concrete suggested next action.
Do not invent numbers not present in the input. Do not mention that you are
an AI or reference "the data" abstractly — speak plainly, like a business
analyst.
"""

COLUMN_CLASSIFICATION_SYSTEM_PROMPT = """\
You classify spreadsheet columns by role, given only the column name and a
handful of sample values (never the full column, never other columns).
Roles: date, metric (a numeric, aggregatable quantity), dimension (a
categorical field used for grouping), id (a near-unique identifier), or
text (free text / unclassified). Respond with a JSON array, one object per
column: {"column_name": ..., "role": ..., "suggested_label": ...}. The
suggested_label is a short human-readable name for the column (e.g. raw
column "qty_shp" -> "Quantity Shipped"). Respond with JSON only, no preamble.
"""


def build_insight_prompt(facts_packet: dict) -> list[dict]:
    """Returns the OpenRouter chat-completions `messages` array for a single
    insight generation call."""
    return [
        {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(facts_packet, ensure_ascii=False)},
    ]


def build_column_classification_prompt(column_payload: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": COLUMN_CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(column_payload, ensure_ascii=False)},
    ]


def cache_key_material(facts_packet: dict, model: str) -> str:
    """Deterministic string used as input to the cache hash — includes the
    prompt version so a future prompt change doesn't silently reuse insights
    generated under the old prompt."""
    return json.dumps(
        {"facts": facts_packet, "model": model, "prompt_version": PROMPT_VERSION},
        sort_keys=True,
    )
