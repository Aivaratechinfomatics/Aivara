import pandas as pd
import pytest
from ingestion.classifier import classify_columns
from analytics.profiler import (
    profile_dataset,
    DOMAIN_COMMERCE,
    DOMAIN_FINANCE,
    DOMAIN_WORKFORCE,
    DOMAIN_FEEDBACK,
    DOMAIN_INVENTORY,
    DOMAIN_PROJECT,
    DOMAIN_TIMESERIES,
    DOMAIN_SNAPSHOT,
)
from analytics.domains.commerce import compute_commerce_analytics
from analytics.domains.finance import compute_finance_analytics
from analytics.domains.workforce import compute_workforce_analytics
from analytics.domains.feedback import compute_feedback_analytics


def test_profile_commerce_dataset():
    df = pd.DataFrame({
        "order_id": [101, 102, 103, 104, 105],
        "customer_id": ["C1", "C2", "C1", "C3", "C2"],
        "product_name": ["Laptop", "Mouse", "Keyboard", "Laptop", "Monitor"],
        "sales": [1200.0, 25.0, 75.0, 1200.0, 300.0],
        "quantity": [1, 2, 1, 1, 1],
    })
    cmap = classify_columns(df)
    profile = profile_dataset(df, cmap)
    assert profile.domain_type == DOMAIN_COMMERCE

    res = compute_commerce_analytics(df)
    assert res.total_orders == 5
    assert res.total_revenue == 2800.0
    assert res.aov == 560.0
    assert res.unique_customers == 3
    assert res.repeat_customer_rate > 0.60  # C1 and C2 both repeated
    assert len(res.top_products_table) > 0


def test_profile_finance_dataset():
    df = pd.DataFrame({
        "line_item": ["Revenue", "COGS", "Marketing", "Salaries", "Rent"],
        "actual": [100000, 40000, 15000, 25000, 5000],
        "budget": [95000, 38000, 18000, 24000, 5000],
    })
    cmap = classify_columns(df)
    profile = profile_dataset(df, cmap)
    assert profile.domain_type == DOMAIN_FINANCE

    res = compute_finance_analytics(df)
    assert res.total_actual == 185000
    assert res.total_budget == 180000
    assert res.variance_abs == 5000
    assert len(res.waterfall_steps) > 0


def test_profile_workforce_dataset():
    df = pd.DataFrame({
        "emp_id": [1, 2, 3, 4, 5, 6],
        "department": ["Engineering", "Engineering", "Sales", "Sales", "HR", "Engineering"],
        "salary": [120000, 140000, 90000, 95000, 80000, 130000],
        "tenure_years": [2, 4, 1, 3, 5, 2],
        "perf_score": [4, 5, 3, 4, 3, 4],
        "status": ["Active", "Active", "Active", "Terminated", "Active", "Active"],
    })
    cmap = classify_columns(df)
    profile = profile_dataset(df, cmap)
    assert profile.domain_type == DOMAIN_WORKFORCE

    res = compute_workforce_analytics(df)
    assert res.headcount == 6
    assert res.departments_count == 3
    assert res.median_salary == 107500.0
    assert res.turnover_rate == pytest.approx(1 / 6, abs=0.01)
    assert res.tenure_perf_corr is not None
    assert len(res.department_summary) == 3


def test_profile_feedback_dataset():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "rating": [10, 9, 10, 8, 7, 9, 4, 2, 10, 8],
        "csat_score": [5, 5, 5, 4, 3, 5, 2, 1, 5, 4],
        "feedback_text": ["Great", "Good", "Love it", "OK", "Fine", "Awesome", "Bad", "Terrible", "Best", "OK"],
    })
    cmap = classify_columns(df)
    profile = profile_dataset(df, cmap)
    assert profile.domain_type == DOMAIN_FEEDBACK

    res = compute_feedback_analytics(df)
    assert res.total_responses == 10
    assert res.nps_score is not None
    # 5 promoters (9,10): indices 0,1,2,5,8 -> 50%
    # 3 passives (7,8): indices 3,4,9 -> 30%
    # 2 detractors (<=6): indices 6,7 -> 20%
    # NPS = 50 - 20 = 30
    assert res.nps_score == 30.0
    assert res.promoter_pct == 50.0
    assert res.detractor_pct == 20.0
