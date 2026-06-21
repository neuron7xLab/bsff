# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Apex command: prove the entire cognitive systemic core in one run.

Cascades the full stack via the decision gate (which runs the honesty gate and
the certificate chain, which in turn run controls, registries, grounding,
conformance, demonstration), then prints a one-screen summary ending on the
derived recommendation. Exit code reflects the core's health.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "decision_gate.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    decision_path = ROOT / "artifacts" / "decision" / "decision.json"
    if not decision_path.is_file():
        print("core verification did not produce a decision artifact")
        print(proc.stdout, proc.stderr)
        return 1
    d = json.loads(decision_path.read_text(encoding="utf-8"))

    print("BSFF — cognitive systemic core\n")
    for c in d["criteria"]:
        print(
            f"  [{'ok' if c['met'] else 'X '}] {c['id']} ({'must' if c['must'] else 'stretch'})  {c['title']}"
        )
    print(f"\n  certificate root: {(d.get('certificate_root') or '')[:16]}…")
    print(
        f"  self-conformance: {d['conformance']['overall']} "
        f"({d['conformance']['unverifiable']} legs honestly UNVERIFIABLE)"
    )
    print(f"\nRECOMMENDATION: {d['recommendation']}")
    # green iff all must-criteria are met (CONDITIONAL GO is an honest pass)
    return 0 if d["must_criteria_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
