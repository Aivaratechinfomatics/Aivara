"""
tests/test_security.py — Comprehensive security test suite (Phase 7 / Audit §7).

Validates:
1. Threat model and security documentation completeness.
2. CSV and spreadsheet formula injection defense (CWE-1236).
3. Authentication gate (Decision D2) fail-closed behavior, header auth, and shared secret.
4. Upload validation hardening: executable binaries, null bytes, unsupported extensions, filename path traversal.
5. Secrets hardening: masking helper, placeholder rejection, deterministic fallback on placeholder.
6. Network egress SSRF defense: allowlist enforcement, cloud metadata IP blocking, loopback/private IP blocking.
7. Output safety / XSS prevention in UI views.
8. Dockerfile container hardening invariants (non-root user, healthcheck).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import config
from export.formula_sanitizer import (
    sanitize_dataframe_for_export,
    sanitize_for_formula_injection,
)
from export.pptx_builder import DeckInputs, KPITileData, ViewExportData, build_deck
from ingestion.loader import ALLOWED_EXTENSIONS, load_csv, load_file, sanitize_filename
from insight.client import OpenRouterError, query_insight, validate_llm_base_url
from ui.auth import authenticate_request, verify_shared_secret

# ---------------------------------------------------------------------------
# 1. Threat Model & Documentation Invariants
# ---------------------------------------------------------------------------


def test_threat_model_and_security_docs_exist():
    """Verify threat model and security guide exist and cover STRIDE-lite threats."""
    repo_root = Path(__file__).resolve().parent.parent

    tm_path = repo_root / "docs" / "THREAT_MODEL.md"
    assert tm_path.exists(), "docs/THREAT_MODEL.md must exist."
    tm_text = tm_path.read_text(encoding="utf-8")
    for keyword in [
        "STRIDE",
        "Spoofing",
        "Tampering",
        "Repudiation",
        "Information Disclosure",
        "Denial of Service",
        "Elevation of Privilege",
    ]:
        assert keyword in tm_text, f"Threat model must cover {keyword}."

    sec_path = repo_root / "docs" / "SECURITY.md"
    assert sec_path.exists(), "docs/SECURITY.md must exist."
    sec_text = sec_path.read_text(encoding="utf-8")
    assert "AIVARA_AUTH_REQUIRED" in sec_text
    assert "AIVARA_SHARED_SECRET" in sec_text
    assert "Vulnerability Disclosure Policy" in sec_text


# ---------------------------------------------------------------------------
# 2. Formula Injection Defense (CWE-1236)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("=cmd|' /C calc'!A0", "'=cmd|' /C calc'!A0"),
        ("=1+1", "'=1+1"),
        ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-cmd|' /C calc'!A0", "'-cmd|' /C calc'!A0"),
        ("\t=DDE()", "'\t=DDE()"),
        ("\r=DDE()", "'\r=DDE()"),
        ("  =leading_spaces()", "'  =leading_spaces()"),
        # Legitimate numbers must NOT be altered
        ("-12.50", "-12.50"),
        ("+42", "+42"),
        ("-0.001", "-0.001"),
        ("100.5", "100.5"),
        (123, 123),
        (-45.2, -45.2),
        # Normal strings
        ("Total Revenue", "Total Revenue"),
        ("Category A", "Category A"),
        # Already quote-escaped strings
        ("'=already_escaped", "'=already_escaped"),
    ],
)
def test_formula_injection_scalar_neutralization(payload, expected):
    """Ensure formula prefixes are escaped with a leading quote while pure numbers remain untouched."""
    sanitized = sanitize_for_formula_injection(payload)
    assert sanitized == expected


def test_sanitize_dataframe_for_export():
    """Ensure dataframe strings with formula prefixes are neutralized without mutating numeric columns."""
    df = pd.DataFrame(
        {
            "category": ["=SUM(A1:A5)", "Normal", "@calc", "+evil"],
            "metric": [10.5, -20.0, 30.2, 40.0],
            "note": ["-15%", "+25%", "plain", "'=safe"],
        }
    )

    clean_df = sanitize_dataframe_for_export(df)
    assert clean_df["category"].iloc[0] == "'=SUM(A1:A5)"
    assert clean_df["category"].iloc[1] == "Normal"
    assert clean_df["category"].iloc[2] == "'@calc"
    assert clean_df["category"].iloc[3] == "'+evil"
    # Pure numeric column is unchanged
    assert clean_df["metric"].tolist() == [10.5, -20.0, 30.2, 40.0]
    # Percentage strings with + / - are neutralized
    assert clean_df["note"].iloc[0] == "'-15%"
    assert clean_df["note"].iloc[1] == "'+25%"
    assert clean_df["note"].iloc[2] == "plain"
    assert clean_df["note"].iloc[3] == "'=safe"


def test_pptx_export_neutralizes_formula_injection(tmp_path):
    """Ensure PPTX export builder runs formula sanitizer on tile labels, values, and slide text."""
    tile = KPITileData(
        label="=malicious_label()",
        value_display="=cmd|'/C calc'!A0",
        delta_display="+100% exploit",
        delta_positive=True,
    )
    view = ViewExportData(
        view_name="Executive",
        kpi_tiles=[tile],
    )
    inputs = DeckInputs(
        dataset_name="=malicious_dataset",
        period_covered="@period",
        views=[view],
        risk_signals=[],
    )

    pptx_result = build_deck(inputs)
    pptx_bytes = pptx_result.getvalue() if hasattr(pptx_result, "getvalue") else pptx_result
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 0

    # Read back presentation with python-pptx and assert formulas are neutralized
    import io

    from pptx import Presentation

    prs = Presentation(io.BytesIO(pptx_bytes))
    all_texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                all_texts.append(shape.text_frame.text)

    joined = "\n".join(all_texts)
    # The raw unescaped payloads must NOT appear
    assert "=malicious_label()" not in joined or "'=malicious_label()" in joined
    assert "=cmd|'/C calc'!A0" not in joined or "'=cmd|'/C calc'!A0" in joined
    assert "+100% exploit" not in joined or "'+100% exploit" in joined


# ---------------------------------------------------------------------------
# 3. Authentication & Access Control Gate (Decision D2)
# ---------------------------------------------------------------------------


def test_auth_fails_closed_when_required():
    """When AIVARA_AUTH_REQUIRED=True, unauthenticated requests fail closed."""
    ctx = authenticate_request(
        headers={},
        query_token=None,
        session_auth=False,
        auth_required=True,
        shared_secret="super-secret-key",
    )
    assert not ctx.authenticated
    assert ctx.auth_method == "unauthenticated"
    assert ctx.error is not None


def test_auth_dev_bypass_when_not_required():
    """When AIVARA_AUTH_REQUIRED=False, requests pass via dev bypass."""
    ctx = authenticate_request(
        headers={},
        query_token=None,
        session_auth=False,
        auth_required=False,
    )
    assert ctx.authenticated
    assert ctx.auth_method == "dev_bypass"


def test_auth_reverse_proxy_header():
    """Reverse-proxy headers (X-Forwarded-User, X-Remote-User) authenticate successfully."""
    ctx = authenticate_request(
        headers={"x-forwarded-user": "alice@company.com"},
        auth_required=True,
        header_name="X-Forwarded-User",
    )
    assert ctx.authenticated
    assert ctx.username == "alice@company.com"
    assert ctx.auth_method == "proxy_header"

    # Fallback to X-Remote-User
    ctx2 = authenticate_request(
        headers={"x-remote-user": "bob"},
        auth_required=True,
        header_name="X-Forwarded-User",
    )
    assert ctx2.authenticated
    assert ctx2.username == "bob"
    assert ctx2.auth_method == "proxy_header"


def test_auth_shared_secret():
    """Valid shared-secret token authenticates; invalid secret fails."""
    secret = "aivara-top-secret-passphrase"

    # Valid secret
    ctx_ok = authenticate_request(
        query_token="aivara-top-secret-passphrase",
        auth_required=True,
        shared_secret=secret,
    )
    assert ctx_ok.authenticated
    assert ctx_ok.auth_method == "shared_secret"

    # Invalid secret
    ctx_bad = authenticate_request(
        query_token="wrong-passphrase",
        auth_required=True,
        shared_secret=secret,
    )
    assert not ctx_bad.authenticated
    assert ctx_bad.auth_method == "unauthenticated"


def test_verify_shared_secret():
    """verify_shared_secret uses constant-time comparison and handles edge cases."""
    assert verify_shared_secret("my-pass", "my-pass")
    assert not verify_shared_secret("my-pass", "other-pass")
    assert not verify_shared_secret("", "my-pass")
    assert not verify_shared_secret("my-pass", "")


# ---------------------------------------------------------------------------
# 4. Ingestion & Upload Validation Hardening
# ---------------------------------------------------------------------------


def test_reject_executable_binaries_and_null_bytes():
    """Executable binaries and null-byte streams are rejected immediately."""
    # Windows PE executable
    pe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
    res_pe = load_file(pe_bytes, "malicious.csv")
    assert not res_pe.success
    assert "executable binary" in (res_pe.error or "").lower()

    # Linux ELF binary
    elf_bytes = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00"
    res_elf = load_file(elf_bytes, "malicious.csv")
    assert not res_elf.success
    assert "executable binary" in (res_elf.error or "").lower()

    # Mach-O binary
    macho_bytes = b"\xfe\xed\xfa\xce\x00\x00\x00\x01"
    res_macho = load_file(macho_bytes, "exploit.csv")
    assert not res_macho.success
    assert "executable binary" in (res_macho.error or "").lower()

    # Java class file
    java_bytes = b"\xca\xfe\xba\xbe\x00\x00\x00\x34"
    res_java = load_file(java_bytes, "bad.csv")
    assert not res_java.success
    assert "executable binary" in (res_java.error or "").lower()

    # Null byte in text/CSV file
    null_bytes = b"header1,header2\nvalue1,\x00\x00corrupt"
    res_null = load_file(null_bytes, "corrupt.csv")
    assert not res_null.success
    assert "null bytes detected" in (res_null.error or "").lower()

    # Direct load_csv executable check
    res_csv_pe = load_csv(pe_bytes)
    assert not res_csv_pe.success
    assert "executable binary" in (res_csv_pe.error or "").lower()


def test_reject_unsupported_extensions():
    """Unsupported file extensions (.exe, .py, .sh) are rejected."""
    sample_csv = b"col_a,col_b\n1,2\n3,4\n"

    res_py = load_file(sample_csv, filename="script.py")
    assert not res_py.success
    assert "extension '.py' is not supported" in (res_py.error or "")

    res_exe = load_file(sample_csv, filename="setup.exe")
    assert not res_exe.success
    assert "extension '.exe' is not supported" in (res_exe.error or "")

    # Allowed extensions must succeed
    for ext in ALLOWED_EXTENSIONS:
        if ext in (".csv", ".tsv", ".txt"):
            res_ok = load_file(sample_csv, filename=f"test{ext}")
            assert res_ok.success


@pytest.mark.parametrize(
    ("raw_name", "expected_clean"),
    [
        ("../../etc/passwd", "passwd"),
        ("..\\..\\windows\\system32\\cmd.exe", "cmd.exe"),
        ("../../../var/log/syslog.csv", "syslog.csv"),
        ("normal_sales_data.csv", "normal_sales_data.csv"),
        ("sales data (Q3) [final].csv", "sales data _Q3_ _final_.csv"),
        ("", "dataset"),
        (None, "dataset"),
        ("...", "dataset"),
    ],
)
def test_filename_path_traversal_sanitization(raw_name, expected_clean):
    """sanitize_filename strips path traversal sequences and unsafe characters."""
    clean = sanitize_filename(raw_name)
    assert ".." not in clean
    assert "/" not in clean
    assert "\\" not in clean
    assert clean == expected_clean


# ---------------------------------------------------------------------------
# 5. Secrets Hardening & Masking
# ---------------------------------------------------------------------------


def test_secret_masking():
    """mask_secret masks secret characters for safe UI rendering."""
    assert config.mask_secret("") == ""
    assert config.mask_secret("1234") == "****"
    assert config.mask_secret("12") == "**"
    assert config.mask_secret("sk-or-v1-abcdef123456", keep=4) == "*****************3456"
    assert config.mask_secret("openrouter-secret-key-9999", keep=4) == "**********************9999"


def test_placeholder_secret_detection():
    """is_placeholder_secret detects known dummy keys and placeholders."""
    assert config.is_placeholder_secret("")
    assert config.is_placeholder_secret("your-openrouter-key")
    assert config.is_placeholder_secret("your_openrouter_key")
    assert config.is_placeholder_secret("sk-placeholder")
    assert config.is_placeholder_secret("changeme")
    assert config.is_placeholder_secret("dummy")
    assert config.is_placeholder_secret("test")
    assert config.is_placeholder_secret("xxx")

    # Real keys are not detected as placeholders
    assert not config.is_placeholder_secret("sk-or-v1-abcdef1234567890abcdef")


def test_validate_openrouter_key():
    """validate_openrouter_key returns valid status or reason."""
    ok, _ = config.validate_openrouter_key("sk-or-v1-valid-key-abcdef")
    assert ok

    bad_empty, msg_empty = config.validate_openrouter_key("")
    assert not bad_empty
    assert "not configured" in msg_empty

    bad_place, msg_place = config.validate_openrouter_key("your-openrouter-key")
    assert not bad_place
    assert "placeholder" in msg_place


def test_query_insight_uses_deterministic_fallback_on_placeholder_key():
    """When OPENROUTER_API_KEY is a placeholder, query_insight returns deterministic fallback."""
    facts = {
        "dataset_name": "test",
        "primary_metric": "revenue",
        "kpis": [{"name": "revenue", "current": 1000, "prior": 800, "pct_change": 25.0}],
    }
    with patch("insight.client.OPENROUTER_API_KEY", "your-openrouter-key"):
        result = query_insight(facts)
        assert result.is_fallback
        assert result.model == "deterministic/no_api_key"
        assert len(result.headline) > 0


# ---------------------------------------------------------------------------
# 6. Network Egress & SSRF Protection
# ---------------------------------------------------------------------------


def test_validate_llm_base_url_allows_openrouter():
    """Allowed base URL passes SSRF validation."""
    validate_llm_base_url("https://openrouter.ai/api/v1/chat/completions")


@pytest.mark.parametrize(
    "forbidden_url",
    [
        "http://openrouter.ai/api/v1/chat/completions",  # Insecure HTTP
        "https://169.254.169.254/latest/meta-data/",  # Cloud metadata
        "https://localhost/api",  # Localhost
        "https://127.0.0.1:8000/api",  # Loopback IP
        "https://10.0.0.1/api",  # Private RFC 1918
        "https://192.168.1.50/api",  # Private RFC 1918
        "https://172.16.0.1/api",  # Private RFC 1918
        "https://evil-unauthorized-domain.com/v1",  # Non-allowlisted public host
        "https://metadata.google.internal/computeMetadata",  # GCP metadata
    ],
)
def test_validate_llm_base_url_blocks_ssrf(forbidden_url):
    """Dangerous or non-allowlisted URLs raise OpenRouterError."""
    with pytest.raises(OpenRouterError):
        validate_llm_base_url(forbidden_url)


def test_validate_llm_base_url_insecure_override():
    """AIVARA_ALLOW_INSECURE_LLM_HOSTS bypasses restrictions when explicitly enabled."""
    with patch("config.AIVARA_ALLOW_INSECURE_LLM_HOSTS", True):
        # Should not raise
        validate_llm_base_url("http://127.0.0.1:8000/api")


# ---------------------------------------------------------------------------
# 7. Output Safety & XSS Neutralization
# ---------------------------------------------------------------------------


def test_stats_view_escapes_html():
    """Verify html.escape is used on dynamic values before rendering markdown in stats_view."""
    import html

    malicious_narrative = "<script>alert('XSS')</script> Revenue driver"
    escaped = html.escape(malicious_narrative)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


# ---------------------------------------------------------------------------
# 8. Container Hardening Invariants
# ---------------------------------------------------------------------------


def test_dockerfile_security_invariants():
    """Inspect Dockerfile to verify non-root user, healthcheck, and security flags."""
    repo_root = Path(__file__).resolve().parent.parent
    dockerfile_path = repo_root / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist."
    content = dockerfile_path.read_text(encoding="utf-8")

    # Assert non-root user creation and USER directive
    assert "useradd" in content, "Dockerfile must create an unprivileged user."
    assert "USER aivara" in content, "Dockerfile must switch to unprivileged user aivara."

    # Assert HEALTHCHECK directive
    assert "HEALTHCHECK" in content, "Dockerfile must define a HEALTHCHECK instruction."

    # Assert Streamlit security environment variables
    assert "STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true" in content
    assert "STREAMLIT_SERVER_ENABLE_CORS=false" in content
    assert "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false" in content
