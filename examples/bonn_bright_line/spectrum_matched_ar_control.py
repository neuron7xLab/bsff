#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
#
# SPECTRUM-MATCHED AR REAL NEGATIVE CONTROL (G2)
# ================================================
# Goal: prove BSFF's specificity (FPR <= alpha) on REAL spectral shapes.
# Method:
#   1. Read a real signal segment (Bonn TXT).
#   2. Fit AR(p) (Yule-Walker) to its spectrum.
#   3. Generate a genuinely-LINEAR Gaussian null with that spectrum.
#   4. Adjudicate the null with the BSFF INSTRUMENT (evaluate_claim_pipeline).
#   5. FPR = rate(verdict == SURVIVED). A correct instrument: FPR <= alpha.
#
# REPAIRS vs the candidate script (real bugs):
#   1. Per-set glob "*.txt" (original globbed only "Z*.txt").
#   2. VERDICT via evaluate_claim_pipeline (the BSFF instrument), NOT the raw
#      rank_order_surrogate_test intermediate (which is anti-conservative on colored
#      spectra; the raw rejection is kept for transparency).
#
# Usage:
#   python spectrum_matched_ar_control.py --input-dir ./bonn_data/A \
#          --n-segments 20 --ar-order 10 --n-surrogates 99

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

BSFF_SRC = Path(__file__).resolve().parents[2] / "src"
if str(BSFF_SRC) not in sys.path:
    sys.path.insert(0, str(BSFF_SRC))

from bsff import ClaimSpec, evaluate_claim_pipeline  # noqa: E402
from bsff.surrogate_engine import rank_order_surrogate_test  # noqa: E402

FloatArray = NDArray[np.float64]
ALPHA = 0.05
SEED_BASE = 20260624


def fit_ar(x: FloatArray, order: int) -> tuple[FloatArray, float]:
    from numpy.linalg import solve

    n = len(x)
    x = x - x.mean()
    r = np.array([np.dot(x[: n - k], x[k:]) / n for k in range(order + 1)])
    R = np.array([[r[abs(i - j)] for j in range(order)] for i in range(order)])
    rhs = r[1 : order + 1]
    try:
        coeffs = solve(R, rhs)
    except np.linalg.LinAlgError:
        coeffs = np.zeros(order)
    noise_var = max(float(r[0] - np.dot(coeffs, r[1 : order + 1])), 1e-12)
    return coeffs, noise_var


def generate_ar_null(x: FloatArray, order: int, seed: int) -> FloatArray:
    rng = np.random.default_rng(seed)
    coeffs, noise_var = fit_ar(x, order)
    n = len(x)
    noise = rng.normal(0, np.sqrt(noise_var), n + order * 2)
    out = np.zeros(n + order * 2)
    for t in range(order, n + order * 2):
        out[t] = np.dot(coeffs, out[t - order : t][::-1]) + noise[t]
    return out[order * 2 :].copy()


def load_segment(path: Path) -> FloatArray:
    arr = np.loadtxt(path, ndmin=2)
    if arr.shape[0] > arr.shape[1]:
        arr = arr.T
    return arr[0].astype(np.float64)


def _spec(seg_id: str, n: int, n_surr: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id=f"ar-null-{seg_id}", signal_type="EEG", task_type="nonlinear_structure",
        sampling_rate_hz=173.61, n_channels=1, n_samples=n, statistic="lagged_quadratic",
        alpha=ALPHA, surrogate_count=int(n_surr),
    )


def run_ar_control(input_dir: Path, *, n_segments: int, ar_order: int, n_surrogates: int, policy: str) -> dict:
    txt_files = sorted(input_dir.glob("*.txt"))[:n_segments]
    if not txt_files:
        raise FileNotFoundError(f"No *.txt in {input_dir}")
    results = []
    for i, fpath in enumerate(txt_files):
        seed = SEED_BASE + i
        x = load_segment(fpath)
        x_null = generate_ar_null(x, ar_order, seed=seed)
        x_null = (x_null - x_null.mean()) / (x_null.std() + 1e-12)
        raw_rej = bool(rank_order_surrogate_test(x_null, n_surrogates=n_surrogates, alpha=ALPHA, seed=seed + 10000)["rejected"])
        v = evaluate_claim_pipeline(_spec(fpath.stem, x_null.size, n_surrogates), x_null, policy=policy, seed=seed + 10000)
        fp = v.verdict == "SURVIVED"
        results.append({
            "segment_id": fpath.stem, "ar_order": ar_order, "n_samples": int(x.size),
            "raw_rank_order_rejected": raw_rej, "verdict": v.verdict,
            "is_false_positive": fp, "seed": seed, "policy": policy,
        })
        print(f"  {fpath.stem}: {v.verdict}{' ← FALSE POSITIVE' if fp else ''}  (raw_rej={raw_rej})")

    n_fp = sum(1 for r in results if r["is_false_positive"])
    n_raw_fp = sum(1 for r in results if r["raw_rank_order_rejected"])
    fpr = n_fp / len(results)
    raw_fpr = n_raw_fp / len(results)
    fpr_ok = fpr <= ALPHA
    print(f"\n  instrument FPR: {n_fp}/{len(results)} = {fpr:.3f}  (raw-rank FPR = {raw_fpr:.3f}) | threshold {ALPHA}")
    print(f"  FPR <= alpha: {fpr_ok}")
    return {
        "n_segments": len(results), "ar_order": ar_order, "n_surrogates": n_surrogates, "policy": policy,
        "n_false_positives": n_fp, "fpr": round(fpr, 4),
        "raw_rank_order_fpr": round(raw_fpr, 4), "fpr_threshold": ALPHA, "fpr_ok": fpr_ok,
        "results": results,
        "interpretation": (
            f"NEGATIVE CONTROL PASS: real-spectrum AR null -> instrument FPR={fpr:.3f} <= {ALPHA}. "
            f"(raw rank-order FPR={raw_fpr:.3f} is anti-conservative; the corroboration gate restores specificity.)"
            if fpr_ok else
            f"NEGATIVE CONTROL FAIL: instrument FPR={fpr:.3f} > {ALPHA} on real spectral shapes."
        ),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Spectrum-matched AR real negative control (G2)")
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--n-segments", type=int, default=20)
    p.add_argument("--ar-order", type=int, default=10)
    p.add_argument("--n-surrogates", type=int, default=99)
    p.add_argument("--policy", choices=["standard", "strict"], default="strict")
    p.add_argument("--output", type=Path, default=Path("ar_negative_control_VERDICT.json"))
    args = p.parse_args(argv)

    print("=" * 60)
    print("BSFF — Spectrum-Matched AR Negative Control (G2, instrument verdict)")
    print(f"  input={args.input_dir} n_segments={args.n_segments} ar_order={args.ar_order} "
          f"n_surrogates={args.n_surrogates} policy={args.policy} alpha={ALPHA}")
    print("=" * 60)

    t0 = time.time()
    ctrl = run_ar_control(args.input_dir, n_segments=args.n_segments, ar_order=args.ar_order,
                          n_surrogates=args.n_surrogates, policy=args.policy)
    bundle = {"schema": "bsff.ar_negative_control/v2", "elapsed_sec": round(time.time() - t0, 2), "control": ctrl}
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"\n  {ctrl['interpretation']}\nEvidence bundle -> {args.output}")
    return 0 if ctrl["fpr_ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
