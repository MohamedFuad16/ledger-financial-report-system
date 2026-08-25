#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m unittest discover -p 'test_*.py'
python test_contract.py
python -m pip_audit -r requirements.txt
python -m bandit -q -r . -x ./.venv,./frontend,./data -ll

npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend audit --audit-level=moderate
npm --prefix frontend run build
