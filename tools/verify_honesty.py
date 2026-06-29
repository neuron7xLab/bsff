# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The honesty gate: one deterministic, fail-closed command over the whole
self-verification stack. Automation of the automation.

First-principle (the bounded, honest guarantee): no software is "100% unable to
lie". What this gate makes *impossible to merge* is a specific, enumerated set of
decorative lies — a VERIFIED claim with no command, a soft status word, an
unsourced threshold, an implicit null, a stale test count, a failed control, or a
silently-passed blocked item. Each is a separate sub-check; the gate is the
conjunction. It is deterministic (no network, no randomness beyond fixed seeds)
and fail-closed (any sub-check non-zero fails the whole gate).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "honesty" / "HONESTY_GATE.json"

# (id, argv) — each must exit 0. Pure-Python, no network/GPU.
CHECKS: list[tuple[str, list[str]]] = [
    ("claim_audit_no_decorative_verified", ["tools/validate_claim_audit.py"]),
    ("grounding_numbers_match_artifacts", ["tools/verify_grounding.py"]),
    ("null_hypotheses_explicit", ["tools/validate_null_registry.py"]),
    ("thresholds_have_provenance", ["tools/validate_threshold_registry.py"]),
    ("self_falsification_controls", ["tools/verify_controls.py"]),
    ("status_metadata_is_generated_and_in_sync", ["tools/update_status.py", "--check"]),
    ("status_count_live_collection", ["tools/update_status.py", "--verify-count"]),
    ("contract_self_conformance", ["tools/run_contract_conformance.py"]),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    results = []
    for check_id, cmd in CHECKS:
        proc = subprocess.run(
            [sys.executable, str(ROOT / cmd[0]), *cmd[1:]],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        ok = proc.returncode == 0
        results.append(
            {
                "check": check_id,
                "exit": proc.returncode,
                "ok": ok,
                "tail": (proc.stdout.strip().splitlines() or [""])[-1],
            }
        )

    ok = all(r["ok"] for r in results)
    payload = {"gate": "bsff_honesty_v1", "all_ok": ok, "checks": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for r in results:
        print(f"  {'[ok]' if r['ok'] else '[X]'} {r['check']:42} exit={r['exit']}")
    if not ok:
        print(
            "\nHONESTY GATE: FAIL — a decorative-lie sub-check did not pass. Merge must be blocked."
        )
        return 1
    print(
        "\nHONESTY GATE: PASS — no decorative VERIFIED, no soft state, no unsourced "
        "threshold, no implicit null, no stale count, live count is collectable, "
        "controls hold, contract self-conformant."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
