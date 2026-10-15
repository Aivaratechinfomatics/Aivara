# Aivara Configuration Reference

This document provides a comprehensive specification of all environment variables, configuration parameters, validation rules, and deployment profiles for Aivara Insight Lite.

---

## 1. Configuration Overview

Aivara follows the [Twelve-Factor App methodology](https://12factor.net/config) for configuration. All configuration is loaded from environment variables (or an optional `.env` file for local development).

Configuration is validated at startup via `config.Settings`. If invalid parameters are detected (e.g. negative budgets or non-positive timeouts), the application raises descriptive configuration errors.

---

## 2. Environment Variables Specification

| Environment Variable | Type | Default | Description |
|---|---|---|---|
| `AIVARA_ENV` | `str` | `"prod"` | Application environment: `dev`, `staging`, `prod`, or `test`. |
| `OPENROUTER_API_KEY` | `str` | `""` | OpenRouter API authentication key. Required for AI insight generation. |
| `OPENROUTER_BASE_URL` | `str` | `https://openrouter.ai/api/v1/chat/completions` | OpenRouter chat completions endpoint. Validated against allowed hosts. |
| `AIVARA_MODEL` | `str` | `"openrouter/auto"` | Default model identifier passed to OpenRouter. |
| `AIVARA_FALLBACK_MODEL` | `str` | `"meta-llama/llama-3.1-8b-instruct:free"` | Secondary model attempted if primary fails before offline fallback. |
| `AIVARA_DAILY_BUDGET` | `int` | `30` | Maximum allowed OpenRouter API calls per calendar day (UTC). |
| `AIVARA_MAX_OUTPUT_TOKENS` | `int` | `150` | Maximum token generation limit per LLM API request. |
| `AIVARA_SESSION_BUDGET` | `int` | `20` | Maximum LLM calls allowed per active browser session. |
| `AIVARA_LLM_TIMEOUT` | `float` | `15.0` | HTTP request timeout in seconds for OpenRouter API requests. |
| `AIVARA_CB_MAX_FAILURES` | `int` | `3` | Consecutive API failures before the circuit breaker trips OPEN. |
| `AIVARA_CB_TIMEOUT` | `float` | `60.0` | Cool-down period in seconds before testing HALF-OPEN state. |
| `AIVARA_LLM_REDACT_LABELS` | `bool` | `true` | Pseudonymize category and entity names before egress (Decision D5). |
| `AIVARA_AUTH_REQUIRED` | `bool` | `false` | Fail closed if reverse-proxy authentication headers or secret are missing. |
| `AIVARA_AUTH_HEADER_USER` | `str` | `"X-Forwarded-User"` | HTTP header containing authenticated username from reverse proxy. |
| `AIVARA_SHARED_SECRET` | `str` | `""` | App-level shared secret passed via `X-Aivara-Secret` header or query. |
| `AIVARA_ALLOWED_LLM_HOSTS` | `str` | `"openrouter.ai"` | Comma-separated domain allowlist for outbound LLM API requests. |
| `AIVARA_ALLOW_INSECURE_LLM_HOSTS` | `bool` | `false` | Allow loopback/private subnets for local testing (disabled in prod). |
| `AIVARA_CACHE_ENABLED` | `bool` | `true` | Enable persistent SQLite WAL cache for generated insights. |
| `AIVARA_CACHE_TTL_DAYS` | `int` | `7` | Time-to-live in days before cached insights are evicted. |
| `AIVARA_CACHE_MAX_ENTRIES` | `int` | `1000` | Maximum entries retained in the SQLite insight cache. |
| `AIVARA_BUDGET_DB_PATH` | `str` | `".aivara_budget.db"` | Path to multi-process safe SQLite database tracking daily call counts. |
| `AIVARA_CACHE_DB_PATH` | `str` | `".aivara_cache.db"` | Path to multi-process safe SQLite database caching insights. |
| `AIVARA_MAX_UPLOAD_MB` | `int` | `100` | Maximum allowed uploaded file size in megabytes. |
| `AIVARA_MAX_COLUMNS` | `int` | `500` | Maximum allowed column width in ingested tabular datasets. |
| `AIVARA_KALEIDO_TIMEOUT` | `float` | `15.0` | Maximum seconds allowed for headless chart PNG rendering. |

---

## 3. Validation Rules

The `config.Settings.validate()` method enforces the following invariants at startup:
- `daily_budget > 0`
- `max_upload_mb > 0`
- `max_columns > 0`
- `cache_ttl_days > 0`
- `cache_max_entries > 0`
- `session_budget > 0`
- `llm_timeout > 0`
- `kaleido_timeout > 0`
- `env in {"dev", "development", "staging", "prod", "production", "test"}`

---

## 4. Production Hardening Checklist

When deploying to production:
1. Set `AIVARA_ENV=prod`.
2. Set `AIVARA_AUTH_REQUIRED=true` and route traffic through an authenticating reverse proxy (see [SECURITY.md](SECURITY.md)).
3. Keep `AIVARA_LLM_REDACT_LABELS=true` to protect internal business entities.
4. Mount persistent storage volumes for `AIVARA_BUDGET_DB_PATH` and `AIVARA_CACHE_DB_PATH` to ensure counters and caches survive container restarts.
5. Set `AIVARA_ALLOW_INSECURE_LLM_HOSTS=false` to block SSRF attempts toward internal network resources.
