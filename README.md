# BalanceHub Minimal (Public-Safe)

[![Forks](https://img.shields.io/github/forks/NguyenCuong1989/balancehub-minimal?style=flat)](https://github.com/NguyenCuong1989/balancehub-minimal/forks)
[![Run with Docker](https://img.shields.io/badge/run-docker-blue)](https://github.com/NguyenCuong1989/balancehub-minimal#quickstart-one-command)
[![Deploy to Render](https://img.shields.io/badge/deploy-render-46E3B7)](https://render.com/)

BalanceHub v2 runtime prototype with:

- `/execute` governance gateway
- `/system/health` (GSSI)
- `/system/economic-weight` (COMPUTE_W)
- `/canon/identity` (APO canonical language + operator map)
- `/catalog/axes` + `/catalog/connectors`
- `/metrics` (Prometheus)

Canonical formal spec:

- `docs/SIGMA_APOMEGA_COS_SPEC_v2.md`
- `docs/DOCKER_APO_MAPPING.md`
- `docs/DOCKER_DOCS_RAG_POLICY.md`
- `docs/DOCKER_SANDBOX_GUARDRAIL.md`
- `docs/DOCKER_RUNTIME_NODE_CONTRACT.md`
- Runtime integrity endpoints:
  - `GET /canon/identity`
  - `GET /canon/validate`
  - `GET /canon/proof`
  - `GET /canon/coverage`
  - `POST /canon/transport/verify`
  - Ontology lint: `python ops/lint_apo_check.py`
  - `POST /canon/memory/sync`

Canonical protection:

- Startup is fail-closed if canonical spec hash mismatches.
- Set `APO_CANON_SIGNING_KEY` to emit signed proof (`X-APO-Proof`) for inter-service trust.
- All JSON responses include `apo_language_id` + `apo_code_signature`.
- All HTTP responses include `X-APO-Code-Signature`.

AI-AI canonical communication:

- No NLP free text in inter-agent packet payload.
- Message must satisfy canonical equations and closure checks.
- Action vocabulary is symbol-mapped (`α1`, `α2`, `αΩ1`, `αΩ2`, `αΩ3`).

Ontology lint check:

```bash
python ops/lint_apo_check.py
```

APO CLI:

```bash
python3 app/cli/apo_cli.py --base-url http://127.0.0.1:8000 canon-validate
python3 app/cli/apo_cli.py --base-url http://127.0.0.1:8000 memory-status
```

## Why this is minimal

- No secret required for local run.
- Stripe path runs in mock-safe mode when `STRIPE_API_KEY` is empty.
- Core health/governance remains active.
- Docker is treated as local runtime substrate and official docs corpus only.
  Docker Desktop is not the APO UI, and Docker Cloud/offload requires an
  explicit Creator value gate.

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

## Email Control Plane (minimal v1)

- Endpoint: `POST /control/email/poll`
- Purpose: poll IMAP inbox, accept commands only from allowlisted senders, dispatch to `/execute`, write audit, optionally reply by SMTP.
- Configure via `.env` keys prefixed with `CONTROL_EMAIL_*` (see `.env.example`).

Example command email body:

```json
{
  "connector": "Stripe",
  "action": "retrieve_balance",
  "payload": {},
  "request_id": "email-demo-001"
}
```

Manual poll trigger:

```bash
curl -s -X POST http://localhost:8000/control/email/poll \
  -H 'Content-Type: application/json' \
  -d '{"token":"<CONTROL_EMAIL_ADMIN_TOKEN>"}' | jq .
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
