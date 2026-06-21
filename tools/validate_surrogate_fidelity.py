# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Validate that BSFF surrogates satisfy the defining IAAFT properties.

A surrogate test is only as trustworthy as its surrogates. IAAFT/MIAAFT must, by
construction, (1) preserve the marginal amplitude distribution exactly, (2) match
the power spectrum to a small residual, and (3) preserve linear covariance across
channels. This tool measures all three on a labelled battery and fails closed if
any drifts past a measured tolerance. Thresholds are calibrated to what IAAFT
actually achieves — in particular the spectrum residual is ~1%, not zero, because
IAAFT trades a perfect spectrum for an exact marginal; a tool that demanded
~1e-6 here would be testing a fantasy, not the algorithm.

This is intrinsic-property validation. An external comparison against the TISEAN
reference binary is complementary future work; the repository's limit disclosure
("not externally validated against TISEAN") stands.

    python tools/validate_surrogate_fidelity.py            # default
    python tools/validate_surrogate_fidelity.py --quick    # fewer fixtures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.surrogate_engine import miaaft_surrogate  # noqa: E402
from bsff.synthetic import ar1_multichannel, henon_series, white_noise_series  # noqa: E402

OUT = ROOT / "artifacts" / "surrogate_fidelity.json"

# Measured tolerances (see docs/SURROGATE_VALIDATION.md): marginal is exact;
# spectrum residual ~1% is the IAAFT marginal/spectrum trade-off; covariance tiny.
MARGINAL_MAX_DIFF = 1e-9
SPECTRUM_REL_ERROR = 0.05
COVARIANCE_REL_RMSD = 0.05


def _marginal_max_diff(original: np.ndarray, surrogate: np.ndarray) -> float:
    # IAAFT rank-matches the surrogate to the original amplitudes -> sorted values
    # must coincide. The max absolute difference of the sorted sequences is 0.
    return float(np.max(np.abs(np.sort(original.ravel()) - np.sort(surrogate.ravel()))))


def _fixtures(quick: bool) -> dict[str, np.ndarray]:
    fx = {
        "ar1_4ch_phi0.75": ar1_multichannel(n_channels=4, n_samples=1024, phi=0.75, seed=7),
        "henon_1d": henon_series(1024, seed=11)[np.newaxis, :],
        "white_1d": white_noise_series(1024, seed=3)[np.newaxis, :],
    }
    if not quick:
        fx["ar1_8ch_phi0.50"] = ar1_multichannel(n_channels=8, n_samples=1024, phi=0.5, seed=13)
        fx["white_4ch"] = ar1_multichannel(n_channels=4, n_samples=1024, phi=0.0, seed=21)
    return fx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="fewer fixtures")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for name, sig in _fixtures(args.quick).items():
        surr, diag = miaaft_surrogate(sig, max_iter=200, tol=1e-4, seed=42, return_diagnostics=True)
        surr2 = np.atleast_2d(surr)
        marginal = _marginal_max_diff(np.asarray(sig), surr2)
        spec = float(diag["relative_spectrum_error"])
        cov = float(diag["covariance_relative_rmsd"])
        ok = (
            marginal <= MARGINAL_MAX_DIFF
            and spec <= SPECTRUM_REL_ERROR
            and cov <= COVARIANCE_REL_RMSD
            and bool(diag["converged"])
        )
        rows.append(
            {
                "fixture": name,
                "marginal_max_diff": marginal,
                "relative_spectrum_error": spec,
                "covariance_relative_rmsd": cov,
                "converged": bool(diag["converged"]),
                "n_iter": int(diag["n_iter_actual"]),
                "ok": ok,
            }
        )
        if not ok:
            failures.append(name)

    payload = {
        "thresholds": {
            "marginal_max_diff": MARGINAL_MAX_DIFF,
            "relative_spectrum_error": SPECTRUM_REL_ERROR,
            "covariance_relative_rmsd": COVARIANCE_REL_RMSD,
        },
        "results": rows,
        "all_pass": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"{'fixture':20} {'marginal':>10} {'spec_relerr':>12} {'cov_relrmsd':>12} ok")
    for r in rows:
        print(
            f"{r['fixture']:20} {r['marginal_max_diff']:>10.1e} "
            f"{r['relative_spectrum_error']:>12.2e} {r['covariance_relative_rmsd']:>12.2e} "
            f"{'PASS' if r['ok'] else 'FAIL'}"
        )
    if failures:
        print(f"\nFAILED fixtures: {failures}")
        return 1
    print(f"\nAll surrogate-fidelity checks passed. Wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
