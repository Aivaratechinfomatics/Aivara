"""
insight/redactor.py — Data Egress Control and Pseudonymization (Phase 5 / Audit §5 / D5).

Protects sensitive business entity and category names before transmission to external LLMs
by substituting them with deterministic pseudonyms ('Category A', 'Entity 1') and restoring
the original human-readable names locally upon receiving the model's response.
"""

from __future__ import annotations

import copy
import re
from typing import Any


def redact_facts_packet(facts_packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Redacts category and entity names in a facts packet, returning:
    (pseudonymized_packet, reverse_map).

    The reverse_map maps pseudonym -> original_name so responses can be de-redacted locally.
    """
    packet = copy.deepcopy(facts_packet)
    reverse_map: dict[str, str] = {}
    forward_map: dict[str, str] = {}
    counter = 1

    def _get_pseudonym(original: str, prefix: str = "Category") -> str:
        nonlocal counter
        if not original or not isinstance(original, str):
            return original
        trimmed = original.strip()
        if not trimmed:
            return original
        if trimmed in forward_map:
            return forward_map[trimmed]
        pseudo = f"{prefix} {chr(64 + counter) if counter <= 26 else counter}"
        counter += 1
        forward_map[trimmed] = pseudo
        reverse_map[pseudo] = trimmed
        return pseudo

    # 1. Standard KPI Driver categories
    for driver_list_key in ("top_positive_drivers", "top_negative_drivers"):
        if driver_list_key in packet and isinstance(packet[driver_list_key], list):
            for d in packet[driver_list_key]:
                if isinstance(d, dict) and "category" in d:
                    cat = d["category"]
                    if cat and isinstance(cat, str):
                        d["category"] = _get_pseudonym(cat, prefix="Category")

    # 2. Snapshot top performer / entity
    if (
        "top_performer" in packet
        and isinstance(packet["top_performer"], str)
        and packet["top_performer"]
    ):
        packet["top_performer"] = _get_pseudonym(packet["top_performer"], prefix="Entity")

    # 3. Flagged risk items (pseudonymize occurrences of known categories in descriptions)
    if "flagged_risk_items" in packet and isinstance(packet["flagged_risk_items"], list):
        for item in packet["flagged_risk_items"]:
            if isinstance(item, dict) and "description" in item:
                desc = item["description"]
                for orig, pseudo in forward_map.items():
                    desc = desc.replace(orig, pseudo)
                item["description"] = desc
            elif isinstance(item, str):
                desc_str = item
                for orig, pseudo in forward_map.items():
                    desc_str = desc_str.replace(orig, pseudo)

    return packet, reverse_map


def unredact_text(text: str, reverse_map: dict[str, str]) -> str:
    """Restores original category and entity names from their pseudonyms.
    Sorts keys by length descending to prevent sub-string prefix collisions.
    """
    if not text or not reverse_map:
        return text

    result = text
    # Sort by length descending to match 'Category 10' before 'Category 1'
    sorted_pseudos = sorted(reverse_map.keys(), key=len, reverse=True)
    for pseudo in sorted_pseudos:
        original = reverse_map[pseudo]
        # Word boundary or exact match
        pattern = re.compile(rf"\b{re.escape(pseudo)}\b", re.IGNORECASE)
        result = pattern.sub(original, result)

    return result


def unredact_insight(
    headline: str, driver: str, action: str, reverse_map: dict[str, str]
) -> tuple[str, str, str]:
    """Un-redacts all 3 components of an insight result using the reverse map."""
    return (
        unredact_text(headline, reverse_map),
        unredact_text(driver, reverse_map),
        unredact_text(action, reverse_map),
    )
