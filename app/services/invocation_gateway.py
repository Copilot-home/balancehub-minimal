import time
import stripe


def execute_action(_db, connector: str, action: str, payload: dict) -> dict:
    if connector != "Stripe":
        raise ValueError(f"Unknown connector: {connector}")

    start = time.time()

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

    latency_ms = int((time.time() - start) * 1000)
    return {"status": "ok", "latency_ms": latency_ms, "data": data}
