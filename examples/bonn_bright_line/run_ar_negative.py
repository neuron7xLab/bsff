#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""G2 — spectrum-matched AR real-spectrum negative control (Sample-Entropy instrument).

Fit AR(p) to each real Bonn segment, generate a genuinely-LINEAR Gaussian null with
that spectrum, and adjudicate with the SAME SampEn lower-tail test used for G1. A
correct instrument: FPR = rate(SURVIVED) <= alpha. Labels are irrelevant; only the
real spectral shape is reused.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from statistics_sampen import STATISTIC_ID, sampen_lower_tail_test  # noqa: E402

SEED_BASE = 20260624


def fit_ar(x, order):
    from numpy.linalg import solve

    x = x - x.mean()
    n = len(x)
    r = np.array([np.dot(x[: n - k], x[k:]) / n for k in range(order + 1)])
    R = np.array([[r[abs(i - j)] for j in range(order)] for i in range(order)])
    try:
        c = solve(R, r[1 : order + 1])
    except np.linalg.LinAlgError:
        c = np.zeros(order)
    return c, max(float(r[0] - np.dot(c, r[1 : order + 1])), 1e-12)


def ar_null(x, order, seed):
    rng = np.random.default_rng(seed)
    c, nv = fit_ar(x, order)
    n = len(x)
    e = rng.normal(0, np.sqrt(nv), n + 2 * order)
    o = np.zeros(n + 2 * order)
    for t in range(order, n + 2 * order):
        o[t] = np.dot(c, o[t - order : t][::-1]) + e[t]
    return o[2 * order :].copy()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="G2 spectrum-matched AR negative control (SampEn)")
    p.add_argument("--input-dir", required=True, type=Path, help="Bonn Set A or B dir")
    p.add_argument("--n-segments", type=int, default=20)
    p.add_argument("--ar-order", type=int, default=10)
    p.add_argument("--n-surrogates", type=int, default=99)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--output", type=Path, default=Path("ar_negative_VERDICT.json"))
    args = p.parse_args(argv)

    files = sorted(args.input_dir.glob("*.txt"))[: args.n_segments]
    if not files:
        print(f"ERROR: no *.txt in {args.input_dir}", file=sys.stderr)
        return 3

    print(f"G2 AR negative control | input={args.input_dir} n={len(files)} ar_order={args.ar_order} "
          f"n_surrogates={args.n_surrogates} alpha={args.alpha} statistic={STATISTIC_ID}")
    t0 = time.time()
    results = []
    for i, f in enumerate(files):
        x = np.loadtxt(f).astype(float)
        seed = SEED_BASE + i
        xn = ar_null(x, args.ar_order, seed=seed)
        test = sampen_lower_tail_test(xn, n_surrogates=args.n_surrogates, alpha=args.alpha, seed=seed + 10000)
        fp = test["verdict"] == "SURVIVED"
        results.append({"segment_id": f.stem, "ar_order": args.ar_order, "p_value": test["p_value"],
                        "verdict": test["verdict"], "is_false_positive": fp, "seed": seed})
        print(f"  {f.stem}: {test['verdict']}{' ← FP' if fp else ''} p={test['p_value']:.3f}")

    n_fp = sum(r["is_false_positive"] for r in results)
    fpr = n_fp / len(results)
    fpr_ok = fpr <= args.alpha
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_HERE).stdout.strip()
    except Exception:
        commit = "unknown"
    bundle = {
        "schema": "bsff.ar_negative_control/v3",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": commit, "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "control": {
            "statistic_id": STATISTIC_ID, "source_dir": str(args.input_dir), "n_segments": len(results),
            "ar_order": args.ar_order, "n_surrogates": args.n_surrogates, "alpha": args.alpha,
            "n_false_positives": n_fp, "fpr": round(fpr, 4), "fpr_threshold": args.alpha, "fpr_ok": fpr_ok,
            "results": results,
            "interpretation": (f"NEGATIVE CONTROL PASS: real-spectrum AR null -> FPR={fpr:.3f} <= {args.alpha}."
                               if fpr_ok else f"NEGATIVE CONTROL FAIL: FPR={fpr:.3f} > {args.alpha}."),
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"\n  FPR={fpr:.3f} (n_fp={n_fp}/{len(results)}) | fpr_ok={fpr_ok}\nEvidence bundle -> {args.output}")
    return 0 if fpr_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
