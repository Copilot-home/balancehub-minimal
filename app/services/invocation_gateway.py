from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import stripe

from app.services.asana_worker import AsanaWorker
from app.services.github_worker import GitHubWorker
from app.services.omni_service import OmniService

MESH_ROOT = Path("/Users/andy/my_too_test")
if str(MESH_ROOT) not in sys.path:
    sys.path.append(str(MESH_ROOT))

try:
    from kernel.connector_mesh import connector_context, connector_route, resolve_connector
except Exception:  # pragma: no cover - mesh fallback for isolated runtime
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _FallbackRoute:
        canonical: str
        aliases: tuple[str, ...] = ()
        layer: str = "unknown"
        transport: str = "unknown"
        status: str = "declared"
        kind: str = "connector"

    def resolve_connector(name: str) -> str:
        return name.strip()

    def connector_route(name: str) -> _FallbackRoute:
        return _FallbackRoute(canonical=resolve_connector(name))

    def connector_context(name: str, *, task_id: str | None = None) -> dict[str, str]:
        return {
            "requested_name": name,
            "canonical": resolve_connector(name),
            "layer": "unknown",
            "transport": "unknown",
            "status": "declared",
            "kind": "connector",
            "task_id": task_id or "",
        }


def _mesh_response(
    *,
    requested_connector: str,
    canonical_connector: str,
    action: str,
    payload: dict[str, Any],
    route: Any,
    mode: str,
) -> dict[str, Any]:
    return {
        "status": "declared",
        "latency_ms": 0,
        "data": {
            "mode": mode,
            "requested_connector": requested_connector,
            "connector": canonical_connector,
            "action": action,
            "payload_keys": sorted(list(payload.keys())),
            "connector_context": connector_context(requested_connector),
            "route": {
                "canonical": getattr(route, "canonical", canonical_connector),
                "layer": getattr(route, "layer", "unknown"),
                "transport": getattr(route, "transport", "unknown"),
                "status": getattr(route, "status", "declared"),
                "kind": getattr(route, "kind", "connector"),
            },
        },
    }


REGISTRY_CANONICALS = {"Registry-Service"}
LIVE_ROUTED_CANONICALS = {"Omega-Core", "BalanceHub", "Invocation-Gateway", "OmniAgent"}
DIRECT_LIVE_CONNECTORS = {
    "github",
    "github-actions",
    "github-cli",
    "github-desktop",
    "copilot",
    "gitkraken",
    "notion",
    "linear",
    "atlassian",
    "rovo",
    "asana",
    "airtable",
    "figma",
    "replit",
    "playwright",
    "tele_node",
    "bridge_agent",
    "balancehub",
    "mcp-router",
}


async def execute_action(_db, connector: str, action: str, payload: dict) -> dict:
    """
    Execute a connector action using the canonical mesh as the first resolver.

    The gateway is intentionally fail-soft:
    - live workers get routed to their dedicated handlers
    - declared connectors return a structured mesh response instead of hard failing
    """

    start = time.time()
    requested = str(payload.get("_requested_capability") or connector)
    requested_normalized = requested.strip().lower()
    route = connector_route(requested)
    canonical = route.canonical or resolve_connector(requested) or connector
    normalized = canonical.strip()

    if normalized == "Stripe":
        if action == "retrieve_balance":
            if not stripe.api_key:
                data = {
                    "object": "balance",
                    "available": [{"amount": 100000, "currency": "usd"}],
                    "pending": [],
                    "livemode": False,
                    "source": "mock",
                }
            else:
                data = stripe.Balance.retrieve()
        else:
            raise ValueError(f"Unknown action: {action}")

    elif normalized in LIVE_ROUTED_CANONICALS:
        if action in {"web_search", "agent_browser", "rag_pipeline", "analysis", "reasoning"}:
            data = await OmniService.execute_query(action, payload)
        elif action in {"status", "catalog", "connectors"}:
            data = {
                "status": "success",
                "connector": normalized,
                "route": {
                    "canonical": normalized,
                    "layer": getattr(route, "layer", "unknown"),
                    "transport": getattr(route, "transport", "unknown"),
                    "status": getattr(route, "status", "declared"),
                    "kind": getattr(route, "kind", "connector"),
                },
            }
        else:
            data = _mesh_response(
                requested_connector=requested,
                canonical_connector=normalized,
                action=action,
                payload=payload,
                route=route,
                mode="mesh-declared",
            )

    elif normalized in REGISTRY_CANONICALS or requested_normalized in DIRECT_LIVE_CONNECTORS:
        if action in {"list_repos", "sync_logic", "audit_repo"} or requested_normalized.startswith("github"):
            data = await GitHubWorker.execute(action, payload)
        elif requested_normalized == "asana" or normalized.lower() == "asana":
            data = await AsanaWorker.execute(action, payload)
        elif action in {"status", "catalog", "snapshot", "snapshots"}:
            from app.services.registry_service import latest_snapshots

            data = latest_snapshots(_db)
        elif requested_normalized in {"memory", "registry"} or normalized.lower() in {"memory", "registry-service"}:
            from app.services.apo_memory_service import memory_status, sync_apo_entity_memory

            data = memory_status(_db) if action == "status" else sync_apo_entity_memory(_db)
        else:
            data = _mesh_response(
                requested_connector=requested,
                canonical_connector=normalized,
                action=action,
                payload=payload,
                route=route,
                mode="registry-declared",
            )

    elif requested_normalized == "memory" or normalized.lower() in {"memory"}:
        from app.services.apo_memory_service import memory_status, sync_apo_entity_memory

        if action == "status":
            data = memory_status(_db)
        elif action == "sync":
            data = sync_apo_entity_memory(_db)
        else:
            raise ValueError(f"Unknown Memory action: {action}")

    elif requested_normalized == "registry" or normalized.lower() in {"registry"}:
        from app.services.registry_service import latest_snapshots

        data = latest_snapshots(_db)

    elif requested_normalized == "asana" or normalized.lower() == "asana":
        data = await AsanaWorker.execute(action, payload)

    elif requested_normalized.startswith("github") or normalized.lower() == "github":
        data = await GitHubWorker.execute(action, payload)

    elif requested_normalized == "system" or normalized.lower() == "system":
        from app.services.registry_service import latest_snapshots

        data = latest_snapshots(_db)

    else:
        try:
            data = await OmniService.execute_query(action, payload)
        except Exception:
            data = _mesh_response(
                requested_connector=requested,
                canonical_connector=normalized,
                action=action,
                payload=payload,
                route=route,
                mode="fallback-declared",
            )

    latency_ms = int((time.time() - start) * 1000)
    if isinstance(data, dict) and "status" not in data:
        data = {"status": "success", **data}
    return {"status": "ok", "latency_ms": latency_ms, "data": data}
