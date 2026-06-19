#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "dist", "build", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".npy", ".pyc"}
PATTERNS = {
    "generic_private_key": re.compile("BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "github_token": re.compile("gh[pousr]_[A-Za-z0-9_]{36,}"),
    "aws_access_key": re.compile("AKIA" + "[0-9A-Z]{16}"),
    "slack_token": re.compile("xox[baprs]-" + "[A-Za-z0-9-]{20,}"),
}
ALLOWLIST = {
    "tools/scan_secrets.py",
}


def iter_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        rel_parts = set(path.relative_to(ROOT).parts)
        if rel_parts.intersection(SKIP_DIRS):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{rel}: possible {name}")
    if findings:
        print("Secret scan failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Secret scan: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
