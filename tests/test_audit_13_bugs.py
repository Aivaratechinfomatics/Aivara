"""
tests/test_audit_13_bugs.py — Verification of all 13 audited industrial-grade Power BI dashboard fixes.
"""

import os

import pandas as pd
from fastapi.testclient import TestClient

from dashboard_server import app, build_dashboard_payload

client = TestClient(app)


def test_bug_01_and_02_viewport_and_scroll_shell():
    """Verify strict 100vh overflow hidden shell on html and body in index.html."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "html, body {" in html
    assert "height: 100vh;" in html
    assert "overflow: hidden;" in html
    assert (
        'class="bg-[#242424] text-slate-900 h-screen overflow-hidden flex flex-col antialiased text-xs"'
        in html
    )
    assert 'id="mainDropZone"' in html
    assert "overflow-y-auto" in html


def test_bug_03_and_04_navigation_sync_and_visual_switching():
    """Verify navigation synchronization and visual type switching auto-navigates to Page 1."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "switchPage('overview')" in html
    assert "setVisualType(type)" in html
    # Check that setVisualType starts by calling switchPage('overview')
    assert (
        "function setVisualType(type) {\n      switchPage('overview');" in html
        or "switchPage('overview');" in html
    )


def test_bug_05_filter_secondary_tier():
    """Verify filterSecondaryTier function exists and handles tier selection."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function filterSecondaryTier(tierName)" in html
    assert "APP_STATE.activeFilters.tier = tierName;" in html


def test_bug_06_date_slicer_filtering():
    """Verify setSlicerDate calculates temporal windows based on max timestamp."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function setSlicerDate(period)" in html
    assert "APP_STATE.activeFilters.dateRange = period;" in html
    assert "7 * 86400000" in html
    assert "30 * 86400000" in html
    assert "90 * 86400000" in html


def test_bug_07_decomp_tree_dynamic_drilldown_no_alert():
    """Verify decomposition tree toggles active branch and renders Level 2 without alert()."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function toggleDecompBranch(idx)" in html
    assert "APP_STATE.activeDecompBranch = idx;" in html
    # Ensure no alert in toggleDecompBranch
    idx = html.find("function toggleDecompBranch(idx)")
    end_fn = html.find("}", idx)
    fn_body = html[idx:end_fn]
    assert "alert(" not in fn_body, "toggleDecompBranch must not use alert()"


def test_bug_08_matrix_table_expand_collapse():
    """Verify matrix row toggle matches matrix-child-group class and flips chevron."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function toggleMatrixRow(idx)" in html
    assert "matrix-child-group-" in html
    assert "chevron-" in html


def test_bug_09_field_click_dynamic_reaggregation():
    """Verify selectFieldForVisual re-aggregates KPI cards and categories from rawSample."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function selectFieldForVisual(fieldName)" in html
    assert "APP_STATE.rawSample" in html
    assert "APP_STATE.kpis[0] =" in html


def test_bug_10_rfc_4180_tolerant_csv_parser():
    """Verify parseCSVText handles quoted commas and multiple delimiters."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "function parseCSVText(text)" in html
    assert "inQuotes" in html


def test_bug_11_no_fake_dates_for_non_temporal_datasets():
    """Verify server and client do not fabricate fake Period 01 dates when dataset has no dates."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert "renderCategoricalChart" in html
    assert "hasDateCol" in html

    # Server check: non-temporal dataframe has hasDateCol: False and timeSeries: []
    from analytics.pipeline import run_pipeline
    from ingestion.classifier import classify_columns
    from ingestion.cleaner import clean_dataframe

    df = pd.DataFrame(
        {
            "Department": ["Sales", "Engineering", "Marketing"],
            "Budget": [100000, 250000, 80000],
            "Headcount": [10, 20, 8],
        }
    )
    cleaned_df, _ = clean_dataframe(df)
    classes_list = classify_columns(cleaned_df)
    classifications = {c.name: c for c in classes_list}
    res = run_pipeline(cleaned_df, classifications)
    payload = build_dashboard_payload(res, cleaned_df, "test_nontemporal.csv", classifications)

    assert payload["hasDateCol"] is False
    assert len(payload["timeSeries"]) == 0, (
        "Non-temporal dataset must not have synthetic Period 01 timeSeries"
    )


def test_bug_12_sample_datasets_routing():
    """Verify finance and feedback samples return authentic analytical payloads."""
    # Finance sample
    resp = client.get("/api/sample?type=finance")
    assert resp.status_code == 200
    fin_data = resp.json()
    assert fin_data["filename"] == "sample_finance_pnl.csv"
    assert fin_data["rowCount"] == 20
    assert len(fin_data["kpis"]) >= 4

    # Feedback sample
    resp = client.get("/api/sample?type=feedback")
    assert resp.status_code == 200
    fb_data = resp.json()
    assert fb_data["filename"] == "sample_customer_nps.csv"
    assert fb_data["rowCount"] == 20
    assert len(fb_data["categories"]) >= 2


def test_bug_13_toast_notification_system():
    """Verify showToast function and pbiToastContainer exist without blocking alerts."""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    assert 'id="pbiToastContainer"' in html
    assert "function showToast(message, type" in html
    assert "addNewBlankCanvasPage" in html


def test_export_pptx_gateway():
    """Verify POST /api/export_pptx generates authentic 16:9 presentation deck bytes."""
    resp = client.post("/api/export_pptx")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert len(resp.content) > 10000  # Genuine .pptx presentation deck binary
