#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Claim-safety gate (Phase 5): fail CI if any public surface makes a forbidden affirmative
claim, or a state-contingent claim (BNCI validated / multi-dataset replicated) that the
executed artifacts do not support.

Forbidden forever: clinical diagnosis, medical decision support, seizure product, regulatory
validation, universal BCI authority, proof of brain nonlinear dynamics. State-contingent:
"BNCI validated" only if bnci_execution_state == BNCI_CONFIRMATORY_PASSED; "replicated" /
"multi-dataset validated" only if replication confirmatory artifacts exist.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json"

SURFACES = [
    "README.md",
    "FORMAL_VERDICT.md",
    "STATUS.md",
    "REPRODUCE.md",
    "docs/validation/CLAIM_AUDIT.md",
    "docs/validation/BONN_STATUS.md",
    "docs/reviewer_packet/REVIEWER_PACKET.md",
    "docs/QUICKSTART.md",
]
# Forbidden affirmative claims (allowed only when the line negates/forbids them).
FOREVER_FORBIDDEN = [
    (r"clinical(?:ly)? (?:proven|validated|approved|diagnos)", "clinical diagnosis/validation"),
    (r"medical (?:device|decision support|diagnosis|use)", "medical decision support / device"),
    (r"seizure[- ](?:detection )?(?:product|device)", "seizure product"),
    (r"regulatory[- ](?:validated|grade|approval|clearance)", "regulatory validation"),
    (r"universal (?:BCI )?(?:benchmark )?authority", "universal BCI authority"),
    (
        r"proof of brain nonlinear dynamics|prove[sd]? brain (?:nonlinear )?dynamics",
        "proof of brain dynamics",
    ),
    (r"\bFDA\b", "FDA"),
]
NEG = re.compile(r"\bno\b|\bnot\b|\bnever\b|forbidden|excluded|out of scope|n't|without")


def _replication_done() -> bool:
    rep = ROOT / "artifacts" / "replication"
    return rep.is_dir() and any(rep.glob("**/CONFIRMATORY_VERDICT.json"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="artifacts/release/CLAIM_SAFETY_REPORT.json")
    a = ap.parse_args(argv)
    truth = json.loads(TRUTH.read_text()) if TRUTH.is_file() else {}
    bnci_passed = truth.get("bnci_execution_state") == "BNCI_CONFIRMATORY_PASSED"
    replicated = _replication_done()

    violations = []
    for rel in SURFACES:
        p = ROOT / rel
        if not p.is_file():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        lows = [ln.lower() for ln in lines]
        for i, low in enumerate(lows):
            # A forbidding context (this line or the previous 3) allows the vocabulary —
            # docs that enumerate forbidden claims to forbid them are not violations.
            ctx = " ".join(lows[max(0, i - 3) : i + 1])
            negated = bool(NEG.search(ctx))
            for pat, why in FOREVER_FORBIDDEN:
                if re.search(pat, low) and not negated:
                    violations.append(f"{rel}:{i + 1}: forbidden ({why}): {lines[i].strip()[:70]}")
            if re.search(r"bnci\b[^.\n]*validated", low) and not bnci_passed and not negated:
                violations.append(
                    f"{rel}:{i + 1}: 'BNCI validated' but bnci_execution_state != PASSED"
                )
            if (
                re.search(r"(multi[- ]dataset|cross[- ]dataset)[^.\n]*(validated|replicated)", low)
                and not replicated
                and not negated
            ):
                violations.append(
                    f"{rel}:{i + 1}: replication claimed but no replication artifacts"
                )

    status = "PASS" if not violations else "FAIL"
    report = {
        "schema": "bsff.claim_safety/v1",
        "status": status,
        "bnci_validated_allowed": bnci_passed,
        "replication_artifacts_present": replicated,
        "checked": [s for s in SURFACES if (ROOT / s).is_file()],
        "violations": violations,
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (ROOT / a.output).write_text(json.dumps(report, indent=2) + "\n")
    print(f"CLAIM_SAFETY: {status}")
    for v in violations:
        print("  -", v)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
