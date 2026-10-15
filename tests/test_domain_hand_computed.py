"""tests/test_domain_hand_computed.py — Hand-verified domain analytics test suite.

Every test case here asserts against independent, plain-Python hand calculations
to guarantee mathematical validity across domain modules (Audit §4).
"""

from __future__ import annotations

import pandas as pd
import pytest

from analytics.domains.commerce import compute_commerce_analytics
from analytics.domains.feedback import compute_feedback_analytics
from analytics.domains.finance import compute_finance_analytics
from analytics.domains.workforce import compute_workforce_analytics


def test_commerce_hand_computed():
    """Hand calculation verification for retail/e-commerce metrics.

    Data:
      Order 1: C1, Widget A, 100.0, 2 units, 0.10 discount
      Order 1: C1, Widget B,  50.0, 1 units, 0.00 discount
      Order 2: C2, Widget A, 200.0, 4 units, 0.20 discount
      Order 3: C1, Widget C, 150.0, 3 units, 0.10 discount

    Hand calculations:
      Total Revenue   = 100 + 50 + 200 + 150 = 500.0
      Total Orders    = unique order_id count: {1, 2, 3} = 3
      Total Units     = 2 + 1 + 4 + 3 = 10
      Unique Cust     = unique customer_id count: {C1, C2} = 2
      AOV             = 500.0 / 3 = 166.67
      Basket Size     = 10 / 3 = 3.33
      Repeat Rate     = C1 (2 orders: 1, 3), C2 (1 order: 2) -> 1 of 2 repeats = 0.50 (50.0%)
      Avg Discount    = (0.10 + 0.00 + 0.20 + 0.10) / 4 = 0.10
    """
    df = pd.DataFrame(
        {
            "order_id": [1, 1, 2, 3],
            "customer_id": ["C1", "C1", "C2", "C1"],
            "product": ["Widget A", "Widget B", "Widget A", "Widget C"],
            "sales": [100.0, 50.0, 200.0, 150.0],
            "quantity": [2, 1, 4, 3],
            "discount": [0.10, 0.00, 0.20, 0.10],
            "channel": ["Online", "Online", "Retail", "Online"],
        }
    )

    res = compute_commerce_analytics(df)

    assert res.total_revenue == 500.0
    assert res.total_orders == 3
    assert res.total_units == 10
    assert res.unique_customers == 2
    assert res.aov == pytest.approx(166.67, abs=0.01)
    assert res.basket_size == pytest.approx(3.33, abs=0.01)
    assert res.repeat_customer_rate == pytest.approx(0.50, abs=0.01)
    assert res.avg_discount_rate == pytest.approx(0.10, abs=0.01)

    # Top products table verification
    top_p = res.top_products_table
    assert top_p.iloc[0]["product"] == "Widget A"
    assert top_p.iloc[0]["sales"] == 300.0  # 100 + 200
    assert top_p.iloc[0]["share_pct"] == pytest.approx(60.0, abs=0.1)


def test_finance_hand_computed_revenue():
    """Hand calculation verification for revenue budget variance.

    Data:
      Actual = 1,200.0, Budget = 1,000.0
      var_abs = 1,200 - 1,000 = +200.0
      var_pct = 200 / 1000 = +20.0%
      is_favorable = True (higher revenue is favorable)
    """
    df = pd.DataFrame(
        {
            "dept": ["Sales East", "Sales West"],
            "revenue_actual": [700.0, 500.0],
            "revenue_budget": [600.0, 400.0],
        }
    )

    res = compute_finance_analytics(
        df,
        account_col="dept",
        actual_col="revenue_actual",
        budget_col="revenue_budget",
    )

    assert res.total_actual == 1200.0
    assert res.total_budget == 1000.0
    assert res.variance_abs == 200.0
    assert res.variance_pct == 20.0
    assert res.is_favorable is True
    assert len(res.waterfall_steps) >= 3


def test_finance_hand_computed_expense_sign_convention():
    """Hand calculation verification for expense/cost budget variance.

    Convention: For costs, spending over budget is UNFAVORABLE.
    Data:
      Cost Actual = 1,200.0, Cost Budget = 1,000.0
      Actual exceeded budget by 200.0 -> unfavorable!
    """
    df = pd.DataFrame(
        {
            "category": ["Cloud Servers", "Contractors"],
            "cost_actual": [800.0, 400.0],
            "cost_budget": [600.0, 400.0],
        }
    )

    res = compute_finance_analytics(
        df,
        account_col="category",
        actual_col="cost_actual",
        budget_col="cost_budget",
    )

    assert res.total_actual == 1200.0
    assert res.total_budget == 1000.0
    # Over budget by 200 on costs is unfavorable
    assert res.is_favorable is False


def test_workforce_hand_computed():
    """Hand calculation verification for HR/workforce metrics.

    Data:
      E1: Eng,   50,000, 3 yrs, 4 rating, Active
      E2: Eng,   70,000, 5 yrs, 5 rating, Active
      E3: Sales, 60,000, 2 yrs, 3 rating, Terminated
      E4: Sales, 80,000, 4 yrs, 4 rating, Active
      E5: HR,    90,000, 1 yrs, 2 rating, Left

    Hand calculations:
      Headcount        = 5
      Dept count       = 3 (Eng, Sales, HR)
      Salaries         = [50k, 60k, 70k, 80k, 90k]
      Median salary    = 70,000.0
      Mean salary      = 350,000 / 5 = 70,000.0
      Q25 = 60k, Q75 = 80k -> IQR = 20,000.0
      Turnover rate    = 2 / 5 = 0.40 (40.0% terminated/left)
    """
    df = pd.DataFrame(
        {
            "emp_id": ["E1", "E2", "E3", "E4", "E5"],
            "department": ["Eng", "Eng", "Sales", "Sales", "HR"],
            "salary": [50000.0, 70000.0, 60000.0, 80000.0, 90000.0],
            "tenure_years": [3, 5, 2, 4, 1],
            "performance_score": [4, 5, 3, 4, 2],
            "status": ["Active", "Active", "Terminated", "Active", "Left"],
        }
    )

    res = compute_workforce_analytics(df)

    assert res.headcount == 5
    assert res.departments_count == 3
    assert res.median_salary == 70000.0
    assert res.mean_salary == 70000.0
    assert res.salary_iqr == 20000.0
    assert res.turnover_rate == pytest.approx(0.40, abs=0.01)
    assert res.tenure_perf_corr is not None


def test_feedback_hand_computed_nps_and_csat():
    """Hand calculation verification for NPS and CSAT scores.

    Data: 10 customer ratings on standard 0-10 NPS scale:
      Ratings = [10, 9, 9, 8, 8, 7, 6, 5, 4, 2]

    Classification:
      Promoters (9-10) = {10, 9, 9} -> count 3 -> 30.0%
      Passives (7-8)   = {8, 8, 7}  -> count 3 -> 30.0%
      Detractors (0-6) = {6, 5, 4, 2} -> count 4 -> 40.0%

    Formulas:
      NPS  = %Promoters - %Detractors = 30.0 - 40.0 = -10.0
      CSAT = % Satisfied (rating >= 8) = (3 + 2) / 10 = 5 / 10 = 50.0%
      Avg  = (10+9+9+8+8+7+6+5+4+2) / 10 = 68 / 10 = 6.8
    """
    df = pd.DataFrame(
        {
            "response_id": list(range(1, 11)),
            "nps_rating": [10, 9, 9, 8, 8, 7, 6, 5, 4, 2],
            "ticket_id": [f"T-{i}" for i in range(1, 11)],
            "resolution_hours": [2.5, 3.0, 1.0, 4.0, 2.0, 5.0, 6.0, 8.0, 3.5, 4.0],
            "priority": ["Low", "Low", "Med", "High", "Low", "Med", "High", "High", "Low", "Med"],
        }
    )

    res = compute_feedback_analytics(df)

    assert res.total_responses == 10
    assert res.promoter_pct == 30.0
    assert res.passive_pct == 30.0
    assert res.detractor_pct == 40.0
    assert res.nps_score == -10.0
    assert res.csat_score == 50.0
    assert res.avg_rating == pytest.approx(6.8, abs=0.01)
    assert res.avg_resolution_time == pytest.approx(3.9, abs=0.01)
