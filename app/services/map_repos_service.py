from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.apo_canon import operator_meta_for
from app.core.models import AxisCatalog, ConnectorCatalog, ConnectorState

AXIS_SEEDS = [
    {"axis_id": "AXIS_1", "axis_name": "Identity & Governance", "canonical_role": "IAM and policy authority", "min_required_nodes": 1},
    {"axis_id": "AXIS_2", "axis_name": "Data Plane", "canonical_role": "Storage and data durability", "min_required_nodes": 2},
    {"axis_id": "AXIS_3", "axis_name": "Execution Fabric", "canonical_role": "Job and workflow execution", "min_required_nodes": 2},
    {"axis_id": "AXIS_4", "axis_name": "Omega Core", "canonical_role": "Central objective and strategy", "min_required_nodes": 1},
    {"axis_id": "AXIS_5", "axis_name": "Connector Runtime", "canonical_role": "External connector orchestration", "min_required_nodes": 3},
    {"axis_id": "AXIS_6", "axis_name": "Observability", "canonical_role": "Metrics and anomaly telemetry", "min_required_nodes": 2},
    {"axis_id": "AXIS_7", "axis_name": "Recovery & Safety", "canonical_role": "Fallback, deferred and self-healing", "min_required_nodes": 2},
    {"axis_id": "AXIS_8", "axis_name": "Economics & Distribution", "canonical_role": "Adoption and value routing", "min_required_nodes": 1},
]

# Runtime canonical map (20 systems).
CONNECTOR_SEEDS = [
    {"name": "Omega-Core", "assigned_axis": "AXIS_4", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
    {"name": "BalanceHub", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 2, "node_degree": 2},
    {"name": "Stripe", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
    {"name": "HuggingFace", "assigned_axis": "AXIS_5", "connector_class": "Peripheral", "economic_weight_base": 0.7, "dependency_degree": 1, "node_degree": 1},
    {"name": "Registry-Service", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "Probe-Worker", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "Invocation-Gateway", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 0.9, "dependency_degree": 2, "node_degree": 2},
    {"name": "Failure-Engine", "assigned_axis": "AXIS_7", "connector_class": "Core", "economic_weight_base": 0.9, "dependency_degree": 1, "node_degree": 1},
    {"name": "Fallback-Router", "assigned_axis": "AXIS_7", "connector_class": "Core", "economic_weight_base": 0.9, "dependency_degree": 1, "node_degree": 1},
    {"name": "Audit-Logger", "assigned_axis": "AXIS_7", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "Prometheus", "assigned_axis": "AXIS_6", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "Redis", "assigned_axis": "AXIS_2", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "Postgres", "assigned_axis": "AXIS_2", "connector_class": "Core", "economic_weight_base": 0.9, "dependency_degree": 1, "node_degree": 1},
    {"name": "DAIOF-Framework", "assigned_axis": "AXIS_3", "connector_class": "Peripheral", "economic_weight_base": 0.6, "dependency_degree": 1, "node_degree": 1},
    {"name": "HyperAI-API", "assigned_axis": "AXIS_3", "connector_class": "Peripheral", "economic_weight_base": 0.6, "dependency_degree": 1, "node_degree": 1},
    {"name": "UEVS-Service", "assigned_axis": "AXIS_7", "connector_class": "Peripheral", "economic_weight_base": 0.5, "dependency_degree": 1, "node_degree": 1},
    {"name": "SACR-Service", "assigned_axis": "AXIS_7", "connector_class": "Peripheral", "economic_weight_base": 0.5, "dependency_degree": 1, "node_degree": 1},
    {"name": "Digital-Ecosystem", "assigned_axis": "AXIS_8", "connector_class": "Experimental", "economic_weight_base": 0.4, "dependency_degree": 1, "node_degree": 1},
    {"name": "Evaluation-Runner", "assigned_axis": "AXIS_6", "connector_class": "Peripheral", "economic_weight_base": 0.5, "dependency_degree": 1, "node_degree": 1},
    {"name": "HAIOS-Monitor", "assigned_axis": "AXIS_6", "connector_class": "Peripheral", "economic_weight_base": 0.6, "dependency_degree": 1, "node_degree": 1},
    {"name": "omniagent", "assigned_axis": "AXIS_4", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 2, "node_degree": 2},
    {"name": "github", "assigned_axis": "AXIS_3", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
    {"name": "phoenix", "assigned_axis": "AXIS_4", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
    {"name": "asana", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
    {"name": "memory", "assigned_axis": "AXIS_1", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 2, "node_degree": 3},
    {"name": "registry", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 0.8, "dependency_degree": 1, "node_degree": 1},
    {"name": "stripe", "assigned_axis": "AXIS_5", "connector_class": "Core", "economic_weight_base": 1.0, "dependency_degree": 1, "node_degree": 1},
]


def bootstrap_catalogs(db: Session) -> None:
    for axis in AXIS_SEEDS:
        row = db.get(AxisCatalog, axis["axis_id"])
        if row is None:
            row = AxisCatalog(**axis)
            db.add(row)
        else:
            row.axis_name = axis["axis_name"]
            row.canonical_role = axis["canonical_role"]
            row.min_required_nodes = axis["min_required_nodes"]
            db.add(row)

    for connector in CONNECTOR_SEEDS:
        row = db.get(ConnectorCatalog, connector["name"])
        if row is None:
            row = ConnectorCatalog(**connector)
            db.add(row)
        else:
            row.assigned_axis = connector["assigned_axis"]
            row.connector_class = connector["connector_class"]
            row.economic_weight_base = connector["economic_weight_base"]
            row.dependency_degree = connector["dependency_degree"]
            row.node_degree = connector["node_degree"]
            db.add(row)

    db.commit()


def sync_connector_state_with_catalog(db: Session) -> None:
    rows = db.execute(select(ConnectorCatalog)).scalars().all()

    for catalog in rows:
        state = db.execute(
            select(ConnectorState).where(func.lower(ConnectorState.name) == catalog.name.lower())
        ).scalar_one_or_none()

        if state is None:
            state = ConnectorState(
                name=catalog.name,
                axis_name=catalog.assigned_axis,
                connector_class=catalog.connector_class,
                economic_impact_weight=catalog.economic_weight_base,
                dependency_degree=catalog.dependency_degree,
                node_degree=catalog.node_degree,
                state="ACTIVE",
                breaker_state="CLOSED",
                stability_score=100,
            )
        else:
            state.axis_name = catalog.assigned_axis
            state.connector_class = catalog.connector_class
            state.economic_impact_weight = catalog.economic_weight_base
            state.dependency_degree = catalog.dependency_degree
            state.node_degree = catalog.node_degree

        db.add(state)

    db.commit()


def list_axis_catalog(db: Session) -> list[AxisCatalog]:
    return db.execute(select(AxisCatalog).order_by(AxisCatalog.axis_id)).scalars().all()


def list_connector_catalog(db: Session) -> list[ConnectorCatalog]:
    return db.execute(select(ConnectorCatalog).order_by(ConnectorCatalog.name)).scalars().all()


def list_connector_catalog_with_apo(db: Session) -> list[dict]:
    rows = list_connector_catalog(db)
    return [
        {
            "name": c.name,
            "assigned_axis": c.assigned_axis,
            "class": c.connector_class,
            "economic_weight_base": c.economic_weight_base,
            "dependency_degree": c.dependency_degree,
            "node_degree": c.node_degree,
            "apo_operator": operator_meta_for(c.name),
        }
        for c in rows
    ]
