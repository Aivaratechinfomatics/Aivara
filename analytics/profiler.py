"""
analytics/profiler.py — intelligent dataset profiling.

Inspects classified columns and data properties to automatically detect:
1. Profile Archetype:
   - PROFILE_TIMESERIES: single timeline with periodic metrics.
   - PROFILE_PROJECT: task/project timeline with start/end dates, progress, duration.
   - PROFILE_SNAPSHOT: cross-sectional catalog / inventory / leaderboard snapshot.
2. Entity Dimension (primary item label) vs Grouping Dimensions (categories).
3. Primary & Secondary Metrics, Rate Metrics, and Duration Metrics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
import pandas as pd

from ingestion.classifier import (
    ROLE_DATE,
    ROLE_DIMENSION,
    ROLE_ID,
    ROLE_METRIC,
    ColumnClassification,
)
from analytics.kpis import select_primary_and_secondary_metrics, is_rate_metric

PROFILE_TIMESERIES = "timeseries"
PROFILE_PROJECT = "project"
PROFILE_SNAPSHOT = "snapshot"

DOMAIN_COMMERCE = "commerce"
DOMAIN_FINANCE = "finance"
DOMAIN_WORKFORCE = "workforce"
DOMAIN_FEEDBACK = "feedback"
DOMAIN_INVENTORY = "inventory"
DOMAIN_PROJECT = "project"
DOMAIN_TIMESERIES = "timeseries"
DOMAIN_SNAPSHOT = "snapshot"

_START_DATE_PATTERN = re.compile(r"(start|begin|open|create|launch)", re.I)
_END_DATE_PATTERN = re.compile(r"(end|due|finish|close|target|deadline|complete)", re.I)
_DURATION_PATTERN = re.compile(r"(day|days|duration|hour|hours|week|weeks|time_spent)", re.I)
_PROJECT_ENTITY_PATTERN = re.compile(r"(task|project|ticket|issue|milestone|feature|deliverable)", re.I)
_ITEM_ENTITY_PATTERN = re.compile(r"(product|item|sku|service|customer|client|employee|account|name|title)", re.I)

_COMMERCE_ORDER_PATTERN = re.compile(r"(order[_\s]?id|invoice|receipt|transaction)", re.I)
_COMMERCE_KEYWORD_PATTERN = re.compile(r"(cart|basket|checkout|discount|shipping|refund|customer[_\s]?id)", re.I)
_FINANCE_KEYWORD_PATTERN = re.compile(r"(budget|actual|variance|cogs|opex|ebitda|gross[_\s]?profit|operating[_\s]?income)", re.I)
_WORKFORCE_KEYWORD_PATTERN = re.compile(r"(salary|compensation|headcount|emp[_\s]?id|employee|hire[_\s]?date|tenure|attrition|turnover|job[_\s]?title)", re.I)
_FEEDBACK_KEYWORD_PATTERN = re.compile(r"(rating|score|nps|csat|satisfaction|stars|feedback|ticket[_\s]?id|resolution[_\s]?time)", re.I)
_INVENTORY_KEYWORD_PATTERN = re.compile(r"(stock|reorder|on[_\s]?hand|inventory|warehouse|sku|lead[_\s]?time|safety[_\s]?stock)", re.I)


@dataclass
class DatasetProfile:
    profile_type: str
    date_columns: list[str]
    primary_date_col: str | None
    end_date_col: str | None
    entity_dimension: str | None
    grouping_dimensions: list[str]
    all_dimensions: list[str]
    primary_metric: str | None
    secondary_metrics: list[str]
    rate_metrics: list[str]
    duration_metric: str | None
    has_progress: bool
    n_rows: int
    n_cols: int
    summary_label: str
    domain_type: str = DOMAIN_SNAPSHOT


def _detect_domain_type(
    df: pd.DataFrame,
    dim_cols: list[str],
    metric_cols: list[str],
    date_cols: list[str],
    profile_type: str,
) -> str:
    all_col_names = " ".join([str(c) for c in df.columns])

    # Check Project first
    if profile_type == PROFILE_PROJECT:
        return DOMAIN_PROJECT

    # Check Finance
    has_budget = any(re.search(r"\bbudget\b", c, re.I) for c in metric_cols)
    has_actual = any(re.search(r"\bactual\b", c, re.I) for c in metric_cols)
    has_variance = any(re.search(r"\bvariance\b", c, re.I) for c in metric_cols)
    if (has_budget and has_actual) or has_variance or len(re.findall(_FINANCE_KEYWORD_PATTERN, all_col_names)) >= 2:
        return DOMAIN_FINANCE

    # Check Commerce
    has_order = any(_COMMERCE_ORDER_PATTERN.search(c) for c in df.columns)
    has_commerce_kw = bool(_COMMERCE_KEYWORD_PATTERN.search(all_col_names))
    has_sales_qty = any(re.search(r"(sales|revenue|price|total)", c, re.I) for c in metric_cols) and any(re.search(r"(qty|quantity|units)", c, re.I) for c in metric_cols)
    if has_order or (has_commerce_kw and has_sales_qty):
        return DOMAIN_COMMERCE

    # Check Workforce
    has_salary = any(re.search(r"(salary|comp|compensation|base[_\s]?pay|wages)", c, re.I) for c in metric_cols)
    has_dept = any(re.search(r"(dept|department|division)", c, re.I) for c in dim_cols)
    has_emp = any(re.search(r"(emp|employee|staff)", c, re.I) for c in df.columns)
    if (has_salary and has_dept) or (has_emp and has_dept):
        return DOMAIN_WORKFORCE

    # Check Feedback / Survey
    has_rating = any(re.search(r"(rating|score|nps|csat|stars)", c, re.I) for c in metric_cols)
    has_feedback_kw = bool(_FEEDBACK_KEYWORD_PATTERN.search(all_col_names))
    if has_rating and has_feedback_kw:
        return DOMAIN_FEEDBACK

    # Check Inventory
    has_stock = any(re.search(r"(stock|inventory|on[_\s]?hand|reorder)", c, re.I) for c in metric_cols)
    if has_stock and any(_INVENTORY_KEYWORD_PATTERN.search(c) for c in df.columns):
        return DOMAIN_INVENTORY

    if profile_type == PROFILE_TIMESERIES:
        return DOMAIN_TIMESERIES

    return DOMAIN_SNAPSHOT


def profile_dataset(
    df: pd.DataFrame,
    classifications: dict[str, ColumnClassification] | list[ColumnClassification],
) -> DatasetProfile:
    """Analyze DataFrame shape, classified columns, and data distributions to
    derive a comprehensive DatasetProfile."""
    if isinstance(classifications, list):
        cmap = {c.name: c for c in classifications}
    else:
        cmap = dict(classifications)

    n_rows, n_cols = df.shape

    date_cols = [name for name, c in cmap.items() if c.role == ROLE_DATE and name in df.columns]
    metric_cols = [name for name, c in cmap.items() if c.role == ROLE_METRIC and name in df.columns]
    dim_cols = [name for name, c in cmap.items() if c.role == ROLE_DIMENSION and name in df.columns]

    rate_metrics = [
        m for m in metric_cols
        if getattr(cmap.get(m), "is_rate", False) or is_rate_metric(m)
    ]

    duration_metric = next((m for m in metric_cols if _DURATION_PATTERN.search(m)), None)

    # Check for start/end date pair
    start_date_col = next((d for d in date_cols if _START_DATE_PATTERN.search(d)), None)
    end_date_col = next((d for d in date_cols if _END_DATE_PATTERN.search(d)), None)

    if not start_date_col and len(date_cols) >= 2:
        start_date_col = date_cols[0]
        end_date_col = date_cols[1]
    elif not start_date_col and len(date_cols) == 1:
        start_date_col = date_cols[0]

    has_project_keywords = any(_PROJECT_ENTITY_PATTERN.search(d) for d in dim_cols)
    has_progress = any(re.search(r"(progress|completion|status|percent_complete)", m, re.I) for m in metric_cols + dim_cols)

    # Decide profile type
    if (len(date_cols) >= 2 or (start_date_col and (duration_metric or end_date_col))) and (has_project_keywords or has_progress):
        profile_type = PROFILE_PROJECT
    elif len(date_cols) >= 1:
        # Check if primary date column has continuous dates
        unique_dates = df[date_cols[0]].dropna().nunique()
        if unique_dates > 1:
            profile_type = PROFILE_TIMESERIES
        else:
            profile_type = PROFILE_SNAPSHOT
    else:
        profile_type = PROFILE_SNAPSHOT

    # Entity Dimension vs Grouping Dimensions
    entity_dimension = None
    grouping_dimensions = []

    if dim_cols:
        # Score dimensions to find the primary entity label
        # Entity labels usually match ITEM_ENTITY_PATTERN and have high cardinality
        ranked_dims = []
        for d in dim_cols:
            n_unq = df[d].dropna().nunique()
            score = n_unq
            if _ITEM_ENTITY_PATTERN.search(d) or _PROJECT_ENTITY_PATTERN.search(d):
                score += 1000
            ranked_dims.append((d, score, n_unq))

        ranked_dims.sort(key=lambda x: x[1], reverse=True)
        entity_dimension = ranked_dims[0][0]
        # Grouping dimensions are those with lower cardinality than the entity
        grouping_dimensions = [d for d in dim_cols if d != entity_dimension]

    # Primary and secondary metrics
    primary_metric, secondary_metrics = select_primary_and_secondary_metrics(df, metric_cols)
    if not primary_metric and metric_cols:
        primary_metric = metric_cols[0]
        secondary_metrics = metric_cols[1:4]

    domain_type = _detect_domain_type(df, dim_cols, metric_cols, date_cols, profile_type)

    # Summary label
    if domain_type == DOMAIN_PROJECT:
        summary_label = f"Project & Task Portfolio ({n_rows} tasks across {len(date_cols)} timeline milestones)"
    elif domain_type == DOMAIN_COMMERCE:
        summary_label = f"E-Commerce & Orders Analytics ({n_rows} orders/items across {len(metric_cols)} metrics)"
    elif domain_type == DOMAIN_FINANCE:
        summary_label = f"Financial & Budget Analytics ({n_rows} line items)"
    elif domain_type == DOMAIN_WORKFORCE:
        summary_label = f"HR & Workforce Analytics ({n_rows} employees across {len(grouping_dimensions)} departments)"
    elif domain_type == DOMAIN_FEEDBACK:
        summary_label = f"Survey & Feedback Analytics ({n_rows} responses)"
    elif domain_type == DOMAIN_INVENTORY:
        summary_label = f"Inventory & Logistics Snapshot ({n_rows} SKUs)"
    elif profile_type == PROFILE_SNAPSHOT:
        entity_desc = entity_dimension or "items"
        summary_label = f"Snapshot Analytics ({n_rows} {entity_desc} across {len(metric_cols)} metrics)"
    else:
        summary_label = f"Time-Series Performance ({n_rows} records over {date_cols[0]})"

    return DatasetProfile(
        profile_type=profile_type,
        date_columns=date_cols,
        primary_date_col=start_date_col if profile_type == PROFILE_PROJECT else (date_cols[0] if date_cols else None),
        end_date_col=end_date_col,
        entity_dimension=entity_dimension,
        grouping_dimensions=grouping_dimensions,
        all_dimensions=dim_cols,
        primary_metric=primary_metric,
        secondary_metrics=secondary_metrics,
        rate_metrics=rate_metrics,
        duration_metric=duration_metric,
        has_progress=has_progress,
        n_rows=n_rows,
        n_cols=n_cols,
        summary_label=summary_label,
        domain_type=domain_type,
    )

