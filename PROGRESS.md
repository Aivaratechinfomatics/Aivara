# Progress

Last updated: 2026-10-15   Current phase: 4 — Analytics validity & coverage   Overall: 4/13 phases complete

> Source of truth for the hardening effort. The agent updates this file at the start of every PLAN, after every significant commit, and at every LOG step. Goal document: `AIVARA_AGENT_PLAN.md`.

## Phase Board

| Phase | Name | Status | Started | Done | Tag |
|---|---|---|---|---|---|
| 0 | Baseline & safety net | done | 2026-10-15 | 2026-10-15 | phase-0-complete |
| 1 | Tooling, CI, repo hygiene | done | 2026-10-15 | 2026-10-15 | phase-1-complete |
| 2 | Core correctness (audit §1) | done | 2026-10-15 | 2026-10-15 | phase-2-complete |
| 3 | Ingestion hardening (audit §3) | done | 2026-10-15 | 2026-10-15 | phase-3-complete |
| 4 | Analytics validity & coverage | not-started | | | |
| 5 | LLM layer: reliability & privacy | not-started | | | |
| 6 | State, concurrency, multi-user | not-started | | | |
| 7 | Security hardening | not-started | | | |
| 8 | Export hardening | not-started | | | |
| 9 | App structure, UX, UI tests | not-started | | | |
| 10 | Observability, config, deployment | not-started | | | |
| 11 | Performance & scale | not-started | | | |
| 12 | Docs, UAT, release v1.0.0 | not-started | | | |

Status values: not-started / planning / in-progress / testing / debugging / gate / done / blocked

---

## Current Phase Detail — Phase 3: Ingestion Hardening (Audit §3)

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
| 2.1 Tier-2 LLM classification unwired | already-fixed | `ui/upload_page.py` lines 101-116: wired to interactive `✨ Auto-classify ambiguous columns with AI` button; slated for removal in Phase 5 per D6 | Phase 5 |
| 2.2 Paid-model toggle / silent substitution | already-fixed | `app.py` line 257 (`allow_paid` toggle) and `ui/components.py` line 116 (`Used fallback model...` caption) | Phase 5 (regression test) |
| 2.3 `MAX_ROWS_FULL_PROCESSING` unused | already-fixed | `ingestion/loader.py` lines 389-393: samples at `MAX_ROWS_FULL_PROCESSING` and appends note | Phase 3 (regression test) |
| 2.4 Unused constants/functions | already-fixed | `SEVERITY_LOW` used in `anomalies.py`; `estimate_tokens` used in `client.py`; `APP_TABS` used in `app.py` | Phase 4 / Phase 9 |
| 2.5 Customers tab duplicate of Operations | already-fixed | `app.py` lines 593-601: filters for customer-shaped dimension columns or shows informative empty state | Phase 9 (regression test) |
| 3.1 `on_bad_lines="skip"` silent drop | fixed | `ingestion/loader.py`: records `skipped_bad_lines` and reports in `notes`; verified by `tests/test_loader.py::test_malformed_csv_bad_lines_counted_and_reported` | Phase 3 |
| 3.2 Percent columns mis-scaled | fixed | `ingestion/cleaner.py`: divides by 100.0, tags `%` unit; verified by `tests/test_cleaner.py::test_percent_columns_scaled_properly` | Phase 3 |
| 3.3 Null tokens inconsistent | fixed | `config.py` & `ingestion/cleaner.py`: centralized `DEFAULT_NULL_STRINGS`; verified by `tests/test_cleaner.py::test_null_placeholders_normalized` | Phase 3 |
| 3.4 Partial coercion not reported | fixed | `ingestion/cleaner.py`: reports unparsed counts in `CleanReport.coercion_failures`; verified by `tests/test_cleaner.py::test_partial_coercion_reports_failure_count` | Phase 3 |
| 3.5 Compact dates claimed by numeric pass | fixed | `ingestion/cleaner.py`: date pattern checks before numeric coercion; verified by `tests/test_cleaner.py::test_compact_date_format_coerced_to_datetime_not_numeric` | Phase 3 |
| 3.6 NaN dimensions dropped silently | fixed | `analytics/drivers.py` & `analytics/anomalies.py`: `.fillna("(missing)")` preserves null dimension groups | Phase 3 |
| 3.7 Narrow exception handling in export | still-broken | `export/pptx_builder.py` line 341 catches Exception but has no timeout or slide placeholder | Phase 8 |
| 3.8 LLM sentence-split parsing / bad cache | still-broken | `insight/client.py` line 48 has fallback sentence regex without strict JSON schema validation | Phase 5 |
| 4.1 Everything aggregated with `.sum()` | still-broken | Rate metrics use `mean`, but general metrics lack configurable aggregation (`sum`, `mean`, `weighted_mean`, `last`) in UI | Phase 4 |
| 4.2 Anomalies = structural outliers | still-broken | `analytics/anomalies.py` only computes category-vs-category cross-sectional z-scores, not temporal rolling baselines | Phase 4 |
| 4.3 Cache/budget not multi-process safe | still-broken | `insight/budget.py` and `cache.py` use `threading.Lock` rather than multi-process safe locks/SQLite | Phase 6 |
| 4.4 Dockerfile kaleido libs | still-broken | `Dockerfile` runs as root, unpinned base digest, no HEALTHCHECK | Phase 1 / Phase 10 |
| 4.5 README privacy overstated | still-broken | `README.md` states "raw data never leaves this server" but facts packets include categorical entity names | Phase 5 / Phase 12 |

---

## Gate Checklists

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

### Global Gate (Phase 3 Evaluation)
- [x] Full test suite passes: 173/173 passed across consecutive runs (0 failures).
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 27 core engine modules.
- [x] `bandit` scan passes with 0 Medium/High issues.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Overall coverage met (85.63% > 75% threshold; `ingestion/` 95.73% > 95% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md` and `CHANGELOG.md` updated.

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

---

## Blockers / Questions for Human

| Date | Question | Options | Recommendation | Blocks |
|---|---|---|---|---|
| None | All Phase 3 tasks complete; Phase 4 ready to proceed. | — | — | — |

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
