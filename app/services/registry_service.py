import hashlib
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.models import RegistrySnapshot


STATIC_REGISTRY = {
    "Stripe": {
        "endpoints": ["/v1/balance", "/v1/customers", "/v1/subscriptions"],
        "scopes": ["balance:read", "customers:write", "subscriptions:write"],
        "link_id": "stripe-core-v1",
    }
}


def _compute_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def capture_snapshot(db: Session, connector: str) -> RegistrySnapshot:
    source = STATIC_REGISTRY.get(connector)
    if source is None:
        raise ValueError(f"Unknown connector: {connector}")

    digest = _compute_hash(source)
    snap = RegistrySnapshot(
        connector_name=connector,
        snapshot_hash=digest,
        endpoint_list=source["endpoints"],
        scope_list=source["scopes"],
        link_id=source["link_id"],
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def latest_snapshots(db: Session):
    stmt = (
        select(RegistrySnapshot)
        .order_by(RegistrySnapshot.connector_name, RegistrySnapshot.created_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    latest = {}
    for row in rows:
        latest.setdefault(row.connector_name, row)
    return list(latest.values())


def snapshot_diff(db: Session):
    rows = (
        db.execute(
            select(RegistrySnapshot).order_by(
                RegistrySnapshot.connector_name,
                RegistrySnapshot.created_at.desc(),
            )
        )
        .scalars()
        .all()
    )

    grouped = {}
    for r in rows:
        grouped.setdefault(r.connector_name, []).append(r)

    out = []
    for connector, items in grouped.items():
        current = items[0]
        previous = items[1] if len(items) > 1 else None
        changed = previous is None or current.snapshot_hash != previous.snapshot_hash
        out.append(
            {
                "connector": connector,
                "changed": changed,
                "current_hash": current.snapshot_hash,
                "previous_hash": previous.snapshot_hash if previous else None,
                "current_created_at": current.created_at.isoformat(),
            }
        )
    return out
