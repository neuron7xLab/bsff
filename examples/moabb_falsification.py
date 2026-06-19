# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Falsify a motor-imagery decoding claim on a real BCI dataset via MOABB.

This is a demonstration, not a CI gate: it requires the optional ``moabb`` stack
and downloads the BNCI2014-001 dataset on first run. It shows the intended usage
of BSFF against genuine EEG rather than synthetic fixtures, and writes the
machine-readable verdict to disk.

    pip install moabb
    PYTHONPATH=src python examples/moabb_falsification.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bsff import ClaimSpec, evaluate_claim

OUT = Path("artifacts/moabb_verdict.json")


def main() -> int:
    try:
        from moabb.datasets import BNCI2014_001
        from moabb.paradigms import LeftRightImagery
    except ImportError:
        print(
            "moabb is not installed. This example is optional:\n"
            "    pip install moabb\n"
            "then re-run. BSFF core has no moabb dependency.",
            file=sys.stderr,
        )
        return 1

    dataset = BNCI2014_001()
    paradigm = LeftRightImagery(fmin=8.0, fmax=35.0)
    x, _labels, _metadata = paradigm.get_data(dataset, subjects=[1])

    trial = x[0]  # (channels, samples)
    spec = ClaimSpec(
        claim_id="BNCI2014_001_subject1_left_right_MI",
        signal_type="EEG",
        task_type="classification",
        sampling_rate_hz=250.0,
        n_channels=trial.shape[0],
        n_samples=trial.shape[1],
        statistic="lagged_quadratic",
        surrogate_count=99,
        alpha=0.05,
        metadata={"bayesian_evidence": True, "dataset": "BNCI2014_001"},
    )

    verdict = evaluate_claim(spec, trial, seed=123)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verdict.to_dict(), indent=2, sort_keys=True) + "\n")
    print(f"verdict={verdict.verdict} p_value={verdict.p_value}")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
