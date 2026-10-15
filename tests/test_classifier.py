import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ingestion.classifier import ROLE_DATE, ROLE_DIMENSION, ROLE_ID, ROLE_METRIC, classify_columns


def _role_map(df: pd.DataFrame) -> dict:
    return {c.name: c.role for c in classify_columns(df)}


def test_date_column_detected():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"] * 10),
            "value": range(30),
        }
    )
    roles = _role_map(df)
    assert roles["date"] == ROLE_DATE


def test_string_date_column_detected():
    df = pd.DataFrame(
        {
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"] * 10,
            "amount": range(30),
        }
    )
    roles = _role_map(df)
    assert roles["order_date"] == ROLE_DATE


def test_metric_column_detected():
    df = pd.DataFrame({"id": range(100), "revenue": [i * 1.5 for i in range(100)]})
    roles = _role_map(df)
    assert roles["revenue"] == ROLE_METRIC


def test_dimension_column_detected():
    df = pd.DataFrame(
        {
            "region": (["North", "South", "East", "West"] * 25),
            "value": range(100),
        }
    )
    roles = _role_map(df)
    assert roles["region"] == ROLE_DIMENSION


def test_id_column_detected():
    df = pd.DataFrame(
        {
            "customer_id": [f"CUST-{i}" for i in range(200)],
            "value": range(200),
        }
    )
    roles = _role_map(df)
    assert roles["customer_id"] == ROLE_ID


def test_numeric_low_cardinality_code_treated_as_dimension():
    df = pd.DataFrame(
        {
            "store_code": ([1, 2, 3, 4, 5] * 40),
            "value": range(200),
        }
    )
    roles = _role_map(df)
    assert roles["store_code"] == ROLE_DIMENSION


def test_entity_name_classified_as_dimension_not_id():
    # 46 products with 46 unique names must be classified as dimension, not ID
    df = pd.DataFrame(
        {
            "product_id": [f"P{100 + i}" for i in range(46)],
            "product_name": [f"Product Item {i}" for i in range(46)],
            "revenue": [100.0 + i for i in range(46)],
        }
    )
    classified = classify_columns(df)
    cmap = {c.name: c for c in classified}
    assert cmap["product_id"].role == ROLE_ID
    assert cmap["product_name"].role == ROLE_DIMENSION


def test_progress_rate_metric_detected():
    df = pd.DataFrame(
        {
            "task": [f"Task {i}" for i in range(10)],
            "progress": [0.0, 0.25, 0.5, 0.75, 1.0, 0.33, 0.8, 0.45, 0.9, 0.1],
        }
    )
    classified = classify_columns(df)
    cmap = {c.name: c for c in classified}
    assert cmap["progress"].role == ROLE_METRIC
    assert cmap["progress"].is_rate is True


def test_classifier_ambiguous_and_payload_and_overrides():
    from ingestion.classifier import (
        ROLE_TEXT,
        ambiguous_columns,
        apply_overrides,
        build_llm_classification_payload,
        classify_columns,
    )

    df = pd.DataFrame(
        {
            "id": range(10),
            "free_text": [
                "quick",
                "brown",
                "fox",
                "jumps",
                "over",
                "lazy",
                "dog",
                "lorem",
                "ipsum",
                "dolor",
            ],
            "ambig_date": [
                "2024-01-01",
                "2024-01-02",
                "not_date",
                "not_date",
                "not_date",
                "not_date",
                "not_date",
                "not_date",
                "not_date",
                "not_date",
            ],
        }
    )
    classified = classify_columns(df)
    ambig = ambiguous_columns(classified, threshold=0.8)
    assert len(ambig) > 0

    payload = build_llm_classification_payload(df, ambig, n_samples=3)
    assert len(payload) == len(ambig)
    assert "column_name" in payload[0]
    assert "sample_values" in payload[0]

    # Test apply_overrides
    overrides = {ambig[0].name: ROLE_TEXT}
    overridden = apply_overrides(classified, overrides)
    omap = {c.name: c for c in overridden}
    assert omap[ambig[0].name].role == ROLE_TEXT
    assert omap[ambig[0].name].confidence == 1.0


def test_classifier_low_confidence_date_name_match():
    # 5 out of 10 parse as dates and column name has "date"
    df = pd.DataFrame(
        {
            "ship_date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "unknown",
                "pending",
                "delayed",
                "tbd",
                "na",
            ],
            "val": range(10),
        }
    )
    classified = classify_columns(df)
    cmap = {c.name: c for c in classified}
    assert cmap["ship_date"].role == ROLE_DATE
    assert cmap["ship_date"].confidence <= 0.6


def test_classifier_near_unique_string_id_large_dataset():
    # >100 rows, unique_ratio >= 0.95, no explicit "id" in name
    df = pd.DataFrame(
        {
            "serial_number_code": [f"SN-{i:05d}" for i in range(120)],
            "val": range(120),
        }
    )
    classified = classify_columns(df)
    cmap = {c.name: c for c in classified}
    assert cmap["serial_number_code"].role == ROLE_ID


def test_classifier_remaining_branches():
    from ingestion.classifier import ROLE_ID, ROLE_TEXT, classify_columns

    # Ignore _is_duplicate
    df = pd.DataFrame({"_is_duplicate": [False, True], "val": [1, 2]})
    classified = classify_columns(df)
    assert len(classified) == 1
    assert classified[0].name == "val"

    # String column that doesn't match id, label, date, or low cardinality -> ROLE_TEXT
    df_text = pd.DataFrame(
        {
            "free_notes": [f"Rambling text value {i % 250}" for i in range(500)],
        }
    )
    c_text = classify_columns(df_text)
    assert c_text[0].role == ROLE_TEXT

    # ID near unique ratio floor without id or code in name
    df_id = pd.DataFrame(
        {
            "token_sequence": [f"TK_{i:04d}" for i in range(150)],
        }
    )
    c_id = classify_columns(df_id)
    assert c_id[0].role == ROLE_ID
