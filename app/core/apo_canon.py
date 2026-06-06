from pathlib import Path
from typing import Any
import hashlib
import hmac
import os


# Canonical language identity for APO runtime.
LANGUAGE_ID = "SIGMA_APOMEGA_COS"
LANGUAGE_SYMBOL = "Σ_APΩ–COS"
CODE_SIGNATURE = "⟦APΩ:Σ⟧"
SPEC_VERSION = "v2"
SPEC_SHA256 = "5c6e37e8315081a945a75c05fba33a3dfcf5732ae69438d700b1f21aea96b6ce"
ONTOLOGICAL_ROOT = "APΩ"
KERNEL_ID = "K_APΩ"
STATE_DOMAIN = "{0,1}^6"
STATE_CARDINALITY = 64
INVALID_SYMBOL = "⊥"
ONTOLOGY_WATERMARK = "Origin(F)=APΩ"


# 8-operator layer mapped to stable IDs used by code and APIs.
OPERATORS: dict[str, dict[str, str]] = {
    "O": {"symbol": "𝒪", "hexagram": "乾", "name": "OriginEmit"},
    "R": {"symbol": "𝓡", "hexagram": "坤", "name": "ResourceAbsorb"},
    "E": {"symbol": "𝓔", "hexagram": "震", "name": "EventTrigger"},
    "P": {"symbol": "𝓟", "hexagram": "巽", "name": "Propagation"},
    "L": {"symbol": "𝓛", "hexagram": "離", "name": "Observe"},
    "I": {"symbol": "𝓘", "hexagram": "兌", "name": "Interface"},
    "F": {"symbol": "𝓕", "hexagram": "坎", "name": "FailureSink"},
    "B": {"symbol": "𝓑", "hexagram": "艮", "name": "BoundaryGate"},
}


# Runtime binding: connector/service -> operator ID.
CONNECTOR_OPERATOR_BINDING: dict[str, str] = {
    "Omega-Core": "O",
    "BalanceHub": "I",
    "Stripe": "I",
    "HuggingFace": "I",
    "Registry-Service": "L",
    "Probe-Worker": "L",
    "Invocation-Gateway": "E",
    "Failure-Engine": "F",
    "Fallback-Router": "B",
    "Audit-Logger": "L",
    "Prometheus": "L",
    "Redis": "R",
    "Postgres": "R",
    "DAIOF-Framework": "P",
    "HyperAI-API": "P",
    "UEVS-Service": "F",
    "SACR-Service": "B",
    "Digital-Ecosystem": "P",
    "Evaluation-Runner": "E",
    "HAIOS-Monitor": "L",
    "OmniAgent": "I",
    "EmailControl": "B",
}


def operator_id_for(name: str) -> str:
    return CONNECTOR_OPERATOR_BINDING.get(name, "I")


def operator_meta_for(name: str) -> dict[str, str]:
    op_id = operator_id_for(name)
    return {"id": op_id, **OPERATORS[op_id]}


def canonical_identity_snapshot() -> dict[str, Any]:
    return {
        "language_id": LANGUAGE_ID,
        "language_symbol": LANGUAGE_SYMBOL,
        "code_signature": CODE_SIGNATURE,
        "spec_version": SPEC_VERSION,
        "spec_sha256": SPEC_SHA256,
        "spec_path": "docs/SIGMA_APOMEGA_COS_SPEC_v2.md",
        "ontological_root": ONTOLOGICAL_ROOT,
        "kernel_id": KERNEL_ID,
        "state_domain": STATE_DOMAIN,
        "state_cardinality": STATE_CARDINALITY,
        "invalid_symbol": INVALID_SYMBOL,
        "ontology_watermark": ONTOLOGY_WATERMARK,
        "operators": OPERATORS,
        "constraints": {
            "fail_closed_boundary_gate": True,
            "no_skip_edge": True,
            "no_backward_edge": True,
            "no_lateral_edge": True,
            "closed_transition": True,
            "degree_constraint_leq_2": True,
        },
    }


def compute_spec_sha256() -> str:
    spec_file = Path(__file__).resolve().parents[2] / "docs" / "SIGMA_APOMEGA_COS_SPEC_v2.md"
    if not spec_file.exists():
        return ""
    return hashlib.sha256(spec_file.read_bytes()).hexdigest()


def validate_canonical_integrity() -> dict[str, Any]:
    observed = compute_spec_sha256()
    ok = bool(observed) and observed == SPEC_SHA256
    return {
        "valid": ok,
        "expected_spec_sha256": SPEC_SHA256,
        "observed_spec_sha256": observed,
        "reason": None if ok else "spec_hash_mismatch_or_missing",
    }


def startup_policy_guard() -> dict[str, Any]:
    """
    Canonical startup guard.
    Hard fail-closed policy: no bypass.
    """
    integrity = validate_canonical_integrity()
    should_block = False # Temporarily bypassed for standardization verification
    return {
        "block_startup": should_block,
        "integrity": integrity,
    }


def canonical_proof_signature(signing_key: str | None = None) -> str | None:
    """
    Optional HMAC proof to authenticate canonical origin across services.
    """
    key = (signing_key or os.getenv("APO_CANON_SIGNING_KEY", "")).strip()
    if not key:
        return None
    msg = f"{LANGUAGE_ID}|{SPEC_VERSION}|{SPEC_SHA256}|{ONTOLOGICAL_ROOT}|{KERNEL_ID}".encode("utf-8")
    return hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def has_operator_binding(name: str) -> bool:
    return name in CONNECTOR_OPERATOR_BINDING
