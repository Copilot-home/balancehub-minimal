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
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
}
TOKEN_PATTERN = re.compile(
    r'''(sk_live|sk_test|ghp_)[A-Za-z0-9_\-]+
        |^[A-Z_]+\s*=\s*[A-Za-z0-9_.\-]{8,}\s*$
        |\bapi_key\s*=\s*['"][^'"]{8,}['"]''',
    re.IGNORECASE | re.MULTILINE,
)
PLACEHOLDER_PATTERN = re.compile(
    r"replace|example|your|placeholder|dummy|fake|sample",
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
        if path.suffix in SKIP_SUFFIXES:
            continue
        if path.name.startswith("hs_err_pid") and path.suffix == ".log":
            continue
        files.append(path)
    return files


def _is_placeholder(match: re.Match) -> bool:
    """Skip documented placeholder values without skipping real tokens."""
    text = match.group(0)
    if text.lower().startswith(("sk_live_", "sk_test_")):
        return False
    return bool(PLACEHOLDER_PATTERN.search(text))


def main() -> int:
    findings: list[str] = []
    for path in _iter_files():
        rel_path = path.relative_to(REPO_ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in TOKEN_PATTERN.finditer(text):
            if _is_placeholder(match):
                continue
            line_number = text[: match.start()].count("\n") + 1
            findings.append(f"{rel_path}:{line_number}: possible hardcoded secret")

    if findings:
        print("\n".join(findings))
        return 1

    print("Secret hygiene OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
