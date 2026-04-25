#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"

python -m pip install -e .
python -m server.app --port "${PORT}"

