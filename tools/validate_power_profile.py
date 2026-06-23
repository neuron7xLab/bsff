#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Fail-closed gate over a measured statistical power profile.

Blocking conditions (exit 1): the null false-positive rate exceeds its limit, the
surrogate convergence rate is below threshold, or seed stability is violated — any
of these means the instrument's verdicts are not trustworthy. A sub-threshold
positive-control detection is reported as scientific status UNSUPPORTED; for the
validation grid to pass, the profile verdict must be PASS.

    python tools/validate_power_profile.py [path]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "artifacts" / "statistics" / "power_profile.json"


def validate(path: Path) -> list[str]:
    if not path.is_file():
        return [f"power profile not found: {path}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    m = data.get("measured", {})
    t = data.get("thresholds", {})
    failures: list[str] = []

    fpr = float(m.get("null_false_positive_rate", 1.0))
    if fpr > float(t.get("null_false_positive_rate_max", 0.05)):
        failures.append(f"null false-positive rate {fpr} exceeds limit (BLOCKING)")

    conv = float(m.get("surrogate_convergence_rate", 0.0))
    if conv < float(t.get("surrogate_convergence_min", 0.95)):
        failures.append(f"surrogate convergence {conv} below threshold (BLOCKING)")

    if t.get("seed_stability_required", True) and not bool(m.get("seed_stable", False)):
        failures.append("seed stability violated (BLOCKING)")

    detection = float(m.get("positive_control_detection", 0.0))
    if detection < float(t.get("positive_control_detection_min", 0.80)):
        failures.append(f"positive-control detection {detection} below threshold (UNSUPPORTED)")

    if data.get("verdict") != "PASS":
        failures.append(f"power profile verdict is not PASS: {data.get('verdict')}")
    return failures


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else DEFAULT
    failures = validate(path)
    if failures:
        print("Statistical power profile FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    m = data["measured"]
    print(
        f"Statistical power: PASS (FPR={m['null_false_positive_rate']}, "
        f"detection={m['positive_control_detection']}, convergence={m['surrogate_convergence_rate']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
