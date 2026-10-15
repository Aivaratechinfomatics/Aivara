# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 5: LLM Layer: Reliability & Privacy (Audit §5)**:
  - Structured JSON output schema enforcement (`headline`, `driver_explanation`, `suggested_action`) with preamble stripping, markdown code-block parsing, and 1-shot repair retry (Audit 3.8).
  - Local numerical faithfulness verification (`insight/faithfulness.py`) checking cited metrics against facts packet numbers and rejecting hallucinations with fallback reversion.
  - Data egress control & pseudonymization (`insight/redactor.py`) mapping business categories and entities to generic tokens (`Category A`, `Entity A`) prior to OpenRouter egress, unredacting locally via in-memory map; configured by `AIVARA_LLM_REDACT_LABELS: bool = True` (Audit 4.5, Decision D5).
  - Prompt injection defense enclosing untrusted data inside `<business_data>` XML tags, stripping control characters and HTML tags, and neutralizing instruction override tokens (`insight/prompts.py`).
  - OpenRouter client resilience with three-state circuit breaker (`CLOSED`, `OPEN`, `HALF_OPEN`), exponential backoff on HTTP 429 and 5xx errors, and per-session call limits (`MAX_SESSION_LLM_CALLS = 20`).
  - Offline deterministic template fallback generator (`insight/fallback.py`) producing 3-sentence executive takeaways for KPIs, snapshots, and project portfolios without network or API dependency.
  - Removed deprecated tier-2 LLM column classification per Decision D6 (Audit 2.1).
  - Transparent model attribution displaying fallback indicators and actual model identifiers (Audit 2.2).
  - Dedicated reliability test suite (`tests/test_insight_reliability.py`) achieving 90.19% branch coverage across `insight/`.
- **Phase 4: Analytics Validity & Coverage (Audit §4)**:
  - Configurable aggregation semantics (`agg`: `sum`, `mean`, `weighted_mean`, `last`) in `analytics/kpis.py`, `trend.py`, `drivers.py`, `snapshot.py`, and `anomalies.py`. Rate/ratio metrics (`rate`, `pct`, `percent`, `ratio`, `avg`, `average`, `score`, `margin`, `nps`, `share`, `yield`) default to `"mean"` instead of being summed (Audit 4.1).
  - Manual aggregation overrides in `DatasetProfile` and UI schema configuration, with aggregation tooltip indicator on KPI tiles.
  - Category-vs-own-history temporal anomaly detection (`detect_temporal_anomalies`) in `analytics/anomalies.py` using rolling baselines and zero-variance baseline floor (Audit 4.2).
  - Relabeled cross-sectional snapshot anomalies as `"structural outlier"` and standardized severity tiers (`SEVERITY_LOW`, `SEVERITY_MEDIUM`, `SEVERITY_HIGH`) across temporal anomalies, group outliers, and period swings.
  - Statistical discovery safeguards: sample size threshold $n \ge 5$ in `compute_correlation_matrix()` to suppress spurious drivers on tiny datasets, explicit `"Correlation indicates statistical association, not direct causation"` disclaimer in driver narratives, and divide-by-zero guards in concentration index.
  - Financial domain mathematical correctness: expense/cost variance convention (`is_cost`) in `analytics/domains/finance.py` ensuring expense overruns are unfavorable and savings under budget are favorable.
  - Dedicated hand-computed verification test suite (`tests/test_domain_hand_computed.py`) hand-checking commerce AOV/basket/repeat rate, finance revenue/cost variances, workforce headcount/median/turnover, and feedback NPS/CSAT.
  - Deep analytics branch test suite (`tests/test_analytics_deep_coverage.py`) achieving 95.71% coverage across `analytics/`.
- **Phase 3: Ingestion Hardening (Audit §3)**:
  - Enforced upload file size limit `MAX_UPLOAD_MB` (100 MB default) across `load_file`, `load_csv`, and `load_excel`.
  - Enforced table column width limit `MAX_COLUMNS` (500 default) preventing denial-of-service memory spikes on wide/malformed sheets.
  - Added empty file guards returning friendly errors without crashing or raising unhandled exceptions.
  - Active CSV bad line tracking with `on_bad_lines=bad_line_handler` reporting skipped malformed lines in `LoadResult.notes` (Audit 3.1).
  - Proper percent scaling dividing percent-formatted columns by 100 with `%` unit tagging (Audit 3.2).
  - Normalized null strings using centralized `DEFAULT_NULL_STRINGS` in `config.py` (Audit 3.3).
  - Enhanced numeric coercion tracking failed coercion counts per column in `CleanReport.coercion_failures` and `CleanReport.total_nulls_found` (Audit 3.4).
  - Compact date priority detection before numeric coercion for compact date strings like `YYYYMMDD` (Audit 3.5).
  - Preserved missing dimension values with explicit `(missing)` bucket preventing silent drop of data points (Audit 3.6).
  - Header normalization and deduplication (`col`, `col_2`, ...) with trimming, whitespace normalization, and blank column labeling (`column_{i+1}`).
  - Interactive Data Quality & Ingestion Summary panel in `ui/upload_page.py` showing rows, columns, duplicate rows, coerced nulls, and coercion failure breakdowns.
  - Expanded test suites in `tests/test_cleaner.py`, `tests/test_loader.py` (including Hypothesis fuzzing), and `tests/test_classifier.py` achieving 95.73% coverage on `ingestion/`.
- **Phase 2: Core Correctness (Audit §1)**:
  - Multi-session isolation in `insight/cache.py` eliminating cross-user view narrative leaks.
  - Canonical state reset function `reset_dataset_state()` in `ui/upload_page.py` invoked upon file upload and hash changes.
  - Hardened SHA-256 content hashing in upload workflow for secure re-upload cache detection.
  - Guarded `format_pct_change` against `math.isnan` and infinite values in `ui/components.py`.
  - Comprehensive correctness test suite in `tests/test_core_correctness.py` covering:
    - Multi-session view cache isolation (Audit 1.1).
    - Trend metric column order independence (Audit 1.2).
    - Offsetting category contributions when net delta is zero (Audit 1.3).
    - Signed infinities and `format_pct_change` edge cases (Audit 1.4, 1.5).
    - Dataset re-upload state resetting across all figures and insights (Audit 1.6, 1.7, 1.8).
    - Screen == Facts == PPTX number consistency invariant across all golden datasets.
- **Phase 1: Tooling, CI, Repo Hygiene**:
  - `pyproject.toml` with `ruff`, `mypy`, `pytest`, and branch `coverage` configurations.
  - `requirements-dev.txt` for development, linting, typing, and security audit dependencies.
  - Test safety harness in `tests/conftest.py` with automatic external socket blocking, isolated temporary cache/budget directories, and fake OpenRouter mock fixture.
  - `tests/test_safety_harness.py` validating that network egress attempts are intercepted and blocked.
  - GitHub Actions CI matrix workflow (`.github/workflows/ci.yml`) running across Python 3.11 and 3.12.
  - `.github/dependabot.yml` for automated dependency updates.
  - Apache 2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `.dockerignore`, `.pre-commit-config.yaml`, and `run.sh`.
  - Relocated sample datasets under `examples/` with dedicated `examples/README.md`.
- **Phase 0: Baseline & Safety Net**:
  - Baseline execution and verification (118 initial tests passing).
  - `docs/ARCHITECTURE_CURRENT.md` documenting end-to-end data pipeline flow.
  - `DECISIONS.md` tracking architecture decisions D1–D10.
  - Characterization golden test suite (`tests/test_golden.py` and `tests/golden/*.json` across 8 fixture datasets).
  - Complete Audit Verification Matrix in `PROGRESS.md` covering audit items 1.1–1.8, 2.1–2.5, 3.1–3.8, and 4.1–4.5.
