import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import pytest
from export.pptx_builder import DeckInputs, ViewExportData, KPITileData, build_deck


def test_pptx_deck_with_domain_and_correlation_slides():
    fig_corr = go.Figure(go.Heatmap(z=[[1, 0.8], [0.8, 1]], x=["A", "B"], y=["A", "B"]))
    fig_wf = go.Figure(go.Waterfall(x=["Budget", "Variance", "Actual"], y=[100, 20, 120], measure=["relative", "relative", "total"]))

    deck_inputs = DeckInputs(
        dataset_name="sales_and_finance.xlsx",
        period_covered="Q1-Q4 2024",
        views=[
            ViewExportData(
                view_name="Executive Summary",
                kpi_tiles=[
                    KPITileData(label="Total Sales", value_display="$1.2M", delta_display="+15%", delta_positive=True),
                    KPITileData(label="AOV", value_display="$340", delta_display="+5%", delta_positive=True),
                ],
                trend_figure=None,
            ),
            ViewExportData(
                view_name="Budget Variance Waterfall",
                kpi_tiles=[],
                trend_figure=fig_wf,
            ),
            ViewExportData(
                view_name="Metric Correlation Matrix",
                kpi_tiles=[],
                trend_figure=fig_corr,
            ),
        ],
        risk_signals=[
            {"description": "Extreme portfolio concentration: top 20% of clients account for 82% of revenue.", "severity": "high"}
        ],
    )

    buffer = build_deck(deck_inputs)
    assert buffer is not None
    assert buffer.getbuffer().nbytes > 1000
