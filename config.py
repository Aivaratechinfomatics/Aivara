"""
config.py — central place for env/secrets loading, budget constants, and model choice.

Nothing in this file should be hardcoded secrets. The OpenRouter API key is
read from the environment only; it is never logged and never echoed back in
full anywhere in the UI (see ui/components.py for the masking helper).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv  # python-dotenv

    load_dotenv()
except ImportError:
    # dotenv is a convenience for local dev; the app must still run without it
    # (e.g. inside Docker where env vars are injected directly).
    pass


__version__ = "1.0.0"
AIVARA_ENV: str = os.environ.get("AIVARA_ENV", "prod").lower()

# ---------------------------------------------------------------------------
# OpenRouter / LLM configuration
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
)

# Keep the model id here, not hardcoded inline in insight/client.py, since
# free-model availability on OpenRouter rotates over time.
DEFAULT_MODEL = os.environ.get("AIVARA_MODEL", "openrouter/auto")
FALLBACK_MODEL = os.environ.get("AIVARA_FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

# Only used if the user explicitly flips the "allow paid models" toggle in the
# settings UI. Never used by default.
ALLOW_PAID_MODELS_DEFAULT = False

# ---------------------------------------------------------------------------
# Authentication configuration (Decision D2 & Phase 7)
# ---------------------------------------------------------------------------
AIVARA_AUTH_REQUIRED: bool = os.environ.get("AIVARA_AUTH_REQUIRED", "false").lower() in (
    "true",
    "1",
    "yes",
)
AIVARA_AUTH_HEADER_USER: str = os.environ.get("AIVARA_AUTH_HEADER_USER", "X-Forwarded-User")
AIVARA_SHARED_SECRET: str = os.environ.get("AIVARA_SHARED_SECRET", "")

# ---------------------------------------------------------------------------
# Network Egress & SSRF Security (Phase 7)
# ---------------------------------------------------------------------------
AIVARA_ALLOWED_LLM_HOSTS: tuple[str, ...] = tuple(
    h.strip().lower()
    for h in os.environ.get("AIVARA_ALLOWED_LLM_HOSTS", "openrouter.ai").split(",")
    if h.strip()
)
AIVARA_ALLOW_INSECURE_LLM_HOSTS: bool = os.environ.get(
    "AIVARA_ALLOW_INSECURE_LLM_HOSTS", "false"
).lower() in ("true", "1", "yes")

# Known placeholder keys that must be rejected at startup
KNOWN_PLACEHOLDER_KEYS: frozenset[str] = frozenset(
    {
        "your-openrouter-key",
        "your_openrouter_key",
        "sk-placeholder",
        "changeme",
        "dummy",
        "test",
        "xxx",
        "placeholder",
        "none",
    }
)


def mask_secret(secret: str, keep: int = 4) -> str:
    """Mask sensitive secret keys for safe display in UI and diagnostics."""
    if not secret:
        return ""
    if len(secret) <= keep:
        return "*" * len(secret)
    return "*" * (len(secret) - keep) + secret[-keep:]


def is_placeholder_secret(key: str) -> bool:
    """Return True if the key is empty or matches a known placeholder value."""
    if not key:
        return True
    k = key.strip().lower()
    if k in KNOWN_PLACEHOLDER_KEYS:
        return True
    return k.startswith(("your-", "your_", "sk-xxx", "sk-placeholder"))


def validate_openrouter_key(key: str) -> tuple[bool, str]:
    """Validate OpenRouter API key format and ensure it is not a placeholder."""
    if not key or not key.strip():
        return False, "OpenRouter API key is not configured."
    if is_placeholder_secret(key):
        return False, "OpenRouter API key is set to a placeholder value and cannot be used."
    return True, "Key is valid."


# ---------------------------------------------------------------------------
# Budget enforcement (see insight/budget.py)
# ---------------------------------------------------------------------------

# Comfortably under OpenRouter's free-tier daily cap (verify current limits at
# https://openrouter.ai/docs/guides/routing/model-variants/free — the account
# free-request daily cap has historically been 50/day with no top-up, 1000/day
# after a one-time >=$10 credit top-up; we default conservatively).
DAILY_CALL_BUDGET = int(os.environ.get("AIVARA_DAILY_BUDGET", "30"))

# Per-call cap on generated tokens, to bound both cost and rambling output.
MAX_OUTPUT_TOKENS = int(os.environ.get("AIVARA_MAX_OUTPUT_TOKENS", "150"))

# Where the daily call counter is persisted (multi-process safe SQLite WAL store).
BUDGET_DB_PATH: str = os.environ.get("AIVARA_BUDGET_DB_PATH", ".aivara_budget.db")
BUDGET_STATE_PATH: str = os.environ.get("AIVARA_BUDGET_STATE_PATH", BUDGET_DB_PATH)

# Where the facts-hash -> LLM response cache is persisted (multi-process safe SQLite WAL store).
CACHE_DB_PATH: str = os.environ.get("AIVARA_CACHE_DB_PATH", ".aivara_cache.db")
INSIGHT_CACHE_PATH: str = os.environ.get("AIVARA_INSIGHT_CACHE_PATH", CACHE_DB_PATH)

# Cache controls (Phase 6 / Audit §6)
AIVARA_CACHE_ENABLED: bool = os.environ.get("AIVARA_CACHE_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
AIVARA_CACHE_TTL_DAYS: int = int(os.environ.get("AIVARA_CACHE_TTL_DAYS", "7"))
AIVARA_CACHE_MAX_ENTRIES: int = int(os.environ.get("AIVARA_CACHE_MAX_ENTRIES", "1000"))

# Prompt version string — bump this whenever prompts.py changes meaningfully,
# so cache keys don't silently reuse insights generated under an old prompt.
PROMPT_VERSION = "v2"

# ---------------------------------------------------------------------------
# LLM Privacy & Resilience configuration (Phase 5 / Audit §5)
# ---------------------------------------------------------------------------

# Pseudonymize category and entity names in outbound facts packets (default ON)
AIVARA_LLM_REDACT_LABELS: bool = os.environ.get("AIVARA_LLM_REDACT_LABELS", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Circuit breaker settings for OpenRouter API failures
CIRCUIT_BREAKER_MAX_FAILURES: int = int(os.environ.get("AIVARA_CB_MAX_FAILURES", "3"))
CIRCUIT_BREAKER_RESET_TIMEOUT: float = float(os.environ.get("AIVARA_CB_TIMEOUT", "60.0"))

# Per-session call budget cap preventing runaway session usage
MAX_SESSION_LLM_CALLS: int = int(os.environ.get("AIVARA_SESSION_BUDGET", "20"))

# OpenRouter HTTP request timeout in seconds
LLM_REQUEST_TIMEOUT_SECONDS: float = float(os.environ.get("AIVARA_LLM_TIMEOUT", "15.0"))

# ---------------------------------------------------------------------------
# Classification / analytics thresholds (Section 8.2-8.6)
# ---------------------------------------------------------------------------

DATE_PARSE_SUCCESS_THRESHOLD = 0.80  # >80% of non-null values must parse as dates
DIMENSION_UNIQUE_RATIO_CAP = 0.05  # <5% unique values (relative to row count)
DIMENSION_UNIQUE_ABS_CAP = 200  # ... or under this many distinct values, whichever is looser
ID_UNIQUE_RATIO_FLOOR = 0.95  # near-unique per row

ANOMALY_ZSCORE_THRESHOLD = 2.0
ANOMALY_PCT_SWING_THRESHOLD = 0.30  # 30% swing fallback when history is short

# Max rows to hold in memory before we sample for expensive operations.
MAX_ROWS_FULL_PROCESSING = 500_000

# File size and column limits (Section 12 & Decision D9)
MAX_UPLOAD_MB = int(os.environ.get("AIVARA_MAX_UPLOAD_MB", "100"))
MAX_COLUMNS = int(os.environ.get("AIVARA_MAX_COLUMNS", "500"))

# Default null placeholders normalized to NaN during ingestion
DEFAULT_NULL_STRINGS: frozenset[str] = frozenset(
    {"", "na", "n/a", "nan", "none", "null", "-", "--", "n.a.", "n/d", "nil"}
)

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------

APP_TITLE = "Aivara Insight Lite"
APP_TABS = ["Executive", "Revenue", "Operations", "Customers", "Charts", "Risk"]


# ---------------------------------------------------------------------------
# Typed Settings & Startup Validation (Phase 10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    """Strongly typed application settings with validation (Phase 10)."""

    version: str = __version__
    env: str = AIVARA_ENV
    openrouter_api_key: str = OPENROUTER_API_KEY
    openrouter_base_url: str = OPENROUTER_BASE_URL
    default_model: str = DEFAULT_MODEL
    fallback_model: str = FALLBACK_MODEL
    daily_budget: int = DAILY_CALL_BUDGET
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    budget_db_path: str = BUDGET_DB_PATH
    cache_db_path: str = CACHE_DB_PATH
    cache_enabled: bool = AIVARA_CACHE_ENABLED
    cache_ttl_days: int = AIVARA_CACHE_TTL_DAYS
    cache_max_entries: int = AIVARA_CACHE_MAX_ENTRIES
    max_upload_mb: int = MAX_UPLOAD_MB
    max_columns: int = MAX_COLUMNS
    auth_required: bool = AIVARA_AUTH_REQUIRED
    auth_header_user: str = AIVARA_AUTH_HEADER_USER
    shared_secret: str = AIVARA_SHARED_SECRET
    allowed_llm_hosts: tuple[str, ...] = AIVARA_ALLOWED_LLM_HOSTS
    redact_labels: bool = AIVARA_LLM_REDACT_LABELS
    session_budget: int = MAX_SESSION_LLM_CALLS
    llm_timeout: float = LLM_REQUEST_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> Settings:
        """Construct Settings directly from current environment variables."""
        return cls(
            version=__version__,
            env=os.environ.get("AIVARA_ENV", "prod").lower(),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.environ.get(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
            ),
            default_model=os.environ.get("AIVARA_MODEL", "openrouter/auto"),
            fallback_model=os.environ.get(
                "AIVARA_FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct:free"
            ),
            daily_budget=int(os.environ.get("AIVARA_DAILY_BUDGET", "30")),
            max_output_tokens=int(os.environ.get("AIVARA_MAX_OUTPUT_TOKENS", "150")),
            budget_db_path=os.environ.get("AIVARA_BUDGET_DB_PATH", ".aivara_budget.db"),
            cache_db_path=os.environ.get("AIVARA_CACHE_DB_PATH", ".aivara_cache.db"),
            cache_enabled=os.environ.get("AIVARA_CACHE_ENABLED", "true").lower()
            in ("true", "1", "yes"),
            cache_ttl_days=int(os.environ.get("AIVARA_CACHE_TTL_DAYS", "7")),
            cache_max_entries=int(os.environ.get("AIVARA_CACHE_MAX_ENTRIES", "1000")),
            max_upload_mb=int(os.environ.get("AIVARA_MAX_UPLOAD_MB", "100")),
            max_columns=int(os.environ.get("AIVARA_MAX_COLUMNS", "500")),
            auth_required=os.environ.get("AIVARA_AUTH_REQUIRED", "false").lower()
            in ("true", "1", "yes"),
            auth_header_user=os.environ.get("AIVARA_AUTH_HEADER_USER", "X-Forwarded-User"),
            shared_secret=os.environ.get("AIVARA_SHARED_SECRET", ""),
            allowed_llm_hosts=tuple(
                h.strip().lower()
                for h in os.environ.get("AIVARA_ALLOWED_LLM_HOSTS", "openrouter.ai").split(",")
                if h.strip()
            ),
            redact_labels=os.environ.get("AIVARA_LLM_REDACT_LABELS", "true").lower()
            in ("true", "1", "yes"),
            session_budget=int(os.environ.get("AIVARA_SESSION_BUDGET", "20")),
            llm_timeout=float(os.environ.get("AIVARA_LLM_TIMEOUT", "15.0")),
        )

    def validate(self) -> list[str]:
        """Validate settings integrity; returns list of error messages."""
        errors: list[str] = []
        if self.daily_budget <= 0:
            errors.append("AIVARA_DAILY_BUDGET must be greater than 0.")
        if self.max_upload_mb <= 0:
            errors.append("AIVARA_MAX_UPLOAD_MB must be greater than 0.")
        if self.max_columns <= 0:
            errors.append("AIVARA_MAX_COLUMNS must be greater than 0.")
        if self.cache_ttl_days <= 0:
            errors.append("AIVARA_CACHE_TTL_DAYS must be greater than 0.")
        if self.cache_max_entries <= 0:
            errors.append("AIVARA_CACHE_MAX_ENTRIES must be greater than 0.")
        if self.session_budget <= 0:
            errors.append("AIVARA_SESSION_BUDGET must be greater than 0.")
        if self.llm_timeout <= 0:
            errors.append("AIVARA_LLM_TIMEOUT must be greater than 0.")
        if self.env not in ("dev", "development", "staging", "prod", "production", "test"):
            errors.append(f"Invalid AIVARA_ENV '{self.env}'. Must be dev, staging, prod, or test.")
        return errors


def load_settings() -> Settings:
    """Load, validate, and return the application Settings instance."""
    settings = Settings.from_env()
    errors = settings.validate()
    if errors:
        raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
    return settings
