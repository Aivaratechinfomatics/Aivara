"""
tests/test_golden.py — characterization / golden snapshot tests.

Snapshots the pipeline outputs (profile, classifications, KPIs, risk signals,
executive takeaways) for all fixture and sample datasets to detect unintentional
regressions during hardening.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import run_pipeline
from ingestion.classifier import classify_columns
from ingestion.cleaner import clean_dataframe
from ingestion.loader import load_file

GOLDEN_DIR = Path(__file__).parent / "golden"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

DATASETS = [
    "clean.csv",
    "currency.csv",
    "inventory_sample.csv",
    "mixed_encoding.csv",
    "no_date.csv",
    "no_header.csv",
    "project_sample.csv",
    "semicolon.csv",
]


def _normalize_num(val: float | None) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None


def extract_pipeline_snapshot(filepath: str | Path, filename: str) -> dict:
    with open(filepath, "rb") as fh:
        raw_bytes = fh.read()

    lres = load_file(raw_bytes, filename=filename)
    clean_df, _ = clean_dataframe(lres.dataframe)
    classified = classify_columns(clean_df)
    cls_dict = {c.name: c for c in classified}

    st.session_state["dataset"] = clean_df
    st.session_state["cleaned_df"] = clean_df
    st.session_state["dataset_name"] = filename
    st.session_state["classifications"] = cls_dict

    pres = run_pipeline()
    prof = pres["profile"]

    kpi_dict = {}
    for name, kpi in (pres.get("kpis") or {}).items():
        kpi_dict[name] = {
            "current_value": _normalize_num(kpi.current_value),
            "prior_value": _normalize_num(kpi.prior_value),
            "pct_change": _normalize_num(kpi.pct_change),
            "abs_change": _normalize_num(kpi.abs_change),
            "unit": kpi.unit,
        }

    risk_list = []
    for r in pres.get("risk_signals") or []:
        if isinstance(r, dict):
            risk_list.append({"description": r.get("description"), "severity": r.get("severity")})
        else:
            risk_list.append(
                {
                    "description": getattr(r, "description", str(r)),
                    "severity": getattr(r, "severity", "medium"),
                }
            )

    snapshot = {
        "dataset_name": filename,
        "shape": list(clean_df.shape),
        "columns": [str(c) for c in clean_df.columns],
        "classifications": {
            c.name: {"role": c.role, "confidence": _normalize_num(c.confidence)} for c in classified
        },
        "profile": {
            "profile_type": prof.profile_type,
            "domain_type": prof.domain_type,
            "primary_metric": prof.primary_metric,
            "primary_date_col": prof.primary_date_col,
            "entity_dimension": prof.entity_dimension,
            "grouping_dimensions": prof.grouping_dimensions,
        },
        "kpis": kpi_dict,
        "risk_signals": risk_list,
        "executive_takeaways": pres.get("executive_takeaways") or [],
    }
    return snapshot


def generate_or_verify_golden(filename: str):
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDEN_DIR / f"{Path(filename).stem}.json"
    fixture_path = FIXTURES_DIR / filename

    live_snapshot = extract_pipeline_snapshot(fixture_path, filename)

    if not golden_path.exists() or os.environ.get("UPDATE_GOLDEN") == "1":
        with open(golden_path, "w", encoding="utf-8") as fh:
            json.dump(live_snapshot, fh, indent=2, sort_keys=True)
        return

    with open(golden_path, encoding="utf-8") as fh:
        expected = json.load(fh)

    assert live_snapshot == expected, (
        f"Golden regression detected for {filename}!\nDiff: {live_snapshot} != {expected}"
    )


@pytest.mark.parametrize("filename", DATASETS)
def test_golden_dataset(filename: str):
    generate_or_verify_golden(filename)
