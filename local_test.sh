#!/bin/bash
set -e

echo "=== Local CI Test ==="

# Setup environment
export MIFOS_BASE_URL="https://tt.mifos.community"
export MIFOS_TENANT="default"

# 1. Setup virtual environment
echo "Setting up virtual environment..."
python -m venv venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Virtual environment activation script not found!"
    exit 1
fi

# 2. Install dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Run linting (Ruff)
echo "Running ruff linting..."
ruff check .

# 4. Run linting (Flake8)
echo "Running flake8 linting..."
flake8 .

# 5. Check formatting
echo "Checking formatting with black..."
black --check .

# 6. Run type checking
echo "Running mypy type checking..."
mypy --explicit-package-bases .

# 7. Run security scan
echo "Running bandit security scan..."
bandit -r . --exclude ./.venv,./venv,./tests -q

# 8. Run unit tests with coverage
echo "Running pytest with coverage..."
export PYTHONPATH=.
python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=50

# 9. MCP smoke check
echo "Running MCP smoke check..."
python -c "
import os, importlib

os.environ.setdefault('MIFOS_BASE_URL', os.getenv('MIFOS_BASE_URL', 'https://tt.mifos.community'))
os.environ.setdefault('MIFOS_TENANT', os.getenv('MIFOS_TENANT', 'default'))

# Test that main module can be imported
m = importlib.import_module('main')

# Check that main module has mcp instance
assert hasattr(m, 'mcp'), 'MCP instance not found in main module'

# Test that router modules can be imported (this will register the tools)
import routers.auth_tools
import routers.client_tools
import routers.beneficiary_tools
import routers.transfer_tools
import resources.overview
import resources.endpoints
import resources.workflows

print('MCP server imported and router modules loaded successfully.')
"

echo "=== All checks passed! ==="
