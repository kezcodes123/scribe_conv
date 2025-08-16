# Issue Creation Scripts

This directory contains scripts to create GitHub milestones, labels, and issues for the scribe_conv project.

## Scripts Available

### 1. Shell Script (`create_issues.sh`)
- **Requirements**: GitHub CLI (`gh`) must be installed and authenticated
- **Usage**: `./scripts/create_issues.sh`
- **Description**: Uses GitHub CLI to create milestones, labels, and issues

### 2. Python Script (`create_issues_api.py`)
- **Requirements**: Python 3, GITHUB_TOKEN environment variable
- **Usage**: `GITHUB_TOKEN=your_token python3 scripts/create_issues_api.py [owner/repo]`
- **Description**: Uses GitHub REST API directly (no external dependencies)

## What Gets Created

### Labels (11 total)
- `ui`, `enhancement`, `epub`, `pdf`, `performance`, `security`
- `accessibility`, `paywall`, `docs`, `devops`, `bug`

### Milestones (6 total)
- "UX/UI polish"
- "EPUB quality" 
- "Engine & performance"
- "Security & compliance"
- "Accessibility & i18n"
- "DevOps & docs"

### Issues (18 total)
Issues are organized across the 6 milestones covering:
1. Redesign header and navigation
2. Form layout and Advanced options
3. Progress and result UX
4. Pricing page refinement
5. Tighten EPUB spacing and typography
6. Robust TOC and headings
7. EPUB image handling + grayscale/bilevel control
8. EPUB: full-page fallback for non-text/vector pages
9. Async worker + request timeouts
10. Temp files + streaming downloads
11. CSRF, cookies, security headers (finalize)
12. Rate limiting + upload limits
13. Stripe paywall hardening
14. Accessibility (WCAG basics)
15. Internationalization scaffold
16. Dependency pinning + Makefile
17. Error reporting + structured logs
18. README + user guide

## Authentication

### For Shell Script
```bash
# Install GitHub CLI if needed
brew install gh  # macOS
# or
apt install gh   # Linux

# Authenticate
gh auth login
```

### For Python Script
```bash
# Set your GitHub token
export GITHUB_TOKEN=ghp_your_token_here
# or
export GH_TOKEN=ghp_your_token_here
```

## Running the Scripts

Both scripts are idempotent - you can run them multiple times safely. They will:
- Create labels if they don't exist
- Create milestones if they don't exist  
- Create issues if they don't exist

```bash
# Option 1: Shell script (requires gh CLI)
./scripts/create_issues.sh

# Option 2: Python script (requires token)
GITHUB_TOKEN=ghp_xxx python3 scripts/create_issues_api.py kezcodes123/scribe_conv
```

## Default Repository

Both scripts default to `kezcodes123/scribe_conv` but can be overridden:
- Shell script: Edit the `REPO` variable in the script
- Python script: Pass repository as argument