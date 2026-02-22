# BalanceHub Minimal (Public-Safe)
[![Forks](https://img.shields.io/github/forks/NguyenCuong1989/balancehub-minimal?style=flat)](https://github.com/NguyenCuong1989/balancehub-minimal/forks)
[![Run with Docker](https://img.shields.io/badge/run-docker-blue)](https://github.com/NguyenCuong1989/balancehub-minimal#quickstart-one-command)
[![Deploy to Render](https://img.shields.io/badge/deploy-render-46E3B7)](https://render.com/)

BalanceHub v2 runtime prototype with:
- `/execute` governance gateway
- `/system/health` (GSSI)
- `/system/economic-weight` (COMPUTE_W)
- `/catalog/axes` + `/catalog/connectors`
- `/metrics` (Prometheus)

## Why this is minimal
- No secret required for local run.
- Stripe path runs in mock-safe mode when `STRIPE_API_KEY` is empty.
- Core health/governance remains active.

## Quickstart (one command)
```bash
docker run -p 8000:8000 balancehub/minimal:latest
```

## Full stack (compose)
```bash
docker compose up -d --build
```

## Smoke checks
```bash
curl -s http://localhost:8000/system/health | jq .
curl -s http://localhost:8000/system/economic-weight | jq .
curl -s http://localhost:8000/catalog/connectors | jq '.items | length'
curl -s -X POST http://localhost:8000/execute \
  -H 'Content-Type: application/json' \
  -d '{"connector":"Stripe","action":"retrieve_balance","payload":{},"request_id":"demo-1"}' | jq .
```

## Public-free core
- Core execution governor: open
- Health index model: open
- Axis topology model: open
- No paywall on core runtime

## Launch Ops
- CI/CD job checklist: `ops/launch/CI_CD_JOB_CHECKLIST.md`
- Growth launch plan (30 days): `ops/launch/GROWTH_LAUNCH_PLAN_30D.md`
- HackerNews template: `ops/launch/HACKERNEWS_POST_TEMPLATE.md`
