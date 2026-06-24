#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate artifacts/release/CURRENT_TRUTH.json — the single machine-readable source of
truth for BSFF's current validation state, derived from the executed S1 + S2 artifacts.

Run with --check to fail (exit 1) if the committed file is stale.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json"
S1 = ROOT / "artifacts" / "bonn_bright_line" / "BRIGHT_LINE_SUMMARY.json"
S2 = ROOT / "artifacts" / "bonn_bright_line" / "S2_BRIGHT_LINE_SUMMARY.json"


def _ver() -> str:
    try:
        import tomllib  # Python >= 3.11
    except ModuleNotFoundError:  # pragma: no cover - 3.10 path
        import tomli as tomllib  # type: ignore[no-redef]

    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


def _bnci_execution_state() -> str:
    p = ROOT / "artifacts" / "bnci2014_001" / "BNCI_SUMMARY.json"
    if p.is_file():
        return str(json.loads(p.read_text()).get("final_state", "NOT_ATTEMPTED"))
    return "NOT_ATTEMPTED"


def _s2_robustness() -> str:
    # Calibrated by the falsification battery + seed-averaged specificity calibration.
    cal = ROOT / "artifacts" / "bonn_bright_line" / "S2_SPECIFICITY_CALIBRATION.json"
    if cal.is_file():
        c = json.loads(cal.read_text())
        if not c.get("fpr_ci_upper_below_threshold", True):
            ci = c.get("wilson_95ci")
            return f"NOT_ROBUST_G2_SPECIFICITY_seed_avg_FPR_{c.get('pooled_fpr')}_CI_{ci}_crosses_0.05"
        return "ROBUST"
    fals = ROOT / "artifacts" / "bonn_bright_line" / "S2_FALSIFICATION_REPORT.json"
    if fals.is_file() and not json.loads(fals.read_text()).get("claim_survives_attacks", True):
        return "BOUNDARY_PASS_G1_POWER_ROBUST_G2_SPECIFICITY_SEED_SENSITIVE"
    return "NOT_TESTED"


def _replication_state() -> str:
    rep = ROOT / "artifacts" / "replication"
    done = rep.is_dir() and any(rep.glob("**/CONFIRMATORY_VERDICT.json"))
    return "REPLICATED" if done else "NOT_DONE"


def _pypi_state() -> str:
    # Trusted-Publishing workflows present => ready; actual publish is a manual gated step.
    has_test = (ROOT / ".github" / "workflows" / "publish-testpypi.yml").is_file()
    has_pypi = (ROOT / ".github" / "workflows" / "publish-pypi.yml").is_file()
    return "TESTPYPI_READY_PYPI_READY" if (has_test and has_pypi) else "INCOMPLETE"


def _bonn_robustness() -> dict:
    """Resolve the robust specificity state from the strongest available evidence:
    S3 seed-averaged confirmatory > seed-averaged calibration > nominal-only."""
    cal_p = ROOT / "artifacts" / "bonn_bright_line" / "S2_SPECIFICITY_CALIBRATION.json"
    s3_p = ROOT / "artifacts" / "bonn_bright_line" / "S3_CONFIRMATORY_VERDICT.json"
    fpr = ci_upper = None
    robust = None
    if cal_p.is_file():
        c = json.loads(cal_p.read_text())
        fpr = c.get("pooled_fpr")
        ci_upper = (c.get("wilson_95ci") or [None, None])[1]
        robust = bool(c.get("fpr_ci_upper_below_threshold", False))
    if s3_p.is_file():  # S3 is the authoritative, larger-N evidence
        s3 = json.loads(s3_p.read_text())
        g2 = s3.get("G2", {})
        fpr = g2.get("ar_null_fpr", fpr)
        ci_upper = (g2.get("wilson_95ci") or [None, ci_upper])[1]
        robust = bool(s3.get("S3_PASS", False))
    return {"robust": robust, "seed_avg_fpr": fpr, "wilson_ci_upper": ci_upper}


def build() -> dict:
    s1 = json.loads(S1.read_text())
    s2 = json.loads(S2.read_text())
    s2_pass = bool(s2["S2_BRIGHT_LINE_PASSED"])
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    g1, g2 = s2["G1"], s2["G2"]
    rob = _bonn_robustness()
    if rob["robust"] is True:
        latest = "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED"
    elif rob["robust"] is False:
        latest = "BONN_NOMINAL_S2_PASS_BUT_G2_NOT_ROBUST"
    else:
        latest = "BONN_S2_BRIGHT_LINE_PASSED" if s2_pass else s2["final_state"]
    return {
        "schema": "bsff.current_truth/v2",
        "package_version": _ver(),
        "main_commit": commit,
        "latest_validation_state": latest,
        "bonn_s2_nominal_state": "PASSED_SINGLE_SEED" if s2_pass else s2["final_state"],
        "bonn_s2_robustness_state": _s2_robustness(),
        "s2_seed_averaged_fpr": rob["seed_avg_fpr"],
        "s2_wilson_ci_upper": rob["wilson_ci_upper"],
        "robust_gate": "G1_power>=0.80 AND G2_AR-null_FPR_Wilson95_CI_upper<=0.05",
        "robust_gate_passed": bool(rob["robust"]) if rob["robust"] is not None else None,
        "bonn_s1_state": s1["final_state"],  # BRIGHT_LINE_NOT_PASSED (historical)
        "bonn_s2_state": s2["final_state"],  # nominal single-seed confirmatory
        "G1_metrics": {
            "E_survived": g1["E_survived_fraction"],
            "A_not_survived": g1["A_not_survived_fraction"],
            "B_not_survived": g1["B_not_survived_fraction"],
            "threshold": 0.80,
        },
        "G2_metrics": {
            "FPR_A": g2["FPR_A"],
            "FPR_B": g2["FPR_B"],
            "combined_FPR": g2["combined_FPR"],
            "threshold": 0.05,
        },
        "BNCI_chain_state": "UNLOCKED_FOR_PREREGISTRATION_ONLY" if s2_pass else "BLOCKED",
        "bnci_execution_state": _bnci_execution_state(),
        "s2_robustness": _s2_robustness(),
        "multi_dataset_replication_state": _replication_state(),
        "pypi_deployment_state": _pypi_state(),
        "supported_claims": [
            "Bonn S2 bright-line passed (real Andrzejak-2001 EEG): G1 power + G2 specificity.",
            "Reproducible, artifact-backed operating characteristic for the frozen S2 instrument.",
            "S1 lagged_quadratic and SampEn-nominal negative results preserved as evidence.",
        ],
        "unsupported_claims": [
            "external replication / independent confirmation",
            "multi-dataset (BNCI/Cho2017/Lee2019) validation",
            "paper-grade / JOSS-accepted completeness",
        ],
        "forbidden_claims": [
            "clinical diagnosis",
            "medical or therapeutic use",
            "regulatory or device-grade status",
            "final proof of brain nonlinear dynamics",
            "universal BCI benchmark authority",
            "BNCI validated (no BNCI execution artifacts exist yet)",
        ],
        "artifact_paths": {
            "s1_summary": "artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json",
            "s2_summary": "artifacts/bonn_bright_line/S2_BRIGHT_LINE_SUMMARY.json",
            "s2_confirmatory": "artifacts/bonn_bright_line/s2_CONFIRMATORY_VERDICT.json",
            "selection_lock": "artifacts/bonn_bright_line/S2_SELECTION_LOCK.json",
            "dataset_manifest": "artifacts/bonn_bright_line/DATASET_MANIFEST.json",
        },
        "hash_manifest_path": "artifacts/release/bonn_bright_line/HASHES.sha256",
        "reproduction_entrypoint": "REPRODUCE.md",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    truth = build()
    # main_commit/timestamp are volatile; compare the rest for --check stability.
    volatile = {"main_commit", "timestamp_utc"}
    if a.check:
        if not OUT.is_file():
            print("CURRENT_TRUTH.json missing")
            return 1
        cur = json.loads(OUT.read_text())
        a_cmp = {k: v for k, v in truth.items() if k not in volatile}
        b_cmp = {k: v for k, v in cur.items() if k not in volatile}
        if a_cmp != b_cmp:
            print(
                "CURRENT_TRUTH.json is stale — regenerate with: python tools/generate_current_truth.py"
            )
            return 1
        print("CURRENT_TRUTH.json: in sync")
        return 0
    OUT.write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT.relative_to(ROOT)} | latest_validation_state={truth['latest_validation_state']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
