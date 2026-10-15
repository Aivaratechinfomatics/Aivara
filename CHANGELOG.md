# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 1: Tooling, CI, Repo Hygiene**:
  - `pyproject.toml` with `ruff`, `mypy`, `pytest`, and branch `coverage` configurations.
  - `requirements-dev.txt` for development, linting, typing, and security audit dependencies.
  - Test safety harness in `tests/conftest.py` with automatic external socket blocking, isolated temporary cache/budget directories, and fake OpenRouter mock fixture.
  - `tests/test_safety_harness.py` validating that network egress attempts are intercepted and blocked.
  - GitHub Actions CI matrix workflow (`.github/workflows/ci.yml`) running across Python 3.11 and 3.12.
  - `.github/dependabot.yml` for automated dependency updates.
  - Apache 2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `.dockerignore`, `.pre-commit-config.yaml`, and `run.sh`.
  - Relocated sample datasets under `examples/` with dedicated `examples/README.md`.
- **Phase 0: Baseline & Safety Net**:
  - Baseline execution and verification (118 initial tests passing).
  - `docs/ARCHITECTURE_CURRENT.md` documenting end-to-end data pipeline flow.
  - `DECISIONS.md` tracking architecture decisions D1–D10.
  - Characterization golden test suite (`tests/test_golden.py` and `tests/golden/*.json` across 8 fixture datasets).
  - Complete Audit Verification Matrix in `PROGRESS.md` covering audit items 1.1–1.8, 2.1–2.5, 3.1–3.8, and 4.1–4.5.
