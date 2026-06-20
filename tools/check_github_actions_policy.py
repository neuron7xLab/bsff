#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ALLOWED_TAGGED_ACTION_PREFIXES = (
    "actions/",
    "github/",
    "ossf/scorecard-action@",
    # slsa-github-generator MUST be referenced by tag, not SHA: slsa-verifier
    # cannot verify a reusable workflow pinned by digest (ossf/scorecard#2174).
    "slsa-framework/slsa-github-generator/",
)
FORBIDDEN = (
    "pull_request_target:",
    "permissions: write-all",
    "contents: write-all",
    "--break-system-packages",
)


def _uses_refs(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"uses:\s*([^\s#]+)", text)]


def main() -> int:
    failures: list[str] = []
    if not WORKFLOWS.exists():
        failures.append(".github/workflows is missing")
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        if "permissions:" not in text:
            failures.append(f"{workflow.name}: missing explicit permissions block")
        for forbidden in FORBIDDEN:
            if forbidden in text:
                failures.append(f"{workflow.name}: forbidden token/pattern: {forbidden}")
        for ref in _uses_refs(text):
            if "@" not in ref:
                failures.append(f"{workflow.name}: action ref has no version: {ref}")
                continue
            _action, version = ref.split("@", 1)
            is_sha = bool(re.fullmatch(r"[0-9a-fA-F]{40}", version))
            is_allowed_stable = ref.startswith(ALLOWED_TAGGED_ACTION_PREFIXES) and bool(
                re.fullmatch(r"v\d+(\.\d+\.\d+)?", version)
            )
            if not is_sha and not is_allowed_stable:
                failures.append(
                    f"{workflow.name}: third-party action must be pinned to full SHA or allowlisted stable tag: {ref}"
                )
    if failures:
        print("GitHub Actions policy failures:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("GitHub Actions policy: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
