#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Validate a mutation-kill report: 100% or it fails closed.

A mutation report is only a gate if a single survivor blocks the build. This reads
``artifacts/adversarial/mutation_kill_report.json`` (or a path argument) and asserts
the report is internally consistent and reflects a perfect score: at least the
expected number of critical mutants, every one killed, no survivors, a 1.0 score,
and a PASS verdict. Any deviation exits non-zero.

    python tools/validate_mutation_report.py [path]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "artifacts" / "adversarial" / "mutation_kill_report.json"
MIN_MUTANTS = 8


def validate(path: Path) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        return [f"mutation report not found: {path}"]
    data = json.loads(path.read_text(encoding="utf-8"))

    total = int(data.get("mutants_total", 0))
    killed = int(data.get("mutants_killed", 0))
    survivors = data.get("survivors", ["<missing>"])
    score = float(data.get("mutation_score", 0.0))
    verdict = str(data.get("verdict", "FAIL"))
    results = data.get("results", [])

    if total < MIN_MUTANTS:
        failures.append(f"too few mutants: {total} < {MIN_MUTANTS}")
    if killed != total:
        failures.append(f"not all mutants killed: {killed}/{total}")
    if survivors:
        failures.append(f"surviving mutants: {survivors}")
    if abs(score - 1.0) > 1e-9:
        failures.append(f"mutation score is not 1.0: {score}")
    if verdict != "PASS":
        failures.append(f"report verdict is not PASS: {verdict}")
    if len(results) != total:
        failures.append(f"results length {len(results)} != mutants_total {total}")
    for r in results:
        if r.get("mutant_status") != "killed":
            failures.append(f"mutant not killed: {r.get('mutant_id')}")
    return failures


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else DEFAULT
    failures = validate(path)
    if failures:
        print("Mutation report INVALID:")
        for item in failures:
            print(f"- {item}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    print(
        f"Mutation report: PASS ({data['mutants_killed']}/{data['mutants_total']} killed, score 1.0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
