# HackerNews Launch Template

## Title Options
1. Open-source System Stability Index for Multi-Connector AI Orchestration
2. We built a Docker-first stability control plane for AI connectors (no secrets required)
3. BalanceHub Minimal: /system/health + /system/economic-weight in one command

## Post Body (Template)
Hi HN,

I’m sharing `balancehub-minimal`, an open-source runtime for connector stability and governance.

What it does:
- Single execution gateway (`POST /execute`)
- Global Stability Index (`GET /system/health`)
- Economic Weight model (`GET /system/economic-weight`)
- Prometheus metrics (`GET /metrics`)

Design constraints:
- Docker-first
- No secret required for local run
- Mock-safe mode by default
- Topology mapped into 8 axes and 20 connectors

Run locally:
```bash
docker compose up -d --build
curl -s http://localhost:8000/system/health | jq .
curl -s http://localhost:8000/system/economic-weight | jq .
```

Repo:
- https://github.com/NguyenCuong1989/balancehub-minimal

I’d like feedback on:
1. Invariant checks for production safety
2. Better economic-weight signals
3. What would make this easier to fork and deploy

## Comment Reply Snippets
- Why mock-safe by default?
  - To keep onboarding friction near zero and preserve reproducibility without paid keys.
- Why not only observability?
  - This includes governance decisions at execution time, not just telemetry.
- Is it production ready?
  - Runtime contracts are active; currently hardening CI/CD and growth instrumentation.
