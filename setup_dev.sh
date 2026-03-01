#!/bin/bash
# Development setup helper for pynpm_bridge
set -e

echo "=== pynpm_bridge development setup ==="

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Install Node.js 20+ first."
    exit 1
fi

NODE_VERSION=$(node -v)
echo "Node.js version: $NODE_VERSION"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Python version: $PYTHON_VERSION"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing pynpm_bridge in editable mode with dev dependencies..."
pip install -e ".[dev]"

echo ""
echo "Setup complete! To activate the venv:"
echo "  source .venv/bin/activate"
echo ""
echo "Run tests:"
echo "  pytest tests/ -v"
echo ""
echo "Run demo:"
echo "  python examples/demo.py"