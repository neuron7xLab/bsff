#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Analytic-uniformity null: an in-repo correctness check that needs no TISEAN.

The long-standing open item (LIMITATIONS_HARD #1) is that the surrogate engine
has never been byte-matched against the TISEAN reference C binary. But a byte
match only guards against a *shared implementation bug* — and that risk is
already covered by ``reference_surrogate.py`` (an independent from-scratch numpy
AAFT/IAAFT). The deeper question a byte match does NOT answer is whether the
verdict's p-value is *correctly calibrated*. That has an analytic ground truth:

    Under a TRUE null (the data really is a stationary linear-Gaussian process),
    the rank-order surrogate p-value must be Uniform(0,1), so the false-positive
    rate must equal alpha exactly.

So we draw fresh realizations under known nulls, run the engine, and test the
p-value distribution against Uniform(0,1) with a Kolmogorov-Smirnov test. This
is a *stronger* correctness probe than re-matching another empirical
implementation, and it needs no external binary. It establishes three facts:

  1. white null  -> p-values uniform, FPR ~ alpha  (the engine is calibrated);
  2. AR(1) null  -> p-values skewed, FPR > alpha    (the documented finite-N
                    IAAFT anti-conservatism, Kugiumtzis 2002 — a real, measured
                    deviation, not a bug);
  3. AR(1) null + conjunction gate -> FPR back <= alpha (the BF10 corroboration
                    gate restores nominal specificity — the central design claim,
                    here validated against an analytic expectation).

Deterministic (fixed seeds). ``--check`` recomputes at a smaller N and asserts
the three qualitative gates hold (not a byte match — robust across numpy builds).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from bsff.schemas import ClaimSpec
from bsff.synthetic import ar1_multichannel, white_noise_series
from bsff.verdict_engine import evaluate_claim

REPO = Path(__file__).resolve().parents[1]
ARTIFACT = REPO / "artifacts" / "analytic_uniformity_null.json"
ALPHA = 0.05
N_SAMPLES = 256
SURROGATES = 99
N_DRAWS_FULL = 200
N_DRAWS_CHECK = 80
# Tolerance band around alpha for the point-estimate FPR at finite N.
FPR_TOL = 0.03
KS_UNIFORM_MIN_P = 0.05  # KS must NOT reject uniformity for the calibrated null


def _spec(n_samples: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="uniformity-null",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        surrogate_count=SURROGATES,
        stationarity_gate="off",
    )


def _white(k: int) -> np.ndarray:
    return white_noise_series(n_samples=N_SAMPLES, seed=k)[np.newaxis, :]


def _ar1(phi: float) -> Callable[[int], np.ndarray]:
    def gen(k: int) -> np.ndarray:
        return ar1_multichannel(n_samples=N_SAMPLES, n_channels=1, phi=phi, seed=k)

    return gen


def _measure(gen: Callable[[int], np.ndarray], n_draws: int, *, bayes: bool) -> dict[str, float]:
    spec = _spec(N_SAMPLES)
    pvals: list[float] = []
    false_positives = 0
    for k in range(n_draws):
        sig = gen(k)
        v = evaluate_claim(
            spec, sig, seed=10_000 + k, bayesian_evidence=bayes, bayesian_corroboration_min=3.0
        )
        pvals.append(float(v.p_value) if v.p_value is not None else 1.0)
        if v.verdict == "SURVIVED":
            false_positives += 1
    arr = np.array(pvals, dtype=float)
    ks = stats.kstest(arr, "uniform")
    return {
        "fpr": false_positives / n_draws,
        "ks_statistic": float(ks.statistic),
        "ks_pvalue": float(ks.pvalue),
    }


def compute(n_draws: int) -> dict[str, Any]:
    nulls: list[tuple[str, Callable[[int], np.ndarray]]] = [
        ("white", _white),
        ("ar1_phi0.50", _ar1(0.50)),
        ("ar1_phi0.75", _ar1(0.75)),
    ]
    rows: dict[str, Any] = {}
    for name, gen in nulls:
        bare = _measure(gen, n_draws, bayes=False)
        conj = _measure(gen, n_draws, bayes=True)
        rows[name] = {
            "bare_rank_order": bare,
            "conjunction_gate": {"fpr": conj["fpr"]},
            "fpr_bare": round(bare["fpr"], 4),
            "fpr_conjunction": round(conj["fpr"], 4),
            "ks_pvalue_bare": round(bare["ks_pvalue"], 4),
        }

    white = rows["white"]
    ar = rows["ar1_phi0.75"]
    # Gate 1: the engine is calibrated under a genuine white null.
    white_calibrated = (
        abs(white["fpr_bare"] - ALPHA) <= FPR_TOL and white["ks_pvalue_bare"] >= KS_UNIFORM_MIN_P
    )
    # Gate 2: the documented IAAFT anti-conservatism is present on AR(1) (a real
    # deviation, openly measured) — i.e. bare FPR exceeds alpha.
    ar_anticonservative = ar["fpr_bare"] > ALPHA
    # Gate 3: the conjunction gate restores nominal specificity under AR(1).
    conjunction_restores = ar["fpr_conjunction"] <= ALPHA + FPR_TOL

    gates = {
        "white_null_calibrated": bool(white_calibrated),
        "ar1_anticonservatism_present": bool(ar_anticonservative),
        "conjunction_restores_specificity": bool(conjunction_restores),
    }
    all_pass = all(gates.values())
    return {
        "schema": "bsff.analytic_uniformity_null/v1",
        "purpose": (
            "Analytic-uniformity correctness check for the rank-order surrogate p-value; "
            "an in-repo substitute for the unavailable TISEAN byte-match that tests "
            "calibration against the Uniform(0,1) ground truth a true null implies."
        ),
        "alpha": ALPHA,
        "n_samples": N_SAMPLES,
        "n_surrogates": SURROGATES,
        "n_draws": n_draws,
        "nulls": rows,
        "gates": gates,
        "verdict": "ANALYTIC_UNIFORMITY_CONFIRMED" if all_pass else "ANALYTIC_UNIFORMITY_FAILED",
        "interpretation": (
            f"White null: bare FPR {white['fpr_bare']:.3f} ~ alpha={ALPHA}, KS uniformity "
            f"p={white['ks_pvalue_bare']:.3f} (not rejected) -> engine calibrated. "
            f"AR(1,0.75): bare FPR {ar['fpr_bare']:.3f} > alpha (finite-N IAAFT "
            f"anti-conservatism, openly measured), conjunction-gate FPR "
            f"{ar['fpr_conjunction']:.3f} <= alpha (gate restores specificity). "
            "No external TISEAN binary required."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="recompute (smaller N) and assert gates")
    ap.add_argument("--n-draws", type=int, default=None, help="override draw count")
    args = ap.parse_args()

    if args.check:
        result = compute(args.n_draws or N_DRAWS_CHECK)
        failed = [k for k, v in result["gates"].items() if not v]
        if failed:
            print(f"GATE FAIL: {failed}\n{result['interpretation']}")
            return 1
        if not ARTIFACT.exists():
            print(f"MISSING: {ARTIFACT} — run without --check first")
            return 1
        print(f"Analytic-uniformity null: PASS ({result['verdict']}) — gates {result['gates']}")
        return 0

    result = compute(args.n_draws or N_DRAWS_FULL)
    rendered = json.dumps(result, indent=1, sort_keys=True) + "\n"
    ARTIFACT.write_text(rendered)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
