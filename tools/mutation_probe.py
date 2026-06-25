# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Mutation probe: do the tests have teeth, or just a high count?

Test count measures volume, not value. This mutates decision-critical logic in the
verdict engine and checks whether the test suite NOTICES (a killed mutant) or not
(a survived mutant = a real gap). It is baseline-guarded: if the suite is not green
before mutation, it aborts, because survivors would be meaningless.

CPU-bound (runs pytest per mutant) and not part of CI; the committed JSON is the
artifact. Re-run after changing the engine or the targeted tests.

    python tools/mutation_probe.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    "tests/test_bayesian_corroboration_gate.py",
    "tests/test_rank_order_verdict.py",
    "tests/test_unsupported_verdict.py",
    "tests/test_controls.py",
    "tests/test_invariants.py",
    "tests/test_low_surrogate_caveat.py",
]
# (relative file, old, new, label) — each a semantically meaningful single-point flip
MUTANTS = [
    (
        "src/bsff/verdict_engine.py",
        '"SURVIVED" if rejected else "REFUTED"',
        '"SURVIVED" if not rejected else "REFUTED"',
        "invert verdict assignment",
    ),
    (
        "src/bsff/verdict_engine.py",
        'float(bf["BF01"]) > 3.0',
        'float(bf["BF01"]) < 3.0',
        "flip BF01 null-evidence comparison",
    ),
    (
        "src/bsff/verdict_engine.py",
        'float(bf["BF10"]) < bayesian_corroboration_min',
        'float(bf["BF10"]) > bayesian_corroboration_min',
        "flip conjunction-gate comparison",
    ),
    (
        "src/bsff/verdict_engine.py",
        "if any_leakage_flagged(leakage_flags):",
        "if not any_leakage_flagged(leakage_flags):",
        "invert leakage fail-closed gate",
    ),
    (
        "src/bsff/verdict_engine.py",
        "spec.surrogate_count < 99",
        "spec.surrogate_count > 99",
        "flip low-surrogate caveat threshold",
    ),
]


def _run() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-q", "-x", "-p", "no:cacheprovider"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    ).returncode


def probe() -> dict:
    if _run() != 0:
        raise SystemExit("baseline not green — mutation results would be invalid")
    results = []
    for rel, old, new, label in MUTANTS:
        p = ROOT / rel
        orig = p.read_text(encoding="utf-8")
        if old not in orig:
            raise SystemExit(f"mutation target not found: {label}")
        try:
            p.write_text(orig.replace(old, new, 1), encoding="utf-8")
            killed = _run() != 0
        finally:
            p.write_text(orig, encoding="utf-8")
        results.append({"label": label, "killed": killed})
    killed = sum(r["killed"] for r in results)
    return {
        "mutants": len(results),
        "killed": killed,
        "score": round(killed / len(results), 3),
        "survivors": [r["label"] for r in results if not r["killed"]],
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "artifacts" / "mutation_probe.json")
    args = p.parse_args(argv)
    res = probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(res, indent=2), encoding="utf-8")
    for r in res["results"]:
        print(f"  [{'KILLED' if r['killed'] else 'SURVIVED'}] {r['label']}")
    print(f"\nMUTATION SCORE: {res['killed']}/{res['mutants']} (={res['score']})")
    if res["survivors"]:
        print("GAPS:", res["survivors"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
