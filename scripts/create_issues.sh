#!/usr/bin/env zsh
# Creates milestones, labels, and issues in GitHub repo kezcodes123/scribe_conv
set -euo pipefail

# Move to repo root
cd "$(dirname "$0")/.."

REPO="kezcodes123/scribe_conv"

# Ensure gh CLI is authenticated
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) not found. Please install with: brew install gh" >&2
  exit 127
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI not authenticated. Starting browser-based login..." >&2
  gh auth login -s repo -w
fi

# Set default repo (ok if already set)
(gh repo set-default "$REPO" >/dev/null 2>&1) || true

# Create labels (idempotent)
for L in ui enhancement epub pdf performance security accessibility paywall docs devops bug; do
  gh label create "$L" -R "$REPO" >/dev/null 2>&1 || true
  echo "Label ensured: $L"
done

# Create milestones (idempotent)
create_ms() {
  local TITLE="$1"
  gh api -X POST -H "Accept: application/vnd.github+json" \
    "/repos/${REPO}/milestones" -f title="$TITLE" >/dev/null 2>&1 || true
  echo "Milestone ensured: $TITLE"
}
create_ms "UX/UI polish"
create_ms "EPUB quality"
create_ms "Engine & performance"
create_ms "Security & compliance"
create_ms "Accessibility & i18n"
create_ms "DevOps & docs"

# Helper to create an issue
mk_issue() {
  local TITLE="$1"; shift
  local MILESTONE="$1"; shift
  local BODY="$1"; shift
  # Remaining args are labels (space-separated)
  local LABEL_ARGS=()
  for label in "$@"; do
    LABEL_ARGS+=("--label" "$label")
  done
  gh issue create -R "$REPO" --title "$TITLE" --milestone "$MILESTONE" "${LABEL_ARGS[@]}" --body "$BODY" >/dev/null
  echo "Created: $TITLE"
}

# 1) Redesign header and navigation
mk_issue "Redesign header and navigation" "UX/UI polish" $'Why: Clearer navigation and branding.\nTasks:\n- Add compact header with logo/title, Home, Pricing, Docs\n- Highlight active route; show Test mode badge when enabled\nAcceptance:\n- Links work; badge visible only in test mode' ui enhancement

# 2) Form layout and Advanced options
mk_issue "Form layout and Advanced options" "UX/UI polish" $'Why: Reduce clutter and guide typical flows.\nTasks:\n- Group into Output, Layout, Processing, Engine\n- Collapse Advanced by default; add tooltips & HTML validation\nAcceptance:\n- Default path requires minimal choices; advanced is clear' ui enhancement

# 3) Progress and result UX
mk_issue "Progress and result UX" "UX/UI polish" $'Why: Better feedback for long conversions.\nTasks:\n- Show spinner/progress; disable submit while processing\n- On success: file summary + Download button; on error: friendly retry\nAcceptance:\n- No double submits; clear success/error states' ui enhancement

# 4) Pricing page refinement
mk_issue "Pricing page refinement" "UX/UI polish" $'Why: Professional paywall presentation.\nTasks:\n- Modern card with features, £2/month, CTA\n- Test mode shows bypass button only in test mode\nAcceptance:\n- Stripe CTA in prod; bypass in test' paywall ui enhancement

# 5) Tighten EPUB spacing and typography
mk_issue "Tighten EPUB spacing and typography" "EPUB quality" $'Why: Reduce whitespace.\nTasks:\n- Tune CSS (margins/line-height), reset image blocks\n- Merge blocks; drop empty paragraphs\nAcceptance:\n- Less whitespace without clipping' epub enhancement

# 6) Robust TOC and headings
mk_issue "Robust TOC and headings" "EPUB quality" $'Why: Better navigation.\nTasks:\n- Improve heading thresholds; hierarchical TOC\n- Fallback to per-page TOC\nAcceptance:\n- TOC jumps correctly; no duplicates' epub enhancement

# 7) Image handling + grayscale/bilevel control (EPUB)
mk_issue "EPUB image handling + grayscale/bilevel control" "EPUB quality" $'Why: Consistent rendering.\nTasks:\n- Grayscale default; optional bilevel + dither toggle\n- Cap long edge ~1600–1920px; JPEG q75–80 progressive\nAcceptance:\n- Send to Kindle accepts; images correct; sizes reasonable' epub enhancement

# 8) Non-text pages: full-page fallback
mk_issue "EPUB: full-page fallback for non-text/vector pages" "EPUB quality" $'Why: Prevent missing/cropped pages.\nTasks:\n- Heuristic: if text density < X, render full-page image\nAcceptance:\n- No blank/cropped pages' epub bug

# 9) Async worker + request timeouts
mk_issue "Async worker + request timeouts" "Engine & performance" $'Why: Avoid timeouts; responsive UI.\nTasks:\n- Background jobs + status polling or SSE\n- Cap processing time per job\nAcceptance:\n- Large files complete; UI stays responsive' performance enhancement

# 10) Temp files + streaming downloads
mk_issue "Temp files + streaming downloads" "Engine & performance" $'Why: Memory/disk hygiene.\nTasks:\n- Use NamedTemporaryFile; cleanup on completion/error\n- Stream downloads\nAcceptance:\n- No orphan temps; stable memory usage' performance enhancement

# 11) CSRF, cookies, security headers
mk_issue "CSRF, cookies, security headers (finalize)" "Security & compliance" $'Why: Harden web surface.\nTasks:\n- CSRF on all POST\n- Cookie HttpOnly/SameSite; Secure on HTTPS\n- CSP, X-Frame-Options, Referrer-Policy, X-Content-Type-Options\nAcceptance:\n- Headers present; CSRF validated; cookies secure on HTTPS' security enhancement

# 12) Rate limiting + upload limits
mk_issue "Rate limiting + upload limits" "Security & compliance" $'Why: Prevent abuse.\nTasks:\n- Flask-Limiter (IP + session)\n- MAX_CONTENT_LENGTH env-configurable\nAcceptance:\n- Excess requests throttled; oversized uploads rejected clearly' security performance

# 13) Stripe paywall hardening
mk_issue "Stripe paywall hardening" "Security & compliance" $'Why: Reliable billing.\nTasks:\n- Enforce real paywall when test mode off\n- Verify webhook signatures; handle cancelation\n- Mask secrets; docs for rotation\nAcceptance:\n- Access only for active subs; test bypass only with env' paywall security

# 14) Accessibility (WCAG basics)
mk_issue "Accessibility (WCAG basics)" "Accessibility & i18n" $'Why: Inclusive UI.\nTasks:\n- ARIA labels; keyboard navigation; focus management\n- Contrast checks; visible focus outlines\nAcceptance:\n- Pass basic WCAG checks; logical tab order' accessibility ui

# 15) Internationalization scaffold
mk_issue "Internationalization scaffold" "Accessibility & i18n" $'Why: Future locales.\nTasks:\n- Externalize strings; lang attribute\n- Locale switcher scaffold\nAcceptance:\n- English default; structure for locales' enhancement

# 16) Dependency pinning + Makefile
mk_issue "Dependency pinning + Makefile" "DevOps & docs" $'Why: Reproducible installs.\nTasks:\n- Pin versions; optional hashes\n- Add Makefile for setup/test targets\nAcceptance:\n- Fresh install reproducible; no version drift' devops

# 17) Error reporting + structured logs
mk_issue "Error reporting + structured logs" "DevOps & docs" $'Why: Easier support.\nTasks:\n- Normalize user-facing errors\n- Structured logs; no sensitive data\nAcceptance:\n- Clear user errors; actionable logs server-side' enhancement devops

# 18) README + user guide
mk_issue "README + user guide" "DevOps & docs" $'Why: Onboarding.\nTasks:\n- Quick start (test vs prod), Stripe setup, security notes\n- Known limitations; troubleshooting\nAcceptance:\n- New users can install, run, convert in minutes' docs enhancement

echo "All issues created for $REPO"
