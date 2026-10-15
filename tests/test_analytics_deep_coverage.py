"""tests/test_analytics_deep_coverage.py — Comprehensive tests for all analytics modules.

Drives coverage across analytics/** to >= 95% by verifying aggregation semantics,
temporal anomaly detection, statistical discovery guards, domain models,
and project/snapshot profiling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import analytics.anomalies as anom
import analytics.drivers as drv
import analytics.kpis as kpi
import analytics.profiler as prof
import analytics.snapshot as snap
import analytics.stats as st
import analytics.trend as trd
from analytics.domains.commerce import compute_commerce_analytics
from analytics.domains.feedback import compute_feedback_analytics
from analytics.domains.finance import compute_finance_analytics
from analytics.domains.workforce import compute_workforce_analytics


# ============================================================================
# 1. KPIs & Aggregation Semantics (Audit §4.1)
# ============================================================================
def test_kpi_rate_metric_aggregation_is_mean_not_sum():
    """Verify that rate/ratio metrics use MEAN aggregation, never SUM."""
    df_cur = pd.DataFrame({"conversion_rate": [0.10, 0.20, 0.30]})
    df_pri = pd.DataFrame({"conversion_rate": [0.05, 0.15, 0.25]})

    res = kpi.compute_kpi(df_cur, df_pri, "conversion_rate")
    # Mean of [0.10, 0.20, 0.30] is 0.20 (20%), NOT 0.60
    assert res.current_value == pytest.approx(0.20, abs=1e-5)
    assert res.prior_value == pytest.approx(0.15, abs=1e-5)
    assert res.agg == "mean"
    assert res.unit == "%"
    assert res.is_derived_ratio is True


def test_kpi_last_and_override_aggregation():
    """Verify manual override to 'last' and 'weighted_mean'."""
    df_cur = pd.DataFrame({"headcount": [100.0, 105.0, 110.0]})
    df_pri = pd.DataFrame({"headcount": [90.0, 95.0, 100.0]})

    res_last = kpi.compute_kpi(df_cur, df_pri, "headcount", agg="last")
    assert res_last.current_value == 110.0
    assert res_last.prior_value == 100.0
    assert res_last.agg == "last"

    # Fallback to mean when weighted_mean has no explicit weights
    res_wm = kpi.compute_kpi(df_cur, df_pri, "headcount", agg="weighted_mean")
    assert res_wm.current_value == pytest.approx(105.0)
    assert res_wm.agg == "mean"


def test_kpi_edge_cases_and_margin():
    df_cur = pd.DataFrame({"sales": [0.0], "cost": [10.0]})
    df_pri = pd.DataFrame({"sales": [0.0], "cost": [0.0]})

    # Signed infinities
    k_zero = kpi.compute_kpi(df_cur, df_pri, "sales")
    assert k_zero.pct_change == 0.0

    # Margin with 0 revenue returns None
    assert kpi.compute_margin_kpi(df_cur, df_pri, "cost", "sales") is None

    # Normal margin computation
    df_c2 = pd.DataFrame({"revenue": [100.0], "cost": [60.0]})
    df_p2 = pd.DataFrame({"revenue": [80.0], "cost": [40.0]})
    m_kpi = kpi.compute_margin_kpi(df_c2, df_p2, "cost", "revenue")
    assert m_kpi is not None
    assert m_kpi.current_value == pytest.approx(40.0)  # (100 - 60) / 100 * 100
    assert m_kpi.prior_value == pytest.approx(50.0)  # (80 - 40) / 80 * 100
    assert m_kpi.abs_change == pytest.approx(-10.0)

    # Margin pair finder
    assert kpi.find_margin_pair(["total_cost", "total_sales"]) == ("total_cost", "total_sales")
    assert kpi.find_margin_pair(["units", "category"]) is None


# ============================================================================
# 2. Trend Time-Series Resampling
# ============================================================================
def test_trend_aggregation_and_excel_dates():
    # Excel serial dates: days since 1899-12-30 (e.g. 44927 = ~2023-01-01)
    excel_dates = [44927, 44928, 44929]
    df_excel = pd.DataFrame({"date": excel_dates, "sales": [10.0, 20.0, 30.0]})
    res = trd.build_trend_series(df_excel, "date", "sales")
    assert res is not None
    assert len(res.series) >= 1

    # Empty date rows
    assert trd.build_trend_series(pd.DataFrame({"d": [], "s": []}), "d", "s") is None

    # Granularity picks: daily vs weekly vs monthly
    dates_d = pd.date_range("2024-01-01", periods=10, freq="D")
    assert trd.pick_granularity(pd.Series(dates_d)) == "D"

    dates_w = pd.date_range("2024-01-01", periods=10, freq="7D")
    assert trd.pick_granularity(pd.Series(dates_w)) == "W"

    dates_m = pd.date_range("2023-01-01", periods=12, freq="30D")
    assert trd.pick_granularity(pd.Series(dates_m)) == "M"

    # Fallback to D for single date or empty
    assert trd.pick_granularity(pd.Series([])) == "D"
    assert trd.pick_granularity(pd.Series([pd.Timestamp("2024-01-01")])) == "D"

    # Agg last in trend series
    df_ts = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "headcount": [10, 12, 15, 20],
        }
    )
    res_last = trd.build_trend_series(df_ts, "date", "headcount", granularity="W", agg="last")
    assert res_last is not None
    assert res_last.series["value"].iloc[-1] == 20


# ============================================================================
# 3. Drivers Decomposition
# ============================================================================
def test_drivers_aggregation_last_and_ranking():
    df_cur = pd.DataFrame(
        {
            "dept": ["Eng", "Sales", "HR"],
            "headcount": [50, 30, 20],
        }
    )
    df_pri = pd.DataFrame(
        {
            "dept": ["Eng", "Sales", "HR"],
            "headcount": [40, 35, 15],
        }
    )

    res = drv.compute_dimension_drivers(df_cur, df_pri, "dept", "headcount", agg="last")
    assert res is not None
    assert len(res.contributions) == 3
    # Eng: 50 - 40 = +10, Sales: 30 - 35 = -5, HR: 20 - 15 = +5
    top_pos = res.top_positive
    assert top_pos[0].category == "Eng"
    assert top_pos[0].delta == 10.0

    # rank_dimensions_by_explanatory_power
    ranked = drv.rank_dimensions_by_explanatory_power(df_cur, df_pri, ["dept"], "headcount")
    assert len(ranked) == 1
    assert ranked[0].dimension == "dept"


# ============================================================================
# 4. Anomalies & Temporal Detection (Audit §4.2)
# ============================================================================
def test_anomalies_temporal_and_severities():
    # Multi-month category data where Category A has historical mean 10, std ~0, then jumps to 100
    dates = []
    cats = []
    vals = []
    # 4 months of history
    for m in range(1, 5):
        d_str = f"2024-0{m}-01"
        dates.extend([d_str, d_str])
        cats.extend(["CatA", "CatB"])
        vals.extend([10.0, 20.0])
    # Month 5 spike for CatA
    dates.extend(["2024-05-01", "2024-05-01"])
    cats.extend(["CatA", "CatB"])
    vals.extend([100.0, 20.0])

    df_hist = pd.DataFrame({"date": dates, "cat": cats, "metric": vals})

    temporal_signals = anom.detect_temporal_anomalies(
        df_hist,
        date_col="date",
        metric_col="metric",
        dimension_col="cat",
        min_periods=3,
        z_threshold=2.0,
    )
    assert len(temporal_signals) >= 1
    sig = temporal_signals[0]
    assert sig.category == "CatA"
    assert "compared to its own history" in sig.description
    assert sig.severity == anom.SEVERITY_HIGH

    # Group outliers: structural outlier labeling and low/med/high tiers
    df_group = pd.DataFrame(
        {
            "dim": ["A", "B", "C", "D", "E"],
            "val": [10.0, 10.0, 10.0, 10.0, 100.0],
        }
    )
    group_sigs = anom.detect_group_outliers(df_group, "val", "dim", z_threshold=1.5)
    assert len(group_sigs) >= 1
    assert "structural outlier" in group_sigs[0].description

    # Period swings
    df_c = pd.DataFrame({"val": [100.0]})
    df_p = pd.DataFrame({"val": [50.0]})
    swings = anom.detect_period_swings(df_c, df_p, "val", pct_threshold=0.30)
    assert len(swings) == 1
    assert swings[0].severity in (anom.SEVERITY_HIGH, anom.SEVERITY_MEDIUM)

    # compute_risk_signals end-to-end
    all_sigs = anom.compute_risk_signals(
        df_c,
        df_p,
        metric_columns=["val"],
        dimension_columns=[],
        full_df=df_hist,
        date_col="date",
    )
    assert len(all_sigs) >= 1


# ============================================================================
# 5. Statistical Engine & Takeaways
# ============================================================================
def test_stats_sample_size_and_disclaimer():
    # Enforces minimum n >= 5
    df_tiny = pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 20, 30, 40]})
    corr_tiny = st.compute_correlation_matrix(df_tiny, ["a", "b"], min_samples=5)
    assert corr_tiny.empty

    df_valid = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
    corr_valid = st.compute_correlation_matrix(df_valid, ["a", "b"], min_samples=5)
    assert not corr_valid.empty

    drivers = st.extract_key_drivers(corr_valid, primary_metric="a")
    assert len(drivers) == 1
    assert (
        "Correlation indicates statistical association, not direct causation"
        in drivers[0].narrative
    )

    # Concentration risk tiers
    conc_ext = st.compute_concentration_index(pd.Series([1000.0, 1.0, 1.0, 1.0]))
    assert conc_ext.risk_level in ("Extreme", "High")

    conc_low = st.compute_concentration_index(pd.Series([10.0] * 20))
    assert conc_low.risk_level == "Low"

    conc_empty = st.compute_concentration_index(pd.Series([]))
    assert conc_empty.risk_level == "Low"

    # Attribute anomalies
    df_outliers = pd.DataFrame(
        {
            "val": [10, 12, 11, 10, 12, 11, 10, 12, 11, 100, 120, 110],
            "cat": ["A", "A", "A", "A", "A", "A", "A", "A", "A", "Faulty", "Faulty", "Faulty"],
        }
    )
    attr = st.attribute_anomalies(df_outliers, "val", ["cat"])
    assert len(attr) >= 1
    assert attr[0].top_driver_category == "Faulty"

    # Executive takeaways formatting
    class MockProfile:
        primary_metric = "val"
        entity_dimension = "cat"
        all_dimensions = ["cat"]

    takeaways = st.generate_executive_takeaways(df_outliers, MockProfile(), drivers, conc_ext)
    assert len(takeaways) >= 3
    assert any("Portfolio Scale" in t for t in takeaways)


# ============================================================================
# 6. Domain Analytics Deep Coverage
# ============================================================================
def test_domains_edge_cases_and_waterfalls():
    # Commerce channel table and discount
    df_comm = pd.DataFrame(
        {
            "order": ["1", "2"],
            "client": ["C1", "C2"],
            "item": ["X", "Y"],
            "amount": [100.0, 200.0],
            "units": [1, 2],
            "disc": [0.05, 0.15],
            "channel": ["Web", "App"],
        }
    )
    c_res = compute_commerce_analytics(df_comm)
    assert c_res.channel_breakdown_table is not None
    assert c_res.avg_discount_rate == pytest.approx(0.10)

    # Finance waterfall without budget (step walk)
    df_fin_nobudget = pd.DataFrame(
        {
            "dept": ["Marketing", "R&D"],
            "spent": [300.0, 500.0],
        }
    )
    f_res = compute_finance_analytics(df_fin_nobudget, actual_col="spent", account_col="dept")
    assert f_res.total_actual == 800.0
    assert len(f_res.waterfall_steps) >= 2

    # Workforce department salary table
    df_wf = pd.DataFrame(
        {
            "id": ["1", "2", "3"],
            "team": ["Eng", "Eng", "Design"],
            "comp": [100000, 120000, 80000],
            "service": [2, 4, 1],
            "rating": [4, 5, 3],
            "status": ["Active", "Active", "Resigned"],
        }
    )
    wf_res = compute_workforce_analytics(df_wf)
    assert wf_res.salary_by_dept_table is not None
    assert wf_res.turnover_rate == pytest.approx(0.333, abs=0.01)

    # Feedback CSAT 1-5 scale
    df_fb = pd.DataFrame(
        {
            "stars": [5, 4, 3, 2, 5],
            "case": ["1", "2", "3", "4", "5"],
            "resolution_hours": [1.0, 2.0, 3.0, 4.0, 5.0],
            "tier": ["P1", "P2", "P3", "P1", "P2"],
        }
    )
    fb_res = compute_feedback_analytics(df_fb, rating_col="stars")
    assert fb_res.csat_score == 60.0  # 3 out of 5 ratings >= 4 -> 60.0%
    assert fb_res.avg_resolution_time == 3.0
    assert fb_res.priority_breakdown is not None


# ============================================================================
# 7. Snapshot & Project Portfolio Analytics
# ============================================================================
def test_snapshot_and_project_analytics():
    # Snapshot ranking
    df_snap = pd.DataFrame(
        {
            "sku": [f"SKU_{i}" for i in range(25)],
            "revenue": [float(i * 10) for i in range(25)],
            "units": [i for i in range(25)],
        }
    )
    s_res = snap.compute_snapshot_analytics(
        df_snap, entity_col="sku", primary_metric="revenue", secondary_metrics=["units"]
    )
    assert len(s_res.top_entities) == 10
    assert len(s_res.bottom_entities) <= 5
    assert "80%" in s_res.pareto_text or "Pareto" in s_res.pareto_text

    # Project portfolio
    df_proj = pd.DataFrame(
        {
            "task": ["T1", "T2", "T3"],
            "project": ["Proj A", "Proj A", "Proj B"],
            "owner": ["Alice", "Bob", "Alice"],
            "progress": [1.0, 0.5, 0.0],
            "duration": [5, 10, 15],
            "start": ["2024-01-01", "2024-01-05", "2024-01-10"],
            "due": ["2024-01-10", "2024-01-20", "2024-01-25"],
        }
    )
    p_res = snap.compute_project_analytics(
        df_proj,
        task_col="task",
        project_col="project",
        assignee_col="owner",
        progress_col="progress",
        duration_col="duration",
        start_date_col="start",
        end_date_col="due",
    )
    assert p_res.total_tasks == 3
    assert p_res.completed_tasks == 1
    assert p_res.in_progress_tasks == 1
    assert p_res.unstarted_tasks == 1
    assert p_res.completion_rate_pct == pytest.approx(50.0, abs=0.1)
    assert not p_res.assignee_workload.empty


# ============================================================================
# 8. Profiler Archetypes & Domains
# ============================================================================
def test_profiler_archetypes():
    from ingestion.classifier import classify_columns

    # 1. Project dataset profiling
    df_proj = pd.DataFrame(
        {
            "task_id": [1, 2],
            "task_name": ["Design", "Build"],
            "start_date": ["2024-01-01", "2024-01-10"],
            "end_date": ["2024-01-09", "2024-01-20"],
            "progress_pct": [1.0, 0.5],
            "duration_days": [8, 10],
        }
    )
    classes_proj = classify_columns(df_proj)
    p_proj = prof.profile_dataset(df_proj, classes_proj)
    assert p_proj.profile_type == prof.PROFILE_PROJECT
    assert p_proj.domain_type == prof.DOMAIN_PROJECT
    assert p_proj.has_progress is True

    # 2. Timeseries dataset profiling
    df_ts = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "region": ["North", "South", "North"],
            "revenue": [100, 200, 150],
        }
    )
    classes_ts = classify_columns(df_ts)
    p_ts = prof.profile_dataset(df_ts, classes_ts)
    assert p_ts.profile_type == prof.PROFILE_TIMESERIES
    assert "revenue" in p_ts.metric_aggregations


# ============================================================================
# 9. Additional Deep Branch Testing
# ============================================================================
def test_anomalies_branches_and_severities():
    # 1. detect_temporal_anomalies: unusually low and severity tiers
    dates = []
    cats = []
    vals = []
    for m in range(1, 5):
        d_str = f"2024-0{m}-01"
        dates.extend([d_str, d_str])
        cats.extend(["CatA", "CatB"])
        vals.extend([100.0, 50.0])
    # Month 5 drop for CatA
    dates.extend(["2024-05-01", "2024-05-01"])
    cats.extend(["CatA", "CatB"])
    vals.extend([10.0, 50.0])

    df_hist = pd.DataFrame({"date": dates, "cat": cats, "metric": vals})
    sigs = anom.detect_temporal_anomalies(
        df_hist, "date", "metric", "cat", min_periods=3, z_threshold=1.5
    )
    assert len(sigs) >= 1
    assert "unusually low" in sigs[0].description

    # Empty / missing columns in detect_temporal_anomalies
    assert anom.detect_temporal_anomalies(pd.DataFrame(), "d", "m", "c") == []
    assert anom.detect_temporal_anomalies(df_hist, "nonexistent", "metric", "cat") == []

    # 2. detect_group_outliers branches: < 3 groups or 0 std
    df_small = pd.DataFrame({"dim": ["A", "B"], "metric": [10.0, 20.0]})
    assert anom.detect_group_outliers(df_small, "metric", "dim") == []

    df_zero_std = pd.DataFrame({"dim": ["A", "B", "C"], "metric": [10.0, 10.0, 10.0]})
    assert anom.detect_group_outliers(df_zero_std, "metric", "dim") == []

    # Direction unusually low in group outliers
    df_low_outlier = pd.DataFrame(
        {"dim": ["A", "B", "C", "D", "E"], "metric": [100.0, 100.0, 100.0, 100.0, 0.0]}
    )
    low_sigs = anom.detect_group_outliers(df_low_outlier, "metric", "dim", z_threshold=1.5)
    assert len(low_sigs) >= 1
    assert "unusually low" in low_sigs[0].description

    # 3. detect_period_swings branches: dimension with agg="mean" and agg="last"
    df_c_dim = pd.DataFrame({"dim": ["A", "B"], "metric": [200.0, 100.0]})
    df_p_dim = pd.DataFrame({"dim": ["A", "B"], "metric": [100.0, 100.0]})
    dim_swings = anom.detect_period_swings(
        df_c_dim, df_p_dim, "metric", dimension_col="dim", pct_threshold=0.30, agg="mean"
    )
    assert len(dim_swings) >= 1
    assert dim_swings[0].category == "A"

    dim_swings_last = anom.detect_period_swings(
        df_c_dim, df_p_dim, "metric", dimension_col="dim", pct_threshold=0.30, agg="last"
    )
    assert len(dim_swings_last) >= 1

    # Empty inputs in detect_period_swings
    assert anom.detect_period_swings(pd.DataFrame(), df_p_dim, "metric") == []
    assert anom.detect_period_swings(df_c_dim, None, "metric") == []


def test_stats_branches_and_relationships():
    # 1. extract_key_drivers with primary_metric=None (upper-triangle pairs)
    corr_df = pd.DataFrame(
        {
            "rev": [1.0, 0.85, -0.80, -0.55],
            "cost": [0.85, 1.0, -0.70, -0.40],
            "units": [-0.80, -0.70, 1.0, 0.60],
            "discount": [-0.55, -0.40, 0.60, 1.0],
        },
        index=["rev", "cost", "units", "discount"],
    )
    drivers = st.extract_key_drivers(corr_df, primary_metric=None, threshold=0.50)
    assert len(drivers) >= 3
    # Check that negative relationships produce inverse driver narratives
    narratives = [d.narrative for d in drivers]
    assert any("inverse driver" in n or "inverse relationship" in n for n in narratives)

    # Empty corr_df
    assert st.extract_key_drivers(pd.DataFrame()) == []

    # 2. compute_concentration_index moderate tier
    vals_mod = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    conc_mod = st.compute_concentration_index(pd.Series(vals_mod))
    assert conc_mod.risk_level in ("High", "Moderate")

    # 3. attribute_anomalies fallback when iqr <= 0
    # Repeating values with one outlier
    s_rep = [10.0] * 15 + [100.0]
    df_rep = pd.DataFrame({"val": s_rep, "cat": ["A"] * 15 + ["B"]})
    attr_rep = st.attribute_anomalies(df_rep, "val", ["cat"])
    assert len(attr_rep) >= 1

    # Empty attribute anomalies
    assert st.attribute_anomalies(pd.DataFrame(), "val", ["cat"]) == []
    assert st.attribute_anomalies(pd.DataFrame({"x": ["a"]}), "x", ["cat"]) == []
    assert st.attribute_anomalies(pd.DataFrame({"val": [1, 2]}), "val", ["cat"]) == []

    # 4. generate_executive_takeaways scale ranges ($M, $k, small)
    class BigScaleProfile:
        primary_metric = "total_revenue"
        entity_dimension = None
        all_dimensions = []

    df_mil = pd.DataFrame({"total_revenue": [500_000.0, 600_000.0]})
    t_mil = st.generate_executive_takeaways(df_mil, BigScaleProfile())
    assert any("$1.1M" in t for t in t_mil)

    df_small = pd.DataFrame({"val": [5.0, 15.0]})

    class SmallProfile:
        primary_metric = "val"
        entity_dimension = None
        all_dimensions = []

    t_small = st.generate_executive_takeaways(df_small, SmallProfile())
    assert any("20.0" in t for t in t_small)


def test_trend_and_snapshot_additional_branches():
    # 1. _ensure_datetime edge cases
    from analytics.trend import (
        _ensure_datetime,
        build_trend_series,
        period_label,
        pick_granularity,
        split_current_prior,
    )

    bad_dates = pd.Series(["not_a_date_1", "not_a_date_2"])
    res_nat = _ensure_datetime(bad_dates)
    assert res_nat.isna().all()

    # Numeric series Excel serial dates
    num_dates = pd.Series([np.nan, np.nan, 44000.0, 44001.0])
    res_excel = _ensure_datetime(num_dates)
    assert pd.api.types.is_datetime64_any_dtype(res_excel)

    # pick_granularity branches
    assert pick_granularity(pd.Series([])) == "D"
    d_daily = pd.Series(pd.date_range("2024-01-01", periods=2, freq="D"))
    assert pick_granularity(d_daily) == "D"
    d_weekly = pd.Series(
        [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-08"), pd.Timestamp("2024-01-15")]
    )
    assert pick_granularity(d_weekly) in ("D", "W")
    d_monthly = pd.Series(pd.date_range("2024-01-01", periods=12, freq="MS"))
    assert pick_granularity(d_monthly) == "M"

    # build_trend_series edge cases (empty or single point)
    df_empty_dates = pd.DataFrame({"d": ["bad", "dates"], "val": [1, 2]})
    assert build_trend_series(df_empty_dates, "d", "val") is None

    df_single = pd.DataFrame({"d": [pd.Timestamp("2024-01-01")], "val": [10.0]})
    t_single = build_trend_series(df_single, "d", "val")
    assert t_single is not None
    assert t_single.prior_period_start is None
    cur_s, pri_s = split_current_prior(df_single, "d", t_single)
    assert pri_s is None
    assert len(cur_s) == 1

    # period_label
    assert "yesterday" in period_label("D")
    assert "week" in period_label("W")
    assert "month" in period_label("M")
    assert "period" in period_label("X")

    # 2. compute_project_analytics at-risk tasks & duration from dates
    df_proj_overdue = pd.DataFrame(
        {
            "task": ["Overdue Task", "Overrunning Task"],
            "project": ["Core", "Core"],
            "assignee": ["Dave", "Eve"],
            "progress": [0.0, 40.0],  # 0.0 with dur 45 triggers at-risk
            "duration": [45, 10],
            "start": ["2023-01-01", "2023-01-01"],
            "due": ["2023-01-10", "2025-01-01"],
        }
    )
    p_risk = snap.compute_project_analytics(
        df_proj_overdue,
        task_col="task",
        project_col="project",
        assignee_col="assignee",
        progress_col="progress",
        duration_col="duration",
        start_date_col="start",
        end_date_col="due",
    )
    assert len(p_risk.at_risk_tasks) >= 1

    # Project duration computed from start and end dates when duration_col is None
    df_proj_dates = pd.DataFrame(
        {
            "task": ["T1", "T2"],
            "start": ["2024-01-01", "2024-01-05"],
            "due": ["2024-01-10", "2024-01-15"],
            "prog": [100.0, 50.0],
        }
    )
    p_dates = snap.compute_project_analytics(
        df_proj_dates,
        task_col="task",
        project_col=None,
        assignee_col=None,
        progress_col="prog",
        duration_col=None,
        start_date_col="start",
        end_date_col="due",
    )
    assert p_dates.total_tasks == 2
    assert "Total Days Required" in p_dates.kpis

    # 3. compute_finance_analytics with explicit variance column
    df_fin_explicit_var = pd.DataFrame(
        {
            "account": ["Office", "Travel"],
            "actual": [100.0, 200.0],
            "budget": [120.0, 180.0],
            "variance": [-20.0, 20.0],
        }
    )
    f_res = compute_finance_analytics(
        df_fin_explicit_var,
        account_col="account",
        actual_col="actual",
        budget_col="budget",
        variance_col="variance",
    )
    assert f_res.variance_abs == 0.0
    assert len(f_res.favorable_items) >= 1


def test_analytics_branch_completeness_part1():
    # Anomalies severities (low, medium, high) and aggregations
    df_anom = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="MS").repeat(3),
            "region": ["East", "West", "Central"] * 12,
            "val": [100.0] * 35 + [180.0],  # Single spike at the end
        }
    )
    sigs_mean = anom.detect_temporal_anomalies(df_anom, "date", "val", "region", agg="mean")
    assert isinstance(sigs_mean, list)
    sigs_last = anom.detect_temporal_anomalies(df_anom, "date", "val", "region", agg="last")
    assert isinstance(sigs_last, list)

    # Empty after dropna in temporal
    df_empty_t = pd.DataFrame({"date": [np.nan], "dim": ["A"], "val": [np.nan]})
    assert anom.detect_temporal_anomalies(df_empty_t, "date", "val", "dim") == []

    # Group outliers: low and medium severity tiers & agg
    df_out = pd.DataFrame(
        {
            "dim": ["A", "B", "C", "D", "E"],
            "val": [10.0, 10.0, 10.0, 10.0, 30.0],
        }
    )
    out_mean = anom.detect_group_outliers(df_out, "val", "dim", agg="mean", z_threshold=1.0)
    assert len(out_mean) >= 1
    out_last = anom.detect_group_outliers(df_out, "val", "dim", agg="last", z_threshold=1.0)
    assert len(out_last) >= 1

    # Group outliers fewer than 3 categories or zero std
    df_few = pd.DataFrame({"dim": ["A", "B"], "val": [10.0, 10.0]})
    assert anom.detect_group_outliers(df_few, "val", "dim") == []
    df_flat = pd.DataFrame({"dim": ["A", "B", "C"], "val": [10.0, 10.0, 10.0]})
    assert anom.detect_group_outliers(df_flat, "val", "dim") == []

    # Period swings: dimension_col is None with mean, last, zero prior
    df_c = pd.DataFrame({"val": [150.0, 200.0]})
    df_p = pd.DataFrame({"val": [100.0, 100.0]})
    sw_mean = anom.detect_period_swings(df_c, df_p, "val", agg="mean", pct_threshold=0.2)
    assert len(sw_mean) >= 1
    sw_last = anom.detect_period_swings(df_c, df_p, "val", agg="last", pct_threshold=0.2)
    assert len(sw_last) >= 1

    # Period swings zero prior
    df_zero = pd.DataFrame({"val": [0.0]})
    assert anom.detect_period_swings(df_c, df_zero, "val") == []

    # Period swings with dimension and zero prior for cat
    df_c_dim = pd.DataFrame({"dim": ["A", "B"], "val": [100.0, 200.0]})
    df_p_dim = pd.DataFrame({"dim": ["A", "B"], "val": [0.0, 100.0]})
    sw_dim = anom.detect_period_swings(
        df_c_dim, df_p_dim, "val", dimension_col="dim", pct_threshold=0.2
    )
    assert len(sw_dim) == 1
    assert sw_dim[0].category == "B"

    # Deduplication in compute_risk_signals
    all_sig = anom.compute_risk_signals(
        df_c_dim, df_p_dim, metric_columns=["val"], dimension_columns=["dim"]
    )
    assert isinstance(all_sig, list)


def test_analytics_branch_completeness_part2():
    # Commerce missing optional columns
    df_c_min = pd.DataFrame({"rev": [100.0, 200.0, 300.0]})
    res_c_min = compute_commerce_analytics(
        df_c_min,
        revenue_col="rev",
        order_col=None,
        qty_col=None,
        customer_col=None,
        product_col=None,
    )
    assert res_c_min.total_revenue == 600.0
    assert res_c_min.total_orders == 3
    assert res_c_min.unique_customers == 0

    # Commerce with product without qty
    df_c_prod = pd.DataFrame({"product": ["P1", "P2"], "rev": [50.0, 150.0]})
    res_c_prod = compute_commerce_analytics(df_c_prod, revenue_col="rev", product_col="product")
    assert not res_c_prod.top_products_table.empty

    # Workforce missing columns & turnover
    df_wf_min = pd.DataFrame({"person": ["A", "B", "C"]})
    res_wf_min = compute_workforce_analytics(
        df_wf_min,
        emp_col="person",
        salary_col=None,
        dept_col=None,
        tenure_col=None,
        perf_col=None,
        status_col=None,
    )
    assert res_wf_min.headcount == 3
    assert res_wf_min.turnover_rate is None
    assert res_wf_min.salary_by_dept_table.empty

    # Workforce with status
    df_wf_term = pd.DataFrame({"person": ["A", "B"], "status": ["Active", "Terminated"]})
    res_wf_term = compute_workforce_analytics(df_wf_term, emp_col="person", status_col="status")
    assert res_wf_term.turnover_rate == 0.5

    # Feedback only NPS (10 scale)
    df_fb_nps = pd.DataFrame({"nps": [10, 9, 8, 7, 2]})
    res_fb_nps = compute_feedback_analytics(df_fb_nps, rating_col="nps")
    assert res_fb_nps.nps_score is not None

    # Snapshot with grouping_cols and metric_aggs
    df_snap = pd.DataFrame(
        {
            "sku": [f"S{i}" for i in range(11)],
            "cat": ["C1"] * 5 + ["C2"] * 6,
            "sales": [10.0] * 10 + [1000.0],
            "margin": [0.2] * 10 + [0.5],
        }
    )
    snap_res = snap.compute_snapshot_analytics(
        df_snap,
        entity_col="sku",
        primary_metric="sales",
        secondary_metrics=["margin"],
        grouping_cols=["cat"],
        metric_aggs={"sales": "sum", "margin": "mean"},
    )
    assert snap_res.kpis["margin"].agg == "mean"
    assert "cat" in snap_res.group_rollups
    assert len(snap_res.outliers) >= 1

    # Stats: correlation matrix with constant column or empty
    df_const = pd.DataFrame({"a": [1.0, 1.0, 1.0, 1.0, 1.0], "b": [1.0, 2.0, 3.0, 4.0, 5.0]})
    corr_const = st.compute_correlation_matrix(df_const, ["a", "b"], min_samples=5)
    assert corr_const.empty

    # Stats: concentration with zero or negative
    assert st.compute_concentration_index(pd.Series([0.0, 0.0])).risk_level == "Low"
    assert st.compute_concentration_index(pd.Series([-10.0, -20.0])).risk_level == "Low"

    # Takeaways with entity dimension and empty takeaways guard
    df_empty_take = pd.DataFrame({"val": [100.0]})

    class EmptyProfile:
        primary_metric = "val"
        entity_dimension = None
        all_dimensions = []

    assert len(st.generate_executive_takeaways(df_empty_take, EmptyProfile())) >= 1


def test_analytics_branch_completeness_part3():
    # 1. Anomalies severity tiers: low (z between 1.0 and 1.5) and medium (z between 1.5 and 2.0)
    # Temporal:
    df_temp_tiers = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="MS"),
            "dim": ["A"] * 10,
            # 9 periods at 10.0 (std=0), period 10 at 10.3 -> effective_std=max(0.5, 0.1)=0.5 -> z=0.6/0.5=1.2 (Low severity)
            # if z_threshold=1.0: 1.0 <= 1.2 < 1.5 -> SEVERITY_LOW
            "val_low": [10.0] * 9 + [10.6],
            # period 10 at 10.9 -> z=0.9/0.5=1.8 -> 1.5 <= 1.8 < 2.0 -> SEVERITY_MEDIUM
            "val_med": [10.0] * 9 + [10.9],
        }
    )
    sig_low = anom.detect_temporal_anomalies(
        df_temp_tiers, "date", "val_low", "dim", z_threshold=1.0
    )
    assert len(sig_low) == 1
    assert sig_low[0].severity == anom.SEVERITY_LOW

    sig_med = anom.detect_temporal_anomalies(
        df_temp_tiers, "date", "val_med", "dim", z_threshold=1.0
    )
    assert len(sig_med) == 1
    assert sig_med[0].severity == anom.SEVERITY_MEDIUM

    # Group outliers: low and medium
    df_grp_tiers = pd.DataFrame(
        {
            "dim": [f"D{i}" for i in range(10)],
            "val": [10.0] * 8 + [13.2, 14.5],
        }
    )
    grp_tiers = anom.detect_group_outliers(df_grp_tiers, "val", "dim", z_threshold=1.0)
    assert len(grp_tiers) >= 1

    # Period swings severity tiers: medium (pct between 1.5*thresh and 2*thresh) and low (between 1*thresh and 1.5*thresh)
    df_cur_sw = pd.DataFrame({"val": [112.0]})  # 12% swing -> with threshold=0.10: 1.2x -> Low
    df_pri_sw = pd.DataFrame({"val": [100.0]})
    sw_low = anom.detect_period_swings(df_cur_sw, df_pri_sw, "val", pct_threshold=0.10)
    assert len(sw_low) == 1
    assert sw_low[0].severity == anom.SEVERITY_LOW

    df_cur_med = pd.DataFrame({"val": [117.0]})  # 17% swing -> with threshold=0.10: 1.7x -> Medium
    sw_med = anom.detect_period_swings(df_cur_med, df_pri_sw, "val", pct_threshold=0.10)
    assert len(sw_med) == 1
    assert sw_med[0].severity == anom.SEVERITY_MEDIUM

    # Period swings with dimension medium and low
    df_cur_d_med = pd.DataFrame({"dim": ["X"], "val": [117.0]})
    df_pri_d_med = pd.DataFrame({"dim": ["X"], "val": [100.0]})
    sw_d_med = anom.detect_period_swings(
        df_cur_d_med, df_pri_d_med, "val", dimension_col="dim", pct_threshold=0.10
    )
    assert len(sw_d_med) == 1
    assert sw_d_med[0].severity == anom.SEVERITY_MEDIUM

    df_cur_d_low = pd.DataFrame({"dim": ["X"], "val": [112.0]})
    sw_d_low = anom.detect_period_swings(
        df_cur_d_low, df_pri_d_med, "val", dimension_col="dim", pct_threshold=0.10
    )
    assert len(sw_d_low) == 1
    assert sw_d_low[0].severity == anom.SEVERITY_LOW

    # Duplicate risk signal deduplication branch (line 303)
    # Using 50% swing so default 20% threshold triggers
    df_cur_dup = pd.DataFrame({"val": [150.0]})
    dup_sigs = anom.compute_risk_signals(
        df_cur_dup, df_pri_sw, metric_columns=["val", "val"], dimension_columns=[]
    )
    assert len(dup_sigs) == 1  # Deduplicated

    # Trend mean aggregation
    df_trend_m = pd.DataFrame(
        {"date": pd.date_range("2024-01-01", periods=10, freq="D"), "val": [10.0] * 10}
    )
    from analytics.trend import build_trend_series

    t_m = build_trend_series(df_trend_m, "date", "val", agg="mean")
    assert t_m is not None

    # 2. Stats module branches:
    # compute_concentration_index with numpy array
    arr = np.array([10.0, 20.0, 30.0, 40.0])
    conc_arr = st.compute_concentration_index(arr)
    assert conc_arr.gini > 0

    # Moderate concentration tier (gini >= 0.35)
    mod_arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 10.0])
    conc_mod = st.compute_concentration_index(mod_arr)
    assert conc_mod.risk_level in ("Moderate", "High")

    # attribute_anomalies branches:
    # std == 0
    df_flat_attr = pd.DataFrame({"m": [10.0] * 12, "dim": ["A", "B"] * 6})
    assert st.attribute_anomalies(df_flat_attr, "m", ["dim"]) == []
    # no outliers
    df_norm_attr = pd.DataFrame({"m": list(range(12)), "dim": ["A", "B"] * 6})
    assert st.attribute_anomalies(df_norm_attr, "m", ["dim"]) == []
    # dim not in df
    assert st.attribute_anomalies(df_norm_attr, "m", ["non_existent_dim"]) == []

    # generate_executive_takeaways without primary metric or with entity_dim from all_dimensions
    class NoPrimaryProfile:
        primary_metric = None
        entity_dimension = None
        all_dimensions = ["dim"]

    df_take = pd.DataFrame({"dim": ["A", "B"], "v": [10.0, 20.0]})
    t_no_p = st.generate_executive_takeaways(df_take, NoPrimaryProfile(), concentration=conc_mod)
    assert any("Dataset Overview" in t for t in t_no_p)
    assert any("Distribution Balance" in t or "Concentration" in t for t in t_no_p)

    # 3. Snapshot module branches:
    # Dead stock outlier
    df_dead = pd.DataFrame(
        {
            "sku": ["SKU1", "SKU2", "SKU3", "SKU4", "SKU5"],
            "rev": [0.0, 10.0, 20.0, 30.0, 40.0],
            "units_sold": [0, 5, 10, 15, 20],
            "stock_qty": [50, 20, 10, 5, 0],
        }
    )
    snap_dead = snap.compute_snapshot_analytics(
        df_dead,
        entity_col="sku",
        primary_metric="rev",
        secondary_metrics=["units_sold", "stock_qty"],
        metric_aggs={"rev": "last"},
    )
    assert any("Dead stock" in str(o.get("issue")) for o in snap_dead.outliers)
    assert snap_dead.kpis["rev"].agg == "last"

    # Project workload with duration_col
    df_proj_workload = pd.DataFrame(
        {
            "task": ["T1", "T2"],
            "owner": ["Alice", "Bob"],
            "prog": [0.5, 0.8],
            "dur": [10, 20],
        }
    )
    p_wl = snap.compute_project_analytics(
        df_proj_workload,
        task_col="task",
        project_col=None,
        assignee_col="owner",
        progress_col="prog",
        duration_col="dur",
        start_date_col=None,
        end_date_col=None,
    )
    assert not p_wl.assignee_workload.empty

    # 4. Domain discovery regex branches:
    # Commerce with discovery
    df_com_discover = pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "customer_id": ["C1", "C2"],
            "product_title": ["P1", "P2"],
            "revenue": [100.0, 200.0],
            "quantity": [1, 2],
            "discount": [0.1, 0.0],
            "channel": ["Online", "Retail"],
        }
    )
    c_disc = compute_commerce_analytics(df_com_discover)
    assert c_disc.total_revenue == 300.0
    assert c_disc.channel_breakdown_table is not None

    # Workforce with discovery
    df_wf_discover = pd.DataFrame(
        {
            "employee_id": ["E1", "E2", "E3", "E4", "E5"],
            "department": ["Eng", "Eng", "Sales", "Sales", "HR"],
            "salary": [100000, 110000, 80000, 85000, 75000],
            "tenure_months": [12, 24, 36, 48, 60],
            "performance_rating": [4, 5, 3, 4, 3],
            "employment_status": ["Active", "Active", "Active", "Active", "Terminated"],
        }
    )
    wf_disc = compute_workforce_analytics(df_wf_discover)
    assert wf_disc.headcount == 5
    assert wf_disc.tenure_perf_corr is not None
    assert wf_disc.departments_count == 3
