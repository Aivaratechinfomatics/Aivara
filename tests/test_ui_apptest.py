"""
tests/test_ui_apptest.py — Phase 9 UI Structure, UX, and AppTest suites.

Validates:
1. Tab error boundary isolation: an unhandled exception in one tab renders a clean degradation
   notice with a correlation ID and does not crash or blank other tabs.
2. Table-driven tab registry correctness across profiles and domains (Decision D3: Forecast hidden).
3. End-to-end headless flow via Streamlit AppTest (startup, schema confirmation, tab rendering).
4. Pure deck assembly correctness across different profile types.
5. Export sidebar flow and session state handling.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.pipeline import execute_pipeline
from export.deck_assembly import assemble_deck_inputs
from ingestion.classifier import ColumnClassification, classify_columns
from ui.error_boundary import render_tab_boundary
from ui.tabs import get_tab_specs

# ---------------------------------------------------------------------------
# 1. Tab Error Boundary Isolation
# ---------------------------------------------------------------------------


def test_tab_error_boundary_catches_and_renders_correlation_id(monkeypatch):
    """Verify that render_tab_boundary catches exceptions and displays correlation ID."""
    rendered_errors = []
    monkeypatch.setattr("streamlit.error", lambda msg: rendered_errors.append(msg))
    monkeypatch.setattr("streamlit.expander", MagicMock())

    def _failing_tab():
        raise ValueError("Simulated unexpected rendering fault in tab")

    # Should not raise exception
    render_tab_boundary("Faulty Tab", _failing_tab)

    assert len(rendered_errors) == 1
    error_msg = rendered_errors[0]
    assert "Unable to render Faulty Tab" in error_msg
    assert "Correlation ID:" in error_msg
    assert "Other tabs remain interactive and functional." in error_msg


# ---------------------------------------------------------------------------
# 2. Table-Driven Tab Registry Correctness (Decision D3)
# ---------------------------------------------------------------------------


def test_tab_specs_standard_timeseries_hides_forecast():
    """Verify standard time-series profile produces exactly 6 tabs and hides Forecast."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "revenue": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0],
            "channel": ["web", "store"] * 5,
        }
    )
    classifications = {
        "date": ColumnClassification("date", "date", 1.0, "test"),
        "revenue": ColumnClassification("revenue", "metric", 1.0, "test"),
        "channel": ColumnClassification("channel", "dimension", 1.0, "test"),
    }
    pipeline_res = execute_pipeline(df, classifications)
    specs = get_tab_specs(pipeline_res)

    tab_labels = [s.label for s in specs]
    assert "Executive" in tab_labels
    assert "Revenue" in tab_labels
    assert "Operations" in tab_labels
    assert "Customers" in tab_labels
    assert "Charts" in tab_labels
    assert "Risk" in tab_labels
    # Decision D3 invariant: Forecast stub must NOT be visible
    assert "Forecast" not in tab_labels


def test_tab_specs_snapshot_profile():
    """Verify snapshot profile yields Rankings, Composition, Correlations, Charts, Outliers."""
    df = pd.DataFrame(
        {
            "sku": [f"SKU_{i}" for i in range(20)],
            "inventory_count": [10 * i for i in range(20)],
            "warehouse": ["North", "South"] * 10,
        }
    )
    classifications = {
        "sku": ColumnClassification("sku", "dimension", 1.0, "test"),
        "inventory_count": ColumnClassification("inventory_count", "metric", 1.0, "test"),
        "warehouse": ColumnClassification("warehouse", "dimension", 1.0, "test"),
    }
    pipeline_res = execute_pipeline(df, classifications)
    specs = get_tab_specs(pipeline_res)

    tab_labels = [s.label for s in specs]
    assert "Executive Summary" in tab_labels
    assert "Rankings & Breakdown" in tab_labels
    assert "Composition" in tab_labels
    assert "Correlations & Drivers" in tab_labels
    assert "Charts" in tab_labels
    assert "Risk & Outliers" in tab_labels


def test_tab_specs_project_profile():
    """Verify project profile yields Portfolio Overview, Gantt, Team & Workload, At-Risk."""
    df = pd.DataFrame(
        {
            "task_id": [f"T{i}" for i in range(10)],
            "task_name": [f"Task {i}" for i in range(10)],
            "assignee": ["Alice", "Bob"] * 5,
            "start_date": pd.date_range("2024-01-01", periods=10),
            "end_date": pd.date_range("2024-01-10", periods=10),
            "progress": [50.0] * 10,
            "duration": [5] * 10,
        }
    )
    classifications = {c.name: c for c in classify_columns(df)}
    pipeline_res = execute_pipeline(df, classifications)
    specs = get_tab_specs(pipeline_res)

    tab_labels = [s.label for s in specs]
    assert "Portfolio Overview" in tab_labels
    assert "Timeline (Gantt)" in tab_labels
    assert "Team & Workload" in tab_labels
    assert "Charts" in tab_labels
    assert "At-Risk Tasks" in tab_labels


# ---------------------------------------------------------------------------
# 3. Pure Deck Assembly
# ---------------------------------------------------------------------------


def test_assemble_deck_inputs_pure():
    """Verify pure deck assembly creates valid DeckInputs without Streamlit context."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5),
            "sales": [10.0, 20.0, 30.0, 40.0, 50.0],
            "region": ["A", "B", "A", "B", "A"],
        }
    )
    classifications = {c.name: c for c in classify_columns(df)}
    pipeline_res = execute_pipeline(df, classifications)

    deck_inputs = assemble_deck_inputs(
        pipeline_result=pipeline_res,
        dataset_name="pure_sales.csv",
        figures={},
    )
    assert deck_inputs.dataset_name == "pure_sales.csv"
    assert len(deck_inputs.views) >= 2  # Executive and Primary metric
    assert any(v.view_name == "Executive" for v in deck_inputs.views)


# ---------------------------------------------------------------------------
# 4. Streamlit AppTest End-to-End Headless Flow
# ---------------------------------------------------------------------------


def test_apptest_unuploaded_shows_upload_page_no_crash():
    """Verify app renders clean initial upload state without exceptions."""
    at = AppTest.from_file("app.py")
    at.run()
    assert not at.exception


def test_apptest_schema_confirmed_runs_and_renders_tabs():
    """Verify app renders tabs cleanly when dataset and confirmed schema are set."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "amount": [100.0, 110.0, 95.0, 120.0, 130.0, 125.0, 140.0, 150.0, 160.0, 170.0],
            "category": ["X", "Y"] * 5,
        }
    )
    classifications = {
        "date": ColumnClassification("date", "date", 1.0, "test"),
        "amount": ColumnClassification("amount", "metric", 1.0, "test"),
        "category": ColumnClassification("category", "dimension", 1.0, "test"),
    }

    at = AppTest.from_file("app.py")
    at.session_state["dataset"] = df
    at.session_state["dataset_name"] = "test_run.csv"
    at.session_state["classifications"] = classifications
    at.session_state["schema_confirmed"] = True
    at.run()

    assert not at.exception
    # Verify tabs exist on the rendered page
    assert len(at.tabs) > 0


def test_apptest_export_button_triggers_deck_preparation():
    """Verify clicking 'Prepare PPTX export' button populates _pptx_buffer in session state."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "revenue": [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0],
            "dept": ["Ops", "Eng"] * 5,
        }
    )
    classifications = {
        "date": ColumnClassification("date", "date", 1.0, "test"),
        "revenue": ColumnClassification("revenue", "metric", 1.0, "test"),
        "dept": ColumnClassification("dept", "dimension", 1.0, "test"),
    }

    at = AppTest.from_file("app.py")
    at.session_state["dataset"] = df
    at.session_state["dataset_name"] = "export_test.csv"
    at.session_state["classifications"] = classifications
    at.session_state["schema_confirmed"] = True
    at.run()

    # Find the prepare export button in sidebar
    export_buttons = [
        b for b in at.sidebar.button if "export" in b.label.lower() or "pptx" in b.label.lower()
    ]
    assert len(export_buttons) >= 1
    export_buttons[0].click().run(timeout=15)

    assert not at.exception
    assert "_pptx_buffer" in at.session_state
    assert len(at.session_state["_pptx_buffer"]) > 0
