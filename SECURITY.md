# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The Aivara engineering team takes the security of our software and user data seriously.
If you believe you have discovered a security vulnerability in Aivara Insight Lite:

1. **Do not create a public GitHub issue.**
2. Report the vulnerability privately by emailing: **security@aivara.ai** (or contact the repository maintainers directly).
3. Include detailed steps to reproduce the vulnerability, sample inputs, and potential impact.
4. We will acknowledge receipt within 48 hours and provide status updates on remediation.

## Security Posture & Architecture
- **Offline Analytics**: All numerical and statistical analytics execute locally in pandas.
- **Controlled Egress**: The application only connects out to the configured OpenRouter API endpoint.
- **Secret Isolation**: API keys and tokens are loaded strictly from the operating environment or secret stores and are masked in logging and the user interface.
- **Container Hardening**: Container images run as unprivileged users with read-only filesystems wherever applicable.
