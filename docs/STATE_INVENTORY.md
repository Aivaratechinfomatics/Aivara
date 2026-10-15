# State Inventory & Persistence Specification

This document provides a comprehensive inventory of all stateful components, disk files, in-memory caches, and `st.session_state` keys in Aivara, detailing their scope, lifetime, persistence, and concurrency guarantees.

---

## 1. Streamlit Session State (`st.session_state`)

All user interaction and analysis parameters are scoped strictly to the active user's browser session. In a multi-user deployment, Streamlit maintains separate `session_state` dictionaries per connection.

| Key | Type | Scope | Lifetime | Purpose |
|---|---|---|---|---|
| `_session_id` | `str` (UUIDv4) | User session | Browser session | Unique identifier assigned to each user connection to ensure strict data and cache isolation. |
| `dataset_hash` | `str` (SHA-256) | User session | Until new file upload | Cryptographic hash of the uploaded CSV/XLSX bytes. Detects re-uploads and triggers canonical state resets. |
| `raw_filename` | `str` | User session | Until new file upload | Display name of the uploaded dataset file. |
| `df_raw` | `pd.DataFrame` | User session | Until new file upload | In-memory raw loaded DataFrame. Never written to disk. |
| `df_cleaned` | `pd.DataFrame` | User session | Until new file upload | Cleaned and validated DataFrame ready for analytics. |
| `clean_report` | `CleanReport` | User session | Until new file upload | Ingestion metrics (row counts, nulls coerced, failed parsing counts). |
| `profile` | `DatasetProfile` | User session | Until new file upload | Inferred column classifications and detected data patterns. |
| `schema_confirmed` | `bool` | User session | Until new file upload | Boolean gate preventing analytics rendering until user approves column schema. |
| `overrides` | `dict[str, str]` | User session | Until new file upload | User manual overrides for column roles or metric aggregation methods. |
| `_view_insights` | `dict[str, dict]` | User session | Until reset / file upload | In-memory narrative insights generated for specific views (Overview, Trends, Drivers, Risks). Used for PPTX export; never written to shared disk. |
| `_export_figures` | `dict[str, Figure]` | User session | Until reset / file upload | In-memory Plotly figures captured during tab rendering for slide deck generation. |
| `_pptx_buffer` | `bytes` | User session | Until reset / download | In-memory binary representation of the exported PowerPoint deck. |

---

## 2. Persistent Storage (On-Disk Files)

Aivara enforces a strict **Zero Raw Row Data Persistence** invariant: raw data rows, customer identifiers, or proprietary records are **never** persisted to disk or databases. Only system counters and cryptographic content-hashed narrative summaries are stored locally.

| File / Database | Format & Engine | Locking & Concurrency | Retention / TTL | Content & Scope |
|---|---|---|---|---|
| `.aivara_budget.db` | SQLite 3 (WAL mode) | Multi-process safe (`BEGIN IMMEDIATE`, busy timeout 5000ms) | Rolling current UTC day (past days pruned) | Daily LLM call usage counter (`daily_budget` table). Tracks `calls_made` per date to enforce hard cost ceiling across processes. |
| `.aivara_cache.db` | SQLite 3 (WAL mode) | Multi-process safe (WAL journal, busy timeout 5000ms) | Default 7 days TTL (`AIVARA_CACHE_TTL_DAYS`), max 1,000 entries | Content-addressed facts-packet insight cache (`insight_cache` table). Keyed by SHA-256 of facts JSON + model + prompt version. |

### Zero Persistence Mode
If `AIVARA_CACHE_ENABLED=false` is configured in the environment:
- Disk cache reads return `None`.
- Disk cache writes are no-ops.
- The app operates in zero-disk-footprint mode for narrative insights.

### Corruption Recovery
If an on-disk SQLite database is corrupted (e.g., due to an abrupt power failure or external filesystem error):
- The store logs a warning.
- The corrupt file is automatically moved aside with a `.corrupt.<timestamp>` suffix.
- A new, healthy database schema is reinitialized immediately, guaranteeing that the application never crashes due to a corrupted persistent cache.

---

## 3. Module-Level In-Memory Globals

| Module | Global Variable | Concurrency Protection | Scope & Purpose |
|---|---|---|---|
| `insight.cache` | `_view_cache: dict[str, dict]` | `threading.Lock` | Fallback in-memory session-keyed store (`<session_id>::<view_name>`) for view-level exports when Streamlit session state is unavailable. |
| `insight.budget` | `_session_calls: dict[str, int]` | `threading.Lock` | Per-session LLM call counters in memory. Enforces per-session call ceiling (`MAX_SESSION_LLM_CALLS = 20`). |
| `insight.client` | `_circuit_breaker: CircuitBreaker` | `threading.Lock` | Tracks consecutive API failures and open/half-open/closed circuit states to prevent cascading downstream failures. |

---

## 4. Temporary Files & Cleanup

- Uploaded files handled via Streamlit's `UploadedFile` interface reside in temporary memory/spool files managed by Streamlit runtime and are cleared upon session close.
- Export generation (PowerPoint slides via `python-pptx` and `kaleido`) generates chart images purely in-memory (`io.BytesIO`) or in ephemeral temp directories that are cleaned up immediately after deck composition.
- No temporary files survive app restart or session closure.
