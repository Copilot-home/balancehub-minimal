# Docker Runtime Node Contract

Status: `RUNTIME_SUBSTRATE_ONLY`

This contract defines how BalanceHub/APO may use Docker as a local runtime node.

## Node Identity

```text
node_id: docker-runtime
node_kind: runtime_substrate
omega_role: execution_projection
owner: Creator / Andy
tool_owner: false
```

Docker can run containers and provide catalog/corpus access. It cannot own
Canon, identity, proof, budget, or redistribution.

## Allowed Responsibilities

- run local containers for explicit tasks
- host Compose stacks for local proof
- expose Docker MCP catalog information for retrieval
- support security/image checks through Scout or hardened-image metadata
- provide reproducible local execution receipts

## Disallowed Responsibilities

- define APO ontology
- decide ownership
- create hidden branches
- merge artifacts into lineage
- initiate paid cloud/offload
- become the primary system UI
- persist secrets as project artifacts

## Health Probe Shape

```json
{
  "node_id": "docker-runtime",
  "axis": ["AXIS_5", "AXIS_6"],
  "engine_available": true,
  "desktop_available": true,
  "mcp_catalog_available": true,
  "hidden_branch_count": 0,
  "cost_event_count": 0,
  "last_probe_at": "ISO-8601"
}
```

## Lineage Return

```text
artifact -> hash -> receipt -> review -> lineage_decision
```

