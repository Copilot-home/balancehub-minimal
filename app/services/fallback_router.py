import hashlib
import json
import os
import redis
from sqlalchemy.orm import Session
from app.core.models import DeferredIntent


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _payload_hash(payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def defer_intent(
    db: Session,
    *,
    connector: str,
    action_type: str,
    payload: dict,
    governance_required: bool,
) -> DeferredIntent:
    rec = DeferredIntent(
        connector=connector,
        action_type=action_type,
        payload_hash=_payload_hash(payload),
        governance_required=governance_required,
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.rpush("balancehub:deferred_queue", str(rec.id))
    except Exception:
        # Queue is best-effort; intent is persisted in Postgres.
        pass

    return rec
