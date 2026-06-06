# Docker Docs RAG Policy

Status: `LOCKED_BY_APO_VALUE_GATE`

Docker documentation may be indexed as an external technical corpus only when it
serves a specific local APO task. Indexing the full corpus without a purpose is
treated as RAG noise.

## Sources

| Source | Role |
| --- | --- |
| `https://docs.docker.com/llms-full.txt` | Full offline corpus candidate |
| Docker page markdown routes | Page-level source material |
| `https://mcp-docs.docker.com/mcp` | Structured retrieval endpoint |

## Admission Rule

```text
Index(DockerDocs) is allowed iff:
  CreatorValueSignal = true
  and Axis in {AXIS_4, AXIS_5, AXIS_6, AXIS_8}
  and Purpose is explicit
  and TTL is set
```

## Required Metadata Per Chunk

Every indexed Docker docs chunk must carry:

- `source_url`
- `source_kind`
- `docker_section`
- `apo_axis`
- `purpose`
- `ttl`
- `indexed_at`
- `hash`
- `creator_value_signal`

## Retrieval Rule

Docker docs retrieval must answer only the scoped task. It must not replace APO
Canon or infer ownership from Docker brand language.

## Metrics

- `docker_docs_index_coverage`
- `docker_docs_chunk_count`
- `docker_docs_stale_chunk_count`
- `docker_docs_retrieval_hit_rate`
- `docker_docs_value_accepted_count`
- `docker_docs_value_rejected_count`

