from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.apo_canon import CODE_SIGNATURE, LANGUAGE_ID, ONTOLOGICAL_ROOT, operator_meta_for
from app.core.models import ApoEntityMemory, ConnectorCatalog, ConnectorState


def _upsert_entity_memory(
    db: Session,
    *,
    entity_name: str,
    entity_type: str,
    memory_ref: str,
    metadata_json: dict | None = None,
) -> None:
    row = db.execute(
        select(ApoEntityMemory).where(ApoEntityMemory.entity_name == entity_name)
    ).scalar_one_or_none()
    op = operator_meta_for(entity_name)
    if row is None:
        row = ApoEntityMemory(
            entity_name=entity_name,
            entity_type=entity_type,
            apo_language_id=LANGUAGE_ID,
            apo_code_signature=CODE_SIGNATURE,
            operator_id=op["id"],
            origin=ONTOLOGICAL_ROOT,
            memory_ref=memory_ref,
            status="ACTIVE",
            metadata_json=metadata_json or {},
        )
    else:
        row.entity_type = entity_type
        row.apo_language_id = LANGUAGE_ID
        row.apo_code_signature = CODE_SIGNATURE
        row.operator_id = op["id"]
        row.origin = ONTOLOGICAL_ROOT
        row.memory_ref = memory_ref
        row.status = "ACTIVE"
        row.metadata_json = metadata_json or row.metadata_json
    db.add(row)


def sync_apo_entity_memory(db: Session) -> dict:
    catalog_rows = db.execute(select(ConnectorCatalog)).scalars().all()
    state_rows = db.execute(select(ConnectorState)).scalars().all()

    for c in catalog_rows:
        _upsert_entity_memory(
            db,
            entity_name=c.name,
            entity_type="connector",
            memory_ref=f"catalog://{c.name}",
            metadata_json={
                "axis": c.assigned_axis,
                "class": c.connector_class,
            },
        )

    for s in state_rows:
        _upsert_entity_memory(
            db,
            entity_name=s.name,
            entity_type="runtime",
            memory_ref=f"state://{s.name}",
            metadata_json={
                "state": s.state,
                "breaker_state": s.breaker_state,
                "stability_score": s.stability_score,
            },
        )

    # Non-catalog control entities must also have memory roots.
    _upsert_entity_memory(
        db,
        entity_name="EmailControl",
        entity_type="control-plane",
        memory_ref="control://email",
        metadata_json={"channel": "imap/smtp"},
    )

    db.commit()

    total = db.execute(select(ApoEntityMemory)).scalars().all()
    orphaned = [
        r.entity_name
        for r in total
        if r.apo_language_id != LANGUAGE_ID or r.apo_code_signature != CODE_SIGNATURE or r.origin != ONTOLOGICAL_ROOT
    ]
    return {
        "synced": len(total),
        "orphaned": orphaned,
    }


def memory_status(db: Session) -> dict:
    rows = db.execute(select(ApoEntityMemory).order_by(ApoEntityMemory.entity_name)).scalars().all()
    orphaned = [
        r.entity_name
        for r in rows
        if r.apo_language_id != LANGUAGE_ID or r.apo_code_signature != CODE_SIGNATURE or r.origin != ONTOLOGICAL_ROOT
    ]
    return {
        "total_entities": len(rows),
        "orphaned_entities": len(orphaned),
        "orphaned_list": orphaned,
        "items": [
            {
                "entity_name": r.entity_name,
                "entity_type": r.entity_type,
                "apo_language_id": r.apo_language_id,
                "apo_code_signature": r.apo_code_signature,
                "operator_id": r.operator_id,
                "origin": r.origin,
                "memory_ref": r.memory_ref,
                "status": r.status,
            }
            for r in rows
        ],
    }
