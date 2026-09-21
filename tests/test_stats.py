import numpy as np
import pandas as pd
import pytest
from analytics.stats import (
    compute_correlation_matrix,
    extract_key_drivers,
    compute_concentration_index,
    attribute_anomalies,
    generate_executive_takeaways,
)
from analytics.profiler import DatasetProfile, PROFILE_SNAPSHOT


def test_compute_correlation_matrix_and_drivers():
    np.random.seed(42)
    x = np.linspace(10, 100, 50)
    # y strongly correlated with x
    y = 2.5 * x + np.random.normal(0, 5, 50)
    # z inversely correlated with x
    z = -1.8 * x + np.random.normal(0, 5, 50)
    # w random
    w = np.random.normal(50, 10, 50)

    df = pd.DataFrame({"Spend": x, "Revenue": y, "Loss": z, "Noise": w})
    corr = compute_correlation_matrix(df, ["Spend", "Revenue", "Loss", "Noise"])

    assert not corr.empty
    assert corr.shape == (4, 4)
    assert corr.loc["Spend", "Revenue"] > 0.90
    assert corr.loc["Spend", "Loss"] < -0.90

    drivers = extract_key_drivers(corr, primary_metric="Revenue")
    assert len(drivers) >= 2
    top_pos = [d for d in drivers if "positive" in d.strength]
    assert len(top_pos) >= 1
    assert top_pos[0].metric_b == "Spend"


def test_compute_concentration_index_even_and_skewed():
    # Perfectly even
    even = pd.Series([10.0] * 100)
    res_even = compute_concentration_index(even)
    assert res_even.gini == pytest.approx(0.0, abs=0.02)
    assert res_even.risk_level == "Low"
    assert res_even.top_20_pct_share == pytest.approx(0.20, abs=0.02)

    # Heavily skewed (Pareto / power law)
    skewed = pd.Series([1.0] * 90 + [100.0] * 10)
    res_skewed = compute_concentration_index(skewed)
    assert res_skewed.gini > 0.60
    assert res_skewed.top_20_pct_share > 0.80
    assert res_skewed.risk_level in ("High", "Extreme")


def test_attribute_anomalies():
    # 95 normal values, 5 extreme outliers from "Region X"
    regions = ["North"] * 30 + ["South"] * 30 + ["East"] * 35 + ["Region X"] * 5
    sales = [100] * 95 + [10000] * 5
    df = pd.DataFrame({"Region": regions, "Sales": sales})

    attributions = attribute_anomalies(df, metric_col="Sales", dimension_cols=["Region"])
    assert len(attributions) == 1
    assert attributions[0].top_driver_dimension == "Region"
    assert attributions[0].top_driver_category == "Region X"
    assert attributions[0].category_share_of_outliers == 1.0


def test_generate_executive_takeaways():
    df = pd.DataFrame({
        "Product": ["Widget A", "Widget B", "Widget C"],
        "Sales": [10000, 3000, 1000],
    })
    profile = DatasetProfile(
        profile_type=PROFILE_SNAPSHOT,
        date_columns=[],
        primary_date_col=None,
        end_date_col=None,
        entity_dimension="Product",
        grouping_dimensions=[],
        all_dimensions=["Product"],
        primary_metric="Sales",
        secondary_metrics=[],
        rate_metrics=[],
        duration_metric=None,
        has_progress=False,
        n_rows=3,
        n_cols=2,
        summary_label="Snapshot",
    )
    takeaways = generate_executive_takeaways(df, profile)
    assert len(takeaways) >= 2
    assert any("Portfolio Scale" in t for t in takeaways)
    assert any("Top Contributor" in t and "Widget A" in t for t in takeaways)
