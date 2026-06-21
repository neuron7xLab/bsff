#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""External-reference validation gate for the BSFF surrogate engine.

TISEAN (Hegger, Kantz & Schreiber 1999) is the canonical external reference for
amplitude-adjusted surrogate data, but it is a compiled C package that is rarely
present in a hermetic CI. So BSFF ships an *independent numpy reference* IAAFT
implementation (``bsff.reference_surrogate``) and validates its own MIAAFT engine
against that second implementation on deterministic fixtures.

This script:

* generates a linear-Gaussian AR(1) fixture and a nonlinear Hénon fixture,
* runs ``compare_against_reference`` on each,
* asserts the two engines agree within documented tolerances (fail closed), and
* writes ``artifacts/tisean_validation.{json,md,csv}``.

Exit code is 1 on any failure, 0 on PASS, so this can run as a CI gate. If a real
TISEAN binary is found on ``PATH`` its location is reported; its absence is
reported, never silently skipped, and TISEAN is never claimed to have run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.reference_surrogate import compare_against_reference, detect_tisean  # noqa: E402
from bsff.synthetic import ar1_multichannel, henon_series  # noqa: E402

SEED = 7
N_ITER = 100


def _build_fixtures() -> list[tuple[str, str, Any]]:
    """Deterministic 1-D fixtures: one linear-Gaussian, one nonlinear chaotic."""
    # AR(1): take the first channel of the multichannel generator for a univariate
    # linear-Gaussian series (the regime AAFT/IAAFT are theoretically exact for).
    ar1 = ar1_multichannel(n_channels=1, n_samples=512, seed=SEED)[0]
    henon = henon_series(n_samples=512, seed=SEED)
    return [
        ("ar1_linear_gaussian", "linear-Gaussian AR(1)", ar1),
        ("henon_nonlinear", "deterministic Hénon map", henon),
    ]


def run() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for key, label, series in _build_fixtures():
        report = compare_against_reference(series, seed=SEED, n_iter=N_ITER)
        report["fixture"] = key
        report["fixture_label"] = label
        report["passed"] = bool(report["agrees"])
        cases.append(report)
    return {
        "schema": "bsff.tisean_validation.v1",
        "seed": SEED,
        "n_iter": N_ITER,
        "tisean_reference": detect_tisean(),
        "tisean_was_run": False,
        "cases": cases,
        "all_passed": all(c["passed"] for c in cases),
    }


def _write_json(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(report: dict[str, Any], path: Path) -> None:
    fields = [
        "fixture",
        "n_samples",
        "amplitude_spectrum_error_bsff",
        "amplitude_spectrum_error_reference",
        "spectrum_error_gap",
        "marginal_ks_bsff",
        "marginal_ks_reference",
        "covariance_rmsd_bsff",
        "covariance_rmsd_reference",
        "covariance_rmsd_gap",
        "rank_order_p_bsff",
        "rank_order_p_reference",
        "rank_correlation_p_stability",
        "passed",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for c in report["cases"]:
            writer.writerow({k: c[k] for k in fields})


def _write_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# TISEAN reference validation",
        "",
        "BSFF MIAAFT engine validated against an **independent numpy IAAFT "
        "reference** (`bsff.reference_surrogate`).",
        "",
        f"- seed: `{report['seed']}`",
        f"- IAAFT iterations: `{report['n_iter']}`",
        f"- TISEAN binary: `{report['tisean_reference']}` (was_run={report['tisean_was_run']})",
        f"- overall: **{'PASS' if report['all_passed'] else 'FAIL'}**",
        "",
        "| fixture | spectrum gap | marginal KS (bsff/ref) | cov RMSD gap | p-stability | result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in report["cases"]:
        lines.append(
            f"| {c['fixture']} | {c['spectrum_error_gap']:.3e} | "
            f"{c['marginal_ks_bsff']:.1e} / {c['marginal_ks_reference']:.1e} | "
            f"{c['covariance_rmsd_gap']:.3e} | {c['rank_correlation_p_stability']:.3f} | "
            f"{'PASS' if c['passed'] else 'FAIL'} |"
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report = run()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    _write_json(report, artifacts / "tisean_validation.json")
    _write_csv(report, artifacts / "tisean_validation.csv")
    _write_md(report, artifacts / "tisean_validation.md")

    for c in report["cases"]:
        flag = "PASS" if c["passed"] else "FAIL"
        print(
            f"{c['fixture']:>22s}: {flag}  "
            f"spectrum_gap={c['spectrum_error_gap']:.3e}  "
            f"cov_gap={c['covariance_rmsd_gap']:.3e}  "
            f"marginal_ks={max(c['marginal_ks_bsff'], c['marginal_ks_reference']):.1e}"
        )
    print(f"TISEAN reference: {report['tisean_reference']} (was_run={report['tisean_was_run']})")
    if report["all_passed"]:
        print("TISEAN reference validation: PASS")
        return 0
    print("TISEAN reference validation: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
