#!/usr/bin/env python3
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

import sys
import os

# Add app directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.core.apo_symbol_map import (
        SIGMA_APOMEGA_COS,
        APO_CODE_SIGNATURE,
        APO_ORIGIN,
        APO_INVALID,
        ALPHA_RETRIEVE_BALANCE,
        ALPHA_OMNI_SEARCH,
        SYMBOL_TO_ASCII,
        X_APO_PROOF
    )
except ImportError as e:
    print(f"FAILED: Could not import apo_symbol_map - {e}")
    sys.exit(1)

def lint():
    print("Scanning Ontological Alignment...")
    
    # 1. Check Identity Constants
    if SIGMA_APOMEGA_COS != "Σ_APΩ–COS":
        print(f"FAILED: Invalid identity constant SIGMA_APOMEGA_COS")
        return False
    if APO_CODE_SIGNATURE != "⟦APΩ:Σ⟧":
        print(f"FAILED: Invalid signature APO_CODE_SIGNATURE")
        return False
    if APO_INVALID != "⊥":
        print("FAILED: Invalid non-existence symbol")
        return False
        
    # 2. Check Action Symbols
    if ALPHA_RETRIEVE_BALANCE != "α1" or ALPHA_OMNI_SEARCH != "αΩ1":
        print("FAILED: Invalid action symbol mapping")
        return False
        
    # 3. Check Portability Map
    if SYMBOL_TO_ASCII.get(APO_ORIGIN) != "APO":
        print("FAILED: Missing or invalid portability map")
        return False
        
    # 4. Check Transport Headers
    if X_APO_PROOF != "X-APO-Proof":
        print("FAILED: Transport header constant mismatch")
        return False

    print("APΩ ontology lint: OK")
    return True

if __name__ == "__main__":
    if lint():
        sys.exit(0)
    else:
        sys.exit(1)
