# CI/CD Job Checklist (Production Expansion)

## Job 1: Validate Runtime Integrity
- Trigger: push, pull_request
- Gate: required
- Steps:
  - Checkout code
  - `python -m pip install -r requirements.txt`
  - `python -m compileall app`
  - `docker compose config`
- Pass criteria:
  - No syntax/config errors
  - No missing dependency

## Job 2: Security and Secret Hygiene
- Trigger: push, pull_request
- Gate: required
- Steps:
  - Secret scan: `python ops/secret_hygiene.py`
  - Dependency audit: `pip-audit` (non-blocking first 2 weeks, then blocking)
- Pass criteria:
  - No hardcoded keys
  - No critical unresolved vulnerabilities

## Job 3: Build and Container Smoke Test
- Trigger: push, pull_request
- Gate: required
- Steps:
  - `docker compose up -d --build`
  - Wait for API health
  - Curl checks:
    - `GET /system/health`
    - `GET /system/economic-weight`
    - `GET /catalog/connectors` -> `20`
    - `GET /catalog/axes` -> `8`
- Pass criteria:
  - All endpoints return 200
  - Catalog counts stable

## Job 4: Invariant Contract Test
- Trigger: push, pull_request
- Gate: required
- Steps:
  - Assert `deg_violation` empty
  - Assert GSSI payload has 8 axes
  - Assert SPOF list present
  - Assert `Stripe` state endpoint returns required fields
- Pass criteria:
  - Canon invariants not broken

## Job 5: Prometheus Metrics Contract
- Trigger: push, pull_request
- Gate: required
- Steps:
  - Curl `/metrics`
  - Verify lines exist:
    - `balancehub_breaker_state`
    - `balancehub_stability_score`
- Pass criteria:
  - Required metrics exported

## Job 6: Publish Artifact (Docker)
- Trigger: tag `v*` on main
- Gate: required
- Steps:
  - Build image
  - Push tags: `latest` and `${GIT_TAG}`
  - Record digest in release notes
- Pass criteria:
  - Image available publicly
  - Pull and run smoke check passes

## Job 7: Release Governance
- Trigger: manual dispatch / tag
- Gate: required
- Steps:
  - Generate release summary
  - Include KPI snapshot: stars/forks/clones/docker pulls
  - Include `/system/health` + `/system/economic-weight` snapshot
- Pass criteria:
  - Evidence attached to release

## Job 8: Weekly Growth KPI Report
- Trigger: schedule (weekly)
- Gate: non-blocking
- Steps:
  - Collect growth signals
  - Compare target vs actual
  - Open issue when KPI below threshold for 2 consecutive weeks
- Pass criteria:
  - KPI report published

## Required Branch Rules
- Require status checks: Job 1-5
- Require linear history
- Block force push on `main`

## Rollback Rule
- If runtime contract fails on main:
  - rollback to last successful tag
  - re-run Job 3 + Job 4 before re-open deploy
