#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$SCRIPT_DIR"

if [[ -f "$SCRIPT_DIR/follow_target.env" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/follow_target.env"
fi

exec "$ROOT_DIR/.venv/bin/python" "$SCRIPT_DIR/follow_target_yolo.py" ${FOLLOW_ARGS:-}
