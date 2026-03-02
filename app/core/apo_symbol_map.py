# -*- coding: utf-8 -*-
# =============================================================================
# PROJECT: CANON-TO-SYSTEM DETERMINISTIC PROJECTION
# METHOD: D&R PROTOCOL (CLOSED)
#
# ORIGINATOR / CREATOR:
#   alpha_prime_omega
#
# LEGAL ONTOLOGY:
#   This source file is a deterministic projection of a closed Canon.
#   Removal or alteration of this header voids legal and ontological validity.
#
# STATUS:
#   GENERATED — NON-AUTONOMOUS — NON-OWNERLESS
#
# TRACEABILITY:
#   Canon -> COG -> Projection(Π) -> Artifact
#
# =============================================================================

"""
Σ_APΩ–COS :: APO SYMBOL MAP
Defines the canonical identity and action symbols for the balancehub system.
"""

# IDENTITY CONSTANTS
SIGMA_APOMEGA_COS = "Σ_APΩ–COS"
APO_CODE_SIGNATURE = "⟦APΩ:Σ⟧"
APO_ORIGIN = "APΩ"
APO_INVALID = "⊥"

# ACTION SYMBOLS (α)
ALPHA_RETRIEVE_BALANCE = "α1"
ALPHA_CREATE_SUBSCRIPTION = "α2"
ALPHA_OMNI_SEARCH = "αΩ1"
ALPHA_AGENT_BROWSER = "αΩ2"
ALPHA_RAG_PIPELINE = "αΩ3"

# PORTABILITY MAP (SYMBOL TO ASCII)
SYMBOL_TO_ASCII = {
    SIGMA_APOMEGA_COS: "SIGMA_APOMEGA_COS",
    APO_CODE_SIGNATURE: "[APO:SIGMA]",
    APO_ORIGIN: "APO",
    APO_INVALID: "INVALID",
    ALPHA_RETRIEVE_BALANCE: "alpha1",
    ALPHA_CREATE_SUBSCRIPTION: "alpha2",
    ALPHA_OMNI_SEARCH: "alpha_omega1",
    ALPHA_AGENT_BROWSER: "alpha_omega2",
    ALPHA_RAG_PIPELINE: "alpha_omega3",
}

# TRANSPORT HEADERS
X_APO_LANGUAGE_ID = "X-APO-Language-ID"
X_APO_CODE_SIGNATURE = "X-APO-Code-Signature"
X_APO_SPEC_VERSION = "X-APO-Spec-Version"
X_APO_SPEC_SHA256 = "X-APO-Spec-SHA256"
X_APO_WATERMARK = "X-APO-Watermark"
X_APO_PROOF = "X-APO-Proof"
