#!/usr/bin/env python3
"""
scripts/bench.py — Performance & scale benchmark harness (Phase 11).

Measures:
1. Per-stage execution time (cleaning, classification, profiling, pipeline, export assembly).
2. Peak memory consumption via tracemalloc.
3. Scaling characteristics across dataset sizes (1k, 10k, 50k, 100k rows).
4. Multi-session concurrency throughput.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import time
import tracemalloc
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.pipeline import execute_pipeline
from analytics.profiler import profile_dataset
from export.deck_assembly import assemble_deck_inputs
from ingestion.classifier import classify_columns
from ingestion.cleaner import clean_dataframe


def generate_synthetic_dataset(rows: int) -> pd.DataFrame:
    """Generate a realistic business dataset with dates, metrics, and dimensions."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=rows, freq="min")
    sales = np.random.lognormal(mean=4.5, sigma=0.8, size=rows)
    costs = sales * np.random.uniform(0.4, 0.8, size=rows)
    regions = np.random.choice(["North", "South", "East", "West", "Central"], size=rows)
    categories = np.random.choice(["Enterprise", "Mid-Market", "SMB", "Consumer"], size=rows)
    satisfaction = np.random.uniform(1.0, 5.0, size=rows)
    cust_ids = [f"CUST_{i % (rows // 5 + 1):06d}" for i in range(rows)]

    return pd.DataFrame(
        {
            "order_date": dates,
            "sales_amount": sales,
            "cost_of_goods": costs,
            "region": regions,
            "customer_segment": categories,
            "satisfaction_score": satisfaction,
            "customer_id": cust_ids,
        }
    )


def benchmark_pipeline_scale(rows: int) -> dict[str, Any]:
    """Benchmark end-to-end processing of a dataset of given row count."""
    df_raw = generate_synthetic_dataset(rows)

    tracemalloc.start()
    t0 = time.perf_counter()

    # 1. Cleaning
    t_clean_start = time.perf_counter()
    clean_df, _ = clean_dataframe(df_raw)
    t_clean = (time.perf_counter() - t_clean_start) * 1000

    # 2. Classification
    t_class_start = time.perf_counter()
    classifications = classify_columns(clean_df)
    cls_dict = {c.name: c for c in classifications}
    t_class = (time.perf_counter() - t_class_start) * 1000

    # 3. Profiling
    t_prof_start = time.perf_counter()
    _ = profile_dataset(clean_df, cls_dict)
    t_prof = (time.perf_counter() - t_prof_start) * 1000

    # 4. Pipeline Execution
    t_pipe_start = time.perf_counter()
    pipeline_res = execute_pipeline(clean_df, cls_dict)
    t_pipe = (time.perf_counter() - t_pipe_start) * 1000

    # 5. Export Deck Assembly
    t_export_start = time.perf_counter()
    deck_inputs = assemble_deck_inputs(pipeline_res, dataset_name="bench.csv", figures={})
    t_export = (time.perf_counter() - t_export_start) * 1000

    total_time_ms = (time.perf_counter() - t0) * 1000
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_mem / (1024 * 1024)

    return {
        "rows": rows,
        "clean_ms": round(t_clean, 1),
        "classify_ms": round(t_class, 1),
        "profile_ms": round(t_prof, 1),
        "pipeline_ms": round(t_pipe, 1),
        "export_ms": round(t_export, 1),
        "total_ms": round(total_time_ms, 1),
        "peak_mb": round(peak_mb, 2),
        "views_generated": len(deck_inputs.views),
    }


def benchmark_concurrency(sessions: int = 5, rows_per_session: int = 10_000) -> float:
    """Simulate concurrent user sessions executing pipelines in parallel."""
    datasets = [generate_synthetic_dataset(rows_per_session) for _ in range(sessions)]

    def _worker(df: pd.DataFrame) -> int:
        clean_df, _ = clean_dataframe(df)
        classified = {c.name: c for c in classify_columns(clean_df)}
        res = execute_pipeline(clean_df, classified)
        return len(res.kpis)

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=sessions) as executor:
        results = list(executor.map(_worker, datasets))
    duration_s = time.perf_counter() - t0

    assert len(results) == sessions
    return duration_s


def main() -> int:
    parser = argparse.ArgumentParser(description="Aivara Performance & Scale Benchmark")
    parser.add_argument(
        "--scales", nargs="+", type=int, default=[1_000, 10_000, 50_000], help="Row counts"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent sessions to simulate"
    )
    args = parser.parse_args()

    print("===============================================================================")
    print("                      AIVARA PERFORMANCE & SCALE BENCHMARK                     ")
    print("===============================================================================")
    print(f"Testing Scales: {args.scales}")
    print("-------------------------------------------------------------------------------")
    print(
        f"{'Rows':>8} | {'Clean':>8} | {'Classify':>8} | {'Profile':>8} | {'Pipeline':>8} | {'Total':>8} | {'Peak RAM':>8}"
    )
    print("-------------------------------------------------------------------------------")

    for rows in args.scales:
        res = benchmark_pipeline_scale(rows)
        print(
            f"{res['rows']:>8,d} | "
            f"{res['clean_ms']:>6.1f}ms | "
            f"{res['classify_ms']:>6.1f}ms | "
            f"{res['profile_ms']:>6.1f}ms | "
            f"{res['pipeline_ms']:>6.1f}ms | "
            f"{res['total_ms']:>6.1f}ms | "
            f"{res['peak_mb']:>6.2f}MB"
        )

    print("-------------------------------------------------------------------------------")
    print(f"Simulating {args.concurrency} concurrent sessions (10,000 rows each)...")
    dur_s = benchmark_concurrency(sessions=args.concurrency, rows_per_session=10_000)
    throughput = (args.concurrency * 10_000) / dur_s
    print(f"Completed {args.concurrency} sessions in {dur_s:.2f}s ({throughput:,.0f} rows/sec).")
    print("===============================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
