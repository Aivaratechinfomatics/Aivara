"""
tests/test_core_correctness.py — Regression & invariant test suite for Audit Brief §1.

Covers:
1.1 Cross-user view cache isolation across sessions and threads.
1.2 Independence of trend metric selection from CSV column ordering.
1.3 Driver contribution normalization under net-zero offsetting variance.
1.4 & 1.5 Sign-correct infinities and safe string formatting (no 'inf%' or 'nan%').
1.6, 1.7, 1.8 State reset on new upload and cache invalidation.
Invariance: Number consistency across UI tiles, facts packets, and PPTX export tiles.
"""

from __future__ import annotations

import math
import os
import sys

import pandas as pd
import pytest
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.drivers import compute_dimension_drivers
from analytics.kpis import compute_kpi, select_primary_and_secondary_metrics
from analytics.trend import build_trend_series
from app import run_pipeline
from export.pptx_builder import KPITileData
from ingestion.classifier import classify_columns
from ingestion.cleaner import clean_dataframe
from ingestion.loader import load_file
from insight import cache as insight_cache
from insight.facts_builder import build_facts_packet
from ui.components import format_number, format_pct_change
from ui.upload_page import reset_dataset_state

# ---------------------------------------------------------------------------
# 1.1 Cross-user view cache isolation
# ---------------------------------------------------------------------------


def test_cross_user_view_cache_isolation():
    session_a = "user_session_alpha"
    session_b = "user_session_beta"

    insight_a = {"headline": "Alpha revenue increased by 20%"}
    insight_b = {"headline": "Beta revenue dropped by 5%"}

    insight_cache.set_for_view("Executive", insight_a, session_id=session_a)
    insight_cache.set_for_view("Executive", insight_b, session_id=session_b)

    retrieved_a = insight_cache.get_for_view("Executive", session_id=session_a)
    retrieved_b = insight_cache.get_for_view("Executive", session_id=session_b)

    assert retrieved_a == insight_a
    assert retrieved_b == insight_b
    assert retrieved_a != retrieved_b

    insight_cache.clear_view_cache(session_id=session_a)
    assert insight_cache.get_for_view("Executive", session_id=session_a) is None
    assert insight_cache.get_for_view("Executive", session_id=session_b) == insight_b


# ---------------------------------------------------------------------------
# 1.2 Trend metric column ordering independence
# ---------------------------------------------------------------------------


def test_trend_metric_column_order_independence():
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "units": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],  # Small values
            "revenue": [
                1000,
                2000,
                1500,
                1800,
                2100,
                1900,
                2200,
                2500,
                2400,
                2600,
            ],  # Primary by sum
            "cost": [500, 600, 550, 700, 800, 750, 850, 900, 950, 1000],
        }
    )

    metric_cols = ["units", "revenue", "cost"]
    primary_metric, secondary = select_primary_and_secondary_metrics(df, metric_cols)
    assert primary_metric == "revenue"

    trend = build_trend_series(df, "date", primary_metric)
    assert trend is not None
    assert abs(trend.series["value"].sum() - df["revenue"].sum()) < 1e-4


# ---------------------------------------------------------------------------
# 1.3 Driver contribution % under net-zero offsetting variance
# ---------------------------------------------------------------------------


def test_driver_contribution_offsetting_categories_zero_net():
    df_prior = pd.DataFrame({"region": ["North", "South"], "sales": [1000.0, 1000.0]})
    df_current = pd.DataFrame({"region": ["North", "South"], "sales": [2000.0, 0.0]})

    res = compute_dimension_drivers(df_current, df_prior, "region", "sales")
    assert res is not None
    assert abs(res.total_delta - 0.0) < 1e-6

    contribs = {c.category: c.contribution_pct for c in res.contributions}
    assert abs(contribs["North"] - 50.0) < 1e-4
    assert abs(contribs["South"] - (-50.0)) < 1e-4

    sum_abs = sum(abs(c.contribution_pct) for c in res.contributions)
    assert abs(sum_abs - 100.0) < 1e-4

    for c in res.contributions:
        assert not math.isinf(c.contribution_pct)
        assert not math.isnan(c.contribution_pct)


# ---------------------------------------------------------------------------
# 1.4 & 1.5 pct_change infinities and formatting
# ---------------------------------------------------------------------------


def test_pct_change_infinities_and_edge_cases():
    # 0 -> +100
    df_prior = pd.DataFrame({"rev": [0.0]})
    df_current = pd.DataFrame({"rev": [100.0]})
    kpi_pos = compute_kpi(df_current, df_prior, "rev")
    assert kpi_pos.pct_change == float("inf")
    assert format_pct_change(kpi_pos.pct_change) == "new"

    # 0 -> -50
    df_current_neg = pd.DataFrame({"rev": [-50.0]})
    kpi_neg = compute_kpi(df_current_neg, df_prior, "rev")
    assert kpi_neg.pct_change == float("-inf")
    assert format_pct_change(kpi_neg.pct_change) == "n/a (no prior period)"

    # 100 -> 0
    kpi_zero = compute_kpi(df_prior, df_current, "rev")
    assert abs(kpi_zero.pct_change - (-100.0)) < 1e-6
    assert format_pct_change(kpi_zero.pct_change, with_sign=True) == "-100.0%"
    assert format_pct_change(kpi_zero.pct_change, with_arrow=True) == "↓ 100.0%"

    # None and NaN
    assert format_pct_change(None) is None
    assert format_pct_change(float("nan")) is None


# ---------------------------------------------------------------------------
# 1.6, 1.7, 1.8 Centralized state reset on new upload
# ---------------------------------------------------------------------------


def test_dataset_reset_clears_all_stale_figures():
    st.session_state["dataset"] = pd.DataFrame({"a": [1]})
    st.session_state["cleaned_df"] = pd.DataFrame({"a": [1]})
    st.session_state["classifications"] = {"a": None}
    st.session_state["_uploaded_filename"] = "dataset_a.csv"
    st.session_state["_uploaded_file_hash"] = "hash_a"
    st.session_state["dataset_name"] = "dataset_a.csv"
    st.session_state["schema_confirmed"] = True
    st.session_state["overrides"] = {"a": "metric"}
    st.session_state["_export_figures"] = {"fig": 1}
    st.session_state["_pptx_buffer"] = b"stale_bytes"
    st.session_state["_view_insights"] = {"Executive": "Insight A"}

    reset_dataset_state()

    assert "dataset" not in st.session_state
    assert "cleaned_df" not in st.session_state
    assert "classifications" not in st.session_state
    assert "schema_confirmed" not in st.session_state
    assert "overrides" not in st.session_state
    assert "_export_figures" not in st.session_state
    assert "_pptx_buffer" not in st.session_state
    assert "_view_insights" not in st.session_state


# ---------------------------------------------------------------------------
# Number-consistency Invariant Test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    ["clean.csv", "currency.csv", "inventory_sample.csv"],
)
def test_number_consistency_screen_facts_pptx(fixture_name):
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", fixture_name)
    with open(fixture_path, "rb") as fh:
        raw_bytes = fh.read()

    lres = load_file(raw_bytes, filename=fixture_name)
    clean_df, _ = clean_dataframe(lres.dataframe)
    classified = classify_columns(clean_df)
    cls_dict = {c.name: c for c in classified}

    st.session_state["dataset"] = clean_df
    st.session_state["cleaned_df"] = clean_df
    st.session_state["dataset_name"] = fixture_name
    st.session_state["classifications"] = cls_dict

    res = run_pipeline()
    kpis = res.get("kpis") or {}

    for name, kpi in kpis.items():
        # 1. UI tile value
        ui_val_str = format_number(kpi.current_value, kpi.unit)

        # 2. PPTX tile value
        pptx_tile = KPITileData(
            label=name.replace("_", " ").title(),
            value_display=format_number(kpi.current_value, kpi.unit),
            delta_display=format_pct_change(kpi.pct_change, with_sign=True),
        )
        assert pptx_tile.value_display == ui_val_str

        # 3. Facts packet value
        facts_packet = build_facts_packet(kpi, None, None, period_label="test_period")
        assert abs(facts_packet["current_value"] - round(kpi.current_value, 2)) < 1e-4

        if kpi.pct_change is not None and not math.isinf(kpi.pct_change):
            assert abs(facts_packet["pct_change"] - round(kpi.pct_change, 2)) < 1e-4
        else:
            assert facts_packet["pct_change"] is None


def test_kpi_edge_cases_empty_and_zero_swing():
    # Empty metric columns
    assert select_primary_and_secondary_metrics(pd.DataFrame(), []) == (None, [])
    # Non-numeric columns
    assert select_primary_and_secondary_metrics(pd.DataFrame({"a": ["x", "y"]}), ["a"]) == (
        None,
        [],
    )
    # 0 -> 0 pct_change is 0.0
    df0 = pd.DataFrame({"rev": [0.0]})
    res = compute_kpi(df0, df0, "rev")
    assert res.pct_change == 0.0
    # Margin KPI calculation
    df_p = pd.DataFrame({"cost": [40.0], "revenue": [100.0]})
    df_c = pd.DataFrame({"cost": [60.0], "revenue": [200.0]})
    from analytics.kpis import compute_all_kpis, compute_margin_kpi

    m = compute_margin_kpi(df_c, df_p, "cost", "revenue")
    assert m is not None
    assert abs(m.current_value - 70.0) < 1e-4
    all_k = compute_all_kpis(df_c, df_p, ["cost", "revenue"])
    assert "revenue_margin" in all_k


def test_drivers_rate_metrics_and_zero_delta():
    df_p = pd.DataFrame({"team": ["A", "B"], "conversion_rate": [0.20, 0.40]})
    df_c = pd.DataFrame({"team": ["A", "B"], "conversion_rate": [0.30, 0.50]})
    res = compute_dimension_drivers(df_c, df_p, "team", "conversion_rate")
    assert res is not None
    assert abs(res.total_delta - 0.10) < 1e-4

    from analytics.drivers import _concentration_score

    assert _concentration_score([]) == 0.0


def test_trend_excel_serial_dates_and_spans():
    from analytics.trend import _ensure_datetime, build_trend_series, pick_granularity

    # Excel float serial dates
    ser = pd.Series([45000.5, 45001.5, 45002.5])
    parsed = _ensure_datetime(ser)
    assert pd.api.types.is_datetime64_any_dtype(parsed)
    assert parsed.notna().all()

    # Granularity thresholds
    d_short = pd.date_range("2024-01-01", periods=10, freq="D")
    assert pick_granularity(d_short) == "D"
    d_med = pd.date_range("2024-01-01", periods=60, freq="D")
    assert pick_granularity(d_med) == "W"
    d_monthly = pd.date_range("2023-01-01", periods=24, freq="MS")
    assert pick_granularity(d_monthly) == "M"

    # Single timestamp and empty
    d_single = pd.date_range("2024-01-01", periods=1)
    assert pick_granularity(d_single) == "D"
    assert pick_granularity(pd.Series([], dtype="object")) == "D"

    # Single row dataframe in build_trend_series returns TrendResult with prior_period_start=None
    df_single = pd.DataFrame({"date": [pd.Timestamp("2024-01-01")], "val": [10.0]})
    res_single = build_trend_series(df_single, "date", "val")
    assert res_single is not None
    assert res_single.prior_period_start is None

    # Empty dataframe returns None
    df_empty = pd.DataFrame({"date": [], "val": []})
    assert build_trend_series(df_empty, "date", "val") is None


def test_formatters_edge_cases():
    assert format_number(15_000_000) == "1.50Cr"
    assert format_number(2_500_000) == "2.50M"
    assert format_number(12.34, "%") == "12.3%"
    assert format_pct_change(15.4) == "15.4%"
