"""
ui/tabs.py — Table-driven tab registry and dispatcher.

Replaces duplicated multi-branch tab logic in app.py with a declarative
TabSpec table per profile/domain, wrapped in error boundaries.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import streamlit as st

from analytics.domains import (
    DOMAIN_COMMERCE,
    DOMAIN_FEEDBACK,
    DOMAIN_FINANCE,
    DOMAIN_WORKFORCE,
)
from analytics.profiler import PROFILE_PROJECT, PROFILE_SNAPSHOT
from ui.chart_builder import render_chart_explorer
from ui.domain_views import (
    render_commerce_view,
    render_feedback_view,
    render_finance_view,
    render_workforce_view,
)
from ui.drivers_view import render_drivers_view
from ui.error_boundary import render_tab_boundary
from ui.executive_view import render_executive_view
from ui.project_view import (
    render_project_at_risk_view,
    render_project_gantt_view,
    render_project_overview_view,
    render_project_team_view,
)
from ui.revenue_view import render_primary_metric_view
from ui.risk_view import render_risk_view
from ui.snapshot_view import (
    render_snapshot_breakdown_view,
    render_snapshot_composition_view,
    render_snapshot_executive_view,
    render_snapshot_outliers_view,
)
from ui.stats_view import render_stats_view


@dataclass(frozen=True)
class TabSpec:
    """Declarative specification for a dashboard tab."""

    key: str
    label: str
    render_fn: Callable[[Any, str, bool], None]


# ---------------------------------------------------------------------------
# Individual Tab Render Wrappers
# ---------------------------------------------------------------------------


def _render_executive_tab(res: Any, model: str, allow_paid: bool) -> None:
    profile = res.get("profile")
    if profile and profile.profile_type == PROFILE_SNAPSHOT:
        render_snapshot_executive_view(
            res["df"],
            res["snapshot_res"],
            profile,
            model,
            allow_paid=allow_paid,
        )
    else:
        render_executive_view(res, model, allow_paid=allow_paid)


def _render_stats_tab(res: Any, _model: str, _allow_paid: bool) -> None:
    render_stats_view(res["df"], res["profile"])


def _render_charts_tab(res: Any, _model: str, _allow_paid: bool) -> None:
    render_chart_explorer(res["df"])


def _render_risk_or_outliers_tab(res: Any, _model: str, _allow_paid: bool) -> None:
    profile = res.get("profile")
    if profile and profile.profile_type == PROFILE_SNAPSHOT:
        render_snapshot_outliers_view(res["snapshot_res"])
    else:
        render_risk_view(res)


def _render_customers_tab(res: Any, _model: str, _allow_paid: bool) -> None:
    st.header("Customers")
    st.caption("Customer-shaped dimension breakdowns appear here when detected.")
    customer_drivers = [
        d
        for d in res.get("all_dimension_drivers", [])
        if re.search(r"(customer|client|account|user|buyer|consumer|segment)", d.dimension, re.I)
    ]
    if customer_drivers:
        base_dict = res.to_dict() if hasattr(res, "to_dict") else dict(res)
        cust_res = {**base_dict, "all_dimension_drivers": customer_drivers}
        render_drivers_view(cust_res, key_prefix="customers")
    else:
        st.info(
            "No customer-shaped dimension columns (e.g. customer, client, account, user) were detected in this dataset."
        )


# ---------------------------------------------------------------------------
# Tab Spec Registry Builders
# ---------------------------------------------------------------------------


def get_tab_specs(pipeline_result: Any) -> list[TabSpec]:
    """Return declarative list of TabSpecs appropriate for the dataset profile."""
    profile = pipeline_result.get("profile")
    if not profile:
        return []

    # 1. Commerce Domain
    if profile.domain_type == DOMAIN_COMMERCE and pipeline_result.get("commerce_res"):
        return [
            TabSpec("exec", "Executive Summary", _render_executive_tab),
            TabSpec(
                "commerce",
                "Orders & Customers",
                lambda res, m, ap: render_commerce_view(res["df"], res["commerce_res"], profile),
            ),
            TabSpec("stats", "Correlations & Drivers", _render_stats_tab),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec("risk", "Risk & Outliers", _render_risk_or_outliers_tab),
        ]

    # 2. Finance Domain
    if profile.domain_type == DOMAIN_FINANCE and pipeline_result.get("finance_res"):
        return [
            TabSpec("exec", "Executive Summary", _render_executive_tab),
            TabSpec(
                "finance",
                "P&L & Budget Variance",
                lambda res, m, ap: render_finance_view(res["df"], res["finance_res"], profile),
            ),
            TabSpec("stats", "Correlations & Drivers", _render_stats_tab),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec("risk", "Risk & Outliers", _render_risk_or_outliers_tab),
        ]

    # 3. Workforce Domain
    if profile.domain_type == DOMAIN_WORKFORCE and pipeline_result.get("workforce_res"):
        return [
            TabSpec("exec", "Executive Summary", _render_executive_tab),
            TabSpec(
                "workforce",
                "Workforce & Compensation",
                lambda res, m, ap: render_workforce_view(res["df"], res["workforce_res"], profile),
            ),
            TabSpec("stats", "Correlations & Drivers", _render_stats_tab),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec("risk", "Risk & Outliers", _render_risk_or_outliers_tab),
        ]

    # 4. Feedback Domain
    if profile.domain_type == DOMAIN_FEEDBACK and pipeline_result.get("feedback_res"):
        return [
            TabSpec("exec", "Executive Summary", _render_executive_tab),
            TabSpec(
                "feedback",
                "Survey, NPS & Support",
                lambda res, m, ap: render_feedback_view(res["df"], res["feedback_res"], profile),
            ),
            TabSpec("stats", "Correlations & Drivers", _render_stats_tab),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec("risk", "Risk & Outliers", _render_risk_or_outliers_tab),
        ]

    # 5. Project Profile
    if profile.profile_type == PROFILE_PROJECT and pipeline_result.get("project_res"):
        return [
            TabSpec(
                "proj_overview",
                "Portfolio Overview",
                lambda res, m, ap: render_project_overview_view(
                    res["df"], res["project_res"], profile, m, allow_paid=ap
                ),
            ),
            TabSpec(
                "proj_gantt",
                "Timeline (Gantt)",
                lambda res, m, ap: render_project_gantt_view(
                    res["df"], res["project_res"], profile
                ),
            ),
            TabSpec(
                "proj_team",
                "Team & Workload",
                lambda res, m, ap: render_project_team_view(res["df"], res["project_res"], profile),
            ),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec(
                "proj_risk",
                "At-Risk Tasks",
                lambda res, m, ap: render_project_at_risk_view(res["project_res"]),
            ),
        ]

    # 6. Snapshot Profile
    if profile.profile_type == PROFILE_SNAPSHOT and pipeline_result.get("snapshot_res"):
        return [
            TabSpec("exec", "Executive Summary", _render_executive_tab),
            TabSpec(
                "snap_breakdown",
                "Rankings & Breakdown",
                lambda res, m, ap: render_snapshot_breakdown_view(
                    res["df"], res["snapshot_res"], profile
                ),
            ),
            TabSpec(
                "snap_comp",
                "Composition",
                lambda res, m, ap: render_snapshot_composition_view(
                    res["df"], res["snapshot_res"], profile
                ),
            ),
            TabSpec("stats", "Correlations & Drivers", _render_stats_tab),
            TabSpec("charts", "Charts", _render_charts_tab),
            TabSpec("risk", "Risk & Outliers", _render_risk_or_outliers_tab),
        ]

    # 7. Standard Time Series (Forecast tab removed for v1.0 per Decision D3)
    return [
        TabSpec(
            "exec",
            "Executive",
            lambda res, m, ap: render_executive_view(res, m, allow_paid=ap),
        ),
        TabSpec(
            "revenue",
            "Revenue",
            lambda res, m, ap: render_primary_metric_view(res, m, allow_paid=ap),
        ),
        TabSpec(
            "ops",
            "Operations",
            lambda res, m, ap: render_drivers_view(res, key_prefix="operations"),
        ),
        TabSpec("customers", "Customers", _render_customers_tab),
        TabSpec("charts", "Charts", _render_charts_tab),
        TabSpec("risk", "Risk", lambda res, m, ap: render_risk_view(res)),
    ]


def render_tab_registry(pipeline_result: Any, model: str, allow_paid: bool) -> None:
    """Render table-driven tabs wrapped in error boundaries."""
    specs = get_tab_specs(pipeline_result)
    if not specs:
        st.info("No views available for this dataset profile.")
        return

    tab_elements = st.tabs([s.label for s in specs])
    for tab_ui, spec in zip(tab_elements, specs, strict=False):
        with tab_ui:
            render_tab_boundary(spec.label, spec.render_fn, pipeline_result, model, allow_paid)
