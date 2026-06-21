# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Run BSFF's self-falsification controls and enforce the contract, fail-closed.

Negative control (no structure) must NOT return SURVIVED; positive control
(genuine nonlinearity) MUST. If either fails, BSFF has no authority to judge
anything else, and this exits non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.controls import verify_controls  # noqa: E402

OUT = ROOT / "artifacts" / "controls"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--surrogates", type=int, default=99)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    result = verify_controls(seed=args.seed, n_surrogates=args.surrogates)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "negative_VERDICT.json").write_text(
        json.dumps(result["negative"], indent=2), encoding="utf-8"
    )
    (args.output / "positive_VERDICT.json").write_text(
        json.dumps(result["positive"], indent=2), encoding="utf-8"
    )
    (args.output / "controls.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        f"negative: {result['negative']['verdict']} (pass={result['negative']['control_passed']})"
    )
    print(
        f"positive: {result['positive']['verdict']} (pass={result['positive']['control_passed']})"
    )
    print(f"contract: {result['contract']}")
    if not result["controls_ok"]:
        print("CONTROLS FAILED — BSFF cannot be trusted to judge other claims.")
        return 1
    print("CONTROLS OK — BSFF fails and passes correctly on ground truth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
