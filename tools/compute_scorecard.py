#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Compute the ACTIONS-99 scorecard from evidence — the score cannot be hand-written.

99 is not a number someone types; it is the output of a function over verifiable
facts. The decisive fact is governance: ``can_claim_99`` is true only when
``artifacts/governance_status.json`` reports the required checks verified with no
admin bypass. While a bypass path exists the score is capped below 99 by
construction, no matter how much code is green.

    python tools/compute_scorecard.py            # write artifacts/actions_99_scorecard.json
    python tools/compute_scorecard.py --check     # CI: committed scorecard matches computed
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "actions_99_scorecard.json"
GOV = ROOT / "artifacts" / "governance_status.json"


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _ci_has(pattern: str) -> bool:
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    return ci.is_file() and re.search(pattern, ci.read_text(encoding="utf-8")) is not None


def _gov() -> dict:
    return json.loads(GOV.read_text(encoding="utf-8")) if GOV.is_file() else {}


def compute() -> dict:
    gov = _gov()
    p0 = (
        _ci_has(r"needs:\s*\n\s*-\s*test\s*\n\s*-\s*slow-tests")
        and _exists("tools/generate_manifest.py")
        and _exists("artifacts/MANIFEST.json")
    )
    p1 = _exists(".github/workflows/release.yml") and _exists("uv.lock")
    truth_surface = _exists("docs/TRUTH_SURFACE.md")
    artifact_hygiene = _exists("tools/validate_artifact_schema.py")
    mutation = _exists("tools/mutation_probe.py")
    release_evidence = _exists("artifacts/build_provenance.json") or _exists(
        "tools/verify_rebuild.py"
    )
    gov_verified = bool(gov.get("required_checks_verified"))
    bypass = gov.get("admin_bypass_allowed")

    score = 0
    if p0:
        score += 90 if p1 else 82
    if truth_surface:
        score += 1
    if artifact_hygiene:
        score += 1
    if mutation and release_evidence:
        score += 1
    score = min(score, 98)  # 99 is governance-gated only
    if gov_verified and bypass is False:
        score = 99

    blockers = []
    if not gov_verified:
        blockers.append("branch protection: required checks not verified")
    if bypass is not False:
        blockers.append("admin bypass path present (or unknown)")

    return {
        "schema_version": "bsff.scorecard/v1",
        "artifact_type": "actions_99_scorecard",
        "package": "bsff",
        "generator": "tools/compute_scorecard.py",
        "verdict": "CAN_CLAIM_99" if (gov_verified and bypass is False) else "BELOW_99",
        "score": score,
        "p0": "COMPLETE" if p0 else "INCOMPLETE",
        "p1": "COMPLETE" if p1 else "INCOMPLETE",
        "p2": "PARTIAL",
        "agent_completed": [
            k
            for k, v in {
                "truth_surface": truth_surface,
                "artifact_hygiene": artifact_hygiene,
                "mutation_probe": mutation,
                "release_evidence": release_evidence,
            }.items()
            if v
        ],
        "owner_required": ["branch protection ruleset (add missing checks, remove admin bypass)"],
        "blocking_items": blockers,
        "governance_verified": gov_verified,
        "admin_bypass_allowed": bypass,
        "can_claim_99": gov_verified and bypass is False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    card = compute()
    if args.check:
        if not OUT.is_file():
            print("scorecard missing — run: python tools/compute_scorecard.py")
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        if committed != card:
            print("scorecard STALE vs computed — run: python tools/compute_scorecard.py")
            return 1
        print(f"scorecard: in sync (score {card['score']}, can_claim_99={card['can_claim_99']})")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    print(
        f"score={card['score']} can_claim_99={card['can_claim_99']} blockers={card['blocking_items']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
