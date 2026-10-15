"""
analytics/anomalies.py — simple, explainable outlier / risk-signal detection.

No black-box ML for v1: z-score / IQR outlier detection per metric within a
dimension group, plus sudden period-over-period swings beyond a threshold.
Each flagged item becomes one "risk signal".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analytics.kpis import get_metric_aggregation
from config import ANOMALY_PCT_SWING_THRESHOLD, ANOMALY_ZSCORE_THRESHOLD

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"


@dataclass
class RiskSignal:
    description: str
    severity: str
    metric: str
    dimension: str | None = None
    category: str | None = None
    value: float | None = None


def detect_temporal_anomalies(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    dimension_col: str,
    min_periods: int = 3,
    z_threshold: float = ANOMALY_ZSCORE_THRESHOLD,
    agg: str | None = None,
) -> list[RiskSignal]:
    """Detects category anomalies relative to each category's OWN history.
    Evaluates rolling baseline mean and standard deviation over prior time periods."""
    signals: list[RiskSignal] = []
    if (
        df.empty
        or date_col not in df.columns
        or metric_col not in df.columns
        or dimension_col not in df.columns
    ):
        return signals

    working = df[[date_col, dimension_col, metric_col]].copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col, metric_col])
    if working.empty:
        return signals

    working["period"] = working[date_col].dt.to_period("M").dt.to_timestamp()
    dim_series = working[dimension_col].fillna("(missing)").astype(str)
    working["dim_clean"] = dim_series

    resolved_agg = get_metric_aggregation(metric_col, override=agg)
    if resolved_agg == "mean":
        grouped = (
            working.groupby(["dim_clean", "period"])[metric_col]
            .mean(numeric_only=True)
            .unstack(fill_value=0.0)
        )
    elif resolved_agg == "last":
        grouped = (
            working.groupby(["dim_clean", "period"])[metric_col].last().unstack(fill_value=0.0)
        )
    else:
        grouped = (
            working.groupby(["dim_clean", "period"])[metric_col]
            .sum(numeric_only=True)
            .unstack(fill_value=0.0)
        )

    if grouped.shape[1] < min_periods:
        return signals

    for cat, series in grouped.iterrows():
        history = series.iloc[:-1]
        current_val = float(series.iloc[-1])
        h_mean = float(history.mean())
        h_std = float(history.std(ddof=0))
        if pd.isna(h_std) or pd.isna(h_mean):
            continue

        if h_std > 1e-6:
            effective_std = h_std
        elif abs(current_val - h_mean) > 1e-6:
            effective_std = max(0.05 * abs(h_mean), 0.1)
        else:
            continue

        z = (current_val - h_mean) / effective_std
        if abs(z) >= z_threshold:
            if abs(z) >= z_threshold * 2.0:
                severity = SEVERITY_HIGH
            elif abs(z) >= z_threshold * 1.5:
                severity = SEVERITY_MEDIUM
            else:
                severity = SEVERITY_LOW
            direction = "unusually high" if z > 0 else "unusually low"
            signals.append(
                RiskSignal(
                    description=(
                        f"'{cat}' {metric_col} is {direction} compared to its own history "
                        f"(z={z:.1f}, current={current_val:,.1f}, historical mean={h_mean:,.1f})."
                    ),
                    severity=severity,
                    metric=metric_col,
                    dimension=dimension_col,
                    category=str(cat),
                    value=current_val,
                )
            )
    return signals


def detect_group_outliers(
    df: pd.DataFrame,
    metric_col: str,
    dimension_col: str,
    z_threshold: float = ANOMALY_ZSCORE_THRESHOLD,
    agg: str | None = None,
) -> list[RiskSignal]:
    """Flag categories within `dimension_col` whose `metric_col` total is a
    z-score structural outlier relative to the other categories."""
    signals: list[RiskSignal] = []
    dim_series = df[dimension_col].fillna("(missing)").astype(str)
    resolved_agg = get_metric_aggregation(metric_col, override=agg)
    if resolved_agg == "mean":
        grouped = df.groupby(dim_series)[metric_col].mean(numeric_only=True)
    elif resolved_agg == "last":
        grouped = df.groupby(dim_series)[metric_col].last()
    else:
        grouped = df.groupby(dim_series)[metric_col].sum(numeric_only=True)
    if len(grouped) < 3:
        return signals

    mean = grouped.mean()
    std = grouped.std(ddof=0)
    if std == 0 or pd.isna(std):
        return signals

    z_scores = (grouped - mean) / std
    for cat, z in z_scores.items():
        if abs(z) >= z_threshold:
            if abs(z) >= z_threshold * 2.0:
                severity = SEVERITY_HIGH
            elif abs(z) >= z_threshold * 1.5:
                severity = SEVERITY_MEDIUM
            else:
                severity = SEVERITY_LOW
            direction = "unusually high" if z > 0 else "unusually low"
            signals.append(
                RiskSignal(
                    description=f"'{cat}' has {direction} {metric_col} (structural outlier relative to other {dimension_col} groups, z={z:.1f}).",
                    severity=severity,
                    metric=metric_col,
                    dimension=dimension_col,
                    category=str(cat),
                    value=float(grouped[cat]),
                )
            )
    return signals


def detect_period_swings(
    df_current: pd.DataFrame,
    df_prior: pd.DataFrame | None,
    metric_col: str,
    dimension_col: str | None = None,
    pct_threshold: float = ANOMALY_PCT_SWING_THRESHOLD,
    agg: str | None = None,
) -> list[RiskSignal]:
    """Flag sudden period-over-period swings beyond a flat % threshold
    (used as the short-history fallback when we don't have enough periods
    to compute a proper historical volatility band)."""
    signals: list[RiskSignal] = []
    if df_prior is None or df_prior.empty or df_current.empty:
        return signals

    resolved_agg = get_metric_aggregation(metric_col, override=agg)

    if dimension_col is None:
        if resolved_agg == "mean":
            cur_total = float(df_current[metric_col].mean(skipna=True))
            prior_total = float(df_prior[metric_col].mean(skipna=True))
        elif resolved_agg == "last":
            s_cur = df_current[metric_col].dropna()
            s_pri = df_prior[metric_col].dropna()
            cur_total = float(s_cur.iloc[-1]) if not s_cur.empty else 0.0
            prior_total = float(s_pri.iloc[-1]) if not s_pri.empty else 0.0
        else:
            cur_total = float(df_current[metric_col].sum(skipna=True))
            prior_total = float(df_prior[metric_col].sum(skipna=True))

        if prior_total == 0:
            return signals
        pct_change = (cur_total - prior_total) / abs(prior_total)
        if abs(pct_change) >= pct_threshold:
            if abs(pct_change) >= pct_threshold * 2.0:
                severity = SEVERITY_HIGH
            elif abs(pct_change) >= pct_threshold * 1.5:
                severity = SEVERITY_MEDIUM
            else:
                severity = SEVERITY_LOW
            signals.append(
                RiskSignal(
                    description=f"{metric_col} swung {pct_change:+.0%} period-over-period.",
                    severity=severity,
                    metric=metric_col,
                    value=cur_total,
                )
            )
        return signals

    cur_dim = df_current[dimension_col].fillna("(missing)").astype(str)
    prior_dim = df_prior[dimension_col].fillna("(missing)").astype(str)
    if resolved_agg == "mean":
        cur_grouped = df_current.groupby(cur_dim)[metric_col].mean(numeric_only=True)
        prior_grouped = df_prior.groupby(prior_dim)[metric_col].mean(numeric_only=True)
    elif resolved_agg == "last":
        cur_grouped = df_current.groupby(cur_dim)[metric_col].last()
        prior_grouped = df_prior.groupby(prior_dim)[metric_col].last()
    else:
        cur_grouped = df_current.groupby(cur_dim)[metric_col].sum(numeric_only=True)
        prior_grouped = df_prior.groupby(prior_dim)[metric_col].sum(numeric_only=True)

    common = set(cur_grouped.index) & set(prior_grouped.index)
    for cat in common:
        prior_val = float(prior_grouped[cat])
        cur_val = float(cur_grouped[cat])
        if prior_val == 0:
            continue
        pct_change = (cur_val - prior_val) / abs(prior_val)
        if abs(pct_change) >= pct_threshold:
            if abs(pct_change) >= pct_threshold * 2.0:
                severity = SEVERITY_HIGH
            elif abs(pct_change) >= pct_threshold * 1.5:
                severity = SEVERITY_MEDIUM
            else:
                severity = SEVERITY_LOW
            signals.append(
                RiskSignal(
                    description=f"'{cat}' {metric_col} swung {pct_change:+.0%} period-over-period.",
                    severity=severity,
                    metric=metric_col,
                    dimension=dimension_col,
                    category=str(cat),
                    value=cur_val,
                )
            )
    return signals


def compute_risk_signals(
    df_current: pd.DataFrame,
    df_prior: pd.DataFrame | None,
    metric_columns: list[str],
    dimension_columns: list[str],
    full_df: pd.DataFrame | None = None,
    date_col: str | None = None,
    metric_aggs: dict[str, str] | None = None,
) -> list[RiskSignal]:
    all_signals: list[RiskSignal] = []
    aggs = metric_aggs or {}

    # 1. Temporal anomalies if history is available
    if full_df is not None and date_col is not None and date_col in full_df.columns:
        for metric in metric_columns:
            m_agg = aggs.get(metric)
            for dim in dimension_columns:
                all_signals.extend(
                    detect_temporal_anomalies(full_df, date_col, metric, dim, agg=m_agg)
                )

    # 2. Period swings & structural group outliers
    for metric in metric_columns:
        m_agg = aggs.get(metric)
        all_signals.extend(detect_period_swings(df_current, df_prior, metric, agg=m_agg))
        for dim in dimension_columns:
            all_signals.extend(detect_group_outliers(df_current, metric, dim, agg=m_agg))
            all_signals.extend(detect_period_swings(df_current, df_prior, metric, dim, agg=m_agg))

    # De-duplicate near-identical descriptions.
    seen = set()
    deduped = []
    for s in all_signals:
        key = (s.metric, s.dimension, s.category, s.description)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped
