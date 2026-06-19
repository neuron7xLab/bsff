# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic MIAAFT performance matrix.

Reports wall-clock, convergence, and covariance fidelity across a channel x
sample grid. The numbers are CPU-bound and reproducible under fixed seeds, so
they belong in the README as measured facts rather than aspirational prose.

Usage:
    PYTHONPATH=src python tools/benchmark_miaaft.py
    PYTHONPATH=src python tools/benchmark_miaaft.py --json artifacts/benchmark_miaaft.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from bsff.surrogate_engine import miaaft_surrogate
from bsff.synthetic import ar1_multichannel

CHANNELS = (4, 8, 16, 32)
SAMPLES = (512, 2048, 4096, 8192)
MAX_ITER = 200
TOL = 1e-3
SEED = 0


def run_matrix() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for m in CHANNELS:
        for n in SAMPLES:
            x = ar1_multichannel(n_channels=m, n_samples=n, seed=42)
            t0 = time.perf_counter()
            _, diag = miaaft_surrogate(
                x, max_iter=MAX_ITER, tol=TOL, seed=SEED, return_diagnostics=True
            )
            dt = time.perf_counter() - t0
            row = {
                "channels": m,
                "samples": n,
                "time_s": round(dt, 3),
                "converged": bool(diag["converged"]),
                "n_iter": int(diag["n_iter_actual"]),
                "rel_cov": round(float(diag["covariance_relative_rmsd"]), 4),
            }
            results.append(row)
            print(
                f"M={m:2d} N={n:4d}: {dt:7.3f}s  "
                f"converged={row['converged']!s:5s} "
                f"n_iter={row['n_iter']:3d}  rel_cov={row['rel_cov']:.4f}"
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", type=Path, default=None, help="optional path to write JSON results"
    )
    args = parser.parse_args()
    results = run_matrix()
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "bsff.benchmark.v1",
            "max_iter": MAX_ITER,
            "tol": TOL,
            "seed": SEED,
            "results": results,
        }
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
