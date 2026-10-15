"""
analytics/kpis.py — summary KPI computation.

Auto-selects a primary metric plus up to 3 secondary metrics, and computes
current/prior period totals + deltas for each. Also derives a margin-like
ratio KPI when a cost/revenue-shaped pair of metrics is present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

COST_NAME_PATTERN = ("cost", "expense", "spend")
REVENUE_NAME_PATTERN = ("revenue", "sales", "income", "gmv")
RATE_NAME_PATTERN = re.compile(
    r"(rate|pct|percent|ratio|avg|average|score|margin|nps|share|yield)", re.I
)
POINT_IN_TIME_NAME_PATTERN = re.compile(
    r"(headcount|balance|inventory|stock|capacity|employees|staff)", re.I
)


@dataclass
class KPIResult:
    name: str
    unit: str | None
    current_value: float
    prior_value: float | None
    pct_change: float | None
    abs_change: float | None
    is_derived_ratio: bool = False
    agg: str = "sum"


def is_rate_metric(metric_name: str) -> bool:
    return bool(RATE_NAME_PATTERN.search(metric_name))


def get_metric_aggregation(metric_name: str, override: str | None = None) -> str:
    """Determines aggregation semantic: 'sum', 'mean', or 'last'.
    Honors user override if valid; otherwise infers via metric name patterns."""
    if override in ("sum", "mean", "weighted_mean", "last"):
        return "mean" if override == "weighted_mean" else override
    if is_rate_metric(metric_name):
        return "mean"
    return "sum"


def select_primary_and_secondary_metrics(
    df: pd.DataFrame, metric_columns: list[str], max_secondary: int = 3
) -> tuple[str | None, list[str]]:
    """Primary = metric column with the largest sum of absolute values.
    Secondary = next `max_secondary` metrics by the same measure."""
    if not metric_columns:
        return None, []

    sums = {
        col: df[col].abs().sum(skipna=True)
        for col in metric_columns
        if pd.api.types.is_numeric_dtype(df[col])
    }
    ranked = sorted(sums.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        return None, []

    primary = ranked[0][0]
    secondary = [name for name, _ in ranked[1 : 1 + max_secondary]]
    return primary, secondary


def _totals(
    series_current: pd.Series,
    series_prior: pd.Series | None,
    agg: str = "sum",
) -> tuple[float, float | None]:
    if agg == "mean":
        current_total = float(series_current.mean(skipna=True))
        prior_total = float(series_prior.mean(skipna=True)) if series_prior is not None else None
    elif agg == "last":
        s_cur = series_current.dropna()
        current_total = float(s_cur.iloc[-1]) if not s_cur.empty else 0.0
        if series_prior is not None:
            s_pri = series_prior.dropna()
            prior_total = float(s_pri.iloc[-1]) if not s_pri.empty else None
        else:
            prior_total = None
    else:
        current_total = float(series_current.sum(skipna=True))
        prior_total = float(series_prior.sum(skipna=True)) if series_prior is not None else None
    return current_total, prior_total


def compute_kpi(
    df_current: pd.DataFrame,
    df_prior: pd.DataFrame | None,
    metric_col: str,
    agg: str | None = None,
) -> KPIResult:
    resolved_agg = get_metric_aggregation(metric_col, override=agg)
    current_total, prior_total = _totals(
        df_current[metric_col],
        df_prior[metric_col] if df_prior is not None else None,
        agg=resolved_agg,
    )

    pct_change = None
    abs_change = None
    if prior_total is not None:
        abs_change = current_total - prior_total
        if prior_total != 0:
            pct_change = (abs_change / abs(prior_total)) * 100
        elif current_total != 0:
            pct_change = float("inf") if current_total > 0 else float("-inf")
        else:
            pct_change = 0.0

    return KPIResult(
        name=metric_col,
        unit="%" if resolved_agg == "mean" and is_rate_metric(metric_col) else None,
        current_value=current_total,
        prior_value=prior_total,
        pct_change=pct_change,
        abs_change=abs_change,
        is_derived_ratio=is_rate_metric(metric_col),
        agg=resolved_agg,
    )


def find_margin_pair(metric_columns: list[str]) -> tuple[str, str] | None:
    """Look for a (cost, revenue) shaped pair of metric names, e.g.
    ('cost', 'revenue') or ('total_cost', 'total_sales')."""
    cost_col = next(
        (c for c in metric_columns if any(p in c.lower() for p in COST_NAME_PATTERN)), None
    )
    revenue_col = next(
        (c for c in metric_columns if any(p in c.lower() for p in REVENUE_NAME_PATTERN)), None
    )
    if cost_col and revenue_col and cost_col != revenue_col:
        return cost_col, revenue_col
    return None


def compute_margin_kpi(
    df_current: pd.DataFrame, df_prior: pd.DataFrame | None, cost_col: str, revenue_col: str
) -> KPIResult | None:
    cur_rev = float(df_current[revenue_col].sum(skipna=True))
    cur_cost = float(df_current[cost_col].sum(skipna=True))
    if cur_rev == 0:
        return None
    cur_margin = (cur_rev - cur_cost) / cur_rev * 100

    prior_margin = None
    pct_change = None
    abs_change = None
    if df_prior is not None and len(df_prior):
        prior_rev = float(df_prior[revenue_col].sum(skipna=True))
        prior_cost = float(df_prior[cost_col].sum(skipna=True))
        if prior_rev != 0:
            prior_margin = (prior_rev - prior_cost) / prior_rev * 100
            abs_change = cur_margin - prior_margin
            pct_change = abs_change  # margin deltas are typically reported in points, not %-of-%

    return KPIResult(
        name=f"{revenue_col}_margin",
        unit="%",
        current_value=cur_margin,
        prior_value=prior_margin,
        pct_change=pct_change,
        abs_change=abs_change,
        is_derived_ratio=True,
        agg="derived",
    )


def compute_all_kpis(
    df_current: pd.DataFrame,
    df_prior: pd.DataFrame | None,
    metric_columns: list[str],
    max_secondary: int = 3,
    metric_aggs: dict[str, str] | None = None,
) -> dict[str, KPIResult]:
    primary, secondary = select_primary_and_secondary_metrics(
        df_current, metric_columns, max_secondary
    )
    results: dict[str, KPIResult] = {}
    aggs = metric_aggs or {}
    if primary:
        results[primary] = compute_kpi(df_current, df_prior, primary, agg=aggs.get(primary))
    for col in secondary:
        results[col] = compute_kpi(df_current, df_prior, col, agg=aggs.get(col))

    margin_pair = find_margin_pair(metric_columns)
    if margin_pair:
        margin_kpi = compute_margin_kpi(df_current, df_prior, *margin_pair)
        if margin_kpi:
            results[margin_kpi.name] = margin_kpi

    return results
