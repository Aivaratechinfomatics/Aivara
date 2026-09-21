"""
analytics/stats.py — Autonomous statistical discovery engine.

Runs 100% offline with zero network dependencies. Computes:
1. Pearson correlation matrix and automated key driver relationship extraction.
2. Gini coefficient and Herfindahl-Hirschman (HHI) concentration risk indices.
3. Dimension attribution for statistical outliers.
4. Deterministic, boardroom-ready executive takeaways.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class DriverRelationship:
    metric_a: str
    metric_b: str
    correlation: float
    strength: str  # "strong positive", "moderate positive", "strong negative", "moderate negative"
    narrative: str


@dataclass
class ConcentrationResult:
    gini: float
    hhi: float
    top_20_pct_share: float
    risk_level: str  # "Low", "Moderate", "High", "Extreme"
    narrative: str


@dataclass
class AnomalyAttribution:
    metric: str
    outlier_count: int
    top_driver_dimension: str | None
    top_driver_category: str | None
    category_share_of_outliers: float


def compute_correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    """Computes a clean Pearson correlation matrix for valid numeric columns."""
    valid_cols = [
        c for c in numeric_cols
        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]) and df[c].dropna().nunique() > 1
    ]
    if len(valid_cols) < 2:
        return pd.DataFrame()

    sub_df = df[valid_cols].dropna(how="all")
    corr = sub_df.corr(method="pearson")
    return corr.fillna(0.0)


def extract_key_drivers(
    corr_df: pd.DataFrame,
    primary_metric: str | None = None,
    threshold: float = 0.45,
) -> list[DriverRelationship]:
    """Extracts top metric relationships from a correlation matrix."""
    if corr_df.empty:
        return []

    relationships = []
    cols = list(corr_df.columns)

    def _human(name: str) -> str:
        s = re.sub(r"[_\s]+", " ", str(name)).strip()
        return s.title()

    if primary_metric and primary_metric in corr_df.columns:
        # Relate all other metrics to the primary metric
        for other in cols:
            if other == primary_metric:
                continue
            val = float(corr_df.loc[primary_metric, other])
            if abs(val) >= threshold and not np.isnan(val):
                rel = _build_relationship(primary_metric, other, val, _human)
                relationships.append(rel)
    else:
        # Find all unique upper-triangle pairs
        seen = set()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col_a, col_b = cols[i], cols[j]
                val = float(corr_df.loc[col_a, col_b])
                if abs(val) >= threshold and not np.isnan(val):
                    key = tuple(sorted([col_a, col_b]))
                    if key not in seen:
                        seen.add(key)
                        rel = _build_relationship(col_a, col_b, val, _human)
                        relationships.append(rel)

    # Sort descending by absolute correlation
    relationships.sort(key=lambda r: abs(r.correlation), reverse=True)
    return relationships


def _build_relationship(col_a: str, col_b: str, r: float, human_fn) -> DriverRelationship:
    ha, hb = human_fn(col_a), human_fn(col_b)
    if r >= 0.75:
        strength = "strong positive"
        narrative = f"Strong positive driver: Higher {hb} strongly associates with higher {ha} (r = {r:+.2f})."
    elif r >= 0.45:
        strength = "moderate positive"
        narrative = f"Moderate positive relationship: {hb} moves in tandem with {ha} (r = {r:+.2f})."
    elif r <= -0.75:
        strength = "strong negative"
        narrative = f"Strong inverse driver: Higher {hb} strongly associates with lower {ha} (r = {r:+.2f})."
    else:
        strength = "moderate negative"
        narrative = f"Moderate inverse relationship: Higher {hb} tends to reduce {ha} (r = {r:+.2f})."

    return DriverRelationship(
        metric_a=col_a,
        metric_b=col_b,
        correlation=round(r, 3),
        strength=strength,
        narrative=narrative,
    )


def compute_concentration_index(series: pd.Series | np.ndarray) -> ConcentrationResult:
    """Computes Gini Coefficient, Herfindahl-Hirschman Index (HHI), and top 20% share."""
    if isinstance(series, pd.Series):
        vals = series.dropna().to_numpy(dtype=float)
    else:
        vals = np.array(series, dtype=float)
        vals = vals[~np.isnan(vals)]

    # Keep only non-negative values
    vals = vals[vals >= 0]
    n = len(vals)

    if n < 2 or vals.sum() == 0:
        return ConcentrationResult(
            gini=0.0,
            hhi=0.0,
            top_20_pct_share=0.0,
            risk_level="Low",
            narrative="Even or single-entity distribution.",
        )

    # Gini calculation
    sorted_vals = np.sort(vals)
    cum_vals = np.cumsum(sorted_vals)
    total_sum = cum_vals[-1]

    # G = (2 * sum(i * y_i) / (n * sum(y))) - (n + 1)/n
    index = np.arange(1, n + 1)
    gini = float((2 * np.sum(index * sorted_vals)) / (n * total_sum) - (n + 1) / n)
    gini = max(0.0, min(1.0, gini))

    # Top 20% share
    top_20_count = max(1, int(np.ceil(0.20 * n)))
    top_20_share = float(np.sum(sorted_vals[-top_20_count:]) / total_sum)

    # HHI: sum of squared percentage market shares (0 to 10,000)
    shares = (vals / total_sum) * 100.0
    hhi = float(np.sum(shares ** 2))

    if gini >= 0.70 or hhi > 2500 or top_20_share > 0.80:
        risk_level = "Extreme"
        narrative = f"Extreme portfolio concentration: top 20% of entries account for {top_20_share:.1%} of total (Gini: {gini:.2f}, HHI: {hhi:,.0f})."
    elif gini >= 0.50 or hhi > 1500 or top_20_share > 0.65:
        risk_level = "High"
        narrative = f"High concentration: top 20% of entries account for {top_20_share:.1%} of total (Gini: {gini:.2f}, HHI: {hhi:,.0f})."
    elif gini >= 0.35:
        risk_level = "Moderate"
        narrative = f"Moderate concentration: top 20% of entries account for {top_20_share:.1%} of total (Gini: {gini:.2f})."
    else:
        risk_level = "Low"
        narrative = f"Evenly distributed: top 20% of entries account for {top_20_share:.1%} of total (Gini: {gini:.2f})."

    return ConcentrationResult(
        gini=round(gini, 3),
        hhi=round(hhi, 1),
        top_20_pct_share=round(top_20_share, 3),
        risk_level=risk_level,
        narrative=narrative,
    )


def attribute_anomalies(
    df: pd.DataFrame,
    metric_col: str,
    dimension_cols: list[str],
) -> list[AnomalyAttribution]:
    """Identifies which category values drive extreme outliers for a metric."""
    if df.empty or metric_col not in df.columns or not pd.api.types.is_numeric_dtype(df[metric_col]):
        return []

    s = df[metric_col].dropna()
    if len(s) < 10:
        return []

    q25, q75 = s.quantile(0.25), s.quantile(0.75)
    iqr = q75 - q25
    if iqr > 0:
        upper_bound = q75 + 2.0 * iqr
        lower_bound = q25 - 2.0 * iqr
    else:
        mean, std = s.mean(), s.std()
        if std > 0:
            upper_bound = mean + 2.5 * std
            lower_bound = mean - 2.5 * std
        else:
            return []

    outliers = df[(df[metric_col] > upper_bound) | (df[metric_col] < lower_bound)]
    if outliers.empty:
        return []

    attributions = []
    n_outliers = len(outliers)

    for dim in dimension_cols:
        if dim not in df.columns:
            continue
        counts = outliers[dim].value_counts()
        if not counts.empty:
            top_cat = counts.index[0]
            top_cat_share = float(counts.iloc[0] / n_outliers)
            if top_cat_share >= 0.35:
                attributions.append(
                    AnomalyAttribution(
                        metric=metric_col,
                        outlier_count=n_outliers,
                        top_driver_dimension=dim,
                        top_driver_category=str(top_cat),
                        category_share_of_outliers=round(top_cat_share, 3),
                    )
                )

    return attributions


def generate_executive_takeaways(
    df: pd.DataFrame,
    profile,
    corr_relationships: list[DriverRelationship] | None = None,
    concentration: ConcentrationResult | None = None,
) -> list[str]:
    """Generates 3-to-4 high-level boardroom executive takeaways deterministically."""
    takeaways = []
    n_rows = len(df)

    # 1. Scale Takeaway
    primary_m = getattr(profile, "primary_metric", None)
    if primary_m and primary_m in df.columns and pd.api.types.is_numeric_dtype(df[primary_m]):
        s = df[primary_m].dropna()
        total_val = s.sum()
        mean_val = s.mean()
        ha = primary_m.replace("_", " ").title()
        if total_val >= 1_000_000:
            scale_str = f"${total_val / 1_000_000:,.1f}M" if "price" in primary_m.lower() or "sales" in primary_m.lower() or "rev" in primary_m.lower() else f"{total_val / 1_000_000:,.1f}M"
        elif total_val >= 1_000:
            scale_str = f"${total_val / 1_000:,.1f}k" if "price" in primary_m.lower() or "sales" in primary_m.lower() or "rev" in primary_m.lower() else f"{total_val:,.0f}"
        else:
            scale_str = f"{total_val:,.1f}"

        takeaways.append(
            f"**Portfolio Scale**: Analyzed {n_rows:,} records totaling **{scale_str}** in {ha} (average **{mean_val:,.2f}** per entry)."
        )
    else:
        takeaways.append(f"**Dataset Overview**: Evaluated {n_rows:,} records across {df.shape[1]} dimensions and metrics.")

    # 2. Performance / Entity Leader Takeaway
    entity_dim = getattr(profile, "entity_dimension", None)
    if not entity_dim and getattr(profile, "all_dimensions", []):
        entity_dim = profile.all_dimensions[0]

    if entity_dim and primary_m and entity_dim in df.columns and primary_m in df.columns:
        grouped = df.groupby(entity_dim)[primary_m].sum().sort_values(ascending=False)
        if not grouped.empty:
            top_entity = grouped.index[0]
            top_val = grouped.iloc[0]
            pct = (top_val / max(1, grouped.sum())) * 100.0
            takeaways.append(
                f"**Top Contributor**: Leading entity is **{top_entity}**, generating {pct:.1f}% of total {primary_m.replace('_', ' ')}."
            )

    # 3. Concentration & Risk Takeaway
    if concentration and concentration.risk_level in ("High", "Extreme"):
        takeaways.append(f"**Concentration Alert**: {concentration.narrative}")
    elif concentration:
        takeaways.append(f"**Distribution Balance**: {concentration.narrative}")

    # 4. Discovered Driver / Correlation Takeaway
    if corr_relationships:
        top_driver = corr_relationships[0]
        takeaways.append(f"**Key Discovered Driver**: {top_driver.narrative}")

    return takeaways
