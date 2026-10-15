# Contributing to Aivara Insight Lite

Thank you for your interest in contributing to Aivara Insight Lite!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Aivaratechinfomatics/Aivara.git
   cd Aivara
   ```
2. Set up virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env
   # Add your OPENROUTER_API_KEY
   ```

## Pre-Commit Verification Checklist

Before submitting a Pull Request, ensure that all automated checks pass locally:

- **Linting & Formatting**:
  ```bash
  ruff check .
  ruff format --check .
  ```
- **Static Type Checking**:
  ```bash
  mypy config.py analytics/ ingestion/ export/ insight/
  ```
- **Test Suite & Coverage**:
  ```bash
  pytest tests/ -v --cov=.
  ```
- **Security Scanning**:
  ```bash
  bandit -r config.py analytics/ ingestion/ export/ insight/ -ll
  pip-audit
  ```

## Conventional Commits
Please structure commits following the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` new feature or capability
- `fix:` bug fix
- `test:` test additions or refactoring
- `chore:` maintenance, dependencies, tooling
- `docs:` documentation updates
