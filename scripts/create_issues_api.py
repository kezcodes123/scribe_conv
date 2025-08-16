#!/usr/bin/env python3
"""
Create milestones, labels, and issues in a GitHub repo via REST API.

Usage:
  GITHUB_TOKEN=ghp_xxx python3 scripts/create_issues_api.py [owner/repo]
Defaults to repo: kezcodes123/scribe_conv

No external deps required (uses urllib).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

API = "https://api.github.com"
DEFAULT_REPO = "kezcodes123/scribe_conv"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _headers() -> Dict[str, str]:
    if not TOKEN:
        print("Set GITHUB_TOKEN env var with a token that has repo access.", file=sys.stderr)
        sys.exit(2)
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "scribe-conv-setup",
    }


def _req(method: str, url: str, data: Dict[str, Any] | None = None) -> Any:
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, method=method, headers=_headers(), data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            txt = resp.read().decode("utf-8")
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8")
        print(f"HTTP {e.code} for {url}: {msg}", file=sys.stderr)
        # If already exists, consider ok for idempotency
        if e.code in (409,):
            return None
        raise


def _get_all(url: str) -> List[Any]:
    # naive single page fetch; good enough for our small lists
    return _req("GET", url) or []


def ensure_labels(repo: str, labels: List[str]) -> None:
    existing = {lab.get("name") for lab in _get_all(f"{API}/repos/{repo}/labels?per_page=100")}
    for name in labels:
        if name in existing:
            print(f"Label exists: {name}")
            continue
        _req("POST", f"{API}/repos/{repo}/labels", {"name": name})
        print(f"Label created: {name}")
        time.sleep(0.2)


def ensure_milestones(repo: str, titles: List[str]) -> Dict[str, int]:
    existing = _get_all(f"{API}/repos/{repo}/milestones?state=all&per_page=100")
    by_title = {m.get("title"): m.get("number") for m in existing}
    out: Dict[str, int] = {}
    for title in titles:
        if title in by_title and isinstance(by_title[title], int):
            out[title] = int(by_title[title])
            print(f"Milestone exists: {title}")
            continue
        m = _req("POST", f"{API}/repos/{repo}/milestones", {"title": title})
        num = int(m.get("number")) if isinstance(m, dict) else None
        if num is None:
            raise RuntimeError(f"Failed to create milestone: {title}")
        out[title] = num
        print(f"Milestone created: {title}")
        time.sleep(0.3)
    return out


def create_issue(repo: str, title: str, body: str, labels: List[str], milestone_num: int) -> None:
    data = {
        "title": title,
        "body": body,
        "labels": labels,
        "milestone": milestone_num,
    }
    _req("POST", f"{API}/repos/{repo}/issues", data)
    print(f"Issue created: {title}")
    time.sleep(0.3)


def main() -> None:
    repo = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO

    labels = [
        "ui", "enhancement", "epub", "pdf", "performance", "security",
        "accessibility", "paywall", "docs", "devops", "bug",
    ]
    milestones = [
        "UX/UI polish",
        "EPUB quality",
        "Engine & performance",
        "Security & compliance",
        "Accessibility & i18n",
        "DevOps & docs",
    ]

    issues = [
        ("Redesign header and navigation", "UX/UI polish",
         "Why: Clearer navigation and branding.\nTasks:\n- Add compact header with logo/title, Home, Pricing, Docs\n- Highlight active route; show Test mode badge when enabled\nAcceptance:\n- Links work; badge visible only in test mode",
         ["ui", "enhancement"]),
        ("Form layout and Advanced options", "UX/UI polish",
         "Why: Reduce clutter and guide typical flows.\nTasks:\n- Group into Output, Layout, Processing, Engine\n- Collapse Advanced by default; add tooltips & HTML validation\nAcceptance:\n- Default path requires minimal choices; advanced is clear",
         ["ui", "enhancement"]),
        ("Progress and result UX", "UX/UI polish",
         "Why: Better feedback for long conversions.\nTasks:\n- Show spinner/progress; disable submit while processing\n- On success: file summary + Download button; on error: friendly retry\nAcceptance:\n- No double submits; clear success/error states",
         ["ui", "enhancement"]),
        ("Pricing page refinement", "UX/UI polish",
         "Why: Professional paywall presentation.\nTasks:\n- Modern card with features, £2/month, CTA\n- Test mode shows bypass button only in test mode\nAcceptance:\n- Stripe CTA in prod; bypass in test",
         ["paywall", "ui", "enhancement"]),
        ("Tighten EPUB spacing and typography", "EPUB quality",
         "Why: Reduce whitespace.\nTasks:\n- Tune CSS (margins/line-height), reset image blocks\n- Merge blocks; drop empty paragraphs\nAcceptance:\n- Less whitespace without clipping",
         ["epub", "enhancement"]),
        ("Robust TOC and headings", "EPUB quality",
         "Why: Better navigation.\nTasks:\n- Improve heading thresholds; hierarchical TOC\n- Fallback to per-page TOC\nAcceptance:\n- TOC jumps correctly; no duplicates",
         ["epub", "enhancement"]),
        ("EPUB image handling + grayscale/bilevel control", "EPUB quality",
         "Why: Consistent rendering.\nTasks:\n- Grayscale default; optional bilevel + dither toggle\n- Cap long edge ~1600–1920px; JPEG q75–80 progressive\nAcceptance:\n- Send to Kindle accepts; images correct; sizes reasonable",
         ["epub", "enhancement"]),
        ("EPUB: full-page fallback for non-text/vector pages", "EPUB quality",
         "Why: Prevent missing/cropped pages.\nTasks:\n- Heuristic: if text density < X, render full-page image\nAcceptance:\n- No blank/cropped pages",
         ["epub", "bug"]),
        ("Async worker + request timeouts", "Engine & performance",
         "Why: Avoid timeouts; responsive UI.\nTasks:\n- Background jobs + status polling or SSE\n- Cap processing time per job\nAcceptance:\n- Large files complete; UI stays responsive",
         ["performance", "enhancement"]),
        ("Temp files + streaming downloads", "Engine & performance",
         "Why: Memory/disk hygiene.\nTasks:\n- Use NamedTemporaryFile; cleanup on completion/error\n- Stream downloads\nAcceptance:\n- No orphan temps; stable memory usage",
         ["performance", "enhancement"]),
        ("CSRF, cookies, security headers (finalize)", "Security & compliance",
         "Why: Harden web surface.\nTasks:\n- CSRF on all POST\n- Cookie HttpOnly/SameSite; Secure on HTTPS\n- CSP, X-Frame-Options, Referrer-Policy, X-Content-Type-Options\nAcceptance:\n- Headers present; CSRF validated; cookies secure on HTTPS",
         ["security", "enhancement"]),
        ("Rate limiting + upload limits", "Security & compliance",
         "Why: Prevent abuse.\nTasks:\n- Flask-Limiter (IP + session)\n- MAX_CONTENT_LENGTH env-configurable\nAcceptance:\n- Excess requests throttled; oversized uploads rejected clearly",
         ["security", "performance"]),
        ("Stripe paywall hardening", "Security & compliance",
         "Why: Reliable billing.\nTasks:\n- Enforce real paywall when test mode off\n- Verify webhook signatures; handle cancelation\n- Mask secrets; docs for rotation\nAcceptance:\n- Access only for active subs; test bypass only with env",
         ["paywall", "security"]),
        ("Accessibility (WCAG basics)", "Accessibility & i18n",
         "Why: Inclusive UI.\nTasks:\n- ARIA labels; keyboard navigation; focus management\n- Contrast checks; visible focus outlines\nAcceptance:\n- Pass basic WCAG checks; logical tab order",
         ["accessibility", "ui"]),
        ("Internationalization scaffold", "Accessibility & i18n",
         "Why: Future locales.\nTasks:\n- Externalize strings; lang attribute\n- Locale switcher scaffold\nAcceptance:\n- English default; structure for locales",
         ["enhancement"]),
        ("Dependency pinning + Makefile", "DevOps & docs",
         "Why: Reproducible installs.\nTasks:\n- Pin versions; optional hashes\n- Add Makefile for setup/test targets\nAcceptance:\n- Fresh install reproducible; no version drift",
         ["devops"]),
        ("Error reporting + structured logs", "DevOps & docs",
         "Why: Easier support.\nTasks:\n- Normalize user-facing errors\n- Structured logs; no sensitive data\nAcceptance:\n- Clear user errors; actionable logs server-side",
         ["enhancement", "devops"]),
        ("README + user guide", "DevOps & docs",
         "Why: Onboarding.\nTasks:\n- Quick start (test vs prod), Stripe setup, security notes\n- Known limitations; troubleshooting\nAcceptance:\n- New users can install, run, convert in minutes",
         ["docs", "enhancement"]),
    ]

    print(f"Target repo: {repo}")
    ensure_labels(repo, labels)
    ms_map = ensure_milestones(repo, milestones)

    for title, ms_title, body, labs in issues:
        ms_num = ms_map[ms_title]
        create_issue(repo, title, body, labs, ms_num)

    print("Done.")


if __name__ == "__main__":
    main()
