import stripe
import time
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.models import ConnectorState
from app.core.metrics import STABILITY_SCORE, BREAKER_STATE, LATENCY_HISTOGRAM, FAILURE_RATE
from app.services.failure_engine import classify


def _breaker_value(breaker_state: str) -> float:
    if breaker_state == "OPEN":
        return 1.0
    if breaker_state == "HALF_OPEN":
        return 0.5
    return 0.0


def run_probe_cycle(db: Session, connector_name: str = "Stripe") -> None:
    state = db.execute(
        select(ConnectorState).where(ConnectorState.name == connector_name)
    ).scalar_one()

    start = time.time()
    try:
        if not stripe.api_key:
            # Minimal/public-safe mode: probe succeeds with synthetic latency.
            latency_ms = 5
        else:
            stripe.Balance.retrieve()
            latency_ms = int((time.time() - start) * 1000)
        LATENCY_HISTOGRAM.labels(connector=connector_name).observe(latency_ms)

        state.last_latency_ms = latency_ms
        state.failure_count = 0
        state.healthy_cycles += 1
        state.stability_score = min(100, state.stability_score + 4)

        if state.breaker_state == "OPEN":
            state.breaker_state = "HALF_OPEN"
            state.state = "RECOVERY"
            state.healthy_cycles = 1
        elif state.breaker_state == "HALF_OPEN" and state.healthy_cycles >= 3:
            state.breaker_state = "CLOSED"
            state.state = "ACTIVE"

        if state.state in {"DEGRADED", "RECOVERY"} and state.stability_score >= 80:
            state.state = "ACTIVE"

        state.last_error = None

    except Exception as exc:
        classified = classify(exc)
        FAILURE_RATE.labels(connector=connector_name, error_type=classified.error_type).inc()

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

    STABILITY_SCORE.labels(connector=connector_name).set(state.stability_score)
    BREAKER_STATE.labels(connector=connector_name).set(_breaker_value(state.breaker_state))

    db.add(state)
    db.commit()
