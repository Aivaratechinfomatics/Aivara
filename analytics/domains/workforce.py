"""
analytics/domains/workforce.py — Specialized HR and people analytics.

Computes:
1. Total headcount and department staffing distribution.
2. Compensation analytics (median salary, IQR spread, department pay bands).
3. Attrition / Turnover rate.
4. Tenure vs Performance correlation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class WorkforceAnalyticsResult:
    headcount: int
    departments_count: int
    median_salary: float
    mean_salary: float
    salary_iqr: float
    turnover_rate: float | None
    tenure_perf_corr: float | None
    department_summary: pd.DataFrame
    salary_by_dept_table: pd.DataFrame


def compute_workforce_analytics(
    df: pd.DataFrame,
    emp_col: str | None = None,
    dept_col: str | None = None,
    salary_col: str | None = None,
    tenure_col: str | None = None,
    perf_col: str | None = None,
    status_col: str | None = None,
) -> WorkforceAnalyticsResult:
    """Computes HR and workforce intelligence metrics."""
    cols = df.columns
    if not emp_col:
        emp_col = next((c for c in cols if re.search(r"(emp[_\s]?id|employee|worker|staff|person)", c, re.I)), None)
    if not dept_col:
        dept_col = next((c for c in cols if re.search(r"(dept|department|division|business[_\s]?unit|team|function)", c, re.I)), None)
    if not salary_col:
        salary_col = next((c for c in cols if re.search(r"(salary|comp|compensation|base[_\s]?pay|wages|rate)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not tenure_col:
        tenure_col = next((c for c in cols if re.search(r"(tenure|years[_\s]?at|service|experience|months)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not perf_col:
        perf_col = next((c for c in cols if re.search(r"(perf|performance|rating|score|evaluation)", c, re.I) and pd.api.types.is_numeric_dtype(df[c])), None)
    if not status_col:
        status_col = next((c for c in cols if re.search(r"(status|attrition|active|employment[_\s]?status|terminated)", c, re.I)), None)

    # 1. Headcount
    headcount = df[emp_col].dropna().nunique() if emp_col else len(df)
    n_depts = df[dept_col].dropna().nunique() if dept_col else 1

    # 2. Compensation
    if salary_col and pd.api.types.is_numeric_dtype(df[salary_col]):
        salaries = df[salary_col].dropna()
        med_sal = float(salaries.median()) if not salaries.empty else 0.0
        mean_sal = float(salaries.mean()) if not salaries.empty else 0.0
        q75, q25 = salaries.quantile(0.75), salaries.quantile(0.25)
        sal_iqr = float(q75 - q25)
    else:
        med_sal, mean_sal, sal_iqr = 0.0, 0.0, 0.0

    # 3. Turnover / Attrition
    turnover = None
    if status_col:
        status_s = df[status_col].dropna().astype(str).str.lower()
        terminated_count = status_s.str.contains(r"(?:term|left|resigned|inactive|no\b|churn)").sum()
        if len(status_s) > 0:
            turnover = float(terminated_count / len(status_s))

    # 4. Correlation Tenure vs Performance
    tenure_perf_corr = None
    if tenure_col and perf_col:
        valid = df[[tenure_col, perf_col]].dropna()
        if len(valid) >= 5 and valid[tenure_col].nunique() > 1 and valid[perf_col].nunique() > 1:
            r = valid.corr().iloc[0, 1]
            if not np.isnan(r):
                tenure_perf_corr = round(float(r), 3)

    # 5. Department Summary Table
    dept_table = pd.DataFrame()
    sal_table = pd.DataFrame()
    if dept_col:
        agg_dict = {dept_col: "count"}
        if salary_col:
            agg_dict[salary_col] = ["count", "mean", "median", "min", "max"]
        
        dept_grouped = df.groupby(dept_col).size().reset_index(name="headcount")
        dept_grouped["share_pct"] = (dept_grouped["headcount"] / max(1, headcount)) * 100.0
        dept_grouped = dept_grouped.sort_values(by="headcount", ascending=False)
        dept_table = dept_grouped

        if salary_col:
            sal_by_dept = (
                df.groupby(dept_col)[salary_col]
                .agg(headcount="count", avg_salary="mean", median_salary="median")
                .reset_index()
                .sort_values(by="avg_salary", ascending=False)
            )
            sal_table = sal_by_dept

    return WorkforceAnalyticsResult(
        headcount=headcount,
        departments_count=n_depts,
        median_salary=round(med_sal, 2),
        mean_salary=round(mean_sal, 2),
        salary_iqr=round(sal_iqr, 2),
        turnover_rate=round(turnover, 3) if turnover is not None else None,
        tenure_perf_corr=tenure_perf_corr,
        department_summary=dept_table,
        salary_by_dept_table=sal_table,
    )
