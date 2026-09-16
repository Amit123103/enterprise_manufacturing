#!/bin/bash
set -e

echo "===> Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "===> Running collectstatic..."
python3 manage.py collectstatic --noinput --clear

echo "===> Build completed successfully!"
