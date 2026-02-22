from dataclasses import dataclass


@dataclass(frozen=True)
class FailureClassification:
    error_type: str
    severity: str
    retry_policy: str
    penalty: int


def classify(error: Exception) -> FailureClassification:
    # Pure classifier: no I/O side effects.
    text = str(error).lower()

    if "timeout" in text:
        return FailureClassification("TIMEOUT", "HIGH", "RETRY", 20)
    if "connection" in text or "network" in text:
        return FailureClassification("CONNECTION_ERROR", "HIGH", "RETRY", 18)
    if "rate" in text or "429" in text:
        return FailureClassification("RATE_LIMIT", "MEDIUM", "BACKOFF", 10)
    if "auth" in text or "key" in text or "401" in text:
        return FailureClassification("AUTH_ERROR", "HIGH", "NO_RETRY", 25)
    return FailureClassification("SERVER_ERROR", "MEDIUM", "RETRY", 15)
