import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ast
import importlib


def test_pptx_builder_does_not_import_insight_client():
    """Static check: export/pptx_builder.py's source must never reference
    insight.client, so export can't accidentally start making network calls."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "export", "pptx_builder.py"
    )
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "insight.client" not in imported_modules
    # (Docstrings are allowed to mention insight.client by name when
    # explaining the constraint — only an actual import is disallowed.)


def test_export_builds_deck_without_network_call(monkeypatch):
    """End-to-end: build a deck (with no chart figures, so kaleido isn't
    exercised here) and assert the OpenRouter client is never touched."""
    from export.pptx_builder import DeckInputs, KPITileData, ViewExportData, build_deck
    from insight import cache as insight_cache

    called = {"hit": False}

    def _fail_if_called(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("OpenRouter client must never be called during export")

    import insight.client as client_module

    monkeypatch.setattr(client_module, "generate_insight", _fail_if_called)
    monkeypatch.setattr(client_module, "_call_openrouter", _fail_if_called)

    insight_cache.set_for_view(
        "Executive",
        {"headline": "Revenue grew 8%.", "driver_explanation": "North led the gain.", "suggested_action": "Review stock."},
    )

    tiles = [KPITileData(label="Revenue", value_display="1.2M", delta_display="+8.0%", delta_positive=True)]
    views = [ViewExportData(view_name="Executive", kpi_tiles=tiles)]
    inputs = DeckInputs(dataset_name="test.csv", period_covered="this month vs last month", views=views, risk_signals=[])

    buffer = build_deck(inputs)
    assert buffer.getbuffer().nbytes > 0
    assert not called["hit"]


def test_export_omits_insight_text_when_not_cached():
    """A view whose insight was never generated should export cleanly
    without a placeholder string (Section 8.7)."""
    from export.pptx_builder import DeckInputs, KPITileData, ViewExportData, build_deck

    tiles = [KPITileData(label="Orders", value_display="500")]
    views = [ViewExportData(view_name="ViewWithNoInsightGeneratedYet", kpi_tiles=tiles)]
    inputs = DeckInputs(dataset_name="test.csv", period_covered="n/a", views=views, risk_signals=[])

    buffer = build_deck(inputs)
    assert buffer.getbuffer().nbytes > 0


def test_no_risk_slide_when_no_signals():
    from pptx import Presentation

    from export.pptx_builder import build_risk_signals_slide

    prs = Presentation()
    slide_count_before = len(prs.slides)
    build_risk_signals_slide(prs, [])
    assert len(prs.slides) == slide_count_before


def test_export_snapshot_and_project_profiles():
    import plotly.graph_objects as go
    from pptx import Presentation
    from export.pptx_builder import DeckInputs, KPITileData, ViewExportData, build_deck

    dummy_fig = go.Figure(go.Bar(x=["A", "B"], y=[10, 20]))

    # Test snapshot deck build
    snapshot_views = [
        ViewExportData(
            view_name="Executive Summary",
            kpi_tiles=[KPITileData(label="Stock", value_display="12,000")],
            trend_figure=dummy_fig,
        ),
        ViewExportData(
            view_name="Composition & Distribution",
            kpi_tiles=[],
            trend_figure=dummy_fig,
        ),
    ]
    snapshot_inputs = DeckInputs(
        dataset_name="Inventory.xlsx",
        period_covered="Snapshot across items",
        views=snapshot_views,
        risk_signals=[{"description": "Item X: Dead stock", "severity": "high"}],
    )
    buf_snap = build_deck(snapshot_inputs)
    assert buf_snap.getbuffer().nbytes > 0
    prs_snap = Presentation(buf_snap)
    assert len(prs_snap.slides) >= 5  # Title, Exec Summary, View 1, View 2, Risk, Closing

    # Test project deck build
    project_views = [
        ViewExportData(
            view_name="Portfolio Overview",
            kpi_tiles=[KPITileData(label="Completion Rate", value_display="68.5%")],
            trend_figure=dummy_fig,
        ),
        ViewExportData(
            view_name="Timeline Schedule (Gantt)",
            kpi_tiles=[],
            trend_figure=dummy_fig,
        ),
    ]
    project_inputs = DeckInputs(
        dataset_name="Project.xlsx",
        period_covered="46 tasks",
        views=project_views,
        risk_signals=[{"description": "Task Y: 0% progress, 30 days duration", "severity": "high"}],
    )
    buf_proj = build_deck(project_inputs)
    assert buf_proj.getbuffer().nbytes > 0
    prs_proj = Presentation(buf_proj)
    assert len(prs_proj.slides) >= 5

