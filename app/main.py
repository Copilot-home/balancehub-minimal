import asyncio
import os
import stripe
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import generate_latest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, init_db, SessionLocal
from app.core.models import ConnectorState
from app.core.metrics import (
    BREAKER_STATE,
    DRIFT_FREQUENCY,
    FALLBACK_USAGE,
    QUARANTINE_DURATION_SECONDS,
    REQUEST_COUNT,
    STABILITY_SCORE,
    FAILURE_RATE,
)
from app.services.audit_logger import write_audit
from app.services.fallback_router import defer_intent
from app.services.failure_engine import classify
from app.services.invocation_gateway import execute_action
from app.services.probe_worker import run_probe_cycle
from app.services.registry_service import capture_snapshot, latest_snapshots, snapshot_diff
from app.services.gssi_service import compute_system_health
from app.services.map_repos_service import (
    bootstrap_catalogs,
    list_axis_catalog,
    list_connector_catalog,
    sync_connector_state_with_catalog,
)

app = FastAPI(title="BalanceHub v2 Runtime Prototype")

stripe.api_key = os.getenv("STRIPE_API_KEY")


def _breaker_value(breaker_state: str) -> float:
    if breaker_state == "OPEN":
        return 1.0
    if breaker_state == "HALF_OPEN":
        return 0.5
    return 0.0


def _require_connector_state(db: Session, connector: str) -> ConnectorState:
    state = db.execute(select(ConnectorState).where(ConnectorState.name == connector)).scalar_one_or_none()
    if state is None:
        raise HTTPException(status_code=404, detail=f"Connector not registered: {connector}")
    return state


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    db = SessionLocal()
    try:
        bootstrap_catalogs(db)
        sync_connector_state_with_catalog(db)

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
    return {"status": "running", "service": "BalanceHub v2"}


@app.post("/execute")
def execute(payload: dict, db: Session = Depends(get_db)) -> dict:
    connector = payload.get("connector")
    action = payload.get("action")
    request_id = payload.get("request_id", "req-unknown")
    data = payload.get("payload", {})

    if not connector or not action:
        raise HTTPException(status_code=400, detail="connector and action are required")

    state = _require_connector_state(db, connector)

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
        return {
            "status": "deferred",
            "reason": "breaker_open",
            "deferred_intent_id": str(deferred.id),
        }

    try:
        out = execute_action(db, connector, action, data)
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
        return out

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

        return {
            "status": outcome,
            "error_type": classified.error_type,
            "severity": classified.severity,
            "retry_policy": classified.retry_policy,
            "breaker_state": state.breaker_state,
            "state": state.state,
            "stability_score": state.stability_score,
        }


@app.get("/registry/snapshot")
def registry_snapshot(db: Session = Depends(get_db)) -> dict:
    snaps = latest_snapshots(db)
    return {
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
    }


@app.get("/registry/diff")
def registry_diff(db: Session = Depends(get_db)) -> dict:
    return {"items": snapshot_diff(db)}


@app.post("/registry/snapshot/{connector}")
def force_capture_snapshot(connector: str, db: Session = Depends(get_db)) -> dict:
    snap = capture_snapshot(db, connector)
    return {
        "connector": snap.connector_name,
        "snapshot_hash": snap.snapshot_hash,
        "created_at": snap.created_at.isoformat(),
    }


@app.get("/connectors/{connector}/state")
def connector_state(connector: str, db: Session = Depends(get_db)) -> dict:
    state = _require_connector_state(db, connector)
    return {
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
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain")


@app.get("/system/health")
def system_health(db: Session = Depends(get_db)) -> dict:
    return compute_system_health(db)


@app.get("/catalog/axes")
def axis_catalog(db: Session = Depends(get_db)) -> dict:
    rows = list_axis_catalog(db)
    return {
        "items": [
            {
                "axis_id": a.axis_id,
                "axis_name": a.axis_name,
                "canonical_role": a.canonical_role,
                "min_required_nodes": a.min_required_nodes,
            }
            for a in rows
        ]
    }


@app.get("/catalog/connectors")
def connector_catalog(db: Session = Depends(get_db)) -> dict:
    rows = list_connector_catalog(db)
    return {
        "items": [
            {
                "name": c.name,
                "assigned_axis": c.assigned_axis,
                "class": c.connector_class,
                "economic_weight_base": c.economic_weight_base,
                "dependency_degree": c.dependency_degree,
                "node_degree": c.node_degree,
            }
            for c in rows
        ]
    }


@app.post("/operators/map_repos")
def map_repos_operator(db: Session = Depends(get_db)) -> dict:
    bootstrap_catalogs(db)
    sync_connector_state_with_catalog(db)
    return {"status": "ok", "operator": "MAP_REPOS"}
