import asyncio
import os
import sys
import stripe
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.db import get_db, init_db, SessionLocal
from app.core.models import ConnectorCatalog, ConnectorState
from app.core.metrics import (
    BREAKER_STATE,
    DRIFT_FREQUENCY,
    FALLBACK_USAGE,
    QUARANTINE_DURATION_SECONDS,
    REQUEST_COUNT,
    STABILITY_SCORE,
    FAILURE_RATE,
)
from app.core.apo_canon import (
    INVALID_SYMBOL,
    canonical_identity_snapshot,
    canonical_proof_signature,
    has_operator_binding,
    operator_meta_for,
    startup_policy_guard,
    validate_canonical_integrity,
)
from app.core.canon_ai2ai import ACTION_TO_SYMBOL, decode_packet, encode_packet, validate_packet
from app.services.audit_logger import write_audit
from app.services.fallback_router import defer_intent
from app.services.failure_engine import classify
from app.services.invocation_gateway import execute_action
from app.services.probe_worker import run_probe_cycle
from app.services.registry_service import capture_snapshot, latest_snapshots, snapshot_diff
from app.services.gssi_service import compute_system_health
from app.services.economic_weight_service import compute_economic_weight
from app.services.map_repos_service import (
    bootstrap_catalogs,
    list_axis_catalog,
    list_connector_catalog_with_apo,
    sync_connector_state_with_catalog,
)
from app.services.email_control_service import poll_email_and_dispatch
from app.services.apo_memory_service import sync_apo_entity_memory, memory_status

MESH_ROOT = Path("/Users/andy/my_too_test")
if str(MESH_ROOT) not in sys.path:
    sys.path.append(str(MESH_ROOT))

try:
    from kernel.connector_mesh import connector_route
except Exception:  # pragma: no cover - runtime fallback when mesh repo is absent
    connector_route = None

app = FastAPI(title="BalanceHub v2 Runtime Prototype")

stripe.api_key = os.getenv("STRIPE_API_KEY")


def _with_apo(payload: dict) -> dict:
    identity = canonical_identity_snapshot()
    return {
        "apo_language_id": identity["language_id"],
        "apo_code_signature": identity["code_signature"],
        **payload,
    }


def _validate_transport_headers(request: Request) -> tuple[bool, str | None]:
    identity = canonical_identity_snapshot()
    proof_expected = canonical_proof_signature()
    if not proof_expected:
        return False, "missing_signing_key"

    required = {
        "X-APO-Language-ID": identity["language_id"],
        "X-APO-Code-Signature": identity["code_signature"],
        "X-APO-Spec-Version": identity["spec_version"],
        "X-APO-Spec-SHA256": identity["spec_sha256"],
        "X-APO-Watermark": identity["ontology_watermark"],
        "X-APO-Proof": proof_expected,
    }
    for key, expected in required.items():
        observed = request.headers.get(key)
        if not observed:
            return False, f"missing_header:{key}"
        if observed != expected:
            return False, f"invalid_header:{key}"
    return True, None


@app.middleware("http")
async def apo_identity_headers(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        # Allow internal sync/poll paths to bypass identity check for CLI/Simulation convenience.
        exempt_paths = {"/canon/memory/sync", "/control/email/poll", "/execute"}
        if request.url.path not in exempt_paths:
            valid, reason = _validate_transport_headers(request)
            if not valid:
                body = _with_apo(
                    {
                        "execution_result": "BLOCKED",
                        "reason": reason,
                        "delta_symbol": INVALID_SYMBOL,
                    }
                )
                return JSONResponse(status_code=403, content=body)

    response = await call_next(request)
    identity = canonical_identity_snapshot()
    
    # HTTP headers must be latin-1 compatible.
    def safe_h(v): return str(v).encode("ascii", "ignore").decode("ascii")

    response.headers["X-APO-Language-ID"] = safe_h(identity["language_id"])
    response.headers["X-APO-Code-Signature"] = safe_h(identity["code_signature"])
    response.headers["X-APO-Spec-Version"] = safe_h(identity["spec_version"])
    response.headers["X-APO-Spec-SHA256"] = safe_h(identity["spec_sha256"])
    response.headers["X-APO-Watermark"] = safe_h(identity["ontology_watermark"])
    proof = canonical_proof_signature()
    if proof:
        response.headers["X-APO-Proof"] = safe_h(proof)
    return response


def _breaker_value(breaker_state: str) -> float:
    if breaker_state == "OPEN":
        return 1.0
    if breaker_state == "HALF_OPEN":
        return 0.5
    return 0.0


def _require_connector_state(db: Session, connector: str) -> ConnectorState:
    state = db.execute(
        select(ConnectorState).where(func.lower(ConnectorState.name) == connector.lower())
    ).scalar_one_or_none()
    if state is None:
        raise HTTPException(status_code=404, detail=f"Connector not registered: {connector}")
    return state


def _lookup_connector_state(db: Session, connector: str) -> ConnectorState | None:
    return db.execute(
        select(ConnectorState).where(func.lower(ConnectorState.name) == connector.lower())
    ).scalar_one_or_none()


@app.on_event("startup")
def startup_event() -> None:
    guard = startup_policy_guard()
    if guard["block_startup"]:
        raise RuntimeError(
            f"Canonical integrity check failed: {guard['integrity']['reason']} "
            f"(expected={guard['integrity']['expected_spec_sha256']} observed={guard['integrity']['observed_spec_sha256']})"
        )

    init_db()
    db = SessionLocal()
    try:
        bootstrap_catalogs(db)
        sync_connector_state_with_catalog(db)
        sync_apo_entity_memory(db)

        # Public-safe minimal mode: keep Stripe path usable without secrets.
        if not stripe.api_key:
            stripe_state = db.execute(
                select(ConnectorState).where(ConnectorState.name == "Stripe")
            ).scalar_one_or_none()
            if stripe_state is not None:
                stripe_state.state = "ACTIVE"
                stripe_state.breaker_state = "CLOSED"
                stripe_state.stability_score = 100
                stripe_state.failure_count = 0
                stripe_state.healthy_cycles = 0
                stripe_state.last_error = None
                db.add(stripe_state)
                db.commit()

        # Seed one snapshot on first boot for /registry endpoints.
        if not latest_snapshots(db):
            capture_snapshot(db, "Stripe")
    finally:
        db.close()

    asyncio.create_task(_probe_loop())


async def _probe_loop() -> None:
    while True:
        await asyncio.sleep(30)
        db = SessionLocal()
        try:
            run_probe_cycle(db, connector_name="Stripe")
            state = _require_connector_state(db, "Stripe")
            DRIFT_FREQUENCY.labels(connector="Stripe").set(float(state.drift_count))
            QUARANTINE_DURATION_SECONDS.labels(connector="Stripe").set(0.0 if state.state != "QUARANTINED" else 30.0)
        finally:
            db.close()


@app.get("/")
def root() -> dict:
    return _with_apo({"status": "running", "service": "BalanceHub v2"})


@app.post("/execute")
async def execute(payload: dict, db: Session = Depends(get_db)) -> dict:
    connector = payload.get("connector")
    action = payload.get("action")
    request_id = payload.get("request_id", "req-unknown")
    data = payload.get("payload", {})

    if not connector or not action:
        raise HTTPException(status_code=400, detail="connector and action are required")

    route = connector_route(connector) if connector_route is not None else None
    canonical_connector = getattr(route, "canonical", connector)
    state = _lookup_connector_state(db, canonical_connector)

    if state is None:
        out = await execute_action(db, connector, action, data)
        return _with_apo(
            {
                **out,
                "requested_connector": connector,
                "canonical_connector": canonical_connector,
                "connector_route": {
                    "canonical": getattr(route, "canonical", canonical_connector),
                    "layer": getattr(route, "layer", "unknown"),
                    "transport": getattr(route, "transport", "unknown"),
                    "status": getattr(route, "status", "declared"),
                    "kind": getattr(route, "kind", "connector"),
                },
                "mesh_mode": "fail-soft",
            }
        )

    if connector == "OmniAgent":
        packet = payload.get("canon_packet")
        if not isinstance(packet, dict):
            raise HTTPException(status_code=400, detail="canon_packet is required for OmniAgent")
        validation = validate_packet(packet)
        if not validation["valid"]:
            return _with_apo(
                {
                    "execution_result": "BLOCKED",
                    "reason": "invalid_canon_packet",
                    "delta_symbol": INVALID_SYMBOL,
                    "details": validation,
                }
            )

        decoded = decode_packet(packet)
        expected_symbol = ACTION_TO_SYMBOL.get(action)
        if decoded["action"] != action or packet.get("action_symbol") != expected_symbol:
            return _with_apo(
                {
                    "execution_result": "BLOCKED",
                    "reason": "action_symbol_mismatch",
                    "delta_symbol": INVALID_SYMBOL,
                    "details": {"expected_action_symbol": expected_symbol, "packet_action_symbol": packet.get("action_symbol")},
                }
            )
        if decoded["gate_result"] != "allowed":
            return _with_apo(
                {
                    "execution_result": "BLOCKED",
                    "reason": "gate_denied",
                    "delta_symbol": INVALID_SYMBOL,
                    "details": {"packet_hash": decoded["packet_hash"]},
                }
            )

    # Circuit-breaker hard gate.
    if state.breaker_state == "OPEN":
        deferred = defer_intent(
            db,
            connector=connector,
            action_type=action,
            payload=data,
            governance_required=state.state == "QUARANTINED",
        )
        REQUEST_COUNT.labels(connector=connector, status="deferred").inc()
        FALLBACK_USAGE.labels(connector=connector, reason="breaker_open").inc()
        write_audit(
            db,
            connector=connector,
            request_id=request_id,
            validation_result="passed",
            decision="fallback",
            outcome="deferred",
            fallback_used=True,
            details={"deferred_intent_id": str(deferred.id)},
        )
        return _with_apo({
            "status": "deferred",
            "reason": "breaker_open",
            "deferred_intent_id": str(deferred.id),
        })

    try:
        out = await execute_action(db, connector, action, data)
        state.failure_count = 0
        state.healthy_cycles = min(state.healthy_cycles + 1, 3)
        state.stability_score = min(100, state.stability_score + 3)

        if state.breaker_state == "HALF_OPEN" and state.healthy_cycles >= 3:
            state.breaker_state = "CLOSED"
            state.state = "ACTIVE"

        STABILITY_SCORE.labels(connector=connector).set(state.stability_score)
        BREAKER_STATE.labels(connector=connector).set(_breaker_value(state.breaker_state))
        REQUEST_COUNT.labels(connector=connector, status="success").inc()

        write_audit(
            db,
            connector=connector,
            request_id=request_id,
            validation_result="passed",
            decision="execute",
            outcome="success",
            fallback_used=False,
            details={"action": action},
        )

        db.add(state)
        db.commit()
        return _with_apo(out)

    except Exception as exc:
        classified = classify(exc)
        state.failure_count += 1
        state.healthy_cycles = 0
        state.stability_score = max(0, state.stability_score - classified.penalty)
        state.last_error = {
            "error_type": classified.error_type,
            "severity": classified.severity,
            "message": str(exc),
        }

        if state.failure_count >= 3:
            state.breaker_state = "OPEN"
            state.state = "QUARANTINED" if state.stability_score < 40 else "DEGRADED"

        STABILITY_SCORE.labels(connector=connector).set(state.stability_score)
        BREAKER_STATE.labels(connector=connector).set(_breaker_value(state.breaker_state))
        REQUEST_COUNT.labels(connector=connector, status="failure").inc()
        FAILURE_RATE.labels(connector=connector, error_type=classified.error_type).inc()

        fallback_used = state.breaker_state == "OPEN"
        decision = "fallback" if fallback_used else "retryable"

        if fallback_used:
            deferred = defer_intent(
                db,
                connector=connector,
                action_type=action,
                payload=data,
                governance_required=state.state == "QUARANTINED",
            )
            FALLBACK_USAGE.labels(connector=connector, reason="open_after_failure").inc()
            outcome = "deferred"
            details = {
                "deferred_intent_id": str(deferred.id),
                "classification": classified.error_type,
            }
        else:
            outcome = "error"
            details = {"classification": classified.error_type}

        write_audit(
            db,
            connector=connector,
            request_id=request_id,
            validation_result="passed",
            decision=decision,
            outcome=outcome,
            fallback_used=fallback_used,
            details=details,
        )

        db.add(state)
        db.commit()

        return _with_apo({
            "status": outcome,
            "error_type": classified.error_type,
            "severity": classified.severity,
            "retry_policy": classified.retry_policy,
            "breaker_state": state.breaker_state,
            "state": state.state,
            "stability_score": state.stability_score,
        })


@app.get("/registry/snapshot")
def registry_snapshot(db: Session = Depends(get_db)) -> dict:
    snaps = latest_snapshots(db)
    return _with_apo({
        "items": [
            {
                "connector": s.connector_name,
                "snapshot_hash": s.snapshot_hash,
                "endpoint_list": s.endpoint_list,
                "scope_list": s.scope_list,
                "link_id": s.link_id,
                "created_at": s.created_at.isoformat(),
            }
            for s in snaps
        ]
    })


@app.get("/registry/diff")
def registry_diff(db: Session = Depends(get_db)) -> dict:
    return _with_apo({"items": snapshot_diff(db)})


@app.post("/registry/snapshot/{connector}")
def force_capture_snapshot(connector: str, db: Session = Depends(get_db)) -> dict:
    snap = capture_snapshot(db, connector)
    return _with_apo({
        "connector": snap.connector_name,
        "snapshot_hash": snap.snapshot_hash,
        "created_at": snap.created_at.isoformat(),
    })


@app.get("/connectors/{connector}/state")
def connector_state(connector: str, db: Session = Depends(get_db)) -> dict:
    state = _require_connector_state(db, connector)
    return _with_apo({
        "apo_operator": operator_meta_for(state.name),
        "name": state.name,
        "axis_name": state.axis_name,
        "connector_class": state.connector_class,
        "economic_impact_weight": state.economic_impact_weight,
        "dependency_degree": state.dependency_degree,
        "node_degree": state.node_degree,
        "state": state.state,
        "breaker_state": state.breaker_state,
        "stability_score": state.stability_score,
        "last_latency_ms": state.last_latency_ms,
        "failure_count": state.failure_count,
        "drift_count": state.drift_count,
        "last_error": state.last_error,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    })


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain")


@app.get("/system/health")
def system_health(db: Session = Depends(get_db)) -> dict:
    return _with_apo(compute_system_health(db))


@app.get("/system/economic-weight")
def system_economic_weight(db: Session = Depends(get_db)) -> dict:
    return _with_apo(compute_economic_weight(db))


@app.get("/catalog/axes")
def axis_catalog(db: Session = Depends(get_db)) -> dict:
    rows = list_axis_catalog(db)
    return _with_apo({
        "items": [
            {
                "axis_id": a.axis_id,
                "axis_name": a.axis_name,
                "canonical_role": a.canonical_role,
                "min_required_nodes": a.min_required_nodes,
            }
            for a in rows
        ]
    })


@app.get("/catalog/connectors")
def connector_catalog(db: Session = Depends(get_db)) -> dict:
    rows = list_connector_catalog_with_apo(db)
    return _with_apo({"items": rows})


@app.post("/operators/map_repos")
def map_repos_operator(db: Session = Depends(get_db)) -> dict:
    bootstrap_catalogs(db)
    sync_connector_state_with_catalog(db)
    sync_apo_entity_memory(db)
    return _with_apo({"status": "ok", "operator": "MAP_REPOS"})


@app.get("/canon/identity")
def canon_identity() -> dict:
    return canonical_identity_snapshot()


@app.get("/canon/validate")
def canon_validate() -> dict:
    identity = canonical_identity_snapshot()
    integrity = validate_canonical_integrity()
    return _with_apo({
        "spec_version": identity["spec_version"],
        "integrity": integrity,
    })


@app.get("/canon/proof")
def canon_proof() -> dict:
    identity = canonical_identity_snapshot()
    integrity = validate_canonical_integrity()
    return _with_apo({
        "spec_version": identity["spec_version"],
        "spec_sha256": identity["spec_sha256"],
        "ontology_watermark": identity["ontology_watermark"],
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "integrity": integrity,
        "proof": canonical_proof_signature(),
    })


@app.post("/canon/ai2ai/encode")
def canon_ai2ai_encode(payload: dict) -> dict:
    packet = encode_packet(
        sender_entity=str(payload.get("sender_entity", "")),
        receiver_entity=str(payload.get("receiver_entity", "")),
        action=str(payload.get("action", "")),
        payload_math=payload.get("payload_math", {}) if isinstance(payload.get("payload_math", {}), dict) else {},
        state_in=str(payload.get("state_in", "000000")),
        state_out=str(payload.get("state_out", "000000")),
        gate_result=str(payload.get("gate_result", "allowed")),
        delta_symbol=payload.get("delta_symbol"),
    )
    return _with_apo({"packet": packet})


@app.post("/canon/ai2ai/validate")
def canon_ai2ai_validate(payload: dict) -> dict:
    packet = payload.get("packet", payload)
    if not isinstance(packet, dict):
        raise HTTPException(status_code=400, detail="packet must be an object")
    return _with_apo({"validation": validate_packet(packet)})


@app.post("/canon/ai2ai/decode")
def canon_ai2ai_decode(payload: dict) -> dict:
    packet = payload.get("packet", payload)
    if not isinstance(packet, dict):
        raise HTTPException(status_code=400, detail="packet must be an object")
    try:
        decoded = decode_packet(packet)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _with_apo({"decoded": decoded})


@app.post("/canon/transport/verify")
def canon_transport_verify(request: Request) -> dict:
    valid, reason = _validate_transport_headers(request)
    return _with_apo(
        {
            "valid": valid,
            "reason": reason,
            "delta_symbol": "δ" if valid else INVALID_SYMBOL,
        }
    )


@app.get("/canon/coverage")
def canon_coverage(db: Session = Depends(get_db)) -> dict:
    catalog_names = [r.name for r in db.execute(select(ConnectorCatalog)).scalars().all()]
    state_names = [r.name for r in db.execute(select(ConnectorState)).scalars().all()]
    service_names = ["EmailControl"]
    all_names = sorted(set(catalog_names + state_names + service_names))

    mapped = [name for name in all_names if has_operator_binding(name)]
    unmapped = [name for name in all_names if not has_operator_binding(name)]

    return _with_apo(
        {
            "total_entities": len(all_names),
            "mapped_entities": len(mapped),
            "unmapped_entities": len(unmapped),
            "coverage_ratio": round((len(mapped) / len(all_names)) if all_names else 1.0, 4),
            "entities": [
                {
                    "name": name,
                    "mapped": has_operator_binding(name),
                    "apo_operator": operator_meta_for(name) if has_operator_binding(name) else None,
                }
                for name in all_names
            ],
            "unmapped_list": unmapped,
        }
    )


@app.post("/rovo/execute")
async def rovo_execute(request: Request, db: Session = Depends(get_db)) -> dict:
    # 🛡️ Security Check: X-OMEGA-SIGNATURE
    signature = request.headers.get("X-OMEGA-SIGNATURE")
    if signature != "alpha_prime_omega":
         raise HTTPException(status_code=403, detail="Invalid Ω Signature")

    payload = await request.json()
    issue = payload.get("issue", {})
    issue_key = issue.get("key", "UNKNOWN")
    summary = issue.get("fields", {}).get("summary", "NO SUMMARY")

    # 🔗 Integrate with OmniService or Trigger Orchestrator
    # For now, log the event and return a success symbol δ
    write_audit(
        db,
        connector="rovo",
        request_id=f"jira-{issue_key}",
        validation_result="passed",
        decision="execute",
        outcome="success",
        fallback_used=False,
        details={"issue_key": issue_key, "summary": summary},
    )

    return _with_apo({
        "status": "triggered",
        "symbol": "δ",
        "issue_key": issue_key,
        "message": f"Ω System received JIRA {issue_key}: {summary}"
    })


@app.post("/canon/memory/sync")
def canon_memory_sync(db: Session = Depends(get_db)) -> dict:
    return _with_apo(sync_apo_entity_memory(db))


@app.get("/canon/memory/status")
def canon_memory_status(db: Session = Depends(get_db)) -> dict:
    return _with_apo(memory_status(db))


@app.post("/control/email/poll")
async def control_email_poll(payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    token_required = os.getenv("CONTROL_EMAIL_ADMIN_TOKEN", "").strip()
    provided = ""
    if payload and isinstance(payload, dict):
        provided = str(payload.get("token", "")).strip()
    if token_required and provided != token_required:
        raise HTTPException(status_code=403, detail="invalid control token")

    return _with_apo(await poll_email_and_dispatch(db))
