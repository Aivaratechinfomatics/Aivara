"""
tests/test_concurrency.py — Test Suite for Phase 6: State, Concurrency & Multi-User (Audit §6, Audit 4.3).

Covers:
- Multi-process atomic budget exhaustion under concurrent load (50 workers across multiple processes).
- TOCTOU race elimination via atomic check_and_increment_daily.
- Persistent insight cache TTL expiration.
- Persistent insight cache capacity pruning (LRU eviction).
- Cache corruption recovery (auto-healing on corrupted store).
- Zero-persistence mode (AIVARA_CACHE_ENABLED=false).
- Multi-session isolation for view caches and dataset states.
- Zero raw row-level data on disk invariant.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor

import config
from insight import budget, cache


def _worker_attempt_budget_call(db_path: str, cap: int) -> bool:
    """Helper invoked in parallel to attempt a call against the budget."""
    allowed, _, _ = budget.check_and_increment_daily(path=db_path, limit=cap)
    return allowed


def test_atomic_check_and_increment_daily(tmp_path):
    db_path = str(tmp_path / "budget_atomic.db")
    cap = 5

    # 1. Calls up to cap succeed
    for i in range(cap):
        allowed, count, remaining = budget.check_and_increment_daily(path=db_path, limit=cap)
        assert allowed is True
        assert count == i + 1
        assert remaining == cap - (i + 1)

    # 2. 6th call exceeds cap -> blocked
    allowed, count, remaining = budget.check_and_increment_daily(path=db_path, limit=cap)
    assert allowed is False
    assert count == cap
    assert remaining == 0


def test_multiprocess_parallel_budget_exhaustion(tmp_path):
    """50 parallel attempts hammering the budget store:
    Final count must equal successful attempts and never exceed the cap."""
    db_path = str(tmp_path / "budget_concurrent.db")
    cap = 15
    total_workers = 50

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_worker_attempt_budget_call, db_path, cap) for _ in range(total_workers)
        ]
        results = [f.result() for f in futures]

    allowed_count = sum(1 for r in results if r is True)
    blocked_count = sum(1 for r in results if r is False)

    assert allowed_count == cap
    assert blocked_count == total_workers - cap

    # Verify database state matches exactly
    status = budget.get_status(path=db_path, daily_budget=cap)
    assert status.calls_made_today == cap
    assert status.remaining == 0
    assert status.exhausted is True


def test_multiprocess_cross_process_budget_exhaustion(tmp_path):
    """50 parallel attempts across 4 separate worker processes hammering the budget store:
    Final count must equal successful attempts and never exceed the cap."""
    import multiprocessing

    db_path = str(tmp_path / "budget_mp.db")
    cap = 15
    total_workers = 50

    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=4) as pool:
        args = [(db_path, cap) for _ in range(total_workers)]
        results = pool.starmap(_worker_attempt_budget_call, args)

    allowed_count = sum(1 for r in results if r is True)
    blocked_count = sum(1 for r in results if r is False)

    assert allowed_count == cap
    assert blocked_count == total_workers - cap

    status = budget.get_status(path=db_path, daily_budget=cap)
    assert status.calls_made_today == cap
    assert status.remaining == 0
    assert status.exhausted is True


def test_cache_ttl_expiration(tmp_path, monkeypatch):
    db_path = str(tmp_path / "cache_ttl.db")
    monkeypatch.setattr(config, "AIVARA_CACHE_TTL_DAYS", 7)

    now = time.time()
    cache.set("recent_key", {"val": "fresh"}, path=db_path)

    # Manually backdate an entry in SQLite to 10 days ago (> 7 days)
    old_time = now - (10 * 86400)
    key_hash = cache._hash_key("expired_key")
    conn = cache._get_sqlite_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO insight_cache (cache_key, payload, created_at, accessed_at) VALUES (?, ?, ?, ?)",
            (key_hash, '{"val": "stale"}', old_time, old_time),
        )
    conn.close()

    # Fresh entry is retrieved
    assert cache.get("recent_key", path=db_path) == {"val": "fresh"}

    # Expired entry is pruned and returns None
    assert cache.get("expired_key", path=db_path) is None

    # Verify expired entry was deleted from table
    conn = cache._get_sqlite_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM insight_cache WHERE cache_key = ?", (key_hash,))
    assert cur.fetchone()[0] == 0
    conn.close()


def test_cache_lru_capacity_pruning(tmp_path, monkeypatch):
    db_path = str(tmp_path / "cache_lru.db")
    monkeypatch.setattr(config, "AIVARA_CACHE_MAX_ENTRIES", 3)

    # Insert 5 entries (exceeds cap of 3)
    for i in range(5):
        cache.set(f"key_{i}", {"index": i}, path=db_path)
        time.sleep(0.01)

    # Check total count is capped at 3
    conn = cache._get_sqlite_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM insight_cache")
    assert cur.fetchone()[0] == 3
    conn.close()

    # Oldest entries (key_0, key_1) were pruned; newest entries (key_3, key_4) exist
    assert cache.get("key_0", path=db_path) is None
    assert cache.get("key_1", path=db_path) is None
    assert cache.get("key_3", path=db_path) == {"index": 3}
    assert cache.get("key_4", path=db_path) == {"index": 4}


def test_cache_corruption_recovery(tmp_path):
    """A corrupted database file must auto-heal and not crash the application."""
    db_path = str(tmp_path / "corrupt_test.db")

    # Write corrupt non-SQLite bytes to database path
    with open(db_path, "wb") as f:
        f.write(b"CORRUPTED_SQLITE_HEADER_GARBAGE_BYTES_1234567890")

    # get() must not raise an unhandled DatabaseError
    assert cache.get("some_key", path=db_path) is None

    # set() must recover, reinitialize the schema, and successfully store the insight
    cache.set("new_key", {"status": "recovered"}, path=db_path)
    assert cache.get("new_key", path=db_path) == {"status": "recovered"}


def test_zero_persistence_mode(tmp_path, monkeypatch):
    """When AIVARA_CACHE_ENABLED=false, cache operations are zero-footprint no-ops."""
    db_path = str(tmp_path / "zero_persist.db")
    monkeypatch.setattr(config, "AIVARA_CACHE_ENABLED", False)

    cache.set("test_key", {"val": "should_not_persist"}, path=db_path)
    assert not os.path.exists(db_path)
    assert cache.get("test_key", path=db_path) is None


def test_session_isolation_and_cross_user_protection():
    """Verify that simulated distinct user sessions never see each other's view data."""
    session_user_a = "user_session_alpha"
    session_user_b = "user_session_beta"

    cache.set_for_view("Overview", {"kpi": "Revenue", "owner": "Alpha"}, session_id=session_user_a)
    cache.set_for_view("Overview", {"kpi": "Costs", "owner": "Beta"}, session_id=session_user_b)

    view_a = cache.get_for_view("Overview", session_id=session_user_a)
    view_b = cache.get_for_view("Overview", session_id=session_user_b)

    assert view_a is not None and view_a["owner"] == "Alpha"
    assert view_b is not None and view_b["owner"] == "Beta"

    # Clearing user A leaves user B untouched
    cache.clear_view_cache(session_id=session_user_a)
    assert cache.get_for_view("Overview", session_id=session_user_a) is None
    assert cache.get_for_view("Overview", session_id=session_user_b) is not None
    assert cache.get_for_view("Overview", session_id=session_user_b)["owner"] == "Beta"

    # Clean up user B
    cache.clear_view_cache(session_id=session_user_b)


def test_zero_raw_row_data_on_disk_invariant(tmp_path):
    """Assert that after loading, cleaning, computing KPIs, and generating insights,
    no raw CSV records or customer names are persisted in plaintext to the cache database."""
    from analytics.anomalies import detect_group_outliers
    from analytics.drivers import compute_dimension_drivers
    from analytics.kpis import compute_kpi
    from ingestion.cleaner import clean_dataframe
    from ingestion.loader import load_file
    from insight import client, facts_builder

    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests",
        "fixtures",
        "clean.csv",
    )
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    load_res = load_file(file_bytes, filename="clean.csv")
    assert load_res.dataframe is not None

    df, clean_report = clean_dataframe(load_res.dataframe)

    kpi = compute_kpi(df, None, metric_col="revenue")
    drivers = compute_dimension_drivers(df, None, "revenue", "product")
    signals = detect_group_outliers(df, "revenue", "product")

    facts = facts_builder.build_facts_packet(kpi, drivers, signals, "Q2 vs Q1")

    db_path = str(tmp_path / "security_check.db")
    # Generate deterministic fallback insight
    res = client.generate_insight(facts)
    cache.set("audit_key", {"insight": res.headline}, path=db_path)

    # Read all raw bytes from the database file
    with open(db_path, "rb") as f:
        db_bytes = f.read()

    # Invariant check: Raw CSV rows or customer names must not appear in the database
    assert b"Widget B" not in db_bytes
    assert b"Widget A" not in db_bytes


def test_budget_and_cache_branch_coverage(tmp_path):
    """Deep branch coverage for budget and cache SQLite engines."""
    # 1. Budget default paths and non-existent DB
    status = budget.get_status(str(tmp_path / "nonexistent.db"))
    assert status.calls_made_today == 0
    assert not status.exhausted

    # 2. Budget corruption recovery
    corrupt_budget = str(tmp_path / "corrupt_budget.db")
    with open(corrupt_budget, "wb") as f:
        f.write(b"CORRUPT_BUDGET_STORE_NOT_SQLITE")
    # check_and_increment_daily should recover and succeed
    allowed, count, remaining = budget.check_and_increment_daily(path=corrupt_budget, limit=5)
    assert allowed is True
    assert count == 1

    # 3. Cache clear_disk_cache removes wal and shm files
    cache_path = str(tmp_path / "test_wal_cleanup.db")
    cache.set("k1", {"val": 1}, path=cache_path)
    # create dummy wal/shm
    with open(f"{cache_path}-wal", "w") as f:
        f.write("wal")
    with open(f"{cache_path}-shm", "w") as f:
        f.write("shm")
    cache.clear_disk_cache(cache_path)
    assert not os.path.exists(cache_path)
    assert not os.path.exists(f"{cache_path}-wal")
    assert not os.path.exists(f"{cache_path}-shm")

    # 4. Cache get on non-existent path
    assert cache.get("key", path=str(tmp_path / "missing_cache.db")) is None
