"""
insight/faithfulness.py — Grounding and Hallucination Verification (Phase 5 / Audit §5).

Verifies that every numerical claim in generated insight text can be traced directly to
pre-computed values in the input facts packet, rejecting ungrounded or hallucinated metrics.
"""

from __future__ import annotations

import re
from typing import Any


def extract_numbers_from_text(text: str) -> list[float]:
    """Extracts numeric values from natural language text, handling currency,
    percentages, commas, and metric suffixes (k, M, Cr, L).
    """
    if not text:
        return []

    # Match numbers like $30,000.50, 81.8%, 1.5M, 2.50Cr, -12.4
    pattern = re.compile(
        r"(?:[\$\€\£\₹])?\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|[kKmM]|cr|Cr|l|L|bn|Bn)?(?=[\s,.;!?\)]|$)"
    )

    extracted: list[float] = []
    for match in pattern.finditer(text):
        num_str = match.group(1).replace(",", "")
        suffix = match.group(2)
        try:
            val = float(num_str)
            if suffix:
                s_lower = suffix.lower()
                if s_lower == "%":
                    extracted.append(val)
                    extracted.append(val / 100.0)
                elif s_lower == "k":
                    extracted.append(val * 1_000.0)
                    extracted.append(val)
                elif s_lower == "m":
                    extracted.append(val * 1_000_000.0)
                    extracted.append(val)
                elif s_lower == "cr":
                    extracted.append(val * 10_000_000.0)
                    extracted.append(val)
                elif s_lower == "l":
                    extracted.append(val * 100_000.0)
                    extracted.append(val)
                elif s_lower == "bn":
                    extracted.append(val * 1_000_000_000.0)
                    extracted.append(val)
            else:
                extracted.append(val)
        except ValueError:
            continue

    return extracted


def collect_packet_numbers(data: Any) -> list[float]:
    """Recursively collects all numerical quantities present within the facts packet,
    generating scaled variants (e.g. M, k, %, absolute value).
    """
    nums: list[float] = []

    def _walk(obj: Any):
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            val = float(obj)
            nums.append(val)
            nums.append(abs(val))
            # Include percent scaling variants
            nums.append(val / 100.0)
            nums.append(val * 100.0)
            # Include abbreviated scale variants (k, M, Cr)
            if abs(val) >= 1_000:
                nums.append(round(val / 1_000.0, 2))
                nums.append(round(val / 1_000.0, 1))
            if abs(val) >= 1_000_000:
                nums.append(round(val / 1_000_000.0, 2))
                nums.append(round(val / 1_000_000.0, 1))
            if abs(val) >= 10_000_000:
                nums.append(round(val / 10_000_000.0, 2))
                nums.append(round(val / 10_000_000.0, 1))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                _walk(item)
        elif isinstance(obj, str):
            # Parse numbers embedded in descriptions (e.g. risk descriptions)
            extracted = extract_numbers_from_text(obj)
            nums.extend(extracted)

    _walk(data)
    return nums


def is_number_grounded(target: float, reference_numbers: list[float]) -> bool:
    """Checks if a target number is close to any reference number within acceptable
    rounding tolerance (e.g. within 0.5 units or 2% relative difference).
    """
    for ref in reference_numbers:
        # Exact match
        if abs(target - ref) < 1e-4:
            return True
        # Small absolute difference (e.g. 81.8% vs 82%)
        if abs(target - ref) <= 0.6:
            return True
        # Relative difference for larger numbers (within 2%)
        if ref != 0 and abs(target - ref) / abs(ref) <= 0.025:
            return True
    return False


def verify_faithfulness(
    headline: str,
    driver: str,
    action: str,
    facts_packet: dict[str, Any],
    exempt_small_counts: bool = True,
) -> bool:
    """Verifies that all numbers cited in headline, driver, and action are grounded
    in the facts packet. If an ungrounded number is found, returns False.
    """
    combined_text = f"{headline} {driver} {action}"
    text_numbers = extract_numbers_from_text(combined_text)
    if not text_numbers:
        return True

    reference_numbers = collect_packet_numbers(facts_packet)

    for num in text_numbers:
        # Small integers (1, 2, 3) often indicate structural positions ("top 3 drivers", "1st")
        if exempt_small_counts and num in (1.0, 2.0, 3.0):
            continue

        if not is_number_grounded(num, reference_numbers):
            return False

    return True
