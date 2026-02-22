from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "balancehub_requests_total",
    "Total execution requests",
    ["connector", "status"],
)

STABILITY_SCORE = Gauge(
    "balancehub_stability_score",
    "Current stability score",
    ["connector"],
)

BREAKER_STATE = Gauge(
    "balancehub_breaker_state",
    "Breaker state (0=closed,0.5=half_open,1=open)",
    ["connector"],
)

LATENCY_HISTOGRAM = Histogram(
    "balancehub_latency_ms",
    "Connector latency in ms",
    ["connector"],
)

FAILURE_RATE = Counter(
    "balancehub_failure_total",
    "Failures per connector",
    ["connector", "error_type"],
)

FALLBACK_USAGE = Counter(
    "balancehub_fallback_usage_total",
    "Fallback/deferred usage",
    ["connector", "reason"],
)

DRIFT_FREQUENCY = Gauge(
    "balancehub_drift_frequency",
    "Registry drift count",
    ["connector"],
)

QUARANTINE_DURATION_SECONDS = Gauge(
    "balancehub_quarantine_duration_seconds",
    "Current quarantine duration in seconds",
    ["connector"],
)
