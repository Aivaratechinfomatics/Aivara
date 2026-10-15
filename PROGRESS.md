# Progress

Last updated: 2026-10-15   Current phase: 1 — Tooling, CI, repo hygiene   Overall: 2/13 phases complete

> Source of truth for the hardening effort. The agent updates this file at the start of every PLAN, after every significant commit, and at every LOG step. Goal document: `AIVARA_AGENT_PLAN.md`.

## Phase Board

| Phase | Name | Status | Started | Done | Tag |
|---|---|---|---|---|---|
| 0 | Baseline & safety net | done | 2026-10-15 | 2026-10-15 | phase-0-complete |
| 1 | Tooling, CI, repo hygiene | done | 2026-10-15 | 2026-10-15 | phase-1-complete |
| 2 | Core correctness (audit §1) | not-started | | | |
| 3 | Ingestion hardening (audit §3) | not-started | | | |
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

## Current Phase Detail — Phase 1: Tooling, CI, Repo Hygiene

### Plan (written before coding)
- **Tasks**:
  - [x] Configure `pyproject.toml` (Ruff line-length 100, Mypy Python 3.12, Pytest options, branch coverage).
  - [x] Split development and runtime dependencies (`requirements-dev.txt`).
  - [x] Build test safety harness (`tests/conftest.py` with socket blocking, temp-dir cache/budget isolation, fake OpenRouter fixture).
  - [x] Add automated test proving socket blocker halts external network requests (`tests/test_safety_harness.py`).
  - [x] Establish CI workflow (`.github/workflows/ci.yml` matrix py3.11, py3.12 with lint, mypy, pytest, bandit, pip-audit).
  - [x] Repo hygiene: add `.dockerignore`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE` (Apache 2.0), `examples/`, `.pre-commit-config.yaml`, `run.sh`.
- **Risks**: Mypy type discrepancies in legacy modules; socket blocker interfering with internal test execution. Resolved by exempting localhost/loopback and adding targeted type annotations to `loader.py`, `workforce.py`, `client.py`, and `pptx_builder.py`.
- **Test strategy**: Run `ruff check`, `ruff format --check`, `mypy`, `bandit`, and `pytest --cov`.

### Work Log (append-only, newest last)
- 2026-10-15 21:48: Created Phase 1 implementation plan artifact.
- 2026-10-15 21:48: Created `pyproject.toml` specifying project metadata, Ruff, Mypy, and Pytest coverage configuration.
- 2026-10-15 21:48: Created `requirements-dev.txt` for development, testing, typing, and security audit tools.
- 2026-10-15 21:48: Built test harness `tests/conftest.py` with automatic external network blocker, temp-dir isolation, and fake LLM mock.
- 2026-10-15 21:49: Added `tests/test_safety_harness.py` verifying external network attempts trigger `RuntimeError`.
- 2026-10-15 21:49: Created `.dockerignore`, `examples/` directory, and `examples/README.md`.
- 2026-10-15 21:49: Created Apache 2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `run.sh`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`.
- 2026-10-15 21:50: Executed Ruff across codebase: formatted 43 files and resolved all lint violations.
- 2026-10-15 21:56: Resolved all Mypy type errors across 27 core engine modules.
- 2026-10-15 21:57: Executed Bandit security scan: 0 Medium/High issues identified.
- 2026-10-15 21:59: Executed full test suite with coverage: 128 passed, 80.86% coverage, 0 regressions in golden tests.
- 2026-10-15 22:00: Verified all Phase 1 Exit Gates and Global Gates passed.

### Test Results
- 2026-10-15 21:52: `python -m ruff check .` & `python -m ruff format --check .` -> Clean (All checks passed!)
- 2026-10-15 21:56: `python -m mypy config.py analytics/ ingestion/ export/ insight/` -> Success: no issues found in 27 source files
- 2026-10-15 21:57: `python -m bandit -r config.py analytics/ ingestion/ export/ insight/ -ll` -> No issues identified (0 High, 0 Medium)
- 2026-10-15 21:58: `python -m pytest tests/ --cov` -> 128 passed, 80.86% total coverage (meets >= 75% bar)
- 2026-10-15 22:00: `python -m pytest tests/test_golden.py -v` -> 8/8 passed with 0 diffs

### Debug Log
- `mypy`: Python 3.11 target failed on numpy 2.5 type syntax -> Updated target to Python 3.12 in `pyproject.toml` -> Resolved (attempt 1/3).
- `mypy`: `pptx.Presentation` factory function invalid as type in `pptx_builder.py` -> Annotated presentation parameter with `prs: Any` -> Resolved (attempt 1/3).
- `mypy`: `workforce.py` `agg_dict` type mismatch -> Removed unused local aggregation dict -> Resolved (attempt 1/3).

---

## Audit Verification Matrix

| Audit item | Status on main (still-broken / already-fixed / n-a) | Test / Evidence | Closed in phase |
|---|---|---|---|
| 1.1 Cross-user `view::*` cache | still-broken | `insight/cache.py` line 79-80 still falls back to global in-memory `_view_cache` when not in session state | Phase 6 |
| 1.2 Trend plots wrong metric | already-fixed | `app.py` line 166-173: `primary_metric` is selected before `build_trend_series` | Phase 2 (regression test) |
| 1.3 Driver contribution % when net delta ≈ 0 | already-fixed | `analytics/drivers.py` lines 86-92: normalizes by `sum_abs_delta` floor floor | Phase 2 (regression test) |
| 1.4 `pct_change` +inf for negative swing | already-fixed | `analytics/kpis.py` line 89: `float('inf') if current_total > 0 else float('-inf')`; covered by `test_negative_swing_from_zero_pct_change` | Phase 2 (regression test) |
| 1.5 `inf%` rendered in UI/PPTX | already-fixed | `ui/components.py` line 69-70 & `app.py` line 283: `format_pct_change` renders "new" / "n/a" for infinite deltas in both UI and PPTX | Phase 2 (regression test) |
| 1.6 Schema gate not reset on new upload | already-fixed | `ui/upload_page.py` line 69: resets `schema_confirmed = False` on new content hash | Phase 2 (regression test) |
| 1.7 Same-name re-upload ignored | already-fixed | `ui/upload_page.py` line 46-48: keyed on `hashlib.md5(file_bytes)` | Phase 2 (regression test) |
| 1.8 Stale export figures across datasets | already-fixed | `ui/upload_page.py` line 71-74: pops `_export_figures`, `_pptx_buffer`, `_view_insights`, calls `clear_view_cache()` | Phase 2 (regression test) |
| 2.1 Tier-2 LLM classification unwired | already-fixed | `ui/upload_page.py` lines 101-116: wired to interactive `✨ Auto-classify ambiguous columns with AI` button; slated for removal in Phase 5 per D6 | Phase 5 |
| 2.2 Paid-model toggle / silent substitution | already-fixed | `app.py` line 257 (`allow_paid` toggle) and `ui/components.py` line 116 (`Used fallback model...` caption) | Phase 5 (regression test) |
| 2.3 `MAX_ROWS_FULL_PROCESSING` unused | already-fixed | `ingestion/loader.py` lines 389-393: samples at `MAX_ROWS_FULL_PROCESSING` and appends note | Phase 3 (regression test) |
| 2.4 Unused constants/functions | already-fixed | `SEVERITY_LOW` used in `anomalies.py`; `estimate_tokens` used in `client.py`; `APP_TABS` used in `app.py` | Phase 4 / Phase 9 |
| 2.5 Customers tab duplicate of Operations | already-fixed | `app.py` lines 593-601: filters for customer-shaped dimension columns or shows informative empty state | Phase 9 (regression test) |
| 3.1 `on_bad_lines="skip"` silent drop | already-fixed | `ingestion/loader.py` lines 359-385: records `skipped_bad_lines` and reports in `notes` | Phase 3 (regression test) |
| 3.2 Percent columns mis-scaled | already-fixed | `ingestion/cleaner.py` line 65: divides by 100.0; verified by `test_percent_columns_scaled_properly` | Phase 3 (regression test) |
| 3.3 Null tokens inconsistent | already-fixed | `ingestion/cleaner.py` line 23: normalized `_NULL_STRINGS` set; verified by `test_null_placeholders_normalized` | Phase 3 (regression test) |
| 3.4 Partial coercion not reported | already-fixed | `ingestion/cleaner.py` line 76: reports unparsed count in `report.messages`; verified by `test_partial_coercion_reports_failure_count` | Phase 3 (regression test) |
| 3.5 Compact dates claimed by numeric pass | already-fixed | `ingestion/cleaner.py` line 48: guards against date-shape before numeric coercion; verified by `test_compact_date_format_coerced_to_datetime_not_numeric` | Phase 3 (regression test) |
| 3.6 NaN dimensions dropped silently | already-fixed | `analytics/drivers.py` & `analytics/anomalies.py`: `.fillna("(missing)")` preserves null dimension groups | Phase 3 (regression test) |
| 3.7 Narrow exception handling in export | still-broken | `export/pptx_builder.py` line 341 catches Exception but has no timeout or slide placeholder | Phase 8 |
| 3.8 LLM sentence-split parsing / bad cache | still-broken | `insight/client.py` line 48 has fallback sentence regex without strict JSON schema validation | Phase 5 |
| 4.1 Everything aggregated with `.sum()` | still-broken | Rate metrics use `mean`, but general metrics lack configurable aggregation (`sum`, `mean`, `weighted_mean`, `last`) in UI | Phase 4 |
| 4.2 Anomalies = structural outliers | still-broken | `analytics/anomalies.py` only computes category-vs-category cross-sectional z-scores, not temporal rolling baselines | Phase 4 |
| 4.3 Cache/budget not multi-process safe | still-broken | `insight/budget.py` and `cache.py` use `threading.Lock` rather than multi-process safe locks/SQLite | Phase 6 |
| 4.4 Dockerfile kaleido libs | still-broken | `Dockerfile` runs as root, unpinned base digest, no HEALTHCHECK | Phase 1 / Phase 10 |
| 4.5 README privacy overstated | still-broken | `README.md` states "raw data never leaves this server" but facts packets include categorical entity names | Phase 5 / Phase 12 |

---

## Gate Checklists

### Phase 1 Exit Gate
- [x] CI workflow files valid and committed (`.github/workflows/ci.yml`).
- [x] `pyproject.toml`, `requirements-dev.txt`, `tests/conftest.py` created and operational.
- [x] `ruff check`, `mypy`, and `pytest` clean.
- [x] Socket blocking fixture actively prevents unauthorized network connections (`tests/test_safety_harness.py`).
- [x] Golden tests pass after tooling configuration (8/8 passing).
- [x] Repo hygiene artifacts (`.dockerignore`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, `examples/`) present.

### Global Gate (Phase 1 Evaluation)
- [x] Full test suite passes: 128/128 passed across consecutive runs.
- [x] `ruff check` and `ruff format --check` clean.
- [x] `mypy` clean on 27 core engine modules.
- [x] No test makes a real network call (enforced by socket-blocking fixture).
- [x] No new skips/xfails.
- [x] Coverage met (80.86% > 75% threshold).
- [x] No secrets, sample customer data, or `.env` content committed.
- [x] `PROGRESS.md` and `CHANGELOG.md` updated.

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
| None | All Phase 1 tasks unblocked. | — | — | — |

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
