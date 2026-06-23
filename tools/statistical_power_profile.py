#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Measure the instrument's statistical operating characteristic, deterministically.

Power is not a slogan. This runs a fixed-seed Monte-Carlo over linear-Gaussian
nulls and nonlinear positive controls and records the measured operating
characteristic: null false-positive rate, positive-control detection (power),
surrogate convergence rate, a coarse minimum-detectable-effect curve, and seed
stability. The result is written to ``artifacts/statistics/power_profile.json``.

    python tools/statistical_power_profile.py --output artifacts/statistics/power_profile.json

Fail-closed semantics live in ``tools/validate_power_profile.py``: an excess
false-positive rate, a sub-threshold convergence rate, or seed instability are
blocking; sub-threshold detection demotes the scientific verdict to UNSUPPORTED.
Deterministic: explicit seeds, no wall-clock, no network.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.synthetic import ar1_multichannel, henon_series, white_noise_series

ROOT = Path(__file__).resolve().parents[1]

THRESHOLDS = {
    "null_false_positive_rate_max": 0.05,
    "positive_control_detection_min": 0.80,
    "surrogate_convergence_min": 0.95,
    "seed_stability_required": True,
}
N_NULL = 40
N_POSITIVE = 30
MDE_FRACTIONS = (0.2, 0.4, 0.6, 0.8, 1.0)
MDE_SEEDS = 10


def _spec(n_samples: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="power",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def _evaluate(signal, n_samples):
    v = evaluate_claim_pipeline(_spec(n_samples), signal, policy="standard", seed=101)
    surrogate = next(n for n in v.evidence_graph["nodes"] if n["stage_id"] == "surrogate_attack")
    converged = bool(surrogate["evidence"]["surrogate_convergence"]["all_converged"])
    return v.verdict, converged


def _standardize(z: np.ndarray) -> np.ndarray:
    z = z - z.mean()
    return (z / (z.std() + 1e-12)).astype(float)


def profile() -> dict:
    # Null specificity: linear-Gaussian AR(1) must rarely SURVIVE.
    null_survived = 0
    conv_hits = conv_total = 0
    for s in range(N_NULL):
        verdict, converged = _evaluate(ar1_multichannel(1, 512, seed=s)[0], 512)
        null_survived += int(verdict == "SURVIVED")
        conv_total += 1
        conv_hits += int(converged)
    null_fpr = null_survived / N_NULL

    # Positive control: nonlinear Hénon must SURVIVE (power).
    detected = 0
    for s in range(N_POSITIVE):
        verdict, converged = _evaluate(henon_series(768, seed=s), 768)
        detected += int(verdict == "SURVIVED")
        conv_total += 1
        conv_hits += int(converged)
    detection = detected / N_POSITIVE
    convergence_rate = conv_hits / conv_total

    # Coarse minimum-detectable-effect: smallest Hénon signal fraction (mixed with
    # white noise) whose detection rate clears the power threshold.
    mde = None
    mde_curve = {}
    for frac in MDE_FRACTIONS:
        hits = 0
        for s in range(MDE_SEEDS):
            sig = _standardize(
                frac * henon_series(768, seed=100 + s)
                + (1.0 - frac) * white_noise_series(768, seed=200 + s)
            )
            verdict, _ = _evaluate(sig, 768)
            hits += int(verdict == "SURVIVED")
        rate = hits / MDE_SEEDS
        mde_curve[f"{frac:.1f}"] = rate
        if mde is None and rate >= THRESHOLDS["positive_control_detection_min"]:
            mde = frac

    # Seed stability: identical input + seed must give an identical verdict.
    a, _ = _evaluate(henon_series(768, seed=11), 768)
    b, _ = _evaluate(henon_series(768, seed=11), 768)
    seed_stable = a == b

    measured = {
        "null_false_positive_rate": round(null_fpr, 4),
        "positive_control_detection": round(detection, 4),
        "surrogate_convergence_rate": round(convergence_rate, 4),
        "false_negative_estimate": round(1.0 - detection, 4),
        "minimum_detectable_effect": mde,
        "minimum_detectable_effect_curve": mde_curve,
        "seed_stable": bool(seed_stable),
        "n_null": N_NULL,
        "n_positive": N_POSITIVE,
    }

    blocking = (
        null_fpr <= THRESHOLDS["null_false_positive_rate_max"]
        and convergence_rate >= THRESHOLDS["surrogate_convergence_min"]
        and seed_stable
    )
    if not blocking:
        verdict = "FAIL"
    elif detection < THRESHOLDS["positive_control_detection_min"]:
        verdict = "UNSUPPORTED"
    else:
        verdict = "PASS"

    return {"measured": measured, "thresholds": THRESHOLDS, "verdict": verdict}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts" / "statistics" / "power_profile.json"
    )
    args = parser.parse_args(argv)
    result = profile()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    m = result["measured"]
    print(
        f"power profile: FPR={m['null_false_positive_rate']} detection={m['positive_control_detection']} "
        f"convergence={m['surrogate_convergence_rate']} seed_stable={m['seed_stable']} "
        f"-> {result['verdict']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
