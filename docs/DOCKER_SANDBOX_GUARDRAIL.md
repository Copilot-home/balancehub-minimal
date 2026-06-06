# Docker Sandbox Guardrail

Status: `SANDBOX_REQUIRES_OMEGA_GATE`

Docker sandboxes are allowed only as bounded execution spaces. They must never
become hidden autonomous branches.

## Admission Gate

Docker sandbox execution requires all of:

- explicit task purpose
- axis assignment
- no production credential exposure
- bounded filesystem scope
- network scope declared
- output path declared
- audit log enabled
- no auto-merge

## Sandbox Contract

```text
DockerSandbox =>
  Isolated
  and Logged
  and Bounded
  and NoAutoMerge
  and NoSecretPersistence
  and OmegaReturnPath
```

## Required Receipt

Each sandbox run must emit a receipt with:

- `run_id`
- `actor`
- `axis`
- `purpose`
- `image`
- `command`
- `input_hashes`
- `output_paths`
- `network_policy`
- `started_at`
- `finished_at`
- `exit_code`
- `lineage_decision`

If any guardrail is missing:

```text
verdict = SANDBOX_BLOCKED_BY_POLICY
```

