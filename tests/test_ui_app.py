import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from streamlit.testing.v1 import AppTest
from ingestion.classifier import ColumnClassification, classify_columns
from ingestion.cleaner import clean_dataframe
from ingestion.loader import load_file


def test_full_app_render_no_duplicate_element_ids():
    df = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=10, freq="D"),
        "sales": [100.0, 120.0, 130.0, 90.0, 110.0, 150.0, 140.0, 160.0, 170.0, 180.0],
        "region": ["North", "South", "North", "South", "North", "South", "North", "South", "North", "South"],
        "customer_segment": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
    })

    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = df
    at.session_state["dataset_name"] = "test.csv"
    at.session_state["classifications"] = {
        "date": ColumnClassification(name="date", role="date", confidence=1.0, reason="test"),
        "sales": ColumnClassification(name="sales", role="metric", confidence=1.0, reason="test"),
        "region": ColumnClassification(name="region", role="dimension", confidence=1.0, reason="test"),
        "customer_segment": ColumnClassification(name="customer_segment", role="dimension", confidence=1.0, reason="test"),
    }
    at.session_state["schema_confirmed"] = True
    at.run()

    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_inventory_excel():
    fpath = "Inventory-Records-Sample-Data.xlsx"
    if not os.path.exists(fpath):
        return
    with open(fpath, "rb") as fh:
        res = load_file(fh.read(), filename=fpath)
    clean_df, _ = clean_dataframe(res.dataframe)
    classified = classify_columns(clean_df)

    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = clean_df
    at.session_state["dataset_name"] = fpath
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()

    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_project_management_excel():
    fpath = "Project-Management-Sample-Data.xlsx"
    if not os.path.exists(fpath):
        return
    with open(fpath, "rb") as fh:
        res = load_file(fh.read(), filename=fpath)
    clean_df, _ = clean_dataframe(res.dataframe)
    classified = classify_columns(clean_df)

    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = clean_df
    at.session_state["dataset_name"] = fpath
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()

    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_commerce_dataset():
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "customer_id": ["C1", "C2", "C1", "C3", "C2"],
        "product_name": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
        "sales": [250.0, 150.0, 50.0, 300.0, 100.0],
        "quantity": [2, 1, 1, 3, 1],
    })
    classified = classify_columns(df)
    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = df
    at.session_state["dataset_name"] = "orders.csv"
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()
    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_finance_dataset():
    df = pd.DataFrame({
        "line_item": ["Revenue", "Cost of Goods", "R&D", "Marketing", "G&A"],
        "actual": [500000, 200000, 80000, 60000, 40000],
        "budget": [480000, 190000, 85000, 55000, 40000],
    })
    classified = classify_columns(df)
    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = df
    at.session_state["dataset_name"] = "p_and_l.csv"
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()
    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_workforce_dataset():
    df = pd.DataFrame({
        "emp_id": [1, 2, 3, 4, 5],
        "department": ["Engineering", "Sales", "Engineering", "Marketing", "HR"],
        "salary": [130000, 95000, 140000, 90000, 85000],
        "performance": [5, 4, 4, 3, 4],
        "status": ["Active", "Active", "Active", "Active", "Terminated"],
    })
    classified = classify_columns(df)
    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = df
    at.session_state["dataset_name"] = "workforce.csv"
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()
    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"


def test_full_app_render_feedback_dataset():
    df = pd.DataFrame({
        "respondent_id": [1, 2, 3, 4, 5, 6, 7, 8],
        "rating": [10, 9, 8, 10, 5, 3, 9, 7],
        "feedback": ["Loved it", "Great service", "Good", "Outstanding", "Slow", "Poor", "Nice", "Okay"],
    })
    classified = classify_columns(df)
    at = AppTest.from_file("app.py")
    at.session_state["cleaned_df"] = df
    at.session_state["dataset_name"] = "nps_survey.csv"
    at.session_state["classifications"] = {c.name: c for c in classified}
    at.session_state["schema_confirmed"] = True
    at.run()
    assert not at.exception, f"AppTest raised unexpected exception(s): {[str(e) for e in at.exception]}"

