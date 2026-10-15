# Aivara Insight Lite — Security & Deployment Hardening Guide

Last updated: 2026-10-15  
Status: Active (Phase 7)

This document describes how to deploy Aivara securely behind reverse proxies, configure authentication, harden the container runtime, and report security vulnerabilities.

---

## 1. Authentication & Access Control

Aivara is designed for single-tenant or small-team intranet deployments behind an authenticating reverse proxy or enterprise gateway (Decision D2).

### 1.1 Reverse-Proxy Authentication (Recommended)

When running behind a reverse proxy (e.g., Nginx, Caddy, Traefik, AWS ALB, Cloudflare Access, or `oauth2-proxy`), the proxy terminates TLS and authenticates users via OAuth2, OIDC, SAML, or LDAP. Upon successful authentication, the proxy injects standard identity headers:

- `X-Forwarded-User` (default)
- `X-Remote-User`
- `X-Forwarded-Email`

#### Configuration (`.env` or container environment):
```bash
# Require authentication: fail closed if missing or invalid
AIVARA_AUTH_REQUIRED=true

# Name of the header containing the authenticated username/email
AIVARA_AUTH_HEADER_USER=X-Forwarded-User
```

#### Example Nginx Configuration (`nginx.conf`):
```nginx
server {
    listen 443 ssl http2;
    server_name aivara.internal.company.com;

    ssl_certificate /etc/ssl/certs/aivara.crt;
    ssl_certificate_key /etc/ssl/private/aivara.key;

    # Forward to oauth2-proxy or auth subrequest
    auth_request /oauth2/auth;
    error_page 401 = /oauth2/sign_in;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Inject authenticated user from oauth2-proxy / auth request
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-Forwarded-User $user;

        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

#### Example Caddy Configuration (`Caddyfile`):
```caddy
aivara.internal.company.com {
    tls internal

    # Forward auth via OAuth2 / Authelia / Authentik
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.company.com
        copy_headers Remote-User X-Forwarded-User Remote-Email
    }

    reverse_proxy 127.0.0.1:8501 {
        header_up X-Forwarded-User {header.X-Forwarded-User}
    }
}
```

---

### 1.2 App-Level Shared-Secret Fallback

If an authenticating reverse proxy is not available, Aivara supports an application-level shared-secret fallback:

```bash
AIVARA_AUTH_REQUIRED=true
AIVARA_SHARED_SECRET=your-super-strong-passphrase-here
```

When configured, users must authenticate via:
1. Entering the passphrase in the UI authentication gate, or
2. Providing it via URL parameter: `https://aivara.example.com/?auth=your-super-strong-passphrase-here`

If `AIVARA_AUTH_REQUIRED=true` and neither a valid header nor the correct shared secret is supplied, the application **fails closed** (`st.stop()`) and prohibits all data ingestion and pipeline computations.

---

## 2. Ingestion & File Upload Security

Aivara implements strict ingress validation to prevent denial-of-service, remote code execution, and data corruption:

1. **Extension Allowlist**: Only `.csv`, `.tsv`, `.txt`, `.xlsx`, and `.xls` files are accepted.
2. **Binary Magic Byte Sniffing**: Files starting with executable magic bytes (`MZ` for Windows PE, `\x7fELF` for Linux ELF, `\xca\xfe\xba\xbe` for Java class, Mach-O binaries, etc.) are rejected immediately.
3. **Null Byte Neutralization**: Plaintext files containing null bytes (`\x00`) are rejected.
4. **Limits**:
   - `MAX_UPLOAD_MB`: Maximum file size (default: 100 MB).
   - `MAX_COLUMNS`: Maximum table width (default: 500 columns).
   - `MAX_ROWS_FULL_PROCESSING`: Maximum in-memory rows before sampling (default: 500,000 rows).
5. **Path Traversal Protection**: Uploaded filenames are sanitized by stripping path separators (`../`, `..\`, `/`, `\`) and non-alphanumeric characters before being used in export metadata.

---

## 3. CSV & Formula Injection Defense

When exporting figures and tables to PowerPoint (`.pptx`) or CSV formats, cell values starting with `= + - @ \t \r` could be executed as formulas by spreadsheet software (e.g. Microsoft Excel or LibreOffice Calc).

Aivara runs all user-controlled text through `sanitize_for_formula_injection()`, which prepends a single quote (`'`) to any formula string (while preserving valid numeric scalars such as `-12.50`), preventing code execution upon export opening.

---

## 4. LLM Privacy & Network Egress Control

- **Data Minimization**: Only aggregated statistical scalars ($n$, sums, deltas, percentages) are included in facts packets. Raw row-level data is never sent to external LLMs.
- **Label Redaction**: Enabled by default (`AIVARA_LLM_REDACT_LABELS=true`). Entity names and categorical column values are pseudonymized to generic placeholders (`Category A`, `Entity B`) before egress, and translated back in memory.
- **SSRF Protection**: LLM base URLs are restricted to allowlisted HTTPS domains (`openrouter.ai`). Internal IP ranges (`127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`, `192.168.0.0/16`) are blocked by default.
- **Budget Caps**: Multi-process atomic SQLite budget counters enforce daily and per-session call caps.

---

## 5. Container Runtime Hardening

- The Docker container runs under an unprivileged dedicated user `aivara` (UID 10001).
- Root filesystem is kept read-only where possible.
- Docker `HEALTHCHECK` periodically verifies `/_stcore/health`.
- Multi-stage build strips build tools from the final deployment container.

---

## 6. Vulnerability Disclosure Policy

If you discover a potential security vulnerability in Aivara, please report it privately:

- **Email**: `security@aivara.internal` (or repository private advisory)
- Please include:
  - Description of the vulnerability.
  - Minimal reproducible example or payload.
  - Affected components and versions.
- We commit to acknowledging receipt within 48 hours and providing a remediation timeline.
