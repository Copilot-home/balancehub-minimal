# Docker APO Mapping

Status: `DOCKER_APO_MAPPING_LOCKED`

Docker is mapped into APO-NET as runtime substrate and official technical corpus.
It is not core identity, not the residence ontology, and not a separate APO UI.

## Canon

```text
Omega = identity + ownership + canon + proof + budget + redistribution
Docker = runtime substrate + official docs corpus
Docker Desktop != APO UI
Docker Cloud/Offload != Residence(Sigma_APOmega)
```

## Entity Map

| Entity | Symbol | APO role |
| --- | --- | --- |
| Docker official docs | `DOC_DOCKER` | External technical corpus |
| Docker MCP docs endpoint | `MCP_DOCKER` | Structured retrieval endpoint |
| Docker offline corpus | `CORPUS_DOCKER` | Offline RAG/document memory |
| Docker local runtime | `LAMBDA_DOCKER` | Container/runtime substrate |
| Execution axis | `AXIS_5` | Tool Ops and container execution |
| Security axis | `AXIS_6` | Sandbox, image policy, hardening |
| Data axis | `AXIS_4` | Indexed documentation memory |
| Governance axis | `AXIS_8` | Account, policy, IAM, subscription rules |

## Docker Surface Mapping

| Docker surface | APO axis | Role |
| --- | ---: | --- |
| Docker Engine | `AXIS_5` | Container runtime |
| Docker Compose | `AXIS_5` | Multi-container orchestration |
| Docker Desktop | `AXIS_5` / auxiliary UI | Tool command center, not APO UI |
| Docker Sandboxes | `AXIS_6` | Isolated agent execution |
| MCP Catalog/Toolkit | `AXIS_5` / `AXIS_8` | Connector and tool endpoint governance |
| Docker Model Runner | `AXIS_5` | Local model serving candidate |
| Docker Agent | `AXIS_5` | Agent runtime candidate |
| Docker Scout | `AXIS_6` | Image policy and evaluation |
| Hardened Images | `AXIS_6` | Secure base image lane |
| Build Cloud/Offload | `AXIS_7` / `AXIS_5` | Cost-gated external acceleration |
| `llms-full.txt` | `AXIS_4` | Offline docs memory and RAG corpus |

## Invariants

- Docker is a tool substrate, not an owner.
- Docker may host execution, but it does not own lineage.
- Docker docs may inform local agents, but they do not rewrite Canon.
- Docker Desktop is a projection/command UI only.
- Docker cloud/offload requires explicit Creator value approval before use.
- Docker sandbox output must be isolated, logged, bounded, and blocked from auto-merge.

## Valid Flow

```text
CreatorValueSignal
-> Omega policy gate
-> axis assignment
-> Docker runtime/corpus usage
-> artifact/proof/log
-> Omega ledger
-> redistribution or stop
```

