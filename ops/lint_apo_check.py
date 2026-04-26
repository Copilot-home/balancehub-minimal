"""
APO Ontology Lint Check
Validates that the runtime symbol map is consistent with the APO canon definitions.
Exits with code 1 if any drift is detected.
"""
import sys
from pathlib import Path

# Allow importing from the app package without installation.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.apo_canon import (
    LANGUAGE_ID,
    LANGUAGE_SYMBOL,
    CODE_SIGNATURE,
    SPEC_VERSION,
    SPEC_SHA256,
    ONTOLOGICAL_ROOT,
    KERNEL_ID,
    INVALID_SYMBOL,
    ONTOLOGY_WATERMARK,
    OPERATORS,
    CONNECTOR_OPERATOR_BINDING,
)
from app.core.apo_symbol_map import (
    SIGMA_APOMEGA_COS,
    APO_CODE_SIGNATURE,
    APO_ORIGIN,
    APO_INVALID,
)

errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


# --- Identity constants must be consistent across modules ---
check(
    SIGMA_APOMEGA_COS == LANGUAGE_SYMBOL,
    f"Symbol map SIGMA_APOMEGA_COS '{SIGMA_APOMEGA_COS}' != apo_canon LANGUAGE_SYMBOL '{LANGUAGE_SYMBOL}'",
)
check(
    APO_CODE_SIGNATURE == CODE_SIGNATURE,
    f"Symbol map APO_CODE_SIGNATURE '{APO_CODE_SIGNATURE}' != apo_canon CODE_SIGNATURE '{CODE_SIGNATURE}'",
)
check(
    APO_ORIGIN == ONTOLOGICAL_ROOT,
    f"Symbol map APO_ORIGIN '{APO_ORIGIN}' != apo_canon ONTOLOGICAL_ROOT '{ONTOLOGICAL_ROOT}'",
)
check(
    APO_INVALID == INVALID_SYMBOL,
    f"Symbol map APO_INVALID '{APO_INVALID}' != apo_canon INVALID_SYMBOL '{INVALID_SYMBOL}'",
)

# --- All OPERATORS entries must have required keys ---
required_operator_keys = {"symbol", "hexagram", "name"}
for op_id, meta in OPERATORS.items():
    missing = required_operator_keys - meta.keys()
    check(
        not missing,
        f"Operator '{op_id}' is missing keys: {missing}",
    )

# --- All connector operator bindings must reference valid operator IDs ---
valid_ops = set(OPERATORS.keys())
for connector, op_id in CONNECTOR_OPERATOR_BINDING.items():
    check(
        op_id in valid_ops,
        f"Connector '{connector}' references unknown operator ID '{op_id}'",
    )

# --- Spec integrity: SPEC_SHA256 must be a 64-char hex string ---
check(
    len(SPEC_SHA256) == 64 and all(c in "0123456789abcdef" for c in SPEC_SHA256),
    f"SPEC_SHA256 '{SPEC_SHA256}' is not a valid 64-char lowercase hex digest",
)

# --- Report ---
if errors:
    print("❌ APO ontology lint FAILED:")
    for err in errors:
        print(f"  • {err}")
    sys.exit(1)

print(f"✅ APO ontology lint passed ({len(OPERATORS)} operators, {len(CONNECTOR_OPERATOR_BINDING)} connector bindings verified)")
