"""
analytics/pipeline.py — Typed pipeline execution contract and modular builders.

Provides:
- PipelineResult: strongly typed dataclass with dict compatibility (__getitem__, get).
- build_snapshot_pipeline: snapshot data processing across entities.
- build_project_pipeline: task/gantt project analytics.
- build_timeseries_pipeline: temporal trend, KPIs, drivers, and risk signals.
- execute_pipeline / run_pipeline: end-to-end pipeline orchestrator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import streamlit as st

from analytics.anomalies import compute_risk_signals
from analytics.domains import (
    DOMAIN_COMMERCE,
    DOMAIN_FEEDBACK,
    DOMAIN_FINANCE,
    DOMAIN_WORKFORCE,
    compute_commerce_analytics,
    compute_feedback_analytics,
    compute_finance_analytics,
    compute_workforce_analytics,
)
from analytics.drivers import (
    rank_dimensions_by_explanatory_power,
)
from analytics.kpis import (
    compute_all_kpis,
    select_primary_and_secondary_metrics,
)
from analytics.profiler import (
    PROFILE_PROJECT,
    PROFILE_SNAPSHOT,
    DatasetProfile,
    profile_dataset,
)
from analytics.snapshot import (
    compute_project_analytics,
    compute_snapshot_analytics,
)
from analytics.stats import (
    compute_concentration_index,
    compute_correlation_matrix,
    extract_key_drivers,
    generate_executive_takeaways,
)
from analytics.trend import (
    build_trend_series,
    period_label,
    split_current_prior,
)
from ingestion.classifier import ROLE_DIMENSION, ROLE_METRIC
from insight.facts_builder import build_facts_packet


@dataclass
class PipelineResult:
    """Strongly typed pipeline output contract with backward-compatible dict access."""

    df: pd.DataFrame
    profile: DatasetProfile
    snapshot_res: Any | None = None
    project_res: Any | None = None
    commerce_res: Any | None = None
    finance_res: Any | None = None
    workforce_res: Any | None = None
    feedback_res: Any | None = None
    executive_takeaways: list[str] = field(default_factory=list)
    corr_drivers: list[Any] = field(default_factory=list)
    concentration: Any | None = None
    date_col: str | None = None
    metric_cols: list[str] = field(default_factory=list)
    dimension_cols: list[str] = field(default_factory=list)
    trend: Any | None = None
    kpis: dict[str, Any] = field(default_factory=dict)
    primary_metric: str | None = None
    all_dimension_drivers: list[Any] = field(default_factory=list)
    top_dimension_driver: Any | None = None
    risk_signals: list[Any] = field(default_factory=list)
    facts_packets: dict[str, Any] = field(default_factory=dict)
    period_label: str = "current vs prior period"

    # Dict-like compatibility interface
    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        return list(self.__dataclass_fields__.keys())

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def _columns_by_role(classifications: dict[str, Any], role: str) -> list[str]:
    return [c.name for c in classifications.values() if getattr(c, "role", None) == role]


def build_snapshot_pipeline(
    df: pd.DataFrame, profile: DatasetProfile
) -> tuple[Any, dict[str, Any], str | None, list[dict[str, Any]], str, dict[str, Any]]:
    """Compute snapshot analytics across entities."""
    metric_name = profile.primary_metric or ""
    snapshot_res = compute_snapshot_analytics(
        df=df,
        entity_col=profile.entity_dimension,
        primary_metric=metric_name,
        secondary_metrics=profile.secondary_metrics,
        grouping_cols=profile.grouping_dimensions,
        metric_aggs=profile.metric_aggregations,
    )
    kpis = snapshot_res.kpis
    primary_metric = profile.primary_metric
    risk_signals = [
        {
            "description": f"{o['item']}: {o['issue']} ({o['detail']})",
            "severity": o.get("severity", "medium"),
        }
        for o in snapshot_res.outliers
    ]
    label = "snapshot across entities"
    facts_packets = (
        {
            primary_metric: {
                "dataset_type": "snapshot",
                "total_items": snapshot_res.total_items,
                "entity_dimension": profile.entity_dimension,
                "primary_metric": profile.primary_metric,
                "pareto_text": snapshot_res.pareto_text,
            }
        }
        if primary_metric
        else {}
    )
    return snapshot_res, kpis, primary_metric, risk_signals, label, facts_packets


def build_project_pipeline(
    df: pd.DataFrame, profile: DatasetProfile
) -> tuple[Any, dict[str, Any], str, list[dict[str, Any]], str, dict[str, Any]]:
    """Compute portfolio task, timeline, and workload analytics."""
    assignee_col = next(
        (
            d
            for d in profile.grouping_dimensions
            if re.search(r"(assign|owner|person|member|resource)", d, re.I)
        ),
        (profile.grouping_dimensions[0] if profile.grouping_dimensions else None),
    )
    project_res = compute_project_analytics(
        df=df,
        task_col=profile.entity_dimension,
        project_col=profile.grouping_dimensions[0] if profile.grouping_dimensions else None,
        assignee_col=assignee_col,
        progress_col=profile.rate_metrics[0] if profile.rate_metrics else None,
        duration_col=profile.duration_metric,
        start_date_col=profile.primary_date_col,
        end_date_col=profile.end_date_col,
    )
    kpis = project_res.kpis
    primary_metric = "Completion Rate"
    risk_signals = [
        {
            "description": f"{t['task']} ({t.get('project', 'N/A')}): {t['reason']}",
            "severity": t.get("severity", "high"),
        }
        for t in project_res.at_risk_tasks
    ]
    label = "portfolio tasks"
    facts_packets = {
        "Completion Rate": {
            "dataset_type": "project",
            "total_tasks": project_res.total_tasks,
            "completed_tasks": project_res.completed_tasks,
            "completion_rate_pct": f"{project_res.completion_rate_pct:.1f}%",
        }
    }
    return project_res, kpis, primary_metric, risk_signals, label, facts_packets


def build_timeseries_pipeline(
    df: pd.DataFrame,
    profile: DatasetProfile,
    metric_cols: list[str],
    dimension_cols: list[str],
) -> tuple[
    Any | None,
    dict[str, Any],
    str | None,
    list[Any],
    Any | None,
    list[Any],
    str,
    dict[str, Any],
]:
    """Compute time-series trend, KPIs, drivers, and temporal anomalies."""
    date_col = profile.primary_date_col
    primary_metric, _ = select_primary_and_secondary_metrics(df, metric_cols)

    trend = None
    df_current, df_prior = df, None
    label = "current vs prior period"

    if date_col and primary_metric:
        trend = build_trend_series(
            df,
            date_col,
            primary_metric,
            agg=profile.metric_aggregations.get(primary_metric),
        )
        if trend is not None:
            df_current, df_prior = split_current_prior(df, date_col, trend)
            label = period_label(trend.granularity)

    kpis = compute_all_kpis(
        df_current, df_prior, metric_cols, metric_aggs=profile.metric_aggregations
    )
    if not primary_metric and kpis:
        primary_metric = next(iter(kpis), None)

    all_dimension_drivers: list[Any] = []
    top_dimension_driver = None
    if primary_metric and dimension_cols:
        all_dimension_drivers = rank_dimensions_by_explanatory_power(
            df_current,
            df_prior,
            dimension_cols,
            primary_metric,
            agg=profile.metric_aggregations.get(primary_metric),
        )
        top_dimension_driver = all_dimension_drivers[0] if all_dimension_drivers else None

    risk_signals = compute_risk_signals(
        df_current,
        df_prior,
        metric_cols,
        dimension_cols,
        full_df=df,
        date_col=date_col,
        metric_aggs=profile.metric_aggregations,
    )

    facts_packets: dict[str, Any] = {}
    for name, kpi in kpis.items():
        dim_driver = top_dimension_driver if name == primary_metric else None
        facts_packets[name] = build_facts_packet(
            kpi, dim_driver, risk_signals if name == primary_metric else None, label
        )

    return (
        trend,
        kpis,
        primary_metric,
        all_dimension_drivers,
        top_dimension_driver,
        risk_signals,
        label,
        facts_packets,
    )


def execute_pipeline(df: pd.DataFrame, classifications: dict[str, Any]) -> PipelineResult:
    """Execute analytics pipeline deterministically on a classified dataframe."""
    profile = profile_dataset(df, classifications)

    metric_cols = _columns_by_role(classifications, ROLE_METRIC)
    dimension_cols = _columns_by_role(classifications, ROLE_DIMENSION)

    snapshot_res = None
    project_res = None
    trend = None
    all_dimension_drivers: list[Any] = []
    top_dimension_driver = None

    if profile.profile_type == PROFILE_SNAPSHOT:
        (
            snapshot_res,
            kpis,
            primary_metric,
            risk_signals,
            label,
            facts_packets,
        ) = build_snapshot_pipeline(df, profile)
    elif profile.profile_type == PROFILE_PROJECT:
        (
            project_res,
            kpis,
            primary_metric,
            risk_signals,
            label,
            facts_packets,
        ) = build_project_pipeline(df, profile)
    else:
        (
            trend,
            kpis,
            primary_metric,
            all_dimension_drivers,
            top_dimension_driver,
            risk_signals,
            label,
            facts_packets,
        ) = build_timeseries_pipeline(df, profile, metric_cols, dimension_cols)

    # Compute domain-specific analytics
    commerce_res = None
    finance_res = None
    workforce_res = None
    feedback_res = None

    if profile.domain_type == DOMAIN_COMMERCE:
        commerce_res = compute_commerce_analytics(df)
    elif profile.domain_type == DOMAIN_FINANCE:
        finance_res = compute_finance_analytics(df)
    elif profile.domain_type == DOMAIN_WORKFORCE:
        workforce_res = compute_workforce_analytics(df)
    elif profile.domain_type == DOMAIN_FEEDBACK:
        feedback_res = compute_feedback_analytics(df)

    # Boardroom executive takeaways and correlation drivers
    corr_df = compute_correlation_matrix(df, metric_cols)
    corr_drivers = extract_key_drivers(corr_df, primary_metric=profile.primary_metric)
    conc = None
    if (
        profile.primary_metric
        and profile.primary_metric in df.columns
        and pd.api.types.is_numeric_dtype(df[profile.primary_metric])
    ):
        conc = compute_concentration_index(df[profile.primary_metric])
    executive_takeaways = generate_executive_takeaways(df, profile, corr_drivers, conc)

    return PipelineResult(
        df=df,
        profile=profile,
        snapshot_res=snapshot_res,
        project_res=project_res,
        commerce_res=commerce_res,
        finance_res=finance_res,
        workforce_res=workforce_res,
        feedback_res=feedback_res,
        executive_takeaways=executive_takeaways,
        corr_drivers=corr_drivers,
        concentration=conc,
        date_col=profile.primary_date_col,
        metric_cols=metric_cols,
        dimension_cols=dimension_cols,
        trend=trend,
        kpis=kpis,
        primary_metric=primary_metric,
        all_dimension_drivers=all_dimension_drivers,
        top_dimension_driver=top_dimension_driver,
        risk_signals=risk_signals,
        facts_packets=facts_packets,
        period_label=label,
    )


def run_pipeline(
    df: pd.DataFrame | None = None,
    classifications: dict[str, Any] | None = None,
) -> PipelineResult:
    """Streamlit entry point: runs ingestion-classified data through analytics once per session.

    Retrieves from session_state when arguments are omitted for backward compatibility.
    """
    if df is None:
        df = (
            st.session_state.get("dataset")
            if "dataset" in st.session_state
            else st.session_state.get("cleaned_df")
        )
    if classifications is None:
        classifications = st.session_state["classifications"]

    assert df is not None, "No dataset loaded in session state"
    assert classifications is not None, "No classifications found in session state"

    result = execute_pipeline(df, classifications)
    st.session_state["_cached_pipeline_result"] = result
    return result
