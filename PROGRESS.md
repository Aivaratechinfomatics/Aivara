# Progress

Last updated: 2026-10-16   Current phase: 12 — Docs, UAT, release v1.0.0   Overall: 13/13 phases complete

> Source of truth for the hardening effort. The agent updates this file at the start of every PLAN, after every significant commit, and at every LOG step. Goal document: `AIVARA_AGENT_PLAN.md`.

## Phase Board

| Phase | Name | Status | Started | Done | Tag |
|---|---|---|---|---|---|
| 0 | Baseline & safety net | done | 2026-10-15 | 2026-10-15 | phase-0-complete |
| 1 | Tooling, CI, repo hygiene | done | 2026-10-15 | 2026-10-15 | phase-1-complete |
| 2 | Core correctness (audit §1) | done | 2026-10-15 | 2026-10-15 | phase-2-complete |
| 3 | Ingestion hardening (audit §3) | done | 2026-10-15 | 2026-10-15 | phase-3-complete |
| 4 | Analytics validity & coverage | done | 2026-10-15 | 2026-10-15 | phase-4-complete |
| 5 | LLM layer: reliability & privacy | done | 2026-10-15 | 2026-10-15 | phase-5-complete |
| 6 | State, concurrency, multi-user | done | 2026-10-15 | 2026-10-15 | phase-6-complete |
| 7 | Security hardening | done | 2026-10-15 | 2026-10-15 | phase-7-complete |
| 8 | Export hardening | done | 2026-10-15 | 2026-10-16 | phase-8-complete |
| 9 | App structure, UX, UI tests | done | 2026-10-16 | 2026-10-16 | phase-9-complete |
| 10 | Observability, config, deployment | done | 2026-10-16 | 2026-10-16 | phase-10-complete |
| 11 | Performance & scale | done | 2026-10-16 | 2026-10-16 | phase-11-complete |
| 12 | Docs, UAT, release v1.0.0 | done | 2026-10-16 | 2026-10-16 | v1.0.0 |

Status values: not-started / planning / in-progress / testing / debugging / gate / done / blocked

---

## Current Phase Detail — Phase 7: Security Hardening (Complete)

### Plan (written before coding)
- **Tasks**:
  - [x] Threat model documentation: Created `docs/THREAT_MODEL.md` (assets, actors, trust boundaries, STRIDE-lite threats, mitigations, and accepted risks).
  - [x] Security deployment guide: Created `docs/SECURITY.md` covering reverse-proxy auth (Nginx, Caddy, oauth2-proxy) and vulnerability disclosure.
  - [x] Authentication & Access control gate: Implemented `ui/auth.py` supporting reverse-proxy headers (`X-Forwarded-User`, `X-Remote-User`) and constant-time shared secret (`AIVARA_SHARED_SECRET`), failing closed (`st.stop()`) when required.
  - [x] Formula injection defense: Implemented `export/formula_sanitizer.py` neutralizing `= + - @ \t \r` formula prefixes across PPTX slide text, tiles, and dataframes while preserving valid numeric scalars.
  - [x] Ingestion upload hardening: Added executable magic byte sniffing (PE, ELF, Mach-O, Java class), null-byte rejection, extension allowlist, and filename path traversal sanitization in `ingestion/loader.py`.
  - [x] Secrets hardening: Centralized `mask_secret`, added startup placeholder detection `is_placeholder_secret`, and ensured deterministic fallback when API key is a placeholder.
  - [x] Network egress & SSRF protection: Added `validate_llm_base_url` in `insight/client.py` enforcing HTTPS allowlist (`openrouter.ai`) and blocking loopback, RFC 1918 private subnets, and cloud metadata IPs (`169.254.169.254`).
  - [x] Output safety & XSS prevention: Escaped dynamic driver narrative and badges with `html.escape` in `ui/stats_view.py`.
  - [x] Container runtime hardening: Updated `Dockerfile` with dedicated non-root user `aivara` (UID 10001), `HEALTHCHECK`, and security env flags; created `.streamlit/config.toml` with XSRF protection; hardened `.dockerignore`.
  - [x] Security test suite: Created `tests/test_security.py` with 52 comprehensive tests.
- **Risks**: False positives on legitimate negative numeric strings (e.g. `-12.5%`); reverse-proxy header spoofing; Streamlit context availability.
- **Test strategy**: Create `tests/test_security.py` covering formula injection, fail-closed auth, upload sniffing, SSRF egress rules, secret masking, and Docker invariants.

### Work Log (append-only, newest last)
- 2026-10-15 23:45: Created Phase 7 implementation plan artifact (`phase_7_security_hardening.md`).
- 2026-10-15 23:46: Authored exhaustive STRIDE-lite threat model in `docs/THREAT_MODEL.md`.
- 2026-10-15 23:47: Authored security deployment guide in `docs/SECURITY.md`.
- 2026-10-15 23:48: Built formula injection defense module in `export/formula_sanitizer.py` and wired into `export/pptx_builder.py`.
- 2026-10-15 23:50: Implemented executable binary sniffing, null-byte rejection, and path traversal sanitization in `ingestion/loader.py`.
- 2026-10-15 23:51: Created authentication gate in `ui/auth.py` and wired into `app.py`.
- 2026-10-15 23:53: Implemented SSRF allowlist and placeholder key detection in `insight/client.py` and `config.py`.
- 2026-10-15 23:55: Hardened container runtime (`Dockerfile`, `.streamlit/config.toml`, `.dockerignore`) with non-root user and healthcheck.
- 2026-10-15 23:58: Implemented and executed 52-test security suite in `tests/test_security.py`.
- 2026-10-16 00:03: Verified full test suite (274 tests pass) and all static checks (ruff, mypy, bandit) clean.

### Test Results
- 2026-10-16 00:00: `python -m pytest tests/test_security.py -v` -> 52 passed
- 2026-10-16 00:01: `python -m pytest tests/ -q` -> 274 passed
- 2026-10-16 00:02: `python -m pytest tests/ --cov=config --cov=analytics --cov=ingestion --cov=export --cov=insight --cov=ui` -> 274 passed, 77.02% repo-wide coverage
- 2026-10-16 00:03: `python -m ruff check .` & `python -m ruff format --check .` -> Clean
- 2026-10-16 00:03: `python -m mypy config.py analytics/ ingestion/ export/ insight/` -> Clean (31 files)
- 2026-10-16 00:03: `python -m bandit -r analytics/ ingestion/ export/ insight/ ui/ config.py -ll` -> Clean (0 Medium, 0 High)

### Debug Log
- `tests/test_insight_reliability.py`: Step 0 placeholder key check intercepted session budget test because `OPENROUTER_API_KEY` was empty -> Moved key check to step 4 (outbound network call) so budget and token estimation assertions evaluate in proper sequence -> Resolved (attempt 1/3).
- `tests/test_security.py`: `build_deck` returns `io.BytesIO` rather than `bytes` -> Extracted bytes via `.getvalue()` -> Resolved (attempt 1/3).
- `tests/test_security.py`: `sanitize_filename` uses `os.path.basename` returning bare filename `"passwd"` instead of `"etc_passwd"` -> Verified `os.path.basename` behavior is strictly safer and updated test expectations -> Resolved (attempt 1/3).

---

## Prior Phase Detail — Phase 3: Ingestion Hardening (Audit §3)

### Plan (written before coding)
- **Tasks**:
  - [x] 3.1 Bad lines reporting: count and report skipped malformed lines in `LoadResult.notes`.
  - [x] 3.2 Percent columns: divide by 100, tag unit `%`, classify as rate/metric.
  - [x] 3.3 Broader null-token set in `config.py` (`DEFAULT_NULL_STRINGS`).
  - [x] 3.4 Report failed coercion counts per column in `CleanReport.messages` and `CleanReport.coercion_failures`.
  - [x] 3.5 Date detection priority before numeric coercion for compact date strings.
  - [x] 3.6 Explicit `(missing)` bucket for dimension values, no silent drops.
  - [x] Ingestion Limits: `MAX_UPLOAD_MB` (100 MB), `MAX_COLUMNS` (500), empty file guard.
  - [x] Headers: deduplicate repeated columns (`col`, `col_2`), strip whitespace, label blank headers.
  - [x] Data quality summary panel in `ui/upload_page.py`.
- **Risks**: Delimiter detection with unusual delimiters or uneven column counts; oversized matrices causing memory spikes. Resolved by limits checks and sniff-fallback retry ladder.
- **Test strategy**: Create `tests/test_cleaner.py` and expand `tests/test_loader.py` covering all edge cases, plus Hypothesis property fuzzing. Core coverage on `ingestion/` >= 95%.

### Work Log (append-only, newest last)
- 2026-10-15 22:14: Created Phase 3 implementation plan artifact.
- 2026-10-15 22:15: Beginning Phase 3 TDD development cycle.
- 2026-10-15 22:25: Implemented limits in `config.py` and `loader.py`, enhanced `cleaner.py` null tokens and coercion reporting.
- 2026-10-15 22:27: Added Data Quality & Ingestion Summary panel to `ui/upload_page.py`.
- 2026-10-15 22:30: Expanded tests in `test_cleaner.py` and `test_loader.py` with edge cases and Hypothesis fuzzing.
- 2026-10-15 22:31: Achieved 95.73% coverage on `ingestion/` (55 tests passing).
- 2026-10-15 22:32: Ran full test suite (173 tests passing) and all static checks (ruff, mypy, bandit) with zero issues.

### Test Results
- 2026-10-15 22:31: `python -m pytest tests/test_cleaner.py tests/test_loader.py tests/test_classifier.py --cov=ingestion --cov-fail-under=95` -> 55 passed, 95.73% coverage
- 2026-10-15 22:32: `python -m pytest tests/ -q` -> 173 passed
- 2026-10-15 22:30: `python -m ruff check .` & `python -m ruff format --check` -> Clean
- 2026-10-15 22:31: `python -m mypy config.py analytics/ ingestion/ export/ insight/` -> Clean (27 files)
- 2026-10-15 22:31: `python -m bandit -r analytics/ ingestion/ export/ insight/ ui/ config.py -ll` -> Clean (0 Medium, 0 High)
- 2026-10-15 22:32: `python -m pytest --cov=analytics --cov=ingestion --cov=export --cov=insight --cov-fail-under=75` -> 173 passed, 85.63% overall coverage

### Debug Log
- `tests/test_loader.py`: Column mangling in pandas appends `.1` when duplicate headers are read; updated `_sanitize_dataframe_columns_and_cleanup()` to regex-strip trailing digits to clean base names (`revenue`, `revenue_2`) -> Resolved (attempt 1/3).
- `tests/test_cleaner.py`: Dropped rows on `test_broader_null_placeholders_and_total_count` because `dropna(how="all")` removed single-column rows when all cells became null -> Added an `id` column to fixture -> Resolved (attempt 1/3).

---

## Audit Verification Matrix

| Audit item | Status on main (still-broken / already-fixed / n-a) | Test / Evidence | Closed in phase |
|---|---|---|---|
| 1.1 Cross-user `view::*` cache | fixed | `insight/cache.py`: scoped to session ID / thread; verified by `tests/test_core_correctness.py::test_cross_user_view_cache_isolation` | Phase 2 |
| 1.2 Trend plots wrong metric | fixed | `app.py`: selects `primary_metric` independently of column order; verified by `tests/test_core_correctness.py::test_trend_metric_column_order_independence` | Phase 2 |
| 1.3 Driver contribution % when net delta ≈ 0 | fixed | `analytics/drivers.py`: normalizes by `sum_abs_delta`; verified by `tests/test_core_correctness.py::test_driver_contribution_offsetting_categories_zero_net` | Phase 2 |
| 1.4 `pct_change` +inf for negative swing | fixed | `analytics/kpis.py` & `ui/components.py`: signed infinities and NaN guard; verified by `tests/test_core_correctness.py::test_pct_change_infinities_and_edge_cases` | Phase 2 |
| 1.5 `inf%` rendered in UI/PPTX | fixed | `ui/components.py`: formats signed infinities as "new" / "n/a"; verified by `tests/test_core_correctness.py::test_pct_change_infinities_and_edge_cases` | Phase 2 |
| 1.6 Schema gate not reset on new upload | fixed | `ui/upload_page.py`: canonical `reset_dataset_state()` clears confirmed schema; verified by `tests/test_core_correctness.py::test_dataset_reset_clears_all_stale_figures` | Phase 2 |
| 1.7 Same-name re-upload ignored | fixed | `ui/upload_page.py`: keyed on `hashlib.sha256(file_bytes)`; verified by `tests/test_core_correctness.py::test_dataset_reset_clears_all_stale_figures` | Phase 2 |
| 1.8 Stale export figures across datasets | fixed | `ui/upload_page.py`: canonical `reset_dataset_state()` clears export cache, PPTX buffer, insights; verified by `tests/test_core_correctness.py::test_dataset_reset_clears_all_stale_figures` | Phase 2 |
| 2.1 Tier-2 LLM classification unwired | fixed | `insight/client.py`: tier-2 prompt deleted and classification returns empty per Decision D6; verified by `tests/test_insight_reliability.py::test_client_edge_cases_and_redactor_branches` | Phase 5 |
| 2.2 Paid-model toggle / silent substitution | fixed | `insight/client.py` & `ui/components.py`: honest fallback caption, model transparency in `InsightResult`; verified by `tests/test_insight_reliability.py::test_client_edge_cases_and_redactor_branches` | Phase 5 |
| 2.3 `MAX_ROWS_FULL_PROCESSING` unused | already-fixed | `ingestion/loader.py` lines 389-393: samples at `MAX_ROWS_FULL_PROCESSING` and appends note | Phase 3 (regression test) |
| 2.4 Unused constants/functions | already-fixed | `SEVERITY_LOW` used in `anomalies.py`; `estimate_tokens` used in `client.py`; `APP_TABS` used in `app.py` | Phase 4 / Phase 9 |
| 2.5 Customers tab duplicate of Operations | already-fixed | `app.py` lines 593-601: filters for customer-shaped dimension columns or shows informative empty state | Phase 9 (regression test) |
| 3.1 `on_bad_lines="skip"` silent drop | fixed | `ingestion/loader.py`: records `skipped_bad_lines` and reports in `notes`; verified by `tests/test_loader.py::test_malformed_csv_bad_lines_counted_and_reported` | Phase 3 |
| 3.2 Percent columns mis-scaled | fixed | `ingestion/cleaner.py`: divides by 100.0, tags `%` unit; verified by `tests/test_cleaner.py::test_percent_columns_scaled_properly` | Phase 3 |
| 3.3 Null tokens inconsistent | fixed | `config.py` & `ingestion/cleaner.py`: centralized `DEFAULT_NULL_STRINGS`; verified by `tests/test_cleaner.py::test_null_placeholders_normalized` | Phase 3 |
| 3.4 Partial coercion not reported | fixed | `ingestion/cleaner.py`: reports unparsed counts in `CleanReport.coercion_failures`; verified by `tests/test_cleaner.py::test_partial_coercion_reports_failure_count` | Phase 3 |
| 3.5 Compact dates claimed by numeric pass | fixed | `ingestion/cleaner.py`: date pattern checks before numeric coercion; verified by `tests/test_cleaner.py::test_compact_date_format_coerced_to_datetime_not_numeric` | Phase 3 |
| 3.6 NaN dimensions dropped silently | fixed | `analytics/drivers.py` & `analytics/anomalies.py`: `.fillna("(missing)")` preserves null dimension groups | Phase 3 |
| 3.7 Narrow exception handling in export | fixed | `export/chart_images.py` ThreadPoolExecutor timeout & `pptx_builder.py` `_add_chart_placeholder`; verified by `tests/test_export_hardening.py` | Phase 8 |
| 3.8 LLM sentence-split parsing / bad cache | fixed | `insight/client.py`: strict JSON schema validation, 1-shot repair prompt, faithfulness check, deterministic fallback; verified by `tests/test_insight_reliability.py` | Phase 5 |
| 4.1 Everything aggregated with `.sum()` | fixed | `analytics/kpis.py`, `trend.py`, `drivers.py`, `snapshot.py`: configurable `agg`, rate metrics default to `mean`; verified by `tests/test_analytics_deep_coverage.py::test_kpi_rate_metric_aggregation_is_mean_not_sum` | Phase 4 |
| 4.2 Anomalies = structural outliers | fixed | `analytics/anomalies.py`: `detect_temporal_anomalies` rolling baselines, structural outlier labeling; verified by `tests/test_analytics_deep_coverage.py::test_anomalies_temporal_and_severities` | Phase 4 |
| 4.3 Cache/budget not multi-process safe | fixed | `insight/budget.py` and `cache.py` migrated to SQLite WAL with atomic check-and-increment and busy timeout; verified by `tests/test_concurrency.py` | Phase 6 |
| 4.4 Dockerfile kaleido libs | fixed | `Dockerfile` runs as dedicated non-root user `aivara` (UID 10001), `HEALTHCHECK` added; verified by `tests/test_security.py` | Phase 7 |
| 4.5 README privacy overstated | fixed | `insight/redactor.py` & `README.md`: label pseudonymization default ON (`AIVARA_LLM_REDACT_LABELS: bool = True`), documented in README; verified by `tests/test_insight_reliability.py` | Phase 5 |

---

## Gate Checklists

### Phase 12 Exit Gate (v1.0.0 Release)
- [x] Official semver `__version__ = "1.0.0"` in `config.py` and displayed in sidebar.
- [x] Comprehensive overhaul of `README.md` reflecting production architecture, verified quickstart, configuration table, supported analytics packs, and security posture.
- [x] Comprehensive documentation suite authored:
  - `docs/ARCHITECTURE.md`: Subsystem layout, data pipelines, error boundaries, and design invariants.
  - `docs/USER_GUIDE.md`: File preparation guidelines, schema review, metric aggregation semantics, and presentation exports.
  - `docs/TESTING.md`: Quality assurance strategy, golden snapshots, AppTest headless tests, and offline isolation invariants.
- [x] User Acceptance Testing (UAT) automated validation harness (`scripts/uat_verify.py`) running 5 diverse real-world domain datasets (Commerce, Inventory, Project, HR, Survey) with 100% pass rate.
- [x] Final release verification: 306/306 pytest tests passing with 81.43% coverage, zero ruff errors, zero mypy errors, zero bandit vulnerabilities.
- [x] Release packaging: `CHANGELOG.md` finalized with `[1.0.0] - 2026-10-16`, tagged `v1.0.0` and `phase-12-complete`.

### Global Gate (Phase 12 / v1.0.0 Release Evaluation)
- [x] Full test suite passes: 306/306 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 58 source files.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (81.43% repo-wide > 75% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] All 13 phases (0 through 12) from `AIVARA_AGENT_PLAN.md` complete.

### Phase 11 Exit Gate
- [x] Benchmark pipeline on 1k, 10k, 50k scales (`scripts/bench.py`) measuring per-stage latency and peak memory via `tracemalloc`.
- [x] 10k rows processes in < 10 seconds on standard laptop (achieved 4.93s).
- [x] Memory consumption stays under 500MB for 50k rows (achieved 9.41MB peak RAM).
- [x] File over `MAX_ROWS_FULL_PROCESSING` (500k rows) triggers informative warning note and safe stratified sampling, not crash.
- [x] Concurrency safety: 5 concurrent worker sessions executing 10k rows in 10.85s (~4,609 rows/sec) without race conditions.
- [x] Performance documentation complete (`docs/PERFORMANCE.md`) with latency breakdown, sizing limits, and hardware deployment profiles.
- [x] Performance test suite (`tests/test_performance.py`) passing (4/4 tests).
- [x] Global gate passes (306/306 tests pass, 81.43% coverage, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 11 Evaluation)
- [x] Full test suite passes: 306/306 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 57 source files.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (81.43% repo-wide > 75% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, `docs/PERFORMANCE.md` updated.

### Phase 10 Exit Gate
- [x] Strongly typed `Settings` dataclass with `validate()` and `.from_env()` startup validation (`config.py`).
- [x] Semver `__version__ = "0.9.0"` defined in `config.py` and displayed in sidebar.
- [x] Structured JSON logging (`infra/logger.py`) with active secret and API key redaction.
- [x] Dedicated LLM call audit logger (`aivara.audit.llm`) tracking model, token usage, and budget balance without capturing prompt or completion content.
- [x] Production `docker-compose.yml` with persistent volume `aivara_data`, resource limits, and health check.
- [x] Documented environment template `.env.example`.
- [x] Automated smoke script `scripts/smoke_container.py` checking health and app endpoints.
- [x] Comprehensive documentation: `docs/CONFIGURATION.md` and `docs/RUNBOOK.md`.
- [x] Observability test suite (`tests/test_observability.py`) with 10 passing tests.
- [x] Global gate passes (302/302 tests pass, 81.33% coverage, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 10 Evaluation)
- [x] Full test suite passes: 302/302 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 56 source files.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (81.33% repo-wide > 75% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, `docs/CONFIGURATION.md`, `docs/RUNBOOK.md` updated.

### Phase 9 Exit Gate
- [x] `app.py` < 200 lines of routing/wiring (achieved 119 lines); no function > 60 lines.
- [x] Table-driven tab registry `TabSpec` per profile/domain replaces duplicated blocks (`ui/tabs.py`).
- [x] Strongly typed `PipelineResult` dataclass in `analytics/pipeline.py` with backward-compatible dict interface.
- [x] Pure PPTX export deck assembly decoupled from UI wiring (`export/deck_assembly.py`).
- [x] Tab error boundaries (`ui/error_boundary.py`) ensure an unhandled tab error displays friendly message + correlation ID and does not blank other tabs.
- [x] Forecast stub tab removed for v1.0 per Decision D3.
- [x] Removed `__import__("pandas")` from codebase.
- [x] Streamlit `AppTest` suite (`tests/test_ui_apptest.py`) covers startup, schema confirm, tab rendering, error boundary, and export.
- [x] mypy clean across `config.py`, `analytics/`, `ingestion/`, `export/`, `insight/`, `ui/`, `app.py` (49 source files).
- [x] Global gate passes (292/292 tests pass, 81.26% coverage, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 9 Evaluation)
- [x] Full test suite passes: 292/292 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 49 source files.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (81.26% repo-wide > 75% threshold; `app.py` 95%, `error_boundary.py` 100%, `pipeline.py` 88%).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md` and `CHANGELOG.md` updated.

### Phase 8 Exit Gate
- [x] Kaleido rendering timeout protection (`export/chart_images.py`) with configurable `AIVARA_KALEIDO_TIMEOUT`.
- [x] Graceful slide placeholder card `_add_chart_placeholder` renders on export failure / timeout (Audit 3.7).
- [x] Degraded & empty deck resilience: empty view lists in `build_toc_slide` and `build_executive_summary_slide` render informative notes without error.
- [x] Large drivers table stress resilience: 50+ category drivers tables safely truncated to top 10 contributors.
- [x] OpenXML presentation zip structure integrity verified via `zipfile.ZipFile`.
- [x] Number consistency verification: asserting exact correspondence between formatted pipeline display values and slide text across KPI tiles and deltas.
- [x] Total offline isolation guarantee: verified zero network calls and zero imports of `insight.client` across the `export/` package.
- [x] Dedicated export hardening test suite (`tests/test_export_hardening.py`) passing (10/10).
- [x] Global gate passes (284/284 tests pass, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 8 Evaluation)
- [x] Full test suite passes: 284/284 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 44 source files.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (77.87% repo-wide, `export/` 91.56%).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md` and `CHANGELOG.md` updated.

### Phase 7 Exit Gate
- [x] Threat model committed (`docs/THREAT_MODEL.md`) and each identified threat has a mitigation or accepted-risk entry.
- [x] Security deployment guide committed (`docs/SECURITY.md`) covering reverse-proxy authentication and vulnerability reporting.
- [x] Authentication fails closed when `AIVARA_AUTH_REQUIRED=true`; verified by test (`tests/test_security.py::test_auth_fails_closed_when_required`).
- [x] Spreadsheet / CSV formula injection neutralized across exports (`export/formula_sanitizer.py`, verified by `test_formula_injection_scalar_neutralization` and `test_pptx_export_neutralizes_formula_injection`).
- [x] Upload validation rejects executables (PE, ELF, Mach-O, Java class), null bytes, and path traversal filenames (`ingestion/loader.py`).
- [x] Secrets masked and placeholders refused at startup (`config.py`).
- [x] Network egress SSRF defense validates LLM base URLs against allowlist and blocks metadata/internal IPs (`insight/client.py`).
- [x] Output safety audited and dynamic views escaped with `html.escape` (`ui/stats_view.py`).
- [x] Container runtime hardened (`Dockerfile`, `.streamlit/config.toml`, `.dockerignore`) with non-root user and healthcheck.
- [x] Global gate passes (274/274 tests pass, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 7 Evaluation)
- [x] Full test suite passes: 274/274 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 31 core modules.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (77.02% repo-wide, core engines >= 81-98%).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, `docs/THREAT_MODEL.md`, `docs/SECURITY.md` updated.

### Phase 6 Exit Gate
- [x] State inventory complete and committed to docs (`docs/STATE_INVENTORY.md`).
- [x] Concurrency tests pass: 10/10 concurrency tests pass including multi-threaded and multi-process cross-process exhaustion.
- [x] Multi-user isolation verified: Session-scoped caches and dataset states cannot leak across concurrent sessions.
- [x] Atomic budget enforcement: SQLite WAL store with `check_and_increment_daily` prevents TOCTOU over-limit calls under load.
- [x] Zero raw row persistence invariant holds across cache, budget, and exports.
- [x] SQLite corruption recovery verified under invalid/corrupt database files.
- [x] Global gate passes (222/222 tests pass, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 6 Evaluation)
- [x] Full test suite passes: 222/222 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 30 core modules.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (92.78% > 75% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, `docs/STATE_INVENTORY.md` updated.

### Phase 5 Exit Gate
- [x] Structured JSON output enforced via strict schema validation (`parse_and_validate_insight`).
- [x] 1-shot repair retry implemented and tested (`build_repair_prompt`).
- [x] Deterministic template fallback verified (no LLM, no crash, 3 sentences via `insight/fallback.py`).
- [x] Prompt injection defenses tested against sample malicious payloads (`<business_data>` encapsulation and string sanitization).
- [x] Faithfulness check rejects synthetic hallucinations in tests (`insight/faithfulness.py`).
- [x] Model name displayed honestly (shows fallback model or fallback template when active).
- [x] OpenRouter labels redaction toggle implemented (`AIVARA_LLM_REDACT_LABELS: bool = True`), documented in README.
- [x] Test coverage on `insight/` >= 80% (achieved 90.19%).
- [x] Global gate passes (212/212 tests pass, ruff clean, mypy clean, bandit clean).

### Global Gate (Phase 5 Evaluation)
- [x] Full test suite passes: 212/212 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 30 core modules.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (89.4% overall, `insight/` 90.19% > 80% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, `README.md` updated.

### Phase 4 Exit Gate
- [x] Coverage >= 95.0% across `analytics/**` (`analytics/` achieves 95.71% branch coverage).
- [x] Every analytics module has dedicated tests (`kpis`, `trend`, `drivers`, `anomalies`, `stats`, `snapshot`, `profiler`, `commerce`, `finance`, `workforce`, `feedback`).
- [x] Rate/ratio metrics are no longer summed (verified by `test_kpi_rate_metric_aggregation_is_mean_not_sum`).
- [x] Anomaly output labeled correctly ("structural outlier"); severity tiers consistent end-to-end (`SEVERITY_LOW`, `SEVERITY_MEDIUM`, `SEVERITY_HIGH`).
- [x] Golden snapshot diffs reviewed and recorded in `DECISIONS.md` (Decision D11).

### Global Gate (Phase 4 Evaluation)
- [x] Full test suite passes: 194/194 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 27 core engine modules.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (88.54% > 75% threshold; `analytics/` 95.71% > 95% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md`, `CHANGELOG.md`, and `DECISIONS.md` updated.

### Phase 3 Exit Gate
- [x] Ingestion unit/property test coverage >= 95.0% (`ingestion/` achieves 95.73% branch coverage).
- [x] Bad line skipping counted and reported in `LoadResult.notes` (Audit 3.1).
- [x] Percent scaling divides by 100 with unit `%` and classified as rate (Audit 3.2).
- [x] Centralized null strings configured in `config.py` and normalized (Audit 3.3).
- [x] Partial coercion failures tracked per column in `CleanReport` (Audit 3.4).
- [x] Compact dates preserved before numeric coercion pass (Audit 3.5).
- [x] Missing dimensions preserved with `(missing)` bucket (Audit 3.6).
- [x] Upload limit `MAX_UPLOAD_MB` (100 MB) and column limit `MAX_COLUMNS` (500) enforced.
- [x] Empty file guard prevents unhandled crashes.
- [x] Column headers deduplicated (`col`, `col_2`) and trimmed.
- [x] Data quality summary panel active on upload page in `ui/upload_page.py`.

### Phase 2 Exit Gate
- [x] All 8 items from Audit §1 have automated regression tests passing (`tests/test_core_correctness.py`).
- [x] Cache is strictly isolated per session/thread (verified by `test_cross_user_view_cache_isolation`).
- [x] Invariant holds across all fixtures: Screen figure == Facts packet == PPTX figure (verified by `test_number_consistency_screen_facts_pptx`).
- [x] Reset on upload wipes all cached analytics, export buffers, and classification states.
- [x] Bandit scan passes with 0 Medium/High issues.

---

## Decisions (see DECISIONS.md)

| ID | Decision | Status | Answer |
|---|---|---|---|
| D1 | Deployment model | accepted | Small shared team, single instance with session isolation |
| D2 | Auth approach | accepted | Reverse-proxy header auth + optional shared secret fallback; fail closed |
| D3 | Forecast tab | accepted | Hide stub for v1.0, backlog it |
| D4 | PPTX chart rendering | accepted | Keep Kaleido with subprocess timeout & placeholder degradation |
| D5 | LLM label redaction default | accepted | Default ON: Redact entity/categorical values in facts packets |
| D6 | Tier-2 column classification | accepted | Delete prompt (less egress, deterministic heuristics sufficient) |
| D7 | License | accepted | Apache 2.0 (committed in LICENSE) |
| D8 | Hosting target / deploy | accepted | Docker + Compose, no auto-deploy from CI |
| D9 | Supported data scale | accepted | 500k rows / 100 MB max |
| D10 | LLM providers | accepted | OpenRouter only with swappable adapter interface |
| D11 | Golden snapshot re-baselining | accepted | Re-baseline golden snapshots for statistical disclaimer and $n \ge 5$ threshold |

---

## Blockers / Questions for Human

| Date | Question | Options | Recommendation | Blocks |
|---|---|---|---|---|
| None | All Phase 4 tasks complete; Phase 5 ready to proceed. | — | — | — |

---

## Backlog (out of scope)
- Advanced time series forecasting engine with prediction intervals (Prophet / ARIMA / NeuralProphet).
- Multi-dataset joins and relational data models.
- Native PowerPoint shapes and charts without Kaleido headless browser dependency.

---

## Metrics Over Time

| Date | Phase | Tests | Coverage % | Lint errors | mypy errors | Open bugs |
|---|---|---|---|---|---|---|
| 2026-10-15 | 0 (Baseline) | 126 | ~82% | TBD | TBD | 0 |
| 2026-10-15 | 1 (Tooling) | 128 | 80.86% | 0 | 0 | 0 |
| 2026-10-15 | 2 (Core Correctness) | 140 | 81.79% | 0 | 0 | 0 |
| 2026-10-15 | 3 (Ingestion Hardening) | 173 | 85.63% (ingestion 95.73%) | 0 | 0 | 0 |
| 2026-10-15 | 4 (Analytics Validity) | 194 | 88.54% (analytics 95.71%) | 0 | 0 | 0 |
| 2026-10-15 | 5 (LLM Reliability & Privacy) | 212 | 89.40% (insight 90.19%) | 0 | 0 | 0 |
| 2026-10-15 | 6 (State & Concurrency) | 222 | 92.78% | 0 | 0 | 0 |
| 2026-10-15 | 7 (Security Hardening) | 274 | 77.02% (repo-wide) | 0 | 0 | 0 |
| 2026-10-16 | 8 (Export Hardening) | 284 | 77.87% (export 91.56%) | 0 | 0 | 0 |
| 2026-10-16 | 9 (App Structure & UX) | 292 | 81.26% (app 95%) | 0 | 0 | 0 |
| 2026-10-16 | 10 (Observability & Deployment) | 302 | 81.33% | 0 | 0 | 0 |
| 2026-10-16 | 11 (Performance & Scale) | 306 | 81.43% | 0 | 0 | 0 |
| 2026-10-16 | 12 (Release v1.0.0) | 306 | 81.43% | 0 | 0 | 0 |
