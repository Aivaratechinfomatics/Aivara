# Aivara Operator Runbook

This runbook provides actionable procedures for deploying, monitoring, maintaining, upgrading, and troubleshooting an Aivara Insight Lite installation in production.

---

## 1. System Architecture & Components

Aivara is a stateless, in-memory Streamlit application backed by lightweight local SQLite WAL state stores:
- **Web App**: Python Streamlit runtime serving interactive analytics and Plotly charts on port `8501`.
- **State Store (`/app/data/aivara_budget.db`)**: Atomic counter enforcing daily LLM budgets across processes.
- **Cache Store (`/app/data/aivara_cache.db`)**: Persistent insight cache keyed on facts hashes with automatic TTL eviction.
- **External Dependencies**:
  - `openrouter.ai`: Outbound HTTPS for AI insight generation.
  - No raw user data is ever written to persistent disk storage.

---

## 2. Common Operational Tasks

### 2.1 Starting the Application

**Using Docker Compose (Recommended):**
```bash
# Start in detached mode
docker compose up -d

# Verify container status
docker compose ps
```

**Local Development / Bare Metal:**
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### 2.2 Stopping the Application

```bash
# Graceful stop
docker compose down

# Stop with volume preservation
docker compose stop
```

### 2.3 Health & Liveness Checks

Aivara exposes Streamlit's native health endpoint:
- **URL**: `http://localhost:8501/_stcore/health`
- **Expected Status**: `HTTP 200 OK`
- **Expected Body**: `ok`

**Automated Smoke Verification:**
```bash
python scripts/smoke_container.py --url http://localhost:8501
```

**Docker Container Health Inspection:**
```bash
docker inspect --format='{{.State.Health.Status}}' aivara_app
```

---

## 3. Secret & Credential Rotation

### 3.1 Rotating OpenRouter API Key
1. Generate a new API key in the [OpenRouter Dashboard](https://openrouter.ai/keys).
2. Update `OPENROUTER_API_KEY` in `.env` (or Kubernetes Secret / AWS Parameter Store).
3. Restart the container gracefully:
   ```bash
   docker compose up -d --force-recreate
   ```
4. Verify logs: the new key will be automatically masked in logs (`[REDACTED_API_KEY]`) and the settings panel will show the last 4 characters.

### 3.2 Rotating Shared Authentication Secret
1. Generate a new cryptographically secure random token (e.g. `openssl rand -hex 24`).
2. Update `AIVARA_SHARED_SECRET` in `.env`.
3. Restart the container:
   ```bash
   docker compose restart aivara
   ```

---

## 4. Cache & State Store Maintenance

### 4.1 Clearing the Insight Cache
If cached insights need to be invalidated (e.g. after prompt updates):
```bash
# Stop service
docker compose stop aivara

# Remove cache DB (WAL and SHM files will be recreated on startup)
rm -f /app/data/aivara_cache.db*

# Start service
docker compose start aivara
```

### 4.2 Resetting the Daily Call Budget
If the daily budget needs to be immediately refreshed:
```bash
# Delete budget store; automatically re-initialized on next call
rm -f /app/data/aivara_budget.db*
```

### 4.3 Backup & Disaster Recovery of State Stores
To take a consistent online snapshot of the state databases:
```bash
# Backup budget store safely using SQLite online backup API
sqlite3 /app/data/aivara_budget.db ".backup /backup/aivara_budget_$(date +%F).db"
sqlite3 /app/data/aivara_cache.db ".backup /backup/aivara_cache_$(date +%F).db"
```

---

## 5. Incident Response & Troubleshooting

### Incident 1: HTTP 429 (Rate Limit Exceeded from OpenRouter)
- **Symptom**: Dashboard displays offline fallback insights; logs show HTTP 429.
- **Root Cause**: Upstream free-tier account rate limit reached.
- **Mitigation**:
  1. Circuit breaker trips to `OPEN` automatically to prevent spamming upstream.
  2. The application falls back gracefully to offline deterministic takeaways.
  3. No operator intervention required. If needed, switch model via `AIVARA_MODEL` or upgrade account credits.

### Incident 2: Headless Chart Export Timeout
- **Symptom**: PPTX generation succeeds but slide shows `"📊 Chart Preview Unavailable"`.
- **Root Cause**: Headless Chromium (Kaleido) timed out or crashed under high memory load.
- **Mitigation**:
  1. Aivara protects presentation generation via `ThreadPoolExecutor` timeout (`AIVARA_KALEIDO_TIMEOUT`).
  2. Increase timeout if running on resource-constrained VM: `AIVARA_KALEIDO_TIMEOUT=30.0`.
  3. Ensure container has at least 1GB memory reserved.

### Incident 3: SQLite Database Corruption
- **Symptom**: Log message: `"SQLite database is corrupt"`.
- **Mitigation**:
  1. Both `insight/budget.py` and `insight/cache.py` feature automated self-healing.
  2. Corrupted `.db`, `.db-wal`, and `.db-shm` files are automatically quarantined with a `.corrupt.<timestamp>` suffix and re-initialized.
  3. Application execution continues without interruption.

### Incident 4: Authentication Gate Denies Access
- **Symptom**: Screen displays `"Authentication Required: Missing remote user identity header"`.
- **Root Cause**: Request arrived without `X-Forwarded-User` header.
- **Mitigation**:
  1. Verify reverse proxy (Nginx / Caddy / OAuth2-Proxy) is actively setting `X-Forwarded-User`.
  2. If testing locally, pass `X-Aivara-Secret: <secret>` or set `AIVARA_AUTH_REQUIRED=false`.
