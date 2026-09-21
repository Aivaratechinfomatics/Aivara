"""
analytics/domains/feedback.py — Specialized survey, NPS, and customer support analytics.

Computes:
1. Net Promoter Score (NPS) and Promoter/Passive/Detractor distribution.
2. Customer Satisfaction (CSAT) score percentage.
3. Rating response distribution.
4. Support ticket resolution metrics and priority distribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
import pandas as pd


@dataclass
class FeedbackAnalyticsResult:
    total_responses: int
    nps_score: float | None
    csat_score: float | None
    promoter_pct: float | None
    passive_pct: float | None
    detractor_pct: float | None
    avg_rating: float
    avg_resolution_time: float | None
    rating_distribution: pd.DataFrame
    priority_breakdown: pd.DataFrame | None


def compute_feedback_analytics(
    df: pd.DataFrame,
    rating_col: str | None = None,
    ticket_col: str | None = None,
    resolution_col: str | None = None,
    priority_col: str | None = None,
) -> FeedbackAnalyticsResult:
    """Computes survey, NPS, and support ticket intelligence."""
    cols = df.columns
    if not rating_col:
        rating_col = next((c for c in cols if re.search(r"(rating|score|nps|csat|satisfaction|stars)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not ticket_col:
        ticket_col = next((c for c in cols if re.search(r"(ticket|case|incident|issue|inquiry)", c, re.I)), None)
    if not resolution_col:
        resolution_col = next((c for c in cols if re.search(r"(resolution|handling|duration|turnaround|time_to_close|sla)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not priority_col:
        priority_col = next((c for c in cols if re.search(r"(priority|severity|urgency|tier)", c, re.I)), None)

    n_rows = len(df)
    nps_score = None
    csat_score = None
    promoter_pct = None
    passive_pct = None
    detractor_pct = None
    avg_rating = 0.0
    dist_df = pd.DataFrame()

    if rating_col and pd.api.types.is_numeric_dtype(df[rating_col]):
        ratings = df[rating_col].dropna()
        if not ratings.empty:
            avg_rating = float(ratings.mean())
            max_r = ratings.max()
            min_r = ratings.min()

            # NPS logic: 0 to 10 scale
            if max_r <= 10 and min_r >= 0 and max_r > 5:
                promoters = (ratings >= 9).sum()
                passives = ((ratings >= 7) & (ratings <= 8)).sum()
                detractors = (ratings <= 6).sum()
                total = len(ratings)
                promoter_pct = round((promoters / total) * 100.0, 1)
                passive_pct = round((passives / total) * 100.0, 1)
                detractor_pct = round((detractors / total) * 100.0, 1)
                nps_score = round(promoter_pct - detractor_pct, 1)
                # CSAT on 10 scale (>= 8 is satisfied)
                csat_score = round(((ratings >= 8).sum() / total) * 100.0, 1)
            else:
                # 1 to 5 scale
                total = len(ratings)
                csat_score = round(((ratings >= 4).sum() / total) * 100.0, 1)

            # Rating distribution
            dist_counts = ratings.value_counts().sort_index().reset_index()
            dist_counts.columns = ["Rating", "Count"]
            dist_counts["Share_Pct"] = (dist_counts["Count"] / len(ratings)) * 100.0
            dist_df = dist_counts

    # Support ticket metrics
    avg_resolution = None
    if resolution_col and pd.api.types.is_numeric_dtype(df[resolution_col]):
        avg_resolution = round(float(df[resolution_col].dropna().mean()), 2)

    priority_df = None
    if priority_col:
        p_counts = df[priority_col].value_counts().reset_index()
        p_counts.columns = ["Priority", "Count"]
        p_counts["Share_Pct"] = (p_counts["Count"] / n_rows) * 100.0
        priority_df = p_counts

    return FeedbackAnalyticsResult(
        total_responses=n_rows,
        nps_score=nps_score,
        csat_score=csat_score,
        promoter_pct=promoter_pct,
        passive_pct=passive_pct,
        detractor_pct=detractor_pct,
        avg_rating=round(avg_rating, 2),
        avg_resolution_time=avg_resolution,
        rating_distribution=dist_df,
        priority_breakdown=priority_df,
    )
