from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.models import ConnectorState

AXES = [f"AXIS_{i}" for i in range(1, 9)]


def _reliability_modifier(state: str) -> float:
    return 0.5 if state == "QUARANTINED" else 1.0


def _clamp_weight(weight: float) -> float:
    if weight <= 0:
        return 0.01
    if weight > 1:
        return 1.0
    return weight


def _connector_health(connector: ConnectorState) -> float:
    s = float(max(0, min(100, connector.stability_score)))
    w = _clamp_weight(float(connector.economic_impact_weight))
    r = _reliability_modifier(connector.state)
    return s * w * r


def compute_system_health(db: Session) -> dict:
    connectors = db.execute(select(ConnectorState)).scalars().all()

    axis_groups = {axis: [] for axis in AXES}
    for c in connectors:
        axis = c.axis_name if c.axis_name in axis_groups else "AXIS_5"
        axis_groups[axis].append(c)

    axis_health = {}
    for axis in AXES:
        members = axis_groups[axis]
        # Runtime convention: empty axis is neutral until onboarded.
        if not members:
            axis_health[axis] = 100.0
            continue
        total = sum(_connector_health(c) for c in members)
        axis_health[axis] = round(total / len(members), 2)

    gssi = round(sum(axis_health.values()) / len(AXES), 2)

    top_volatility = sorted(
        (
            {
                "connector": c.name,
                "volatility": max(0, 100 - int(c.stability_score)),
            }
            for c in connectors
        ),
        key=lambda x: x["volatility"],
        reverse=True,
    )[:5]

    spof = []
    for axis in AXES:
        members = axis_groups[axis]
        live = [c for c in members if c.state != "QUARANTINED"]
        if members and len(live) <= 1:
            spof.append(axis)

    # Connector-level SPOF signal is folded into the same list for ops simplicity.
    for c in connectors:
        if c.dependency_degree > 2:
            spof.append(c.name)

    deg_violation = [c.name for c in connectors if c.node_degree > 2]

    return {
        "system_health": gssi,
        "axis_health": axis_health,
        "top_volatility": top_volatility,
        "single_point_of_failure": sorted(set(spof)),
        "deg_violation": sorted(set(deg_violation)),
    }
