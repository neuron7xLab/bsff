# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Validate that every threshold carries provenance (fail-closed).

No hardcoded magic numbers: each threshold must declare a value, a reason, and a
source. A threshold without provenance is pseudoscience with a number.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("value", "reason", "source")


def main(argv: list[str] | None = None) -> int:
    import yaml

    path = ROOT / "thresholds.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    thresholds = (data or {}).get("thresholds", {})
    if not thresholds:
        print("FAIL: no thresholds registered")
        return 1
    failures = []
    for name, spec in thresholds.items():
        for field in REQUIRED:
            if spec.get(field) in (None, ""):
                failures.append(f"{name}: missing '{field}'")
    if failures:
        print("Threshold registry FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"Threshold registry OK: {len(thresholds)} thresholds, all with provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
