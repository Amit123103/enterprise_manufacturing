#!/bin/bash
set -e

echo "===> Installing dependencies from requirements.txt..."
if command -v uv &> /dev/null; then
    echo "Detected uv package manager. Installing with uv..."
    uv pip install --system -r requirements.txt
else
    echo "Installing with pip (--break-system-packages)..."
    python3 -m pip install --break-system-packages -r requirements.txt || python3 -m pip install -r requirements.txt
fi

echo "===> Running collectstatic..."
python3 manage.py collectstatic --noinput --clear

echo "===> Build completed successfully!"
