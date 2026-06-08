"""Repository secret hygiene check.

Keeps CI from failing on its own documentation while still blocking obvious
hardcoded provider tokens and API key assignments.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "venv",
}
SKIP_FILES = {
    Path("ops/secret_hygiene.py"),
}
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
}
TOKEN_PATTERN = re.compile(
    r"(sk_live|sk_test|ghp_)[A-Za-z0-9_\-]+"
    r"|api_key\s*=\s*['\"][^'\"]{8,}['\"]",
    re.IGNORECASE,
)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        rel_path = path.relative_to(REPO_ROOT)
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in rel_path.parts):
            continue
        if rel_path in SKIP_FILES:
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        if path.name.startswith("hs_err_pid") and path.suffix == ".log":
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in _iter_files():
        rel_path = path.relative_to(REPO_ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if TOKEN_PATTERN.search(line):
                findings.append(f"{rel_path}:{line_number}: possible hardcoded secret")

    if findings:
        print("\n".join(findings))
        return 1

    print("Secret hygiene OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
