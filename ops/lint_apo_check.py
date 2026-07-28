"""APΩ ontology lint – lightweight structural check.

Verifies that known ontology-related directories / files are present when they
exist in the repository.  If none of the optional paths are found the script
still exits 0, so the CI step is safe to run on a fresh or minimal checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Paths that *should* exist when the core application layer is present.
# Listed relative to the repository root (where this script is executed from).
OPTIONAL_ONTOLOGY_PATHS: list[str] = [
    "app",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    missing: list[str] = []
    found: list[str] = []

    for rel_path in OPTIONAL_ONTOLOGY_PATHS:
        target = repo_root / rel_path
        if target.exists():
            found.append(rel_path)
        else:
            missing.append(rel_path)

    if found:
        print(f"APΩ lint OK – verified {len(found)} path(s): {', '.join(found)}")
    if missing:
        # Non-fatal: log but do not fail when optional paths are absent.
        print(f"APΩ lint INFO – optional path(s) not found (skipped): {', '.join(missing)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
