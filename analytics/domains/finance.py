"""
analytics/domains/finance.py — Specialized financial, P&L, and budget analytics.

Computes:
1. Actual vs Budget variance ($ and %).
2. Favorable vs Unfavorable variance attribution.
3. Waterfall step data for budget bridges and profitability walks.
4. Margin ratios (Gross, Operating, Net).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
import pandas as pd


@dataclass
class WaterfallStep:
    label: str
    measure: str  # "relative" or "total"
    amount: float


@dataclass
class FinanceAnalyticsResult:
    total_actual: float
    total_budget: float
    variance_abs: float
    variance_pct: float
    is_favorable: bool
    line_item_table: pd.DataFrame
    waterfall_steps: list[WaterfallStep]
    favorable_items: list[tuple[str, float]]
    unfavorable_items: list[tuple[str, float]]


def compute_finance_analytics(
    df: pd.DataFrame,
    account_col: str | None = None,
    actual_col: str | None = None,
    budget_col: str | None = None,
    variance_col: str | None = None,
) -> FinanceAnalyticsResult:
    """Analyzes budget vs actuals, line items, and computes bridge waterfall data."""
    cols = df.columns
    if not account_col:
        account_col = next((c for c in cols if re.search(r"(account|line[_\s]?item|category|item|desc|dept)", c, re.I)), None)
    if not actual_col:
        actual_col = next((c for c in cols if re.search(r"(actual|realized|current|spent|cost|rev)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not budget_col:
        budget_col = next((c for c in cols if re.search(r"(budget|target|plan|forecast|quota)", c, re.I) and pd.api.types.is_numeric_dtype(df[c]) and c != actual_col), None)
    if not variance_col:
        variance_col = next((c for c in cols if re.search(r"(variance|diff|delta)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)

    # Compute actual and budget totals
    total_act = float(df[actual_col].dropna().sum()) if actual_col else 0.0
    total_bud = float(df[budget_col].dropna().sum()) if budget_col else 0.0

    if variance_col and variance_col in df.columns:
        var_abs = float(df[variance_col].dropna().sum())
    else:
        var_abs = total_act - total_bud

    var_pct = (var_abs / total_bud * 100.0) if total_bud != 0 else 0.0
    is_favorable = var_abs >= 0

    # Line item table
    table_df = pd.DataFrame()
    favorable_items = []
    unfavorable_items = []
    waterfall_steps = []

    if account_col and actual_col:
        agg_map = {actual_col: "sum"}
        if budget_col:
            agg_map[budget_col] = "sum"
        if variance_col:
            agg_map[variance_col] = "sum"

        grouped = df.groupby(account_col).agg(agg_map).reset_index()
        if budget_col and "variance" not in [c.lower() for c in grouped.columns]:
            grouped["variance"] = grouped[actual_col] - grouped[budget_col]
            var_col_name = "variance"
        elif variance_col:
            var_col_name = variance_col
        else:
            grouped["variance"] = grouped[actual_col]
            var_col_name = "variance"

        grouped["variance_pct"] = (
            (grouped[var_col_name] / grouped[budget_col].replace(0, float("nan")) * 100.0)
            if budget_col in grouped.columns
            else 0.0
        )
        grouped = grouped.sort_values(by=var_col_name, ascending=False)
        table_df = grouped

        for _, row in grouped.iterrows():
            item_name = str(row[account_col])
            diff = float(row[var_col_name])
            if diff > 0:
                favorable_items.append((item_name, diff))
            elif diff < 0:
                unfavorable_items.append((item_name, diff))

        # Build Waterfall Steps
        if budget_col:
            waterfall_steps.append(WaterfallStep(label="Budget", measure="total", amount=total_bud))
            # Add top 6 variance drivers
            sorted_by_impact = grouped.reindex(grouped[var_col_name].abs().sort_values(ascending=False).index)
            top_drivers = sorted_by_impact.head(6)
            for _, r in top_drivers.iterrows():
                waterfall_steps.append(
                    WaterfallStep(
                        label=str(r[account_col]),
                        measure="relative",
                        amount=float(r[var_col_name]),
                    )
                )
            waterfall_steps.append(WaterfallStep(label="Actual", measure="total", amount=total_act))
        else:
            # General step walk
            for _, r in grouped.head(8).iterrows():
                waterfall_steps.append(
                    WaterfallStep(
                        label=str(r[account_col]),
                        measure="relative",
                        amount=float(r[actual_col]),
                    )
                )
            waterfall_steps.append(WaterfallStep(label="Total", measure="total", amount=total_act))

    return FinanceAnalyticsResult(
        total_actual=round(total_act, 2),
        total_budget=round(total_bud, 2),
        variance_abs=round(var_abs, 2),
        variance_pct=round(var_pct, 2),
        is_favorable=is_favorable,
        line_item_table=table_df,
        waterfall_steps=waterfall_steps,
        favorable_items=favorable_items[:5],
        unfavorable_items=unfavorable_items[:5],
    )
