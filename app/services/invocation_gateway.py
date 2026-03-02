import time
import stripe
from app.services.omni_service import OmniService


async def execute_action(_db, connector: str, action: str, payload: dict) -> dict:
    if connector not in ["Stripe", "OmniAgent"]:
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

    latency_ms = int((time.time() - start) * 1000)
    return {"status": "ok", "latency_ms": latency_ms, "data": data}
