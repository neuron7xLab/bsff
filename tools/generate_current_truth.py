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


def build() -> dict:
    s1 = json.loads(S1.read_text())
    s2 = json.loads(S2.read_text())
    s2_pass = bool(s2["S2_BRIGHT_LINE_PASSED"])
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    g1, g2 = s2["G1"], s2["G2"]
    latest = "BONN_S2_BRIGHT_LINE_PASSED" if s2_pass else s2["final_state"]
    return {
        "schema": "bsff.current_truth/v1",
        "package_version": _ver(),
        "main_commit": commit,
        "latest_validation_state": latest,
        "bonn_s1_state": s1["final_state"],  # BRIGHT_LINE_NOT_PASSED (historical)
        "bonn_s2_state": s2["final_state"],  # S2_BRIGHT_LINE_PASSED (current)
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
