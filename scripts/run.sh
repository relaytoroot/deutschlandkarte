#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# venv aktivieren (Git Bash auf Windows)
if [[ -f "$ROOT_DIR/.venv/Scripts/activate" ]]; then
  source "$ROOT_DIR/.venv/Scripts/activate"
fi

export PYTHONPATH="$ROOT_DIR"

python src/app/main.py
