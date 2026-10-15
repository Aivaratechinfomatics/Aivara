# Aivara Testing Guide

This document outlines the testing architecture, quality assurance methodologies, quality gates, and instructions for running the test suite for **Aivara**.

---

## 1. Test Architecture & Pytest Suite

Aivara enforces an exhaustive test battery spanning unit, property-based fuzzing, golden regression, headless UI, security, concurrency, and performance domains.

### Test Directory Layout

```
tests/
├── conftest.py                    # Global fixtures & socket network blocker
├── fixtures/                      # Messy CSVs (mixed encoding, BOM, semicolons, currency)
├── golden_snapshots/              # Expected JSON output snapshots across golden datasets
├── test_analytics_deep_coverage.py# Aggregations, anomalies, drivers, and domain logic
├── test_classifier.py             # Semantic column classification heuristics
├── test_cleaner.py                # Type coercion, percent scaling, null tokens
├── test_concurrency.py            # SQLite WAL concurrency, TTL, LRU, atomic budget
├── test_core_correctness.py       # Number consistency and screen facts verification
├── test_export_hardening.py       # PPTX zip integrity, timeout defense, placeholder cards
├── test_export_no_network.py      # Network isolation assertion for export module
├── test_golden.py                 # Golden snapshot regression tests
├── test_insight_reliability.py    # Schema validation, repair prompt, faithfulness check
├── test_loader.py                 # File sniffing, encodings, delimiters, limits
├── test_observability.py          # Settings validation, secret redaction, audit logging
├── test_performance.py            # Latency bounds, memory footprint, sampling guards
├── test_security.py               # Formula injection, auth gate, upload sniffing, SSRF
├── test_ui_app.py                 # Streamlit UI component assertions
└── test_ui_apptest.py             # Streamlit AppTest headless execution flows
```

---

## 2. Testing Principles & Invariants

1. **Deterministic Offline Isolation (Socket Blocker)**:
   - All tests run under a strict socket-blocking fixture (`tests/conftest.py`). Any unauthorized outbound network socket call triggers an immediate test failure.
2. **Zero Raw Row Data Persistence Invariant**:
   - Tests assert that no user raw data records or uploaded rows are ever written to disk or persistent SQLite stores (`tests/test_concurrency.py`).
3. **Number Consistency Guarantee**:
   - Tests verify exact numerical correspondence between computed pipeline data, UI formatted strings, and OpenXML presentation text shapes (`tests/test_core_correctness.py`, `tests/test_export_hardening.py`).
4. **Coverage Standard**:
   - Repository-wide test coverage must meet or exceed **75.0%** (currently **81.43%**), with core analytical and ingestion engines exceeding **90–98%**.

---

## 3. Running Tests

### Standard Test Execution
Run the complete test suite:

```bash
pytest tests/ -v
```

### Running with Code Coverage
Measure branch and line coverage across all packages:

```bash
python -m pytest tests/ --cov=config --cov=analytics --cov=ingestion --cov=export --cov=insight --cov=ui --cov=infra --cov=app -q
```

### Running Specific Test Categories

```bash
# Security & Threat Model tests (52 tests)
pytest tests/test_security.py -v

# Concurrency & Multi-process tests (10 tests)
pytest tests/test_concurrency.py -v

# Headless UI AppTest flows (8 tests)
pytest tests/test_ui_apptest.py -v

# Golden snapshot regression suite (6 tests)
pytest tests/test_golden.py -v

# Performance regression tests (4 tests)
pytest tests/test_performance.py -v
```

---

## 4. Static Analysis & Security Scans

Prior to any commit or release, the following linters and security scanners must execute cleanly:

```bash
# 1. Ruff linting
python -m ruff check .

# 2. Ruff formatting verification
python -m ruff format --check .

# 3. Mypy static type checking
python -m mypy config.py analytics/ ingestion/ export/ insight/ ui/ infra/ scripts/ app.py

# 4. Bandit security AST scan (Medium and High severity)
python -m bandit -r analytics/ ingestion/ export/ insight/ ui/ infra/ config.py app.py -ll
```

---

## 5. End-to-End Verification Scripts

In addition to pytest, Aivara includes dedicated standalone validation harnesses:

1. **UAT Scenario Verification**:
   ```bash
   python scripts/uat_verify.py
   ```
   Validates 5 diverse domain datasets (Commerce, Inventory, Project, HR, Survey) end-to-end through loading, cleaning, classification, pipeline execution, and deck assembly.

2. **Performance & Scale Benchmark**:
   ```bash
   python scripts/bench.py
   ```
   Measures per-stage latency, peak memory (`tracemalloc`), and concurrent session throughput.

3. **Container Smoke Verification**:
   ```bash
   python scripts/smoke_container.py --url http://localhost:8501
   ```
   Polls container health endpoints (`/_stcore/health`) and validates web application availability.
