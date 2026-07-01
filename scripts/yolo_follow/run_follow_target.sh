#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="/home/oneday/project4/scripts/yolo_follow"
cd "$SCRIPT_DIR"

if [[ -f "$SCRIPT_DIR/follow_target.env" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/follow_target.env"
fi

exec /home/oneday/project4/.venv/bin/python "$SCRIPT_DIR/follow_target_yolo.py" ${FOLLOW_ARGS:-}
