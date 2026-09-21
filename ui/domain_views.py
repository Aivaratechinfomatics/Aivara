"""
ui/domain_views.py — Specialized interactive dashboards for business domains.

Provides tailored dashboards for:
1. E-Commerce & Orders (`render_commerce_view`)
2. Financial & Budget Waterfall (`render_finance_view`)
3. HR & Workforce Analytics (`render_workforce_view`)
4. Survey, NPS & Support Analytics (`render_feedback_view`)
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics.domains.commerce import CommerceAnalyticsResult
from analytics.domains.finance import FinanceAnalyticsResult
from analytics.domains.workforce import WorkforceAnalyticsResult
from analytics.domains.feedback import FeedbackAnalyticsResult
from ui.components import format_number, humanize_col


def render_commerce_view(df: pd.DataFrame, res: CommerceAnalyticsResult, profile) -> None:
    """Renders E-Commerce & Retail Dashboard."""
    st.header("Orders & Customers Analytics")
    st.caption("Transaction patterns, customer behavior, and basket intelligence.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"${res.total_revenue:,.0f}")
    k2.metric("Total Orders", f"{res.total_orders:,}")
    k3.metric("Average Order Value (AOV)", f"${res.aov:,.2f}")
    k4.metric("Basket Size", f"{res.basket_size:.1f} units")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Selling Products")
        if not res.top_products_table.empty:
            p_col = res.top_products_table.columns[0]
            val_col = res.top_products_table.columns[1]
            fig_p = px.bar(
                res.top_products_table.head(10).sort_values(by=val_col, ascending=True),
                x=val_col,
                y=p_col,
                orientation="h",
                labels={val_col: humanize_col(val_col), p_col: humanize_col(p_col)},
                title="Top 10 Products by Revenue",
            )
            fig_p.update_layout(template="plotly_white", height=380, margin=dict(l=40, r=20, t=40, b=40))
            st.plotly_chart(fig_p, width="stretch", key="comm_top_prod")
            if "_export_figures" not in st.session_state:
                st.session_state["_export_figures"] = {}
            st.session_state["_export_figures"]["Commerce_products"] = fig_p
        else:
            st.info("Product breakdown table not available.")

    with c2:
        st.subheader("Customer Intelligence")
        m1, m2 = st.columns(2)
        m1.metric("Unique Customers", f"{res.unique_customers:,}")
        m2.metric("Repeat Customer Rate", f"{res.repeat_customer_rate:.1%}")
        if not res.customer_spend_table.empty:
            st.caption("Top Customer Spend Breakdown")
            st.dataframe(res.customer_spend_table.head(10), use_container_width=True)
        else:
            st.info("Customer identifier columns not present.")

    if res.channel_breakdown_table is not None and not res.channel_breakdown_table.empty:
        st.subheader("Sales Channel Performance")
        st.dataframe(res.channel_breakdown_table, use_container_width=True)


def render_finance_view(df: pd.DataFrame, res: FinanceAnalyticsResult, profile) -> None:
    """Renders Financial P&L and Budget Waterfall Dashboard."""
    st.header("Financial Performance & Budget Variance")
    st.caption("Budget vs. actual tracking and bridge waterfall walk.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Actual", f"${res.total_actual:,.0f}")
    k2.metric("Total Budget", f"${res.total_budget:,.0f}")
    var_sign = "+" if res.variance_abs >= 0 else ""
    k3.metric("Variance ($)", f"{var_sign}${res.variance_abs:,.0f}", delta=f"{res.variance_pct:+.1f}%")
    k4.metric("Status", "Favorable" if res.is_favorable else "Unfavorable")

    st.subheader("Bridge Waterfall Walk")
    if res.waterfall_steps:
        fig_wf = go.Figure(
            go.Waterfall(
                name="Budget Bridge",
                orientation="v",
                measure=[s.measure for s in res.waterfall_steps],
                x=[s.label for s in res.waterfall_steps],
                textposition="outside",
                text=[f"${s.amount:,.0f}" for s in res.waterfall_steps],
                y=[s.amount for s in res.waterfall_steps],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            )
        )
        fig_wf.update_layout(
            template="plotly_white",
            height=420,
            margin=dict(l=50, r=20, t=40, b=50),
        )
        st.plotly_chart(fig_wf, width="stretch", key="fin_waterfall")
        if "_export_figures" not in st.session_state:
            st.session_state["_export_figures"] = {}
        st.session_state["_export_figures"]["Finance_waterfall"] = fig_wf

    if not res.line_item_table.empty:
        st.subheader("Line Item Breakdown Table")
        st.dataframe(res.line_item_table, use_container_width=True)


def render_workforce_view(df: pd.DataFrame, res: WorkforceAnalyticsResult, profile) -> None:
    """Renders HR & People Analytics Dashboard."""
    st.header("Workforce & People Analytics")
    st.caption("Staffing headcount, department compensation, and workforce retention.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Headcount", f"{res.headcount:,}")
    k2.metric("Departments", f"{res.departments_count}")
    k3.metric("Median Salary", f"${res.median_salary:,.0f}")
    if res.turnover_rate is not None:
        k4.metric("Turnover / Attrition", f"{res.turnover_rate:.1%}")
    else:
        k4.metric("Salary IQR Spread", f"${res.salary_iqr:,.0f}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Headcount by Department")
        if not res.department_summary.empty:
            dept_col = res.department_summary.columns[0]
            fig_dept = px.pie(
                res.department_summary,
                names=dept_col,
                values="headcount",
                hole=0.4,
                title="Staff Distribution by Department",
            )
            fig_dept.update_layout(template="plotly_white", height=380, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_dept, width="stretch", key="wf_dept_pie")
            if "_export_figures" not in st.session_state:
                st.session_state["_export_figures"] = {}
            st.session_state["_export_figures"]["Workforce_headcount"] = fig_dept

    with c2:
        st.subheader("Department Compensation Overview")
        if not res.salary_by_dept_table.empty:
            st.dataframe(res.salary_by_dept_table, use_container_width=True)
            if res.tenure_perf_corr is not None:
                st.caption(f"📈 Tenure vs Performance Rating correlation: **r = {res.tenure_perf_corr:+.2f}**")
        else:
            st.info("Salary details by department not available.")


def render_feedback_view(df: pd.DataFrame, res: FeedbackAnalyticsResult, profile) -> None:
    """Renders Survey, NPS, and Customer Support Dashboard."""
    st.header("Survey, NPS & Support Analytics")
    st.caption("Customer satisfaction, Net Promoter Score distribution, and sentiment indicators.")

    k1, k2, k3, k4 = st.columns(4)
    if res.nps_score is not None:
        k1.metric("Net Promoter Score (NPS)", f"{res.nps_score:+.0f}", help="Scale -100 to +100")
    else:
        k1.metric("Average Rating", f"{res.avg_rating:.2f}")

    if res.csat_score is not None:
        k2.metric("CSAT %", f"{res.csat_score:.1f}%")
    else:
        k2.metric("Total Responses", f"{res.total_responses:,}")

    k3.metric("Total Responses", f"{res.total_responses:,}")
    if res.avg_resolution_time is not None:
        k4.metric("Avg Resolution Time", f"{res.avg_resolution_time:.1f} hrs")
    elif res.promoter_pct is not None:
        k4.metric("Promoters", f"{res.promoter_pct:.0f}%")
    else:
        k4.metric("Average Rating", f"{res.avg_rating:.2f}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("NPS / Sentiment Breakdown")
        if res.promoter_pct is not None:
            nps_breakdown = pd.DataFrame({
                "Group": ["Promoters (9-10)", "Passives (7-8)", "Detractors (0-6)"],
                "Share": [res.promoter_pct, res.passive_pct, res.detractor_pct],
            })
            fig_nps = px.bar(
                nps_breakdown,
                x="Group",
                y="Share",
                color="Group",
                color_discrete_map={
                    "Promoters (9-10)": "#34a853",
                    "Passives (7-8)": "#fbbc04",
                    "Detractors (0-6)": "#ea4335",
                },
                title="Promoter vs Detractor Share (%)",
            )
            fig_nps.update_layout(template="plotly_white", height=380, margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
            st.plotly_chart(fig_nps, width="stretch", key="fb_nps_bar")
            if "_export_figures" not in st.session_state:
                st.session_state["_export_figures"] = {}
            st.session_state["_export_figures"]["Feedback_nps"] = fig_nps
        else:
            st.info("NPS score calculation requires a 0-10 rating column.")

    with c2:
        st.subheader("Rating Response Distribution")
        if not res.rating_distribution.empty:
            fig_dist = px.bar(
                res.rating_distribution,
                x="Rating",
                y="Count",
                title="Response Frequency by Rating",
            )
            fig_dist.update_layout(template="plotly_white", height=380, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_dist, width="stretch", key="fb_dist_bar")
        if res.priority_breakdown is not None:
            st.caption("Ticket Priority Breakdown")
            st.dataframe(res.priority_breakdown, use_container_width=True)
