"""
tests/test_export_hardening.py — Phase 8 Export Hardening Verification.

Validates:
1. Kaleido hang / timeout handling with graceful slide placeholders (Audit 3.7).
2. Kaleido crash / failure handling with graceful slide placeholders.
3. Empty / degraded deck generation without crash (empty views, empty KPIs).
4. Large drivers table handling (50+ rows clipped to top 10 gracefully).
5. OpenXML presentation zip structure integrity.
6. Number consistency between pipeline KPIs and PPTX slide text.
7. Total offline isolation (zero network / client imports in export/).
"""

from __future__ import annotations

import ast
import io
import os
import sys
import time
import zipfile

import plotly.graph_objects as go
import pytest
from pptx import Presentation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export.chart_images import figure_to_png_bytes
from export.pptx_builder import DeckInputs, KPITileData, ViewExportData, build_deck


def _extract_all_text_from_pptx(pptx_bytes: bytes) -> list[str]:
    """Helper to extract all text from all shapes in a PPTX presentation."""
    prs = Presentation(io.BytesIO(pptx_bytes))
    all_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = "".join(r.text for r in para.runs).strip()
                    if text:
                        all_text.append(text)
    return all_text


# ---------------------------------------------------------------------------
# 1 & 2. Kaleido Hang / Timeout & Crash Handling (Audit 3.7)
# ---------------------------------------------------------------------------


def test_figure_to_png_bytes_timeout_raises_timeout_error():
    """Verify that figure_to_png_bytes times out when kaleido rendering hangs."""
    fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))

    def _hanging_to_image(*args, **kwargs):
        time.sleep(0.5)
        return b"fake-png-bytes"

    fig.to_image = _hanging_to_image

    with pytest.raises(TimeoutError, match="timed out after"):
        figure_to_png_bytes(fig, timeout=0.05)


def test_deck_builds_with_placeholder_when_kaleido_crashes():
    """Verify that when kaleido crashes (RuntimeError), the deck builds successfully
    and includes the graceful chart preview unavailable placeholder card."""
    fig = go.Figure(go.Bar(x=["A", "B"], y=[10, 20]))

    def _crashing_to_image(*args, **kwargs):
        raise RuntimeError("Kaleido subprocess terminated unexpectedly with signal SIGKILL")

    fig.to_image = _crashing_to_image

    view = ViewExportData(
        view_name="Sales Performance",
        kpi_tiles=[KPITileData(label="Revenue", value_display="$100k")],
        trend_figure=fig,
    )
    deck_inputs = DeckInputs(
        dataset_name="crashed_chart.csv",
        period_covered="2024",
        views=[view],
        risk_signals=[],
    )

    deck_stream = build_deck(deck_inputs)
    assert deck_stream is not None
    deck_bytes = deck_stream.getvalue()
    assert len(deck_bytes) > 0

    texts = _extract_all_text_from_pptx(deck_bytes)
    assert any("Chart Preview Unavailable" in t for t in texts)
    assert any("Offline graphics renderer did not complete" in t for t in texts)


def test_deck_builds_with_placeholder_when_kaleido_hangs(monkeypatch):
    """Verify that when kaleido hangs, timeout fires and deck includes placeholder."""
    fig = go.Figure(go.Bar(x=["X", "Y"], y=[1, 2]))

    def _hanging_to_image(*args, **kwargs):
        time.sleep(1.0)
        return b"late-bytes"

    fig.to_image = _hanging_to_image

    # Set very small timeout via env or parameter
    monkeypatch.setattr("export.chart_images.KALEIDO_TIMEOUT_SECONDS", 0.05)

    view = ViewExportData(
        view_name="Hanging View",
        kpi_tiles=[KPITileData(label="Volume", value_display="1,200")],
        trend_figure=fig,
    )
    deck_inputs = DeckInputs(
        dataset_name="hang.csv",
        period_covered="2024",
        views=[view],
        risk_signals=[],
    )

    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()
    texts = _extract_all_text_from_pptx(deck_bytes)
    assert any("Chart Preview Unavailable" in t for t in texts)


# ---------------------------------------------------------------------------
# 3. Empty / Degraded Decks
# ---------------------------------------------------------------------------


def test_deck_empty_views():
    """Verify deck builds when views list is completely empty."""
    deck_inputs = DeckInputs(
        dataset_name="empty_views.csv",
        period_covered="N/A",
        views=[],
        risk_signals=[],
    )
    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()
    texts = _extract_all_text_from_pptx(deck_bytes)

    assert any("No domain views selected for export" in t for t in texts)
    assert any("No executive summary KPIs or insights available" in t for t in texts)


def test_deck_single_kpi_no_figures():
    """Verify deck builds with a single KPI tile and no figures."""
    view = ViewExportData(
        view_name="Minimalist View",
        kpi_tiles=[KPITileData(label="Solo Metric", value_display="42.0%")],
    )
    deck_inputs = DeckInputs(
        dataset_name="single_kpi.csv",
        period_covered="Current",
        views=[view],
        risk_signals=[],
    )
    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()
    texts = _extract_all_text_from_pptx(deck_bytes)

    assert "Solo Metric" in texts
    assert "42.0%" in texts


def test_deck_view_with_no_kpi_and_no_figures():
    """Verify view slide shows fallback note when both KPIs and charts are absent."""
    view = ViewExportData(
        view_name="Blank Domain",
        kpi_tiles=[],
        trend_figure=None,
    )
    deck_inputs = DeckInputs(
        dataset_name="blank.csv",
        period_covered="Q1",
        views=[view],
        risk_signals=[],
    )
    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()
    texts = _extract_all_text_from_pptx(deck_bytes)

    assert any("No data or charts available for this view" in t for t in texts)


# ---------------------------------------------------------------------------
# 4. Large Drivers Table Stress Test
# ---------------------------------------------------------------------------


def test_deck_large_drivers_table_capped_safely():
    """Verify that a drivers table with 50+ categories is safely capped to top 10."""
    drivers = [
        {"category": f"Driver Category {i:02d}", "contribution_pct": round(50.0 - i * 1.5, 1)}
        for i in range(50)
    ]
    view = ViewExportData(
        view_name="Operations",
        kpi_tiles=[KPITileData(label="Efficiency", value_display="94%")],
        drivers_table=drivers,
        drivers_figure=None,
    )
    deck_inputs = DeckInputs(
        dataset_name="stress_drivers.csv",
        period_covered="Year to Date",
        views=[view],
        risk_signals=[],
    )
    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()
    texts = _extract_all_text_from_pptx(deck_bytes)

    assert "Top contributors" in texts
    # First top driver must appear
    assert any("Driver Category 00" in t for t in texts)
    # 9th top driver must appear
    assert any("Driver Category 09" in t for t in texts)
    # 20th driver should NOT appear (capped at top 10)
    assert not any("Driver Category 20" in t for t in texts)


# ---------------------------------------------------------------------------
# 5. OpenXML Zip Structure Integrity
# ---------------------------------------------------------------------------


def test_deck_openxml_zip_structure():
    """Verify that the generated PPTX is a valid OpenXML zip archive with standard parts."""
    view = ViewExportData(
        view_name="Finance",
        kpi_tiles=[KPITileData(label="Profit", value_display="$50k")],
    )
    deck_inputs = DeckInputs(
        dataset_name="openxml_test.csv",
        period_covered="Q2 2024",
        views=[view],
        risk_signals=[{"description": "Margin compression risk", "severity": "high"}],
    )
    deck_stream = build_deck(deck_inputs)
    deck_bytes = deck_stream.getvalue()

    with zipfile.ZipFile(io.BytesIO(deck_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "[Content_Types].xml" in namelist
        assert "_rels/.rels" in namelist
        assert "ppt/presentation.xml" in namelist
        assert "ppt/_rels/presentation.xml.rels" in namelist
        # Verify slide xml files exist
        slide_parts = [
            n for n in namelist if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        ]
        assert len(slide_parts) >= 4  # Cover, TOC, Exec, View, Risk, Closing


# ---------------------------------------------------------------------------
# 6. Number Consistency Between Pipeline KPIs and Slide Text
# ---------------------------------------------------------------------------


def test_number_consistency_pipeline_to_pptx():
    """Verify exact match of KPI labels, values, and deltas in slide text."""
    test_tiles = [
        KPITileData(
            label="Gross Merchandise Value",
            value_display="$4,819,203.45",
            delta_display="+12.4%",
            delta_positive=True,
        ),
        KPITileData(
            label="Average Order Value",
            value_display="$128.50",
            delta_display="-3.1%",
            delta_positive=False,
        ),
        KPITileData(
            label="Active Customers",
            value_display="37,504",
            delta_display=None,
            delta_positive=None,
        ),
    ]

    view = ViewExportData(
        view_name="Core KPIs",
        kpi_tiles=test_tiles,
    )
    deck_inputs = DeckInputs(
        dataset_name="numbers_check.csv",
        period_covered="FY2024",
        views=[view],
        risk_signals=[],
    )

    deck_stream = build_deck(deck_inputs)
    texts = _extract_all_text_from_pptx(deck_stream.getvalue())

    from export.formula_sanitizer import sanitize_for_formula_injection

    # Every label and formatted display value must appear verbatim (accounting for formula sanitization)
    for tile in test_tiles:
        sanitized_label = str(sanitize_for_formula_injection(tile.label))
        sanitized_val = str(sanitize_for_formula_injection(tile.value_display))
        assert sanitized_label in texts, f"Missing label: {sanitized_label}"
        assert sanitized_val in texts, f"Missing value: {sanitized_val}"
        if tile.delta_display:
            sanitized_delta = str(sanitize_for_formula_injection(tile.delta_display))
            assert sanitized_delta in texts, f"Missing delta: {sanitized_delta}"


# ---------------------------------------------------------------------------
# 7. Total Offline Isolation (Zero Network / LLM Imports in export/)
# ---------------------------------------------------------------------------


def test_export_package_has_no_network_or_llm_imports():
    """Verify that no module inside export/ imports insight.client, urllib, requests, or httpx."""
    export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "export")
    forbidden_modules = {
        "insight.client",
        "urllib",
        "urllib.request",
        "requests",
        "httpx",
        "http.client",
    }

    for root, _, files in os.walk(export_dir):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                with open(fpath, encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=fname)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert alias.name not in forbidden_modules, (
                                f"{fname} imports forbidden module {alias.name}"
                            )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module not in forbidden_modules, (
                            f"{fname} imports forbidden module {node.module}"
                        )
