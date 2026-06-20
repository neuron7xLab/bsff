#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Measure and persist the BSFF instrument operating characteristic.

Runs the labelled ground-truth battery (deterministic-chaos vs linear-Gaussian /
white-noise nulls) and writes a machine-readable report comparing the
frequentist-only decision rule against the shipped frequentist-AND-Bayesian
conjunction rule. The artifact is the empirical evidence that the conjunction
gate restores nominal specificity without costing power.

    python tools/calibrate_operating_characteristic.py            # default (heavy)
    python tools/calibrate_operating_characteristic.py --quick    # fast smoke

The heavy default is intended for local / nightly runs; --quick is a cheap
sanity pass. Deterministic: same flags => same artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.operating_characteristic import measure_operating_characteristic  # noqa: E402

OUT = ROOT / "artifacts" / "operating_characteristic.json"


def _summary_lines(payload: dict) -> list[str]:
    lines = ["class                power/FPR  frequentist  conjunction  verdict"]
    for c in payload["classes"]:
        target = "power" if c["expect_survive"] else "FPR  "
        ok = (
            c["conjunction_survive_rate"] >= 0.95
            if c["expect_survive"]
            else c["conjunction_ci95"][0] <= payload["config"]["alpha"]
        )
        lines.append(
            f"{c['name']:<20}{target:>9}  "
            f"{c['frequentist_survive_rate']:>11.3f}  "
            f"{c['conjunction_survive_rate']:>11.3f}  "
            f"{'OK' if ok else 'CHECK'}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="fast reduced-seed smoke run")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    if args.quick:
        oc = measure_operating_characteristic(
            n_seeds=12, n_samples=512, surrogate_count=49, corroboration_min=3.0
        )
    else:
        oc = measure_operating_characteristic(
            n_seeds=60, n_samples=1024, surrogate_count=99, corroboration_min=3.0
        )

    payload = oc.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for line in _summary_lines(payload):
        print(line)
    print(f"\nWrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
