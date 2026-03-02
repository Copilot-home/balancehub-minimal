import hashlib
import json
import re
from typing import Any

from app.core.apo_canon import LANGUAGE_ID, ONTOLOGICAL_ROOT


CANON_COMM_VERSION = "Σ_APΩ-COMM/v1"
LINEAR_PATH = ["O", "E", "P", "L", "I", "F", "B"]
DELTA_SET = {"δ", "⊥"}
GATE_SET = {"allowed", "denied"}

# Symbolic action vocabulary (no NLP).
ACTION_TO_SYMBOL = {
    "retrieve_balance": "α1",
    "create_subscription": "α2",
    "omni_search": "αΩ1",
    "agent_browser": "αΩ2",
    "rag_pipeline": "αΩ3",
}
SYMBOL_TO_ACTION = {v: k for k, v in ACTION_TO_SYMBOL.items()}

STATE_RE = re.compile(r"^[01]{6}$")
SYMBOL_STRING_RE = re.compile(r"^[-A-Za-z0-9_αΩδ⊥:+\\./=]{1,64}$")
REQUIRED_PACKET_FIELDS = {
    "comm_version",
    "language_id",
    "origin",
    "operator_path",
    "sender_entity",
    "receiver_entity",
    "action_symbol",
    "state_in",
    "state_out",
    "delta_symbol",
    "gate_result",
    "payload_math",
}
OPTIONAL_PACKET_FIELDS = {"equations", "packet_hash"}


def _is_symbolic_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, str):
        # Reject natural language-like strings (spaces or long prose).
        if " " in value:
            return False
        return bool(SYMBOL_STRING_RE.fullmatch(value))
    if isinstance(value, list):
        return all(_is_symbolic_value(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and SYMBOL_STRING_RE.fullmatch(k) and _is_symbolic_value(v) for k, v in value.items())
    return False


def _packet_hash(packet: dict[str, Any]) -> str:
    blob = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    unknown_fields = set(packet.keys()) - REQUIRED_PACKET_FIELDS - OPTIONAL_PACKET_FIELDS
    missing_fields = REQUIRED_PACKET_FIELDS - set(packet.keys())
    if unknown_fields:
        errors.append("unknown_packet_fields")
    if missing_fields:
        errors.append("missing_packet_fields")

    if packet.get("comm_version") != CANON_COMM_VERSION:
        errors.append("invalid_comm_version")
    if packet.get("language_id") != LANGUAGE_ID:
        errors.append("invalid_language_id")
    if packet.get("origin") != ONTOLOGICAL_ROOT:
        errors.append("invalid_origin")

    state_in = str(packet.get("state_in", ""))
    state_out = str(packet.get("state_out", ""))
    if not STATE_RE.fullmatch(state_in):
        errors.append("invalid_state_in")
    if not STATE_RE.fullmatch(state_out):
        errors.append("invalid_state_out")

    delta_symbol = packet.get("delta_symbol")
    if delta_symbol not in DELTA_SET:
        errors.append("invalid_delta_symbol")

    gate_result = packet.get("gate_result")
    if gate_result not in GATE_SET:
        errors.append("invalid_gate_result")

    path = packet.get("operator_path", [])
    if not isinstance(path, list) or not path:
        errors.append("invalid_operator_path")
    else:
        if any(op not in LINEAR_PATH for op in path):
            errors.append("unknown_operator_in_path")
        # Must be an ordered subsequence of O->E->P->L->I->F->B
        indexes = []
        for op in path:
            try:
                indexes.append(LINEAR_PATH.index(op))
            except ValueError:
                indexes.append(-1)
        if any(i < 0 for i in indexes) or indexes != sorted(indexes) or len(set(indexes)) != len(indexes):
            errors.append("non_linear_path")

    action_symbol = packet.get("action_symbol")
    if action_symbol not in SYMBOL_TO_ACTION:
        errors.append("unknown_action_symbol")

    sender_entity = packet.get("sender_entity")
    receiver_entity = packet.get("receiver_entity")
    if not isinstance(sender_entity, str) or not SYMBOL_STRING_RE.fullmatch(sender_entity):
        errors.append("invalid_sender_entity")
    if not isinstance(receiver_entity, str) or not SYMBOL_STRING_RE.fullmatch(receiver_entity):
        errors.append("invalid_receiver_entity")

    payload_math = packet.get("payload_math", {})
    if not isinstance(payload_math, dict) or not _is_symbolic_value(payload_math):
        errors.append("non_symbolic_payload")

    if gate_result == "denied" and delta_symbol != "⊥":
        errors.append("denied_requires_bottom")
    if delta_symbol == "⊥" and state_out != state_in:
        errors.append("bottom_requires_no_state_transition")

    ok = len(errors) == 0
    return {
        "valid": ok,
        "errors": errors,
        "packet_hash": _packet_hash(packet),
    }


def encode_packet(
    *,
    sender_entity: str,
    receiver_entity: str,
    action: str,
    payload_math: dict[str, Any],
    state_in: str,
    state_out: str,
    gate_result: str,
    delta_symbol: str | None = None,
) -> dict[str, Any]:
    symbol = ACTION_TO_SYMBOL.get(action)
    if symbol is None:
        raise ValueError(f"action not canon-mapped: {action}")

    ds = delta_symbol or ("⊥" if gate_result == "denied" else "δ")
    packet = {
        "comm_version": CANON_COMM_VERSION,
        "language_id": LANGUAGE_ID,
        "origin": ONTOLOGICAL_ROOT,
        "operator_path": LINEAR_PATH,
        "sender_entity": sender_entity,
        "receiver_entity": receiver_entity,
        "action_symbol": symbol,
        "state_in": state_in,
        "state_out": state_out,
        "delta_symbol": ds,
        "gate_result": gate_result,
        "payload_math": payload_math,
        "equations": {
            "transition": "δ:S→S∪{⊥}",
            "gate": "B(s)=s|⊥",
            "closure": "s∉S⇒⊥",
        },
    }
    result = validate_packet(packet)
    if not result["valid"]:
        raise ValueError(f"invalid_canon_packet: {','.join(result['errors'])}")
    packet["packet_hash"] = result["packet_hash"]
    return packet


def decode_packet(packet: dict[str, Any]) -> dict[str, Any]:
    result = validate_packet(packet)
    if not result["valid"]:
        raise ValueError(f"invalid_canon_packet: {','.join(result['errors'])}")

    action = SYMBOL_TO_ACTION[packet["action_symbol"]]
    return {
        "sender_entity": packet["sender_entity"],
        "receiver_entity": packet["receiver_entity"],
        "action": action,
        "payload_math": packet.get("payload_math", {}),
        "state_in": packet["state_in"],
        "state_out": packet["state_out"],
        "delta_symbol": packet["delta_symbol"],
        "gate_result": packet["gate_result"],
        "packet_hash": result["packet_hash"],
    }
