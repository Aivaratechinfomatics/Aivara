"""Performance, scale, and concurrency regression tests for Aivara."""

from __future__ import annotations

import concurrent.futures
import time
import tracemalloc

import numpy as np
import pandas as pd

from analytics.pipeline import execute_pipeline
from analytics.profiler import profile_dataset
from export.deck_assembly import assemble_deck_inputs
from ingestion.classifier import classify_columns
from ingestion.cleaner import clean_dataframe


def _generate_synthetic_df(rows: int) -> pd.DataFrame:
    """Generate a realistic test dataset for performance regression testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=rows, freq="min")
    sales = np.random.lognormal(mean=4.5, sigma=0.8, size=rows)
    costs = sales * np.random.uniform(0.4, 0.8, size=rows)
    regions = np.random.choice(["North", "South", "East", "West", "Central"], size=rows)
    categories = np.random.choice(["Enterprise", "Mid-Market", "SMB", "Consumer"], size=rows)

    return pd.DataFrame(
        {
            "order_date": dates,
            "sales_amount": sales,
            "cost_of_goods": costs,
            "region": regions,
            "category": categories,
        }
    )


def test_10k_row_pipeline_latency_under_10s():
    """Verify that a 10,000 row dataset processes through the full pipeline well within 10s."""
    df = _generate_synthetic_df(10_000)

    start = time.perf_counter()
    clean_df, _ = clean_dataframe(df)
    classifications = classify_columns(clean_df)
    cls_dict = {c.name: c for c in classifications}
    _ = profile_dataset(clean_df, cls_dict)
    pipeline_res = execute_pipeline(clean_df, cls_dict)
    deck_inputs = assemble_deck_inputs(pipeline_res, dataset_name="perf_test.csv")
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0, f"Pipeline exceeded 10.0s SLA: {elapsed:.2f}s"
    assert pipeline_res.kpis is not None
    assert deck_inputs.dataset_name == "perf_test.csv"


def test_memory_consumption_bounded():
    """Verify that memory consumption for 25k rows stays well below 500MB (target: < 50MB)."""
    tracemalloc.start()
    try:
        df = _generate_synthetic_df(25_000)
        clean_df, _ = clean_dataframe(df)
        classifications = classify_columns(clean_df)
        cls_dict = {c.name: c for c in classifications}
        _ = profile_dataset(clean_df, cls_dict)
        _ = execute_pipeline(clean_df, cls_dict)

        _, peak = tracemalloc.get_traced_memory()
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 50.0, f"Peak memory {peak_mb:.2f}MB exceeded 50MB bound"
    finally:
        tracemalloc.stop()


def test_max_rows_sampling_safety(monkeypatch):
    """Verify that exceeding MAX_ROWS triggers safe sampling without error or crash."""
    import ingestion.loader as ldr

    monkeypatch.setattr(ldr, "MAX_ROWS_FULL_PROCESSING", 200)

    csv_data = "col_a,col_b\n" + "\n".join(f"{i},{i * 2}" for i in range(500)) + "\n"
    res = ldr.load_csv(csv_data.encode("utf-8"), filename="test_large.csv")

    assert res.success
    assert len(res.dataframe) == 200
    assert any("sampled down" in note for note in res.notes)
    assert res.error is None


def test_multi_session_concurrency():
    """Verify thread-safety and concurrency across 4 simultaneous pipeline executions."""
    dfs = [_generate_synthetic_df(2_000) for _ in range(4)]

    def _worker(worker_df: pd.DataFrame) -> dict:
        clean_df, _ = clean_dataframe(worker_df)
        classifications = classify_columns(clean_df)
        cls_dict = {c.name: c for c in classifications}
        res = execute_pipeline(clean_df, cls_dict)
        return res.to_dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_worker, df_item) for df_item in dfs]
        results = [f.result(timeout=15.0) for f in futures]

    assert len(results) == 4
    for r in results:
        assert "kpis" in r
