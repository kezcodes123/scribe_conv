#!/usr/bin/env zsh
# Start the web UI in test mode (bypass paywall) and force web UI
set -euo pipefail

# Move to repo root
cd "$(dirname "$0")/.."

# Ensure venv python exists
if [[ ! -x .venv/bin/python ]]; then
  echo "Python venv not found at .venv/bin/python" >&2
  exit 1
fi

export PAYWALL_TEST_MODE=1
export SCRIBE_UI_FORCE_WEB=1

exec .venv/bin/python -m scribe_tools.app

# Run from 'untitled folder':
# ./scripts/run_web_test.sh
