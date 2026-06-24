#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Multi-null robustness gate (predeclared: docs/validation/MULTI_NULL_ROBUSTNESS_PROTOCOL.md).

The null model is a researcher degree of freedom. Specificity is robust only if the seed-averaged
AR-null result holds across independent linear-null families. For each null model the gate is the
same as S3: pooled seed-averaged FPR Wilson-95-CI upper bound <= 0.05.

Null families (each generates the NULL DATA from the real Set-A/B signals, then runs the unchanged
S2-C1 sampen lower-tail test on it; a linear null must NOT survive):
  - ar        : spectrum-matched AR(p)            (reuses run_ar_negative.ar_null; = S3)
  - iaaft     : classic Schreiber-Schmitz IAAFT   (preserves spectrum + amplitude distribution)
  - phaserand : Fourier phase randomization        (preserves spectrum, Gaussianizes)
The iaaft/phaserand generators are standalone (independent of the test's internal MIAAFT).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from loader import load_set  # noqa: E402
from run_ar_negative import ar_null  # noqa: E402
from statistics_sampen import sampen_lower_tail_test  # noqa: E402

NSUR = 199
ALPHA_EFF = 0.025
G2_MAX_FPR = 0.05
SEEDS = [20260623, 7, 999, 314159, 2718, 42, 161803, 27182, 31337, 123456]


def phaserand_null(x, seed):
    """Fourier phase-randomized surrogate: keep amplitudes, randomize phases."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    f = np.fft.rfft(x)
    phases = rng.uniform(0, 2 * np.pi, size=f.shape)
    phases[0] = 0.0
    if x.size % 2 == 0:
        phases[-1] = 0.0
    return np.fft.irfft(np.abs(f) * np.exp(1j * phases), n=x.size)


def iaaft_null(x, seed, iters=100):
    """Classic Schreiber-Schmitz IAAFT: matches power spectrum AND amplitude distribution."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    amp = np.abs(np.fft.rfft(x))
    sorted_x = np.sort(x)
    surr = rng.permutation(x)
    prev = None
    for _ in range(iters):
        # impose spectrum
        f = np.fft.rfft(surr)
        surr = np.fft.irfft(amp * np.exp(1j * np.angle(f)), n=x.size)
        # impose amplitude distribution (rank-match)
        ranks = np.argsort(np.argsort(surr))
        surr = sorted_x[ranks]
        if prev is not None and np.array_equal(np.argsort(surr), prev):
            break
        prev = np.argsort(surr)
    return surr


NULLS = {"ar": lambda s, sd: ar_null(s, 10, sd), "iaaft": iaaft_null, "phaserand": phaserand_null}


def _survived(sig, seed):
    t = sampen_lower_tail_test(np.asarray(sig, float), n_surrogates=NSUR, alpha=0.05, seed=seed)
    return t["surrogate_converged"] and t["p_value"] <= ALPHA_EFF


def _wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = (z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den
    return float(p), float(max(0.0, c - h)), float(min(1.0, c + h))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="examples/bonn_bright_line/bonn_data", type=Path)
    ap.add_argument("--n-segments", type=int, default=50)
    ap.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    ap.add_argument("--nulls", nargs="+", default=["ar", "iaaft", "phaserand"])
    ap.add_argument(
        "--output", type=Path, default=Path("artifacts/bonn_bright_line/MULTI_NULL_ROBUSTNESS.json")
    )
    a = ap.parse_args(argv)
    t0 = time.time()
    A = [s.data for s in load_set(a.data_dir, "A", n_segments=a.n_segments)]
    B = [s.data for s in load_set(a.data_dir, "B", n_segments=a.n_segments)]
    sets = [("A", A), ("B", B)]
    results = {}
    for null in a.nulls:
        gen = NULLS[null]
        fp = tot = 0
        for sb in a.seeds:
            for _label, sigs in sets:
                for i, sig in enumerate(sigs):
                    if _survived(gen(sig, sb + i + 500), sb + i + 700):
                        fp += 1
                    tot += 1
            print(f"  [{null}] seed {sb} done ({fp}/{tot})", flush=True)
        fpr, lo, hi = _wilson(fp, tot)
        results[null] = {
            "fpr": round(fpr, 4),
            "wilson_95ci": [round(lo, 4), round(hi, 4)],
            "n": tot,
            "n_false_positives": fp,
            "pass": bool(hi <= G2_MAX_FPR),
        }
        print(
            f"  [{null}] FPR={fpr:.4f} CI=[{lo:.4f},{hi:.4f}] pass={hi <= G2_MAX_FPR}", flush=True
        )
    all_pass = all(r["pass"] for r in results.values())
    out = {
        "schema": "bsff.multi_null_robustness/v1",
        "verdict": "MULTI_NULL_ROBUST" if all_pass else "MULTI_NULL_NOT_ROBUST",
        "all_nulls_pass": bool(all_pass),
        "gate": "per-null seed-averaged FPR Wilson-95-CI-upper <= 0.05",
        "n_seeds": len(a.seeds),
        "n_segments_per_set": a.n_segments,
        "n_surrogates": NSUR,
        "nulls": results,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"\n{out['verdict']} | "
        + " ".join(f"{k}:{v['fpr']}(<=0.05?{v['pass']})" for k, v in results.items())
    )
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
