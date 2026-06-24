#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S3 seed-averaged bright-line re-confirmatory (robust specificity gate).

Pre-declared gate (docs/validation/S3_SEED_AVERAGED_PROTOCOL.md, FROZEN before run):
  G1 (power):       seed-averaged Set-E SURVIVED fraction >= 0.80
  G2 (specificity): seed-averaged AR-null FPR (Sets A+B) with Wilson 95% CI;
                    PASS requires the CI UPPER bound <= 0.05 (not just the point estimate).
  K seeds, N segments/set, n_surrogates=199, statistic S2-C1 (sampen lower-tail, p<=alpha/2=0.025).
No tuning after results. The artifact decides.
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
from statistics_sampen import STATISTIC_ID, sampen_lower_tail_test  # noqa: E402

NSUR = 199
ALPHA_EFF = 0.025
G1_MIN = 0.80
G2_MAX_FPR = 0.05
SEEDS = [20260623, 7, 999, 314159, 2718, 42, 161803, 27182, 31337, 123456]


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = (z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def _survived(sig, seed) -> str:
    t = sampen_lower_tail_test(np.asarray(sig, float), n_surrogates=NSUR, alpha=0.05, seed=seed)
    if not t["surrogate_converged"]:
        return "UNSUPPORTED"
    return "SURVIVED" if t["p_value"] <= ALPHA_EFF else "REFUTED"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default="examples/bonn_bright_line/bonn_data", type=Path)
    p.add_argument("--n-segments", type=int, default=50)
    p.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    p.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/bonn_bright_line/S3_CONFIRMATORY_VERDICT.json"),
    )
    a = p.parse_args(argv)
    t0 = time.time()
    E = [s.data for s in load_set(a.data_dir, "E", n_segments=a.n_segments)]
    A = [s.data for s in load_set(a.data_dir, "A", n_segments=a.n_segments)]
    B = [s.data for s in load_set(a.data_dir, "B", n_segments=a.n_segments)]

    e_surv = e_tot = 0
    fp = ar_tot = 0
    per_seed = []
    for sb in a.seeds:
        es = sum(_survived(E[i], sb + i) == "SURVIVED" for i in range(len(E)))
        fa = sum(
            _survived(ar_null(A[i], 10, sb + i + 500), sb + i + 700) == "SURVIVED"
            for i in range(len(A))
        )
        fbb = sum(
            _survived(ar_null(B[i], 10, sb + i + 900), sb + i + 1100) == "SURVIVED"
            for i in range(len(B))
        )
        e_surv += es
        e_tot += len(E)
        fp += fa + fbb
        ar_tot += len(A) + len(B)
        per_seed.append(
            {
                "seed": sb,
                "E_survived": round(es / len(E), 4),
                "ar_null_fpr": round((fa + fbb) / (len(A) + len(B)), 4),
            }
        )
        print(
            f"  seed {sb}: E={es / len(E):.2f} fpr={(fa + fbb) / (len(A) + len(B)):.3f}", flush=True
        )

    e_frac = e_surv / e_tot
    fpr, fpr_lo, fpr_hi = _wilson(fp, ar_tot)
    g1 = e_frac >= G1_MIN
    g2 = fpr_hi <= G2_MAX_FPR  # robust gate: CI upper bound, not the point estimate
    passed = bool(g1 and g2)
    verdict = "S3_BRIGHT_LINE_ROBUSTLY_PASSED" if passed else "S3_BRIGHT_LINE_NOT_ROBUSTLY_PASSED"
    out = {
        "schema": "bsff.s3_seed_averaged/v1",
        "verdict": verdict,
        "statistic_id": STATISTIC_ID,
        "n_seeds": len(a.seeds),
        "n_segments_per_set": a.n_segments,
        "n_surrogates": NSUR,
        "G1": {
            "E_survived_fraction": round(e_frac, 4),
            "threshold": G1_MIN,
            "pass": g1,
            "n": e_tot,
        },
        "G2": {
            "ar_null_fpr": round(fpr, 4),
            "wilson_95ci": [round(fpr_lo, 4), round(fpr_hi, 4)],
            "ci_upper_threshold": G2_MAX_FPR,
            "pass": g2,
            "n_ar_null": ar_tot,
            "n_false_positives": fp,
        },
        "S3_PASS": passed,
        "per_seed": per_seed,
        "gate": "G1 seed-avg SURVIVED>=0.80 AND G2 AR-null FPR Wilson-95-CI-upper<=0.05",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"\n{verdict} | G1 E={e_frac:.3f}(>=0.80) G2 FPR={fpr:.4f} CI=[{fpr_lo:.4f},{fpr_hi:.4f}] (upper<=0.05?{g2})"
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
