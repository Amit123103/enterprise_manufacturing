#!/bin/bash
set -e

echo "===> Setting up Python 3.12 environment..."

if command -v uv &> /dev/null; then
    echo "Installing/verifying Python 3.12 with uv..."
    uv python install 3.12
    echo "Creating virtual environment with Python 3.12..."
    uv venv --python 3.12 /tmp/build_venv
    source /tmp/build_venv/bin/activate
    echo "Installing dependencies with uv..."
    uv pip install -r requirements.txt
elif command -v python3.12 &> /dev/null; then
    echo "Using system python3.12..."
    python3.12 -m venv /tmp/build_venv
    source /tmp/build_venv/bin/activate
    python -m pip install -r requirements.txt
elif command -v python3.11 &> /dev/null; then
    echo "Using system python3.11..."
    python3.11 -m venv /tmp/build_venv
    source /tmp/build_venv/bin/activate
    python -m pip install -r requirements.txt
else
    echo "Falling back to system python3..."
    python3 -m venv /tmp/build_venv
    source /tmp/build_venv/bin/activate
    python -m pip install -r requirements.txt
fi

echo "===> Using Python version: $(python --version)"

echo "===> Running collectstatic..."
python manage.py collectstatic --noinput --clear

echo "===> Build completed successfully!"
