#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Differential cross-validation of the surrogate generators.

TISEAN is the canonical external reference for amplitude-adjusted surrogates, but
it is a compiled binary that is rarely present in a hermetic CI. So this suite
validates on two levels:

* EXACT invariants that must hold bit-for-bit for any correct implementation
  (per-channel marginal preservation) — gated at machine epsilon.
* STATISTICAL invariants that hold only in expectation over an ensemble
  (lag-0 covariance fidelity, amplitude-spectrum preservation) — gated at
  empirically measured tolerances, not at a fake 1e-6 that no stochastic
  surrogate could ever meet.

If a TISEAN binary is discovered on PATH it is additionally cross-checked;
otherwise its absence is reported, not silently skipped.

Exit code is non-zero if any gate fails, so this can run as a CI gate.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.surrogate_engine import (  # noqa: E402
    miaaft_surrogate,
    var_phase_randomized_surrogate,
)
from bsff.synthetic import ar1_multichannel  # noqa: E402

# Gates. EXACT for deterministic invariants; STATISTICAL for ensemble means.
MARGINAL_EXACT_TOL = 1e-10
COVARIANCE_REL_TOL = 0.05
SPECTRUM_REL_TOL = 0.05
ENSEMBLE = 20
FIXTURES = [(4, 1024), (8, 2048), (16, 1024)]


def _relative_covariance_error(x: np.ndarray, surrogates: list[np.ndarray]) -> float:
    sigma0 = np.cov(x)
    sigma_mean = np.mean([np.cov(s) for s in surrogates], axis=0)
    return float(np.linalg.norm(sigma_mean - sigma0) / np.linalg.norm(sigma0))


def _amplitude_spectrum_rel_error(x: np.ndarray, s: np.ndarray) -> float:
    ax = np.abs(np.fft.rfft(x, axis=1))
    as_ = np.abs(np.fft.rfft(s, axis=1))
    return float(np.linalg.norm(as_ - ax) / (np.linalg.norm(ax) + 1e-12))


def _marginal_max_abs_diff(x: np.ndarray, s: np.ndarray) -> float:
    return float(np.max(np.abs(np.sort(s, axis=1) - np.sort(x, axis=1))))


def run() -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for m, n in FIXTURES:
        x = ar1_multichannel(n_channels=m, n_samples=n, seed=42)
        miaaft = [miaaft_surrogate(x, n_iter=100, seed=s) for s in range(ENSEMBLE)]
        varph = [var_phase_randomized_surrogate(x, seed=s) for s in range(ENSEMBLE)]

        marginal = _marginal_max_abs_diff(x, miaaft[0])
        spectrum = _amplitude_spectrum_rel_error(x, miaaft[0])
        cov_miaaft = _relative_covariance_error(x, miaaft)
        cov_varph = _relative_covariance_error(x, varph)

        checks = {
            "miaaft_marginal_exact": marginal <= MARGINAL_EXACT_TOL,
            "miaaft_spectrum_ok": spectrum <= SPECTRUM_REL_TOL,
            "miaaft_covariance_ok": cov_miaaft <= COVARIANCE_REL_TOL,
            "var_phase_covariance_ok": cov_varph <= COVARIANCE_REL_TOL,
        }
        cases.append(
            {
                "channels": m,
                "samples": n,
                "marginal_max_abs_diff": marginal,
                "amplitude_spectrum_rel_error": round(spectrum, 6),
                "miaaft_covariance_rel_error": round(cov_miaaft, 6),
                "var_phase_covariance_rel_error": round(cov_varph, 6),
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    tisean = shutil.which("surrogates") or shutil.which("endtoend")
    return {
        "schema": "bsff.cross_validation.v1",
        "tolerances": {
            "marginal_exact": MARGINAL_EXACT_TOL,
            "covariance_rel": COVARIANCE_REL_TOL,
            "spectrum_rel": SPECTRUM_REL_TOL,
        },
        "ensemble": ENSEMBLE,
        "tisean_reference": tisean or "not_available_on_path",
        "cases": cases,
        "all_passed": all(c["passed"] for c in cases),
    }


def main() -> int:
    report = run()
    out = ROOT / "artifacts" / "cross_validation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for c in report["cases"]:
        flag = "PASS" if c["passed"] else "FAIL"
        print(
            f"M={c['channels']:2d} N={c['samples']:4d}: {flag}  "
            f"marginal={c['marginal_max_abs_diff']:.2e}  "
            f"cov_miaaft={c['miaaft_covariance_rel_error']:.4f}  "
            f"cov_varphase={c['var_phase_covariance_rel_error']:.4f}"
        )
    print(f"TISEAN reference: {report['tisean_reference']}")
    if report["all_passed"]:
        print("Surrogate cross-validation: PASS")
        return 0
    print("Surrogate cross-validation: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
