# BalanceHub Minimal (Public-Safe)

BalanceHub v2 runtime prototype with:
- `/execute` governance gateway
- `/system/health` (GSSI)
- `/catalog/axes` + `/catalog/connectors`
- `/metrics` (Prometheus)

## Why this is minimal
- No secret required for local run.
- Stripe path runs in mock-safe mode when `STRIPE_API_KEY` is empty.
- Core health/governance remains active.

## Quickstart (one command)
```bash
docker compose up -d --build
```

## Smoke checks
```bash
curl -s http://localhost:8000/system/health | jq .
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
