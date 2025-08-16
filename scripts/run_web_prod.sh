#!/usr/bin/env zsh
# Start the web UI in production mode (real paywall). Requires Stripe env vars.
set -euo pipefail

# Move to repo root
cd "$(dirname "$0")/.."

# Ensure venv python exists
if [[ ! -x .venv/bin/python ]]; then
  echo "Python venv not found at .venv/bin/python" >&2
  exit 1
fi

unset PAYWALL_TEST_MODE
export SCRIBE_UI_FORCE_WEB=1

# Required for paywall:
# export STRIPE_SECRET_KEY=sk_test_...
# export STRIPE_PRICE_ID=price_...
# export STRIPE_WEBHOOK_SECRET=whsec_...
# export BASE_URL="http://127.0.0.1:5000"  # or your public URL

exec .venv/bin/python -m scribe_tools.app

# Run from 'untitled folder':
# ./scripts/run_web_prod.sh
