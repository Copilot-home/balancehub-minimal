# Launch 14-Day Execution Lock

## Commitment
- Launch window: 7 days ignition + 7 days amplification
- Mode: distribution-only
- Constraint: no new connector, no new axis, no invariant changes

## Rule 0 — Freeze
- [x] Freeze to launch mode (no feature expansion)
- [x] CI workflow in place (`.github/workflows/ci.yml`)
- [x] Branch protection enforced on `main` (runtime-integrity, secret-hygiene, smoke-contract)

## Week 1 — Gravity Ignition

### Day 1 — Docker Public
- [x] Built image tags locally: `balancehub/minimal:latest`, `balancehub/minimal:stable`
- [x] README includes one-command run: `docker run -p 8000:8000 balancehub/minimal:latest`
- [x] Standalone run verified without `.env` (sqlite default)
- [ ] Docker Hub push `latest` + `stable` (blocked: Docker Hub auth/namespace)

### Day 2 — Screenshot Pack
- [ ] `assets/launch/health-dashboard.png`
- [ ] `assets/launch/economic-weight.png`
- [ ] `assets/launch/axis-breakdown.png`

### Day 3 — Demo Video (60s)
- [ ] Record and upload unlisted
- [ ] Add link in README

### Day 4 — README Hard Polish
- [ ] TL;DR section
- [ ] Architecture diagram
- [ ] Why this exists (3 lines)
- [ ] Screenshot embeds

### Day 5 — HackerNews Launch
- [ ] Publish with fixed title
- [ ] Include problem/measure/importance/how-to-run/link

### Day 6-7 — Monitor + Respond
- [ ] Reply all launch comments
- [ ] Capture feedback summary issue

## Week 2 — Signal Amplification
- [ ] Reddit wave (`r/devops`, `r/selfhosted`, `r/microservices`, `r/opensource`)
- [ ] 3 direct deploy requests
- [ ] At least 1 external deployment proof

## KPI Targets (Day 14)
- [ ] Stars >= 10
- [ ] Forks >= 3
- [ ] Docker pulls >= 50
- [ ] External deploy >= 1

## Current blockers
1. Docker Hub push denied: `insufficient_scope` for `docker.io/balancehub/minimal`.
2. GitHub Actions blocked by billing lock, so required CI checks cannot start on PR #1.
