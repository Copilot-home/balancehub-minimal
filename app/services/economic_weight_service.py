import os
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import ConnectorState

AXES = [f"AXIS_{i}" for i in range(1, 9)]


def _env_float(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _fetch_github_signals(repo: str, token: str | None) -> dict[str, float]:
    if not repo:
        return {"stars": 0.0, "forks": 0.0, "watchers": 0.0, "views": 0.0, "clones": 0.0}

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    stars = forks = watchers = views = clones = 0.0
    timeout = httpx.Timeout(2.5, connect=2.0)
    with httpx.Client(timeout=timeout) as client:
        try:
            repo_resp = client.get(f"https://api.github.com/repos/{repo}", headers=headers)
            if repo_resp.status_code == 200:
                payload = repo_resp.json()
                stars = float(payload.get("stargazers_count", 0) or 0)
                forks = float(payload.get("forks_count", 0) or 0)
                watchers = float(payload.get("subscribers_count", 0) or 0)
        except Exception:
            pass

        try:
            views_resp = client.get(f"https://api.github.com/repos/{repo}/traffic/views", headers=headers)
            if views_resp.status_code == 200:
                views = float((views_resp.json() or {}).get("count", 0) or 0)
        except Exception:
            pass

        try:
            clones_resp = client.get(f"https://api.github.com/repos/{repo}/traffic/clones", headers=headers)
            if clones_resp.status_code == 200:
                clones = float((clones_resp.json() or {}).get("count", 0) or 0)
        except Exception:
            pass

    return {
        "stars": stars,
        "forks": forks,
        "watchers": watchers,
        "views": views,
        "clones": clones,
    }


def _connector_multiplier(connector: ConnectorState, signals: dict[str, float], extras: dict[str, float]) -> float:
    adoption = (
        signals["stars"]
        + 2.0 * signals["forks"]
        + signals["clones"]
        + 0.5 * signals["views"]
        + 0.2 * signals["watchers"]
    )

    distribution = 0.0
    if connector.name in {"BalanceHub", "Invocation-Gateway", "Registry-Service", "Probe-Worker"}:
        distribution += 0.01 * extras["docker_pulls"]
    if connector.name == "HuggingFace":
        distribution += 2.0 * extras["hf_likes"]

    revenue = (extras["stripe_revenue_usd"] / 100.0) if connector.name == "Stripe" else 0.0
    external_index = adoption + distribution + revenue
    return min(2.0, external_index / 1000.0)


def compute_economic_weight(db: Session) -> dict[str, Any]:
    connectors = db.execute(select(ConnectorState)).scalars().all()

    repo = os.getenv("GITHUB_REPO", "NguyenCuong1989/balancehub-minimal")
    token = os.getenv("GITHUB_TOKEN")
    github = _fetch_github_signals(repo, token)

    extras = {
        "docker_pulls": _env_float("DOCKER_PULLS", 0.0),
        "hf_likes": _env_float("HF_LIKES", 0.0),
        "stripe_revenue_usd": _env_float("STRIPE_REVENUE_USD", 0.0),
    }

    connector_weights: list[dict[str, Any]] = []
    axis_weight_map: dict[str, float] = {axis: 0.0 for axis in AXES}

    for connector in connectors:
        base = float(max(0.01, connector.economic_impact_weight))
        multiplier = _connector_multiplier(connector, github, extras)
        weight = round(base * (1.0 + multiplier), 4)

        connector_weights.append(
            {
                "connector": connector.name,
                "axis": connector.axis_name,
                "state": connector.state,
                "base_weight": round(base, 4),
                "multiplier": round(multiplier, 4),
                "weight": weight,
            }
        )
        axis_weight_map[connector.axis_name] = round(axis_weight_map.get(connector.axis_name, 0.0) + weight, 4)

    system_weight = round(sum(axis_weight_map.values()), 4)

    connector_sorted = sorted(connector_weights, key=lambda x: x["weight"], reverse=True)
    monthly_cost = _env_float("MONTHLY_COST_USD", 275.0)
    monthly_revenue = (
        _env_float("REV_SPONSORS_USD", 0.0)
        + _env_float("REV_DONATIONS_USD", 0.0)
        + _env_float("REV_OTHER_USD", 0.0)
    )
    cash_reserve = _env_float("CASH_RESERVE_USD", 600.0)
    coverage_ratio = (monthly_revenue / monthly_cost) if monthly_cost > 0 else 0.0
    break_even_gap = max(0.0, monthly_cost - monthly_revenue)
    burn_rate = break_even_gap
    runway_months = float("inf") if burn_rate == 0 else (cash_reserve / burn_rate)

    if coverage_ratio >= 1.0:
        economic_health = "SUSTAINABLE"
        priority_action = "Reinvest into external deployments and reliability."
    elif coverage_ratio >= 0.6:
        economic_health = "STABLE BUT UNDERFUNDED"
        priority_action = "Increase sponsorship while keeping node footprint stable."
    elif coverage_ratio >= 0.3:
        economic_health = "AT RISK"
        priority_action = "Reduce experimental nodes or increase sponsorship."
    else:
        economic_health = "CRITICAL"
        priority_action = "Freeze growth and reduce infra immediately."

    return {
        "economic_health": economic_health,
        "coverage_ratio": round(coverage_ratio, 4),
        "monthly_cost": round(monthly_cost, 2),
        "monthly_revenue": round(monthly_revenue, 2),
        "break_even_gap": round(break_even_gap, 2),
        "runway_months": "INF" if runway_months == float("inf") else round(runway_months, 2),
        "priority_action": priority_action,
        "details": {
            "system_economic_weight": system_weight,
            "C_base": round(monthly_cost, 2),
            "C_shared": 0.0,
            "node_breakdown": connector_sorted,
            "axis_economic_weight": axis_weight_map,
            "signals": {
                "github_repo": repo,
                **github,
                **extras,
            },
            "formula": "W_connector = base_weight * (1 + min(2, external_index/1000))",
        },
    }
