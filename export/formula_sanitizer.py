"""
export/formula_sanitizer.py — Defense against CSV / Spreadsheet Formula Injection (CWE-1236).

Neutralizes strings starting with '=', '+', '-', '@', '\\t', '\\r' that can trigger
arbitrary command execution (e.g. DDE formulas) when opened in Microsoft Excel,
LibreOffice Calc, or other spreadsheet processors.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Characters that trigger formula execution in spreadsheet software
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Regex to detect pure numbers (positive, negative, float, int, scientific notation)
# Examples: "123", "-45.6", "+7.8", "-1.2e-3"
_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def sanitize_for_formula_injection(value: Any) -> Any:
    """Neutralize spreadsheet formula injection characters in a scalar value.

    If value is a string starting with '=', '+', '-', '@', '\\t', or '\\r',
    and is not a valid numeric scalar, it is prepended with a single quote (').
    If value is already numeric or non-string, it is returned unchanged.
    """
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped:
        return value

    # Check if string starts with dangerous prefix
    if value.startswith(_FORMULA_PREFIXES) or stripped.startswith(_FORMULA_PREFIXES):
        # Allow pure numbers (e.g. "-12.5", "+42", "-0.01")
        if _NUMERIC_RE.match(stripped):
            return value

        # If it's already quote-escaped, return as is
        if value.startswith("'"):
            return value

        return "'" + value

    return value


def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with all string/object cells sanitized against formula injection."""
    if df.empty:
        return df.copy()

    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == object or pd.api.types.is_string_dtype(df_clean[col]):
            df_clean[col] = df_clean[col].map(
                lambda x: sanitize_for_formula_injection(x) if isinstance(x, str) else x
            )
    return df_clean
