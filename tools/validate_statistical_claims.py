#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Statistical-claims gate (PI-grade): a point estimate must not be sold as a final pass
when the confidence interval crosses the threshold.

Fails CI if:
 1. CURRENT_TRUTH lacks the robustness fields (robustness state absent).
 2. The G2 specificity CI upper bound > 0.05 but the canonical state still claims a robust /
    unqualified bright-line pass (point-estimate-as-pass while CI crosses the gate).
 3. A public surface headlines a robust pass while robust_gate_passed is false.
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
SURFACES = ["README.md", "FORMAL_VERDICT.md", "STATUS.md", "docs/validation/CLAIM_AUDIT.md"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="artifacts/release/STATISTICAL_CLAIMS_REPORT.json")
    a = ap.parse_args(argv)
    t = json.loads(TRUTH.read_text())
    viol = []

    required = {
        "robust_gate",
        "robust_gate_passed",
        "s2_wilson_ci_upper",
        "bonn_s2_robustness_state",
    }
    missing = [k for k in required if k not in t]
    if missing:
        viol.append(f"CURRENT_TRUTH missing robustness fields: {missing}")

    ci_upper = t.get("s2_wilson_ci_upper")
    gate_passed = t.get("robust_gate_passed")
    state = t.get("latest_validation_state", "")
    # 2. CI crosses the gate but the state claims a robust/unqualified pass.
    if ci_upper is not None and ci_upper > 0.05:
        if gate_passed is True:
            viol.append(
                f"robust_gate_passed=True but CI upper {ci_upper} > 0.05 (point-estimate-as-pass)"
            )
        if state in {"BONN_S2_BRIGHT_LINE_PASSED", "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED"}:
            viol.append(
                f"latest_validation_state={state!r} claims a (robust) pass while CI upper {ci_upper} > 0.05"
            )

    # 3. Public surfaces must not headline a robust/unqualified pass while gate not passed.
    if gate_passed is not True:
        bad = re.compile(
            r"robustly (?:passed|crossed|validated)|bright[- ]line (?:robustly )?validated", re.I
        )
        neg = re.compile(r"\bnot\b|\bno\b|never|n't|fail|marginal|favorable[- ]seed|crosses")
        for rel in SURFACES:
            p = ROOT / rel
            if not p.is_file():
                continue
            lines = p.read_text(encoding="utf-8").splitlines()
            lows = [ln.lower() for ln in lines]
            for i, ln in enumerate(lines):
                # negation context = this line + previous 2 (handles wrapped "not\nrobustly crossed").
                ctx = " ".join(lows[max(0, i - 2): i + 1])
                if bad.search(ln) and not neg.search(ctx):
                    viol.append(
                        f"{rel}:{i + 1}: claims robust pass while robust_gate_passed!=True: {ln.strip()[:60]}"
                    )

    status = "PASS" if not viol else "FAIL"
    rep = {
        "schema": "bsff.statistical_claims/v1",
        "status": status,
        "latest_validation_state": state,
        "s2_wilson_ci_upper": ci_upper,
        "robust_gate_passed": gate_passed,
        "violations": viol,
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (ROOT / a.output).write_text(json.dumps(rep, indent=2) + "\n")
    print(f"STATISTICAL_CLAIMS: {status}")
    for v in viol:
        print("  -", v)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
