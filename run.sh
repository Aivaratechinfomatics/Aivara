#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "======================================================"
echo "            Aivara Analytics Platform"
echo "======================================================"
echo ""

# Activate virtual environment if present
if [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment .venv ..."
    source .venv/bin/activate
elif [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment venv ..."
    source venv/bin/activate
fi

# Verify Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "[ERROR] Python was not found in your PATH."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    PYTHON_CMD="python"
fi

# Verify streamlit installed
if ! $PYTHON_CMD -c "import streamlit" &>/dev/null; then
    echo "Streamlit not detected. Installing dependencies from requirements.txt ..."
    pip install -r requirements.txt
fi

echo "Starting Aivara web interface on http://localhost:8501 ..."
$PYTHON_CMD -m streamlit run app.py
