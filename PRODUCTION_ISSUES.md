# Critical Production Security Issues for GitHub

## Issue 1: CRITICAL - Production paywall bypass allows unauthorized PDF/EPUB conversion

**Priority:** P0 - Critical Security
**Labels:** security, paywall, bug, production
**Milestone:** Security & compliance

**Description:**
In production mode, users can still convert PDFs/EPUBs without payment or account verification. The paywall check is not properly enforced on the main conversion endpoint.

**Current Behavior:**
- Server runs in production mode (no test mode badge)
- `/pricing` returns 503 (Stripe not configured)
- Main `/` endpoint still accepts file uploads and processes conversions
- No subscription validation on POST requests

**Expected Behavior:**
- All conversion requests should require active subscription
- Unauthenticated users redirected to pricing
- Failed payment verification blocks conversion
- Clear error messages for payment issues

**Steps to Reproduce:**
1. Start server with `./scripts/run_web_prod.sh`
2. Navigate to http://127.0.0.1:57269
3. Upload a PDF file
4. Click "Optimize" 
5. File processes successfully without payment

**Technical Details:**
- `web_ui.py` line ~84: Customer validation bypassed on GET but not enforced on POST
- Missing Stripe configuration causes 503 but doesn't block conversions
- Session-based auth allows processing after initial redirect

**Acceptance Criteria:**
- [ ] POST `/` returns 402 Payment Required when no active subscription
- [ ] GET `/` redirects to pricing when not authenticated
- [ ] Proper error handling for missing Stripe configuration
- [ ] All conversion endpoints protected by subscription check
- [ ] Clear user messaging about payment requirements

**Security Impact:** HIGH
- Unauthorized access to paid features
- Revenue loss from unpaid usage
- Potential abuse/resource exhaustion

---

## Issue 2: Stripe configuration validation missing

**Priority:** P1 - High
**Labels:** paywall, production, devops
**Milestone:** Security & compliance

**Description:**
Production mode should validate Stripe configuration on startup and provide clear error messages when misconfigured.

**Current Behavior:**
- Server starts successfully without Stripe keys
- Routes return 503 errors
- No startup validation

**Expected Behavior:**
- Startup check for required Stripe environment variables
- Graceful degradation or clear error messages
- Health check endpoint for monitoring

---

## Issue 3: Session management and CSRF hardening

**Priority:** P2 - Medium
**Labels:** security, csrf
**Milestone:** Security & compliance  

**Description:**
Strengthen session management and CSRF protection for production deployment.

**Tasks:**
- [ ] Session timeout implementation
- [ ] Secure cookie configuration validation
- [ ] CSRF token rotation
- [ ] Session invalidation on subscription changes

---

## Issue 4: Rate limiting and abuse prevention

**Priority:** P2 - Medium
**Labels:** security, performance
**Milestone:** Security & compliance

**Description:**
Implement rate limiting to prevent abuse of conversion endpoints.

**Tasks:**
- [ ] Per-IP rate limiting
- [ ] Per-user subscription quota enforcement
- [ ] File size and processing time limits
- [ ] Abuse detection and blocking

---

## Issue 5: Production deployment documentation

**Priority:** P3 - Low  
**Labels:** docs, production, devops
**Milestone:** DevOps & docs

**Description:**
Document proper production deployment with HTTPS, environment variables, and monitoring.

**Tasks:**
- [ ] HTTPS reverse proxy setup guide
- [ ] Environment variable reference
- [ ] Stripe webhook configuration
- [ ] Health checks and monitoring
- [ ] Backup and recovery procedures

---

## Quick GitHub Issue Creation Commands

```bash
# Issue 1 - Critical paywall bypass
gh issue create \
  --title "CRITICAL: Production paywall bypass allows unauthorized conversions" \
  --label "security,paywall,bug,production" \
  --milestone "Security & compliance" \
  --assignee "@me" \
  --body "Production mode allows file conversion without payment verification..."

# Issue 2 - Stripe validation  
gh issue create \
  --title "Stripe configuration validation missing on startup" \
  --label "paywall,production,devops" \
  --milestone "Security & compliance" \
  --body "Server should validate Stripe config and fail gracefully..."

# Issue 3 - Session hardening
gh issue create \
  --title "Session management and CSRF hardening for production" \
  --label "security,csrf" \
  --milestone "Security & compliance" \
  --body "Strengthen session security for production deployment..."

# Issue 4 - Rate limiting
gh issue create \
  --title "Rate limiting and abuse prevention" \
  --label "security,performance" \
  --milestone "Security & compliance" \
  --body "Implement rate limiting to prevent conversion abuse..."

# Issue 5 - Production docs
gh issue create \
  --title "Production deployment documentation" \
  --label "docs,production,devops" \
  --milestone "DevOps & docs" \
  --body "Document HTTPS deployment, env vars, monitoring..."
```

## Immediate Action Required

**Priority 1:** Fix the paywall bypass in `web_ui.py`:
- Move subscription check to decorator
- Apply to all protected routes  
- Return 402 Payment Required for invalid subscriptions
- Test with both valid/invalid subscription states
