import time
import stripe
from app.services.omni_service import OmniService

# All connectors registered in the catalog.  Stripe and OmniAgent have real
# (or mock-safe) handlers; every other connector returns a standardised mock
# response so that circuit-breaker logic works for the full catalog without
# raising an unhandled ValueError.
_CATALOG_CONNECTORS = {
    "Omega-Core",
    "BalanceHub",
    "Stripe",
    "HuggingFace",
    "Registry-Service",
    "Probe-Worker",
    "Invocation-Gateway",
    "Failure-Engine",
    "Fallback-Router",
    "Audit-Logger",
    "Prometheus",
    "Redis",
    "Postgres",
    "DAIOF-Framework",
    "HyperAI-API",
    "UEVS-Service",
    "SACR-Service",
    "Digital-Ecosystem",
    "Evaluation-Runner",
    "HAIOS-Monitor",
    "OmniAgent",
}


async def execute_action(_db, connector: str, action: str, payload: dict) -> dict:
    if connector not in _CATALOG_CONNECTORS:
        raise ValueError(f"Unknown connector: {connector}")

    start = time.time()

    if connector == "Stripe":
        if action == "retrieve_balance":
            # Minimal/public-safe mode: no external secret required.
            if not stripe.api_key:
                data = {
                    "object": "balance",
                    "available": [{"amount": 100000, "currency": "usd"}],
                    "pending": [],
                    "livemode": False,
                    "source": "mock",
                }
            else:
                data = stripe.Balance.retrieve()
        elif action == "create_subscription":
            raise NotImplementedError("create_subscription wired for deferred path in prototype")
        else:
            raise ValueError(f"Unknown action: {action}")

    elif connector == "OmniAgent":
        data = await OmniService.execute_query(action, payload)

    else:
        # Generic mock-safe handler for all other catalog connectors.
        # Returns a deterministic stub so the circuit-breaker and audit paths
        # exercise normally without requiring real external credentials.
        data = {
            "connector": connector,
            "action": action,
            "source": "mock",
            "result": "ok",
        }

    latency_ms = int((time.time() - start) * 1000)
    return {"status": "ok", "latency_ms": latency_ms, "data": data}
