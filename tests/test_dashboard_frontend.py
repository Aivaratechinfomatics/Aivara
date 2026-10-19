"""
tests/test_dashboard_frontend.py — Automated verification for the Power BI executive dashboard frontend.
"""

from __future__ import annotations

import io
import os
from fastapi.testclient import TestClient

from dashboard_server import app


def test_dashboard_file_exists():
    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    assert os.path.exists(dashboard_path), f"Dashboard HTML not found at {dashboard_path}"
    
    with open(dashboard_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify key Power BI structural sections
    assert "Aivara Insight" in content
    assert "Power BI" in content
    assert "pbiPage-overview" in content, "Missing Executive Overview page"
    assert "pbiPage-decomp" in content, "Missing Decomposition Tree page"
    assert "pbiPage-matrix" in content, "Missing Financial Matrix page"
    assert "pbiPage-anomaly" in content, "Missing Anomaly Detector page"
    assert "pbiPage-transform" in content, "Missing Power Query Schema page"
    assert "pbiPage-export" in content, "Missing 16:9 PPTX Export page"


def test_dashboard_power_bi_visuals_and_panes():
    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "index.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify Visualizations and Fields Panes
    assert "Visualizations" in content
    assert "Data Fields" in content
    assert "pbi-page-tab" in content

    # Verify Decomposition Tree and Slicers
    assert "Decomposition Tree" in content
    assert "slicer-pill" in content
    assert "dynamicSlicerPills" in content


def test_dashboard_launch_scripts():
    root = os.path.dirname(os.path.dirname(__file__))
    run_dash = os.path.join(root, "run_dashboard.bat")
    run_all = os.path.join(root, "run_all.bat")
    
    assert os.path.exists(run_dash), "run_dashboard.bat must exist"
    assert os.path.exists(run_all), "run_all.bat must exist"


def test_dashboard_api_endpoints():
    client = TestClient(app)

    # 1. Test Sample API
    r_sample = client.get("/api/sample?type=commerce")
    assert r_sample.status_code == 200
    data = r_sample.json()
    assert "filename" in data
    assert "kpis" in data
    assert len(data["kpis"]) >= 3
    assert "categories" in data
    assert "decompTree" in data

    # 2. Test File Upload API
    csv_content = b"date,region,sales\n2024-01-01,North,1000\n2024-01-02,South,2000\n"
    r_upload = client.post(
        "/api/upload",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r_upload.status_code == 200
    upload_data = r_upload.json()
    assert upload_data["filename"] == "test.csv"
    assert upload_data["rowCount"] == 2

    # 3. Test PPTX Export API
    r_pptx = client.post("/api/export_pptx")
    assert r_pptx.status_code == 200
    assert len(r_pptx.content) > 1000, "PPTX file size should be substantial"
    assert r_pptx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
