"""
export/deck_assembly.py — Pure, testable PPTX deck inputs assembly.

Separates view and figure mapping from Streamlit sidebar UI components,
enabling headless unit testing of presentation assembly logic.
"""

from __future__ import annotations

import math
from typing import Any

from analytics.profiler import PROFILE_PROJECT, PROFILE_SNAPSHOT
from export.pptx_builder import DeckInputs, KPITileData, ViewExportData
from ui.components import format_number, format_pct_change


def assemble_deck_inputs(
    pipeline_result: Any,
    dataset_name: str = "dataset.csv",
    figures: dict[str, Any] | None = None,
) -> DeckInputs:
    """Assembles pure DeckInputs from PipelineResult and cached UI figures."""
    if figures is None:
        figures = {}

    kpis = pipeline_result.get("kpis", {})
    profile = pipeline_result.get("profile")

    exec_tiles = [
        KPITileData(
            label=name.replace("_", " ").title(),
            value_display=format_number(k.current_value, k.unit),
            delta_display=format_pct_change(k.pct_change, with_sign=True),
            delta_positive=(
                k.pct_change is not None and not math.isinf(k.pct_change) and k.pct_change >= 0
            ),
        )
        for name, k in kpis.items()
    ]

    drivers_table = None
    top_driver = pipeline_result.get("top_dimension_driver")
    if top_driver is not None:
        drivers_table = [
            {"category": c.category, "contribution_pct": c.contribution_pct}
            for c in (top_driver.top_positive + top_driver.top_negative)
        ]

    if profile and profile.profile_type == PROFILE_SNAPSHOT:
        views = [
            ViewExportData(
                view_name="Executive Summary",
                kpi_tiles=exec_tiles[:4],
                trend_figure=figures.get("Executive_trend"),
            ),
        ]
        if figures.get("Snapshot_breakdown") is not None:
            views.append(
                ViewExportData(
                    view_name="Rankings & Breakdown",
                    kpi_tiles=[],
                    trend_figure=figures.get("Snapshot_breakdown"),
                )
            )
        if figures.get("Snapshot_composition") is not None:
            views.append(
                ViewExportData(
                    view_name="Composition Distribution",
                    kpi_tiles=[],
                    trend_figure=figures.get("Snapshot_composition"),
                )
            )

    elif profile and profile.profile_type == PROFILE_PROJECT:
        views = [
            ViewExportData(
                view_name="Portfolio Overview",
                kpi_tiles=exec_tiles[:4],
                trend_figure=figures.get("Project_status"),
            ),
        ]
        if figures.get("Project_gantt") is not None:
            views.append(
                ViewExportData(
                    view_name="Timeline & Milestones",
                    kpi_tiles=[],
                    trend_figure=figures.get("Project_gantt"),
                )
            )
        if figures.get("Project_workload") is not None:
            views.append(
                ViewExportData(
                    view_name="Team Workload Distribution",
                    kpi_tiles=[],
                    trend_figure=figures.get("Project_workload"),
                )
            )

    else:
        primary_name = pipeline_result.get("primary_metric", "Revenue")
        views = [
            ViewExportData(
                view_name="Executive",
                kpi_tiles=exec_tiles[:4],
                trend_figure=figures.get("Executive_trend"),
            ),
            ViewExportData(
                view_name=primary_name.replace("_", " ").title()
                if primary_name
                else "Primary Metric",
                kpi_tiles=exec_tiles[:1],
                trend_figure=figures.get("Revenue_trend"),
                drivers_table=drivers_table,
                drivers_figure=figures.get("Revenue_drivers"),
            ),
        ]

    # Domain-specific slides
    if figures.get("Commerce_products") is not None:
        views.append(
            ViewExportData(
                view_name="Product Sales Performance",
                kpi_tiles=[],
                trend_figure=figures.get("Commerce_products"),
            )
        )
    if figures.get("Finance_waterfall") is not None:
        views.append(
            ViewExportData(
                view_name="Budget Variance Waterfall",
                kpi_tiles=[],
                trend_figure=figures.get("Finance_waterfall"),
            )
        )
    if figures.get("Workforce_headcount") is not None:
        views.append(
            ViewExportData(
                view_name="Staffing Distribution",
                kpi_tiles=[],
                trend_figure=figures.get("Workforce_headcount"),
            )
        )
    if figures.get("Feedback_nps") is not None:
        views.append(
            ViewExportData(
                view_name="NPS & Sentiment Distribution",
                kpi_tiles=[],
                trend_figure=figures.get("Feedback_nps"),
            )
        )
    if figures.get("Stats_correlation") is not None:
        views.append(
            ViewExportData(
                view_name="Metric Correlation Matrix",
                kpi_tiles=[],
                trend_figure=figures.get("Stats_correlation"),
            )
        )

    # Risk signals
    raw_risks = list(pipeline_result.get("risk_signals", []))
    if pipeline_result.get("concentration") and getattr(
        pipeline_result["concentration"], "risk_level", ""
    ) in ("High", "Extreme"):
        raw_risks.append(
            {
                "description": pipeline_result["concentration"].narrative,
                "severity": "high",
            }
        )

    risk_dicts = [
        {"description": s["description"], "severity": s.get("severity", "medium")}
        if isinstance(s, dict)
        else {
            "description": getattr(s, "description", str(s)),
            "severity": getattr(s, "severity", "medium"),
        }
        for s in raw_risks
    ]

    period_covered = pipeline_result.get("period_label", "n/a")
    return DeckInputs(
        dataset_name=dataset_name,
        period_covered=period_covered,
        views=views,
        risk_signals=risk_dicts,
    )
