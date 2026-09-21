"""
ui/stats_view.py — Interactive statistical discovery and correlation dashboard.

Renders:
1. Interactive correlation heatmap across all numeric metrics.
2. Top discovered driver cards (positive and inverse correlations).
3. Portfolio concentration analysis (Gini, HHI, Top 20% share).
4. Statistical outlier root-cause attribution.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.stats import (
    compute_correlation_matrix,
    extract_key_drivers,
    compute_concentration_index,
    attribute_anomalies,
)
from ui.components import humanize_col, format_number


def render_stats_view(df: pd.DataFrame, profile) -> None:
    """Renders the autonomous statistical discovery view."""
    st.header("Statistical Discovery & Key Drivers")
    st.caption(
        "Autonomous statistical analysis calculated 100% locally. "
        "Uncovers metric correlations, portfolio concentration risks, and outlier drivers."
    )

    metric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "_is_duplicate"]
    dim_cols = getattr(profile, "all_dimensions", [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])])

    if len(metric_cols) < 2:
        st.info("At least 2 numeric metrics are required to compute correlation matrices and driver relationships.")
        return

    corr_df = compute_correlation_matrix(df, metric_cols)
    drivers = extract_key_drivers(corr_df, primary_metric=profile.primary_metric)

    # --- Section 1: Discovered Drivers Callouts ------------------------------
    st.subheader("Discovered Driver Relationships")
    if drivers:
        d_cols = st.columns(min(3, len(drivers)))
        for idx, driver in enumerate(drivers[:3]):
            with d_cols[idx % len(d_cols)]:
                badge = "🟢 Positive Driver" if "positive" in driver.strength else "🔴 Inverse Driver"
                st.markdown(
                    f"""
                    <div style="background-color: rgba(26,115,232,0.05); padding: 14px; border-radius: 8px; border-left: 4px solid {'#1a73e8' if 'positive' in driver.strength else '#ea4335'}; margin-bottom: 12px;">
                        <span style="font-size: 11px; font-weight: bold; text-transform: uppercase; color: #5f6368;">{badge}</span>
                        <div style="font-size: 18px; font-weight: bold; margin: 4px 0;">r = {driver.correlation:+.2f}</div>
                        <div style="font-size: 13px; color: #3c4043;">{driver.narrative}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No strong metric correlations (|r| >= 0.45) detected in this dataset.")

    # --- Section 2: Interactive Correlation Matrix ---------------------------
    st.subheader("Metric Correlation Matrix")
    h_labels = [humanize_col(c) for c in corr_df.columns]
    fig_corr = go.Figure(
        go.Heatmap(
            z=corr_df.values,
            x=h_labels,
            y=h_labels,
            colorscale="RdBu",
            zmid=0,
            text=[[f"{v:.2f}" for v in row] for row in corr_df.values],
            texttemplate="%{text}",
            showscale=True,
        )
    )
    fig_corr.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=60, r=20, t=40, b=60),
    )
    st.plotly_chart(fig_corr, width="stretch", key="stats_corr_heatmap")

    # Cache for PPTX export
    if "_export_figures" not in st.session_state:
        st.session_state["_export_figures"] = {}
    st.session_state["_export_figures"]["Stats_correlation"] = fig_corr

    st.divider()

    # --- Section 3: Concentration Risk & Outlier Attribution -----------------
    st.subheader("Portfolio Concentration & Outlier Root Causes")
    c1, c2 = st.columns(2)

    primary_m = profile.primary_metric
    if primary_m and primary_m in df.columns and pd.api.types.is_numeric_dtype(df[primary_m]):
        conc = compute_concentration_index(df[primary_m])
        with c1:
            st.markdown(f"**Concentration Risk: {humanize_col(primary_m)}**")
            k1, k2 = st.columns(2)
            k1.metric("Gini Coefficient", f"{conc.gini:.2f}", help="0 = completely even, 1 = extreme concentration")
            k2.metric("Top 20% Share", f"{conc.top_20_pct_share:.1%}", help="Share of total metric held by top 20% entries")
            st.caption(conc.narrative)

        with c2:
            st.markdown(f"**Outlier Root-Cause Attribution: {humanize_col(primary_m)}**")
            attributions = attribute_anomalies(df, metric_col=primary_m, dimension_cols=dim_cols)
            if attributions:
                for att in attributions[:3]:
                    st.warning(
                        f"**{att.outlier_count} outlier records detected.** Category **'{att.top_driver_category}'** "
                        f"(in `{humanize_col(att.top_driver_dimension or '')}`) accounts for **{att.category_share_of_outliers:.0%}** of all extreme values."
                    )
            else:
                st.success("No anomalous category clusters or extreme distribution skew detected.")
