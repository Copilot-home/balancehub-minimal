import uuid
from sqlalchemy import Boolean, DateTime, Float, Integer, String, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class ConnectorState(Base):
    __tablename__ = "connector_state"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    axis_name: Mapped[str] = mapped_column(String(16), nullable=False, default="AXIS_5")
    connector_class: Mapped[str] = mapped_column(String(32), nullable=False, default="Core")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    breaker_state: Mapped[str] = mapped_column(String(32), nullable=False, default="CLOSED")
    stability_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    economic_impact_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    dependency_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    node_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    drift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    healthy_cycles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AxisCatalog(Base):
    __tablename__ = "axis_catalog"

    axis_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    axis_name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_role: Mapped[str] = mapped_column(String(128), nullable=False)
    min_required_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConnectorCatalog(Base):
    __tablename__ = "connector_catalog"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    assigned_axis: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    connector_class: Mapped[str] = mapped_column(String(32), nullable=False)
    economic_weight_base: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    dependency_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    node_degree: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RegistrySnapshot(Base):
    __tablename__ = "registry_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint_list: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scope_list: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    link_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class DeferredIntent(Base):
    __tablename__ = "deferred_intent"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    governance_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditChain(Base):
    __tablename__ = "audit_chain"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    validation_result: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    commit_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
