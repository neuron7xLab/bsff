#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Verify the live branch ruleset against the declared required checks — honestly.

Reads the GitHub ruleset for the default branch via ``gh api`` and diffs its
required status checks (and admin-bypass posture) against
``docs/GOVERNANCE_REQUIRED_CHECKS.md``. It NEVER reports verified=true when it
lacks API access (returns owner_required) and NEVER when an admin bypass path
exists, because a bypassable gate does not actually block human (or agent) error.

Writes ``artifacts/governance_status.json`` and exits non-zero unless governance
is fully verified.

    python tools/verify_branch_protection.py --repo neuron7xLab/bsff
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARED_DOC = ROOT / "docs" / "GOVERNANCE_REQUIRED_CHECKS.md"
OUT = ROOT / "artifacts" / "governance_status.json"


def _declared_checks() -> list[str]:
    if not DECLARED_DOC.is_file():
        return []
    # checks are listed in a fenced ```text block, one per line
    blocks = re.findall(r"```text\n(.*?)```", DECLARED_DOC.read_text(encoding="utf-8"), re.DOTALL)
    checks: list[str] = []
    for b in blocks:
        for line in b.splitlines():
            line = line.strip()
            if line and re.fullmatch(r"[A-Za-z0-9 ._/-]+", line):
                checks.append(line)
    return sorted(set(checks))


def _gh_json(args: list[str]) -> tuple[object | None, str]:
    try:
        proc = subprocess.run(["gh", "api", *args], text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return None, "gh CLI not available"
    if proc.returncode != 0:
        return None, proc.stderr.strip() or "gh api error"
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError:
        return None, "unparseable gh output"


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def verify(repo: str) -> dict:
    declared = _declared_checks()
    status: dict = {
        "commit_sha": _git_sha(),
        "repo": repo,
        "required_checks_declared": bool(declared),
        "declared_checks": declared,
    }
    rulesets, err = _gh_json([f"repos/{repo}/rulesets"])
    if not isinstance(rulesets, list):
        status.update(
            {
                "required_checks_verified": False,
                "owner_action_required": True,
                "admin_bypass_allowed": None,
                "score_blocker": True,
                "note": f"cannot read rulesets ({err}); owner verification required",
            }
        )
        return status
    target = next((r for r in rulesets if r.get("name") == "main-integrity-gate"), None)
    if target is None:
        status.update(
            {
                "required_checks_verified": False,
                "owner_action_required": True,
                "admin_bypass_allowed": None,
                "score_blocker": True,
                "note": "no active main-integrity-gate ruleset found",
            }
        )
        return status
    detail, err = _gh_json([f"repos/{repo}/rulesets/{target['id']}"])
    actual: list[str] = []
    bypass = detail.get("bypass_actors") or [] if isinstance(detail, dict) else []
    if isinstance(detail, dict):
        for rule in detail.get("rules", []):
            if rule.get("type") == "required_status_checks":
                actual = [
                    c.get("context")
                    for c in rule.get("parameters", {}).get("required_status_checks", [])
                ]
    missing = sorted(set(declared) - set(actual))
    bypass_allowed = any(b.get("bypass_mode") == "always" for b in bypass)
    verified = bool(declared) and not missing and not bypass_allowed
    status.update(
        {
            "ruleset_enforcement": detail.get("enforcement") if isinstance(detail, dict) else None,
            "actual_required_checks": sorted(actual),
            "missing_required_checks": missing,
            "admin_bypass_allowed": bypass_allowed,
            "required_checks_verified": verified,
            "owner_action_required": not verified,
            "score_blocker": not verified,
        }
    )
    return status


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default="neuron7xLab/bsff")
    p.add_argument("--output", type=Path, default=OUT)
    args = p.parse_args(argv)
    status = verify(args.repo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))
    if status.get("required_checks_verified"):
        print("\nGOVERNANCE: VERIFIED — gates required, no admin bypass.")
        return 0
    print("\nGOVERNANCE: NOT VERIFIED — owner action required (see note/missing).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
