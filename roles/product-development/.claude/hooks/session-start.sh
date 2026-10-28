#!/bin/bash
# Make a fresh cloud container ready for unattended catalog work.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"
pip install -q -r requirements.txt >/dev/null 2>&1 || pip install -q -r requirements.txt
pip install -q -e . --no-deps >/dev/null 2>&1 || true
