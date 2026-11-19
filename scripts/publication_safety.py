#!/usr/bin/env python3
"""Reject common private-data and credential artifacts in a publication tree."""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_SUFFIXES = {".pgn", ".pgn.gz", ".jsonl", ".log", ".safetensors", ".pt", ".pth", ".ckpt"}
FORBIDDEN_NAMES = {"kaggle.json", "credentials.json", ".env", ".env.local", "id_rsa", "id_ed25519"}
SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
PRIVATE_PATH_PARTS = {".aws", ".ssh", ".kaggle", "checkpoints", "weights", "models", "runs", "outputs"}


def check_tree(root: Path) -> list[str]:
    problems: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (
            ".git" in relative.parts
            or ".ruff_cache" in relative.parts
            or "__pycache__" in relative.parts
            or path.suffix == ".pyc"
        ):
            continue
        if path.is_symlink():
            problems.append(f"symlink: {relative}")
            continue
        if not path.is_file():
            continue
        parts = {part.casefold() for part in relative.parts}
        name = path.name.casefold()
        if parts & PRIVATE_PATH_PARTS:
            problems.append(f"private path: {relative}")
        if name in FORBIDDEN_NAMES or any(name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            problems.append(f"private or binary artifact: {relative}")
        if path.stat().st_size > 5 * 1024 * 1024:
            problems.append(f"oversized file (>5 MiB): {relative}")
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            problems.append(f"non-text file: {relative}")
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                problems.append(f"possible credential: {relative}")
                break
    return problems


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems = check_tree(root)
    if problems:
        print("Publication safety check failed:")
        print("\n".join(f"- {item}" for item in problems))
        return 1
    print("Publication safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
