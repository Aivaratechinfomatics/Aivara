# Aivara Insight Lite — Industrial-Grade Hardening Plan (Agent Goal Document)

**Repo:** https://github.com/Aivaratechinfomatics/Aivara (Streamlit + pandas + OpenRouter + python-pptx)
**Mission:** Take Aivara Insight Lite from a working prototype to a secure, correct, tested, observable, deployable v1.0 that a team can run in production with confidence.
**Audience:** An autonomous AI coding agent. Humans review at gates and answer escalations.

---

## 0. Operating Contract (read first, obey always)

### 0.1 The Phase Loop
Every phase runs this exact loop. Do not skip steps. Do not start phase N+1 until phase N's gate is green.

```
PLAN → DEVELOP → TEST → DEBUG → GATE → LOG → (next phase)
```

1. **PLAN** — Before touching code: re-read the phase, inspect the current code it touches, and write a short phase plan into `PROGRESS.md` (tasks, files, risks, test strategy, what "done" means). Create the task list.
2. **DEVELOP** — Work in small commits on branch `phase-N-<slug>`. Write the failing test first wherever a bug is being fixed (red → green). One concern per commit.
3. **TEST** — Run the full suite, linters, type checks, and the phase's specific verification commands. Record real command output summaries in the log, not guesses.
4. **DEBUG** — Any failure: reproduce → minimal failing test → root cause → fix → rerun *everything*. Max **3 fix attempts per distinct failure**; then log a blocker and ask the human (see 0.4).
5. **GATE** — Check every item in the phase's Exit Gate plus the Global Gate (0.2). All must pass.
6. **LOG** — Update `PROGRESS.md`, tag `phase-N-complete`, merge to `main` via PR (or fast-forward if solo), and write 5–10 lines of summary: what changed, what was learned, what is deferred.

### 0.2 Global Gate (applies to every phase exit)
- [ ] Full test suite passes, **3 consecutive runs** (detects flakiness)
- [ ] `ruff check` and `ruff format --check` clean (from Phase 1 onward)
- [ ] `mypy` clean on modules covered so far (from Phase 1 onward)
- [ ] No test makes a real network call (enforced by a socket-blocking fixture, from Phase 1)
- [ ] No new `skip`/`xfail`/`# noqa`/`# type: ignore` without a logged reason in `PROGRESS.md`
- [ ] Coverage did not decrease; phase-specific coverage target met
- [ ] App starts (`streamlit run app.py`) and the smoke checklist (Appendix A) passes
- [ ] `PROGRESS.md` updated; commit(s) pushed; tag created
- [ ] No secrets, sample customer data, or `.env` content committed

### 0.3 Hard Rules
- **Never weaken, delete, or skip a test to make it pass.** Fix the code or log a blocker.
- **Verify before fixing.** `aivara-insight-lite_AUDIT_AND_FIX_BRIEF.md` is partly stale (e.g. `app.py` already has `format_pct_change`, the Customers tab filter, the paid-model toggle, and computes `primary_metric` before the trend). For every audit item: write a repro test on current `main` first. If it passes already, record "already fixed" and keep the test as a regression guard.
- **Compute-first principle is inviolable:** all arithmetic stays local in pandas; the LLM only narrates pre-computed facts.
- **Do not change product behavior silently.** Behavior changes go in `CHANGELOG.md` and `DECISIONS.md`.
- **No scope creep.** New ideas go to the `Backlog` section of `PROGRESS.md`, not into the current phase.
- **Commit hygiene:** conventional commits (`fix:`, `feat:`, `test:`, `chore:`, `docs:`), no force-push to `main`.

### 0.4 When to Stop and Ask the Human
Stop (log it under **Blockers** in `PROGRESS.md`, then ask) when:
- A decision in section 14 (Open Decisions) is needed and not yet answered
- Fixing a bug requires changing documented product behavior
- A failure survives 3 fix attempts
- A change would delete features/tabs or alter data-retention behavior
- You need credentials, a deploy target, or access you don't have
- Two requirements conflict

When asking, give: the question, 2–3 options, your recommendation, and what is blocked. Keep working on unblocked tasks meanwhile.

---

## 1. Baseline Findings (from repo review, Oct 2026)

Facts observed in the repository that this plan is built on:

| # | Observation | Implication |
|---|---|---|
| F1 | No `.github/` (no CI), no `LICENSE`, no `pyproject.toml`, no `.dockerignore`, no linter/type config | Phases 1, 7, 10 |
| F2 | `requirements.txt`: 2024-era pins (streamlit 1.38.0, pandas 2.2.2, numpy 1.26.4); `kaleido>=0.2.1` **unpinned** (newer major versions of kaleido need a system Chrome and behave differently); no dev/test deps, no hashes/lockfile | Pin, upgrade, `pip-audit`; verify kaleido behavior in Docker |
| F3 | `Dockerfile`: runs as root, no `HEALTHCHECK`, `COPY . .` with no `.dockerignore` (can bake `.env`, `.git`, cache JSONs into the image), unpinned base image | Phases 7, 10 |
| F4 | `app.py` is 613 lines: five near-identical tab-routing blocks, a ~170-line `run_pipeline`, a ~150-line `render_export_button`, `__import__("pandas")` hack, `render_sidebar() -> str` annotation but returns a tuple | Phase 9 refactor |
| F5 | The app has grown past the README: new modules (`analytics/profiler`, `snapshot`, `stats`, `domains/*`, `ui/chart_builder`, `ui/project_view`, `ui/domain_views`, `ui/stats_view`) plus project/snapshot/commerce/finance/workforce/feedback profiles. README, layout diagram, and tests describe only v1 core. README also references `aivara-insight-lite_product_guide.md`, which is not in the repo | Phases 4, 12; test gap is large |
| F6 | README says "your raw data never leaves this server", but facts packets include **data values** (entity names, category names, risk descriptions such as `"{item}: {issue}"`). Customer/employee/product names can reach OpenRouter | Phase 5 data-egress audit + redaction mode; fix wording |
| F7 | Insight cache and budget are JSON files guarded by `threading.Lock`; not safe across processes or sessions; `view::*` key was shared across users (audit §1.1) | Phase 6 |
| F8 | `.aivara_insight_cache.json` / `.aivara_budget_state.json` persist business figures to disk | Verify `.gitignore`; Phase 6 retention policy |
| F9 | Sample data are `.xlsx` files in repo root, but the app ingests CSV | Move to `examples/`, add CSV variants; verify they contain no real customer data |
| F10 | `MAX_ROWS_FULL_PROCESSING`, tier-2 LLM column classification, `estimate_tokens`, `SEVERITY_LOW`, `GRANULARITY_ORDER`: defined, never wired (audit §2) | Phase 5 / Phase 9: wire in or delete |
| F11 | Test files cover only: loader, classifier, kpis, drivers, budget, export-no-network. Nothing for cleaner, trend, anomalies, insight client/cache/facts, chart_images, profiler, snapshot, stats, domains, UI | Phases 2–9 add tests |
| F12 | No authentication (README says to put it behind VPN/reverse proxy); no upload size/type limits seen; no structured logging; no health endpoint | Phases 7, 10 |

---

## 2. Target State (definition of "industrial-grade")

- **Correct:** numbers on screen == numbers in exports == numbers in the LLM facts packet; every known audit bug has a regression test.
- **Honest:** every dropped row, coerced value, substituted model, or skipped insight is surfaced to the user.
- **Safe:** authenticated access, validated uploads, least-privilege container, no secrets in repo/image/logs, dependency and secret scanning in CI, documented data egress.
- **Isolated:** per-session state; no cross-user leakage; atomic budget/cache across processes.
- **Tested:** ≥85% line coverage overall, ≥95% on `analytics/` and `ingestion/`, UI smoke tests via `streamlit.testing.v1.AppTest`, container smoke test in CI.
- **Operable:** structured logs, health check, config validation at startup, pinned reproducible builds, runbook, versioned releases.
- **Maintainable:** typed, linted, table-driven UI routing, no dead code, docs that match reality.

---

## 3. Phase Overview

| Phase | Name | Core outcome |
|---|---|---|
| 0 | Baseline & safety net | Reproducible env, characterization tests, audit items verified against `main` |
| 1 | Tooling, CI, repo hygiene | Lint/type/test/security CI; pinned deps; clean repo |
| 2 | Core correctness (audit §1) | All wrong-number bugs fixed with regression tests |
| 3 | Ingestion hardening (audit §3) | No silent data loss; `test_cleaner.py` etc. |
| 4 | Analytics validity & coverage | Aggregation semantics, better anomalies, tests for all analytics modules |
| 5 | LLM layer reliability & privacy | Structured output, injection defense, egress control, mocked tests |
| 6 | State, concurrency, multi-user | Session isolation, atomic budget/cache, retention |
| 7 | Security hardening | Auth, upload validation, container hardening, threat model |
| 8 | Export hardening | Robust PPTX, kaleido timeouts, graceful degradation, container-tested |
| 9 | App structure, UX, UI tests | Refactor `app.py`, error boundaries, `AppTest` suite |
| 10 | Observability, config, deploy | Logging, health, config validation, Docker/compose, runbook |
| 11 | Performance & scale | Benchmarks at 500k rows, memory, concurrency |
| 12 | Docs, UAT, release v1.0.0 | Docs match reality; UAT passed; tagged release |

Phases are sequential. Phase 2 before 3 because correctness bugs corrupt everything downstream; Phase 9 refactor comes after tests exist (Phases 2–8) so refactoring is protected.

---

## 4. Phase 0 — Baseline & Safety Net

**Goal:** Know exactly what works today, and be able to detect any regression.

**PLAN**
- Clone repo, create `venv`, install requirements; note Python version used (target 3.11, confirm 3.12 compatibility).
- Create `PROGRESS.md`, `DECISIONS.md`, `CHANGELOG.md` (Keep-a-Changelog format).
- Read every module once; write a 1-page `docs/ARCHITECTURE_CURRENT.md` (data flow: upload → ingest → classify → profile → analytics → facts → LLM → UI → export).

**DEVELOP**
- Run existing tests (`pytest tests/ -v`); record pass/fail baseline. Fix only environment issues here.
- **Characterization ("golden") tests:** run the pipeline on both sample datasets (convert to CSV) and on every fixture CSV; snapshot key outputs (profile type, classifications, KPI values, driver tables, risk signals, executive takeaways) as JSON under `tests/golden/`. These pin current behavior so later phases show intentional diffs only.
- **Audit verification matrix:** for each of audit items 1.1–1.8, 2.1–2.5, 3.1–3.8, 4.1–4.5, write a repro test or script. Produce a table in `PROGRESS.md`: `item | status on main (still-broken / already-fixed / n-a) | evidence`.
- Check git history and the public repo for committed secrets or real data (`gitleaks detect` over full history); inspect the two `.xlsx` files for real personal/customer data. **If any secret is found: stop and ask the human immediately (rotate first).**

**TEST / DEBUG**
- Golden tests must be deterministic (fixed seeds, no wall-clock dependence — freeze time).
- Existing suite green or each failure triaged (env issue vs real bug).

**Exit Gate**
- [ ] Baseline test results recorded; golden snapshots committed
- [ ] Audit verification matrix complete (every item has a status + evidence)
- [ ] Secret/PII scan result recorded
- [ ] `PROGRESS.md`, `DECISIONS.md`, `CHANGELOG.md` exist

---

## 5. Phase 1 — Tooling, CI, Repo Hygiene

**Goal:** Automated quality bar that every later phase relies on.

**PLAN:** Decide tool set (defaults below); list files to add/move.

**DEVELOP**
- `pyproject.toml`: project metadata, `ruff` (lint+format), `mypy` (start lenient on legacy modules via per-module overrides, strict on new/fixed ones), `pytest` + `coverage` config (branch coverage).
- Dependencies: split `requirements.txt` (runtime, pinned) and `requirements-dev.txt` (pytest, pytest-cov, hypothesis, ruff, mypy, pip-audit, bandit, pandas-stubs). Generate a lock (pip-tools `pip-compile --generate-hashes` or `uv`). **Upgrade** to currently supported releases of streamlit/pandas/numpy/plotly/python-pptx/requests; pin kaleido to a tested version and document how it finds Chrome. Re-run golden tests after upgrade; investigate every diff.
- Test infrastructure: `conftest.py` with (a) socket-blocking fixture (fail any real network), (b) frozen-time fixture, (c) temp-dir isolation for cache/budget paths, (d) fake LLM client fixture.
- Repo hygiene: `.gitignore` (verify `.env`, `.aivara_*.json`, `.venv`, `__pycache__`, `*.pptx`); `.dockerignore`; move sample data to `examples/` (CSV + xlsx); `LICENSE` (ask human which); `CONTRIBUTING.md`; `SECURITY.md`; `CODEOWNERS`; issue/PR templates; `pre-commit` config (ruff, gitleaks, end-of-file, large-file check).
- GitHub Actions: `ci.yml` — matrix (py3.11, 3.12): install from lock → ruff → mypy → pytest+coverage (fail under threshold, ratcheted) → `pip-audit` → `bandit` → `gitleaks`; `docker.yml` — build image, run container smoke test (Phase 10 fills it in). Dependabot config.
- Fix `run.bat` (verify it works on Windows paths; make it call venv python; add `run.sh`).

**TEST / DEBUG:** Intentionally break a lint rule, a type, a test, and a fake-secret in a throwaway branch to prove CI fails each time. Fix lint/type findings in small commits (no behavior changes mixed in).

**Exit Gate**
- [ ] CI green on `main`; each check proven capable of failing
- [ ] Reproducible install from lockfile in a clean venv
- [ ] Golden tests still pass after dependency upgrade (diffs explained in `DECISIONS.md`)
- [ ] `.dockerignore`, `.gitignore`, `LICENSE`, `SECURITY.md` present

---

## 6. Phase 2 — Core Correctness (audit §1)

**Goal:** No screen, export, or insight shows a wrong number.

**PLAN:** From the Phase 0 matrix, list items still broken. For each, write the failing test *first*.

**DEVELOP** (skip any marked already-fixed, but keep its test)
- **1.1 Cross-user cache:** `view::*` keys must be session-scoped or live only in `st.session_state`. Test: two simulated sessions writing the same view name never read each other's insight.
- **1.2 Trend uses the same metric it is titled with:** trend built from `primary_metric` everywhere (including snapshot/other profile paths). Test with column order `units, revenue, cost`.
- **1.3 Driver contribution %:** normalize by `Σ|delta_i|` (or documented alternative) with a denominator floor; offsetting categories (+1000/−1000) must show large opposite contributions. Property test: contributions' absolute values sum to 100% (or documented invariant); never NaN/inf.
- **1.4 / 1.5 pct_change infinities:** sign-correct infinities; one shared `format_pct_change` used by UI, PPTX, facts builder; renders "new"/"n/a". Test all cases: 0→+, 0→−, +→0, None, NaN, ±inf.
- **1.6 / 1.7 / 1.8 Upload/session reset:** content-hash (not filename) detects new uploads; a single `reset_dataset_state()` clears dataset, classifications, `schema_confirmed`, overrides, `_export_figures`, `_pptx_buffer`, cached pipeline results. Test via `AppTest`: upload A → confirm → export → upload B same name different content → gate re-appears, no A figures in B's deck.
- **Number-consistency invariant test:** for each golden dataset, KPI values on screen == facts packet == PPTX tile text.

**TEST / DEBUG:** Hand-verify at least 3 computed results by independent calculation (spreadsheet or plain Python) and record in the test as comments. Add `hypothesis` property tests for KPI/driver math (no crash, no NaN/inf leaking to display, deltas sum correctly).

**Exit Gate**
- [ ] Every audit §1 item has a passing regression test (or documented "already fixed" test)
- [ ] Number-consistency test passes on all golden datasets
- [ ] Coverage ≥95% on `analytics/kpis.py`, `analytics/drivers.py`, `analytics/trend.py`, `ui/components.py` formatters
- [ ] `CHANGELOG.md` lists user-visible behavior changes

---

## 7. Phase 3 — Ingestion Hardening (audit §3)

**Goal:** Nothing is dropped, coerced, or misread without telling the user.

**PLAN:** Write `tests/test_cleaner.py` skeleton and new fixtures first: percent column, `YYYYMMDD` dates, offsetting categories, mixed null tokens (`N/A`, `n/a`, `-`, `NULL`, `null`, `none`), partial-numeric column (89% numeric), malformed-row CSV, BOM + UTF-16, huge-header, duplicate column names, empty file, header-only file, single-row file, all-null column.

**DEVELOP**
- **3.1** Count/report rows skipped by `on_bad_lines`; add to `LoadResult.notes` and show in UI.
- **3.2** Percent handling: divide by 100 + tag unit `%` *or* classify as rate (ties into Phase 4 aggregation semantics). Never silently strip.
- **3.3** Case-insensitive broader null-token set `{"", "na", "n/a", "nan", "none", "null", "-", "--"}`; configurable in `config.py`.
- **3.4** Report failed-coercion counts per column in `CleanReport.messages`.
- **3.5** Try date detection before numeric for 8-digit/compact patterns (reuse loader's date-shape regex).
- **3.6** Missing dimension values: group with `dropna=False` → explicit "(missing)" bucket, or report excluded-row counts; choose one and document.
- **Limits:** implement `MAX_ROWS_FULL_PROCESSING` (sample for expensive ops with a visible note) and add `MAX_UPLOAD_MB`, `MAX_COLUMNS`; reject oversized files with a clear message (before parsing into memory where possible).
- **Duplicate/blank/odd headers:** deduplicate (`col`, `col_2`), strip, reject fully blank.
- **Data-quality summary panel** in the UI: rows loaded, rows dropped (with reason), values nulled, columns coerced, assumptions made.

**TEST / DEBUG:** Each fixture asserts both the output and the user-facing note. Fuzz the loader with `hypothesis` (random delimiters/encodings/quotes) — must never crash with an unhandled exception; must return either a result with notes or a clean, user-readable error.

**Exit Gate**
- [ ] `test_cleaner.py`, extended `test_loader.py`, `test_classifier.py` pass; coverage ≥95% on `ingestion/`
- [ ] Zero silent-drop paths remain (grep for `on_bad_lines`, `errors="coerce"`, `dropna` — each has a reported counter or a documented exemption)
- [ ] Oversized/garbage uploads produce friendly errors, never stack traces

---

## 8. Phase 4 — Analytics Validity & Coverage

**Goal:** Metrics mean what they say; every analytics module is tested.

**PLAN:** Inventory all analytics modules (including those added after v1: `profiler`, `snapshot`, `stats`, `domains/commerce|finance|workforce|feedback`). Write a table of: inputs, outputs, assumptions, known weaknesses.

**DEVELOP**
- **4.1 Aggregation semantics:** introduce `agg` per metric (`sum` | `mean` | `weighted_mean` | `last`) chosen by name heuristics (`rate|pct|percent|ratio|avg|average|score|nps`) + classifier hint + **manual override in the schema UI**. Apply consistently in KPIs, trend resampling, drivers, anomalies. Show the aggregation used in the KPI tile tooltip.
- **4.2 Anomaly detection:** replace/augment category-vs-category z-score with category-vs-own-history (rolling baseline) when history exists; keep the snapshot method as fallback but label it "structural outlier", not "anomaly"; add the genuine `low` severity band or delete it; fix `SEVERITY` plumbing.
- **Profiler correctness:** misclassification tests (e.g., a numeric ID column, a date stored as text, a boolean flag, currency symbols, thousands separators, negative-in-parentheses).
- **Stats module:** correlation on tiny samples/constant columns/NaNs must not produce misleading "key drivers"; require minimum n and show correlation ≠ causation caption; guard divide-by-zero in concentration index.
- **Executive takeaways:** each generated sentence must be traceable to a computed number; unit-test templates against edge cases (zero, negative, single category, ties).
- **Domain modules:** one test file each with hand-computed expectations (e.g., budget variance sign convention, headcount aggregation, NPS formula = %promoters − %detractors).
- **Customers/Operations tabs:** confirm the customer-dimension heuristic and its empty state; no duplicate tab content.

**TEST / DEBUG:** Hypothesis properties (e.g., scaling a metric by k scales KPIs by k and leaves percentages unchanged; permuting rows does not change results). Golden tests re-baselined *only* with a logged justification.

**Exit Gate**
- [ ] Coverage ≥95% across `analytics/**`; every module has a dedicated test file
- [ ] Rate/ratio metrics are no longer summed (test with `conversion_rate`)
- [ ] Anomaly output labeled correctly; severity tiers consistent end-to-end
- [ ] Golden snapshot diffs reviewed and recorded in `DECISIONS.md`

---

## 9. Phase 5 — LLM Layer: Reliability & Privacy

**Goal:** Insight text is trustworthy, bounded, and the data leaving the machine is known and controllable.

**PLAN:** Diagram exactly what each outbound call contains. Enumerate every field of every facts packet and classify it: *aggregate number* / *category label (data value)* / *free text from data*.

**DEVELOP**
- **Structured output:** request JSON `{headline, driver, action}`; validate with a schema (pydantic or jsonschema); on invalid output: one repair retry, then deterministic template fallback built from the computed facts. **Never cache invalid/garbled output.** Replaces `_split_into_sentences`. Test decimals (`$30,000.50`, `81.8%`).
- **Faithfulness check:** after generation, verify every number mentioned appears in the facts packet (tolerance for rounding); if not, discard and use the fallback.
- **Prompt-injection defense:** column names and category values come from untrusted CSVs and go into prompts. Sanitize (length cap, strip control chars/markup, neutralize instruction-like strings), place data in a delimited, clearly-labeled JSON block, system prompt states data is untrusted. Add an injection test corpus (`"Ignore previous instructions…"` as a category name) — output must remain schema-valid and unaffected.
- **Data egress control:** setting `AIVARA_LLM_REDACT_LABELS` (default **on** for production profile) replaces category/entity labels with stable pseudonyms (`Category A`…) in the packet and maps back locally when rendering. Settings toggle to disable per user decision. Update README privacy wording to match reality (F6).
- **Resilience:** request timeouts, bounded retries with exponential backoff + jitter on 429/5xx, circuit breaker after repeated failure, clear user message; dashboard always renders without insight (already a goal — test it).
- **Model transparency:** show the model actually used; if the paid-model request was substituted by the fallback, say so in the UI.
- **Dead-code decisions:** tier-2 column classification — wire in (after user confirms schema, only for low-confidence columns, budget-aware) **or** delete (see Open Decisions). Use `estimate_tokens` to cap packet size before sending, or delete it and `tiktoken`.
- **Cost/abuse controls:** per-call and daily budgets stay; add per-session cap.
- **Tests:** a `FakeOpenRouter` HTTP stub (responses library or custom) covering success, malformed JSON, empty, 429, 500, timeout, injection, oversized output. Contract test pins the request payload shape.

**TEST / DEBUG:** Run an optional, manually-triggered live smoke test (marked `@pytest.mark.live`, excluded from CI) against the real API with a throwaway key to confirm parsing against real model output; record results.

**Exit Gate**
- [ ] Coverage ≥90% on `insight/**`
- [ ] No unparsed free-text path to the UI; invalid outputs never cached
- [ ] Injection corpus passes; redaction mode proven by a test that inspects the outbound payload
- [ ] Privacy section of README rewritten and reviewed by the human

---

## 10. Phase 6 — State, Concurrency, Multi-User

**Goal:** Two users on one deployment can never see or affect each other's data, and shared counters are correct.

**PLAN:** Decide deployment model (Open Decision D1: single-user local / small-team shared / multi-instance). Document state inventory: every `st.session_state` key, every file on disk, every module-level global, with scope and lifetime.

**DEVELOP**
- Per-session ID in `session_state`; any cross-rerun cache keyed with it; `@st.cache_data` usage reviewed — never cache dataframes across users unless keyed by content hash and size-bounded with TTL.
- **Atomic budget:** replace JSON + `threading.Lock` with SQLite (WAL, `BEGIN IMMEDIATE`, single `check_and_increment` operation) or an OS file lock — correct across threads *and* processes. Remove separate `can_make_call()`/`record_call()` race.
- Insight cache: same store; add TTL, max entries, and corruption recovery (a corrupt file must not crash the app).
- Retention policy: purge cache older than N days; `AIVARA_CACHE_ENABLED=false` option for zero-persistence mode; document what is on disk.
- Cleanup of temp files; no raw rows ever written to disk (assert in a test by scanning the temp dir after a full run).

**TEST / DEBUG:** Concurrency tests: N threads and N *processes* hammering the budget (final count must equal successful calls and never exceed the cap); kill-mid-write test (corrupted store recovers); simulated two-session isolation via `AppTest`.

**Exit Gate**
- [ ] Budget never exceeds cap under 50 parallel attempts across 4 processes
- [ ] Session isolation tests pass
- [ ] State inventory doc committed; no undocumented persistence

---

## 11. Phase 7 — Security Hardening

**Goal:** Safe to expose beyond localhost behind standard controls.

**PLAN:** Write `docs/THREAT_MODEL.md` (assets: uploaded data, API key, aggregated insights; actors: curious colleague, outsider, malicious CSV; threats: STRIDE-lite) before changing code.

**DEVELOP**
- **Authentication:** implement per Open Decision D2 — default: Streamlit native OIDC/auth if available in the pinned version, else reverse-proxy auth (document nginx/Caddy + oauth2-proxy config) plus an app-level shared-secret fallback; disable the app entirely if auth is required and not configured (fail closed).
- **Upload validation:** extension + MIME + size + row/column caps; reject binaries; zip-bomb/decompression guard if archives are ever supported; sanitize filenames (used in export names).
- **CSV/formula injection:** any user-controlled text written into exports (PPTX text, any future CSV/XLSX output) is neutralized (leading `= + - @` etc.).
- **Output safety:** all `st.markdown(..., unsafe_allow_html=True)` usage audited; LLM text and data values rendered as plain text, never HTML.
- **Secrets:** key only from env/secret manager; never logged; masking helper tested; startup check refuses placeholder keys; `.env.example` has no real values.
- **Container:** non-root user, read-only root filesystem where possible, drop capabilities, `HEALTHCHECK`, pinned base image digest, minimal apt packages, no build tools in final image (multi-stage), `.dockerignore` verified by inspecting the built image for `.env`/`.git`.
- **Dependency & code scanning in CI:** `pip-audit` (fail on high/critical), `bandit`, `gitleaks`, Trivy image scan, Dependabot; SBOM (CycloneDX) as release artifact.
- **Network egress:** only `openrouter.ai` outbound; document firewall rule; make base URL allow-listed (reject arbitrary `OPENROUTER_BASE_URL` unless explicitly overridden in a dev profile).
- **Security headers / transport:** document TLS termination, `--server.enableXsrfProtection`, CORS settings, disabling Streamlit usage stats.

**TEST / DEBUG:** Security tests: malicious CSV corpus (formula cells, enormous cells, null bytes, injection strings, deeply nested quotes, 1M-column header); attempt unauthenticated access; image scan results must be clean or each finding triaged in `SECURITY.md`.

**Exit Gate**
- [ ] Threat model committed and each identified threat has a mitigation or accepted-risk entry
- [ ] Auth fails closed; verified by test
- [ ] CI security scans green; image scan clean or triaged
- [ ] Built image contains no `.env`, `.git`, caches; runs as non-root

---

## 12. Phase 8 — Export Hardening

**Goal:** PPTX export never crashes the app, never lies, and works in the shipped container.

**PLAN:** Map every figure/tile/table that enters a slide and its source in `pipeline_result`.

**DEVELOP**
- Per-chart graceful degradation: wrap each chart render in `except Exception` (log it), insert a placeholder note on the slide ("Chart unavailable"), continue. Add a **timeout** around kaleido rendering (subprocess or thread-with-timeout) to survive known hang modes.
- Verify the kaleido/Chrome path inside the actual container (F2/F3). If kaleido needs Chrome, install and pin it in the image, or switch to an approach that avoids it (e.g., native python-pptx charts — Open Decision D4).
- Slide content from the same `pipeline_result` objects as the screen (number-consistency invariant from Phase 2 extended to slide text).
- Deck metadata: dataset name (sanitized), period, generated-at, app version, "AI-generated narrative" disclaimer when insights are present; page numbers; consistent theme; text-overflow handling for long labels.
- Empty-data deck, single-KPI deck, 50-category deck: must all build.

**TEST / DEBUG:** Open generated decks by unzipping and asserting slide count/text/image presence (python-pptx read-back); render to PDF with LibreOffice in CI (if available) to check no corruption; export test inside Docker; kill-kaleido test proves degradation.

**Exit Gate**
- [ ] Coverage ≥90% on `export/**`
- [ ] Forced chart failure and forced kaleido hang both yield a valid deck
- [ ] Container export smoke test green in CI
- [ ] Export remains network-free (existing test retained)

---

## 13. Phase 9 — App Structure, UX, UI Tests

**Goal:** Maintainable, predictable UI, now safe to refactor because tests exist.

**PLAN:** Sketch the target structure and get no behavior diffs vs. golden screenshots/outputs.

**DEVELOP**
- **Refactor `app.py`:** table-driven tab registry (`TabSpec(name, render_fn, visible_when)`) per profile/domain replacing five duplicated blocks; split `run_pipeline` into `build_snapshot_pipeline`, `build_project_pipeline`, `build_timeseries_pipeline` returning typed dataclasses (not a 25-key dict); split `render_export_button` into view assembly (pure, testable) and UI wiring; remove `__import__("pandas")`; fix return annotations; move `APP_TABS` logic out of config if unused.
- **Typed contracts:** `PipelineResult` dataclass; mypy strict on `app.py`, `ui/`, `analytics/`.
- **Error boundaries:** one wrapper so an exception in one tab shows a friendly error + correlation ID and does not blank the other tabs; global handler logs details.
- **UX:** loading spinners for long steps, empty states for every tab, clear schema-review step, downloadable data-quality report, consistent number formatting/locale, colorblind-safe palette, chart alt-text/captions, keyboard-friendly layout, mobile-width sanity.
- **Performance:** cache pure computations with `st.cache_data` keyed on content hash; avoid recomputing pipeline on every widget interaction.
- **Dead features:** Forecast tab — implement (simple, clearly-labeled baseline forecast with intervals) or hide (Open Decision D3). No visible stub in v1.0.
- **UI tests:** `streamlit.testing.v1.AppTest` suites for: upload → schema confirm → each profile/domain tab renders without exception; session reset; export button; error boundary; settings sidebar.

**TEST / DEBUG:** Golden outputs unchanged by the refactor (any diff must be a deliberate, logged change). Run the app manually through Appendix A on three browsers' worth of widths if possible.

**Exit Gate**
- [ ] `app.py` < 200 lines of routing/wiring; no function > 60 lines without justification
- [ ] mypy strict clean on `app.py`, `ui/`, `analytics/`
- [ ] AppTest suite covers every tab for every profile/domain on golden datasets
- [ ] No placeholder/stub features visible

---

## 14. Open Decisions (agent must ask the human before the relevant phase)

| ID | Decision | Default if human unavailable | Needed by |
|---|---|---|---|
| D1 | Deployment model: single-user local / small shared team / multi-instance | Small shared team, single instance | Phase 6 |
| D2 | Auth approach: OIDC provider, reverse-proxy auth, or shared secret | Reverse-proxy auth + shared-secret fallback, fail closed | Phase 7 |
| D3 | Forecast tab: build baseline forecast or hide | Hide for v1.0, backlog it | Phase 9 |
| D4 | PPTX charts: keep Plotly→PNG via kaleido or native python-pptx charts | Keep kaleido if container-proven; else native | Phase 8 |
| D5 | LLM label redaction default ON or OFF | ON | Phase 5 |
| D6 | Tier-2 LLM column classification: wire in or delete | Delete (less egress, simpler) | Phase 5 |
| D7 | License | Ask — do not pick | Phase 1 |
| D8 | Hosting target (Docker host, Azure/AWS/GCP, on-prem) and CI/CD deploy step | Docker + compose, no auto-deploy | Phase 10 |
| D9 | Supported data scale (max rows/MB) | 500k rows / 100 MB | Phase 3 |
| D10 | Other LLM providers/models or only OpenRouter | OpenRouter only, provider interface kept swappable | Phase 5 |

---

## 15. Phase 10 — Observability, Config, Deployment

**Goal:** Operators can run, monitor, upgrade, and roll back the app.

**PLAN:** Define operational requirements: what must be logged, what "healthy" means, upgrade/rollback procedure.

**DEVELOP**
- **Config:** one `Settings` object (pydantic-settings or equivalent), validated at startup with clear errors; secrets typed as `SecretStr`; profiles (`dev`, `prod`); `docs/CONFIGURATION.md` generated from the schema.
- **Logging:** structured JSON logs (`structlog`/stdlib), levels, correlation/session IDs, **no data values, no API keys, no filenames beyond a hash** (test with a log-capture assertion); audit log of LLM calls (timestamp, model, token counts, budget remaining — never content).
- **Health & metrics:** health endpoint (Streamlit `/_stcore/health` wired into Docker `HEALTHCHECK`), version string in the sidebar footer, optional Prometheus counters (LLM calls, failures, export count, pipeline duration) if Open Decision D8 calls for it.
- **Docker:** multi-stage build, pinned digest, non-root, healthcheck, `docker-compose.yml` with volume for the state DB and env-file for secrets, resource limits; `docker run` smoke test script (`scripts/smoke_container.sh`) used by CI.
- **Release engineering:** semantic versioning, `__version__`, CHANGELOG discipline, GitHub Release workflow producing image + SBOM; rollback doc.
- **Runbook:** `docs/RUNBOOK.md` — start/stop, rotate API key, clear cache, budget reset, common errors and fixes, backup/restore of state store, incident checklist.

**TEST / DEBUG:** Boot the container from scratch in CI, hit health endpoint, run an AppTest-equivalent headless flow or scripted request; verify logs contain no sensitive values; kill the container mid-run and confirm clean restart.

**Exit Gate**
- [ ] Container smoke test in CI green (build → health → basic flow)
- [ ] Startup refuses invalid config with a readable message
- [ ] Log-hygiene test passes
- [ ] Runbook reviewed by the human

---

## 16. Phase 11 — Performance & Scale

**Goal:** Known, documented limits with graceful behavior beyond them.

**PLAN:** Generate synthetic datasets (10k, 100k, 500k, 2M rows; wide: 200 columns; high-cardinality dimension) with a reproducible generator script.

**DEVELOP**
- Benchmark script (`scripts/bench.py`) measuring per-stage time and peak RSS (ingestion, classification, profiling, analytics, chart build, PPTX export).
- Optimize measured hotspots only (categoricals for low-cardinality dims, vectorized ops, avoid repeated groupby, chunked CSV reading, `usecols`/dtype hints, downcasting, avoid keeping multiple full copies in session state).
- Enforce limits from Phase 3 using measured numbers; adjust defaults to what the benchmark supports within the agreed memory budget (container limit).
- Concurrency: simulate 5–10 simultaneous sessions with a headless driver; record latency and memory.

**TEST / DEBUG:** Performance regression guard — CI job runs a small fixed benchmark and fails on >X% slowdown (generous threshold to avoid flakiness); memory-limit test inside the container.

**Exit Gate**
- [ ] Benchmark report committed (`docs/PERFORMANCE.md`) with limits and numbers
- [ ] 500k-row file completes within the agreed time/memory budget (set budget with the human) or degrades gracefully with a visible notice
- [ ] No OOM at documented concurrency in the container

---

## 17. Phase 12 — Docs, UAT, Release v1.0.0

**Goal:** Documentation is true, users have validated it, and v1.0.0 ships.

**DEVELOP**
- Rewrite `README.md` to match reality (modules, profiles/domains, auth, privacy/egress, config table generated from code, quickstart that is *tested* in CI, known limits). Remove references to missing files or add the missing product guide.
- `docs/`: ARCHITECTURE.md (updated), USER_GUIDE.md (how to prepare a CSV, how schema review works, how to read each tab, what the numbers mean, aggregation rules, limits), ADRs for each Open Decision, THREAT_MODEL.md, RUNBOOK.md, PERFORMANCE.md, CONFIGURATION.md, TESTING.md.
- **UAT with real-shaped data:** run at least 5 diverse datasets (sales time series, inventory snapshot, project plan, HR roster, survey/NPS) end-to-end; for each, a human (or the owner) checks the headline numbers against their own spreadsheet. Log discrepancies as bugs → fix → rerun.
- Final regression: full CI, container smoke test, security scans, golden tests, performance benchmark.
- Cut `v1.0.0`: tag, release notes, image push (if D8 allows), SBOM attached, CHANGELOG finalized.

**Exit Gate (project done)**
- [ ] All phase gates green; Global Gate green on the release commit
- [ ] UAT sign-off recorded by the human
- [ ] README quickstart verified by following it verbatim in a clean environment
- [ ] `v1.0.0` tagged; backlog triaged into `Backlog` section

---

## 18. Progress Tracking Protocol

Maintain `PROGRESS.md` at repo root. Update it **at the start of PLAN, after every significant commit, and at LOG**. It is the single source of truth; the human reads only this file to know status.

### 18.1 Required structure
```
# Progress
Last updated: <ISO timestamp>   Current phase: <N — name>   Overall: <x/13 phases complete>

## Phase Board
| Phase | Status (not-started / planning / in-progress / testing / debugging / gate / done / blocked) | Started | Done | Tag |

## Current Phase Detail
### Plan (written before coding)
- Tasks: [ ] ...
- Risks: ...
- Test strategy: ...
### Work Log (append-only, newest last)
- <timestamp> <what was done> <commit sha>
### Test Results
- <timestamp> <command> → <pass/fail counts, coverage %>
### Debug Log
- <failure> → <root cause> → <fix> → <verification> (attempt n/3)

## Audit Verification Matrix (Phase 0; update as items close)
| Audit item | Status on main | Test | Closed in phase |

## Gate Checklists (copy each phase gate here and tick off with evidence)

## Decisions (links to DECISIONS.md entries; D1–D10 status)

## Blockers / Questions for Human
| Date | Question | Options | Recommendation | Blocks |

## Backlog (out of scope, captured ideas)

## Metrics Over Time
| Date | Phase | Tests | Coverage % | Lint errors | mypy errors | Open bugs |
```

### 18.2 Rules
- Never mark a phase `done` until every gate box is ticked **with evidence** (command + result).
- Never edit past Work Log entries; append corrections.
- If context is lost or the session restarts, resume by reading `PROGRESS.md` top to bottom, then re-run the test suite before touching code.
- Keep the Phase Board accurate at all times — a stale board is a gate failure.

---

## Appendix A — Smoke Checklist (run at every gate)

1. `pytest -q` passes; `ruff`, `mypy` clean.
2. `streamlit run app.py` starts without warnings about config.
3. Upload a clean CSV → schema review shows → confirm → dashboard renders all tabs without exceptions.
4. Upload a messy CSV (semicolon, odd encoding, `N/A`s, percent column) → data-quality notes appear and are accurate.
5. Upload a second, different file → previous state fully reset; schema gate re-appears.
6. With no API key / exhausted budget → dashboard still renders; insight area shows a clear message.
7. Export PPTX → opens in PowerPoint/LibreOffice; numbers match screen; no `inf`/`nan` text.
8. Logs contain no data values or secrets.

## Appendix B — Debug Protocol Detail
1. Capture the exact error, inputs, versions.
2. Write the smallest failing test that reproduces it.
3. Form one hypothesis; verify with a print/trace/debugger, not by guessing.
4. Fix the root cause (not the symptom); check neighbors for the same pattern (`grep` the idiom).
5. Run the new test, then the whole suite, then the smoke checklist.
6. Log: symptom → cause → fix → test name → attempt number.
7. Attempt 3 failed → stop, log a blocker, ask the human with findings.
