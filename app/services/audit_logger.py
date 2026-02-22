from sqlalchemy.orm import Session
from app.core.models import AuditChain


def write_audit(
    db: Session,
    *,
    connector: str,
    request_id: str,
    validation_result: str,
    decision: str,
    outcome: str,
    fallback_used: bool,
    details: dict | None = None,
) -> None:
    record = AuditChain(
        connector=connector,
        request_id=request_id,
        validation_result=validation_result,
        decision=decision,
        outcome=outcome,
        fallback_used=fallback_used,
        details=details,
    )
    db.add(record)
    db.commit()
