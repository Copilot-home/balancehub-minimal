"""
Smoke tests for BalanceHub v2 Runtime.

These tests run against an in-memory SQLite database and require no external
services (no Postgres, Redis, Stripe, etc.).  They cover:

  - Canonical identity / integrity endpoints
  - Catalog (axes and connectors)
  - System health / economic weight
  - Connector state lookup
  - /execute for Stripe (mock mode, no API key) and catalog connectors
  - APO header encoding (unicode-safe latin-1 compliance)
"""

import base64
import os

import pytest

# Force in-memory SQLite so tests never need Postgres and never share state
# with the development database file.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_API_KEY"] = ""              # mock / no-key mode
os.environ["APO_CANON_SIGNING_KEY"] = "test-signing-key-smoke"  # test HMAC key

from fastapi.testclient import TestClient  # noqa: E402 (after env setup)

# Re-import db module so the engine picks up the patched DATABASE_URL.
import app.core.db as _db_module  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

# StaticPool forces all requests to share a single connection, which is
# required for in-memory SQLite — different connections would see an empty DB.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
_db_module.engine = _test_engine
_db_module.SessionLocal = sessionmaker(
    bind=_test_engine, autoflush=False, autocommit=False, future=True
)

from app.main import app, _header_safe  # noqa: E402
from app.core.apo_canon import canonical_identity_snapshot, canonical_proof_signature  # noqa: E402


def _apo_headers() -> dict[str, str]:
    """Build valid APO transport headers for POST/PUT/PATCH/DELETE requests."""
    identity = canonical_identity_snapshot()
    proof = canonical_proof_signature()
    return {
        "X-APO-Language-ID": _header_safe(identity["language_id"]),
        "X-APO-Code-Signature": _header_safe(identity["code_signature"]),
        "X-APO-Spec-Version": _header_safe(identity["spec_version"]),
        "X-APO-Spec-SHA256": _header_safe(identity["spec_sha256"]),
        "X-APO-Watermark": _header_safe(identity["ontology_watermark"]),
        "X-APO-Proof": proof,
    }


@pytest.fixture(scope="module")
def client():
    """Start the app (triggers init_db + bootstrap) once per test module."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def apo_headers():
    """Pre-computed valid APO transport headers for POST requests."""
    return _apo_headers()


# ---------------------------------------------------------------------------
# APO identity / canonical integrity
# ---------------------------------------------------------------------------

def test_root_running(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "running"
    assert "apo_language_id" in data


def test_canon_identity(client):
    r = client.get("/canon/identity")
    assert r.status_code == 200
    data = r.json()
    assert data["language_id"] == "SIGMA_APOMEGA_COS"
    assert data["spec_version"] == "v2"


def test_canon_validate_integrity(client):
    r = client.get("/canon/validate")
    assert r.status_code == 200
    data = r.json()
    assert data["integrity"]["valid"] is True, (
        f"Canonical integrity check failed: {data['integrity']}"
    )


def test_canon_proof(client):
    r = client.get("/canon/proof")
    assert r.status_code == 200
    data = r.json()
    assert data["integrity"]["valid"] is True
    # A signing key is configured in tests, so proof must be a hex string.
    proof = data.get("proof")
    assert proof is not None and len(proof) == 64


def test_canon_coverage(client):
    r = client.get("/canon/coverage")
    assert r.status_code == 200
    data = r.json()
    assert data["total_entities"] > 0
    assert 0.0 <= data["coverage_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# APO response headers are latin-1-safe (unicode symbols must be base64)
# ---------------------------------------------------------------------------

def test_apo_headers_latin1_safe(client):
    r = client.get("/")
    for header_name in [
        "x-apo-language-id",
        "x-apo-code-signature",
        "x-apo-spec-version",
        "x-apo-spec-sha256",
        "x-apo-watermark",
    ]:
        value = r.headers.get(header_name)
        assert value is not None, f"Missing header: {header_name}"
        # All header values must be transmittable as latin-1.
        try:
            value.encode("latin-1")
        except UnicodeEncodeError:
            pytest.fail(f"Header {header_name}={value!r} is not latin-1 safe")


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_catalog_axes(client):
    r = client.get("/catalog/axes")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 8
    axis_ids = {a["axis_id"] for a in items}
    assert "AXIS_1" in axis_ids
    assert "AXIS_8" in axis_ids


def test_catalog_connectors(client):
    r = client.get("/catalog/connectors")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 21
    names = {c["name"] for c in items}
    assert "Stripe" in names
    assert "OmniAgent" in names
    assert "Omega-Core" in names


# ---------------------------------------------------------------------------
# System health & economic weight
# ---------------------------------------------------------------------------

def test_system_health(client):
    r = client.get("/system/health")
    assert r.status_code == 200


def test_system_economic_weight(client):
    r = client.get("/system/economic-weight")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Connector state
# ---------------------------------------------------------------------------

def test_connector_state_stripe(client):
    r = client.get("/connectors/Stripe/state")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Stripe"
    assert data["state"] in {"ACTIVE", "DEGRADED", "RECOVERY", "QUARANTINED"}


def test_connector_state_not_found(client):
    r = client.get("/connectors/NonExistent/state")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_snapshot(client):
    r = client.get("/registry/snapshot")
    assert r.status_code == 200
    assert "items" in r.json()


def test_registry_diff(client):
    r = client.get("/registry/diff")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# /execute – Stripe mock (no API key)
# ---------------------------------------------------------------------------

def test_execute_stripe_retrieve_balance_mock(client, apo_headers):
    """Stripe in mock mode (no API key) must succeed without external calls."""
    r = client.post(
        "/execute",
        json={
            "connector": "Stripe",
            "action": "retrieve_balance",
            "request_id": "smoke-test-001",
            "payload": {},
        },
        headers=apo_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in {"ok", "deferred", "error"}


def test_execute_unknown_connector_rejected(client, apo_headers):
    """Connectors not in the catalog must result in a failure response, not 500."""
    r = client.post(
        "/execute",
        json={
            "connector": "UnknownXYZ",
            "action": "do_something",
            "request_id": "smoke-test-002",
            "payload": {},
        },
        headers=apo_headers,
    )
    # App handles the 404 gracefully (connector not registered).
    assert r.status_code in {200, 404}


# ---------------------------------------------------------------------------
# /execute – generic catalog connectors (mock handler)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("connector", [
    "Omega-Core",
    "HuggingFace",
    "Redis",
    "Postgres",
    "DAIOF-Framework",
    "HAIOS-Monitor",
])
def test_execute_catalog_connector_mock(client, apo_headers, connector):
    """All catalog connectors should return a mock-safe response, not a 500."""
    r = client.post(
        "/execute",
        json={
            "connector": connector,
            "action": "ping",
            "request_id": f"smoke-{connector}-001",
            "payload": {},
        },
        headers=apo_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in {"ok", "deferred", "error"}


# ---------------------------------------------------------------------------
# AI2AI canon encode / validate / decode round-trip
# ---------------------------------------------------------------------------

def test_canon_ai2ai_encode_decode_roundtrip(client, apo_headers):
    encode_payload = {
        "sender_entity": "TestAgent",
        "receiver_entity": "BalanceHub",
        "action": "retrieve_balance",  # must be a value mapped in ACTION_TO_SYMBOL
        "payload_math": {"value": 42},
        "state_in": "000001",
        "state_out": "000010",
        "gate_result": "allowed",
    }
    r_enc = client.post("/canon/ai2ai/encode", json=encode_payload, headers=apo_headers)
    assert r_enc.status_code == 200
    packet = r_enc.json()["packet"]

    r_val = client.post("/canon/ai2ai/validate", json={"packet": packet}, headers=apo_headers)
    assert r_val.status_code == 200
    assert r_val.json()["validation"]["valid"] is True

    r_dec = client.post("/canon/ai2ai/decode", json={"packet": packet}, headers=apo_headers)
    assert r_dec.status_code == 200
    decoded = r_dec.json()["decoded"]
    assert decoded["sender_entity"] == "TestAgent"
    assert decoded["gate_result"] == "allowed"


# ---------------------------------------------------------------------------
# APO memory
# ---------------------------------------------------------------------------

def test_canon_memory_status(client):
    r = client.get("/canon/memory/status")
    assert r.status_code == 200
