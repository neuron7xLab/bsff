# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Executable NEGATIVE CONTROLS for the statistics/validation gate battery.

Each test feeds a gate a *known-bad* state (tampered artifact, monkeypatched
loader, over-dispersed input, or a violated claim/threshold) and asserts the
gate FAILS (non-zero exit / status FAIL). A gate that cannot be made to fail on
bad input is decorative, not an instrument; these tests prove the opposite.

None of these tests touch the real repository state: every bad input lives in a
temp directory or a monkeypatched module attribute, so the committed artifacts,
registries, and gate tools remain untouched and the real suite stays green.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from tools import analytic_uniformity_null as aun
from tools import cluster_robust_specificity as crs
from tools import validate_null_registry as vnr
from tools import validate_power_profile as vpp
from tools import validate_statistical_claims as vsc
from tools import validate_statistical_proof_gate as vspg
from tools import validate_surrogate_fidelity as vsf
from tools import validate_threshold_registry as vtr


def test_validate_power_profile_fails_on_overrun_null_fpr(tmp_path: Path) -> None:
    """A profile whose measured null false-positive rate blows past the limit
    (and whose verdict is not PASS) must be rejected with exit 1."""
    bad = tmp_path / "power_profile.json"
    bad.write_text(
        json.dumps(
            {
                "measured": {
                    "null_false_positive_rate": 0.90,  # >> 0.05 limit (BLOCKING)
                    "surrogate_convergence_rate": 0.30,  # << 0.95 (BLOCKING)
                    "seed_stable": False,  # seed stability violated (BLOCKING)
                    "positive_control_detection": 0.10,
                },
                "thresholds": {},
                "verdict": "FAIL",
            }
        ),
        encoding="utf-8",
    )
    assert vpp.main([str(bad)]) == 1


def test_validate_statistical_claims_fails_on_point_estimate_sold_as_pass(
    tmp_path: Path, monkeypatch
) -> None:
    """A CURRENT_TRUTH that headlines a robust bright-line pass while its Wilson
    CI upper bound crosses 0.05 is the exact overclaim this gate exists to catch."""
    bad_truth = tmp_path / "CURRENT_TRUTH.json"
    bad_truth.write_text(
        json.dumps(
            {
                "robust_gate": "g2_specificity",
                "robust_gate_passed": True,  # claims pass...
                "s2_wilson_ci_upper": 0.20,  # ...but CI upper crosses 0.05
                "bonn_s2_robustness_state": "ROBUST",
                "latest_validation_state": "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vsc, "TRUTH", bad_truth)
    # Absolute --output keeps the report out of the real repo (ROOT / abs == abs).
    out = tmp_path / "report.json"
    assert vsc.main(["--output", str(out)]) == 1
    assert json.loads(out.read_text())["status"] == "FAIL"


def test_validate_statistical_proof_gate_fails_on_missing_evidence_artifact(
    tmp_path: Path,
) -> None:
    """A measured claim whose bound evidence artifacts are absent must produce a
    FAIL proof (the artifact-binding invariant is not satisfiable)."""
    root = tmp_path / "root"
    (root / "artifacts" / "release").mkdir(parents=True)
    (root / "claims.yaml").write_text(
        json.dumps(
            {
                "claims": {
                    "BSFF-CLAIM-BAD": {
                        "status": ["internally_verified"],
                        "required_metrics": ["wilson_ci"],
                        "evidence_artifacts": ["artifacts/does_not_exist.json"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "artifacts" / "release" / "CURRENT_TRUTH.json").write_text(
        json.dumps({"artifact_paths": {}}), encoding="utf-8"
    )
    assert vspg.main([], root=root) == 1


def test_validate_surrogate_fidelity_fails_on_marginal_violating_surrogate(
    tmp_path: Path, monkeypatch
) -> None:
    """If the surrogate engine returns surrogates that break the IAAFT defining
    properties (marginal / spectrum / covariance / convergence), the fidelity
    gate must fail closed rather than certify a broken instrument."""

    def broken_surrogate(sig, **_kwargs):
        diag = {
            "relative_spectrum_error": 1.0,  # >> 0.05
            "covariance_relative_rmsd": 1.0,  # >> 0.05
            "converged": False,
            "n_iter_actual": 0,
        }
        # Zeros destroy the marginal amplitude distribution as well.
        return np.zeros_like(np.atleast_2d(np.asarray(sig))), diag

    monkeypatch.setattr(vsf, "miaaft_surrogate", broken_surrogate)
    out = tmp_path / "surrogate_fidelity.json"
    assert vsf.main(["--quick", "--output", str(out)]) == 1
    assert json.loads(out.read_text())["all_pass"] is False


def test_cluster_robust_specificity_fails_on_overdispersed_seeds(
    tmp_path: Path, monkeypatch
) -> None:
    """Over-dispersed per-seed false-positive rates push the cluster-robust CI
    upper bound past 0.05; --check must then FAIL even though the on-disk
    artifact is byte-in-sync with the (bad) recomputation."""
    src = tmp_path / "S3_CONFIRMATORY_VERDICT.json"
    src.write_text(
        json.dumps(
            {
                "per_seed": [
                    {"ar_null_fpr": 0.0},
                    {"ar_null_fpr": 0.0},
                    {"ar_null_fpr": 0.0},
                    {"ar_null_fpr": 0.4},  # one wild seed -> large between-seed variance
                ],
                "G2": {"n_ar_null": 400, "n_false_positives": 40},
            }
        ),
        encoding="utf-8",
    )
    art = tmp_path / "S3_CLUSTER_ROBUST_CI.json"
    monkeypatch.setattr(crs, "SOURCE", src)
    monkeypatch.setattr(crs, "ARTIFACT", art)
    # Commit a byte-exact snapshot so we bypass the drift check and land squarely
    # on the threshold check (proving it is the threshold, not staleness, failing).
    art.write_text(json.dumps(crs.compute(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["cluster_robust_specificity", "--check"])
    assert crs.main() == 1


def test_analytic_uniformity_null_fails_when_engine_is_uncalibrated(monkeypatch) -> None:
    """If the verdict engine emits SURVIVED on every draw (FPR == 1.0), the
    white-null calibration gate must reject: p-values are not Uniform(0,1)."""

    class _AlwaysSurvived:
        verdict = "SURVIVED"
        p_value = 0.5

    def uncalibrated_evaluate(*_args, **_kwargs):
        return _AlwaysSurvived()

    monkeypatch.setattr(aun, "evaluate_claim", uncalibrated_evaluate)
    # Small draw count keeps the (now trivial) computation fast.
    monkeypatch.setattr(sys, "argv", ["analytic_uniformity_null", "--check", "--n-draws", "4"])
    assert aun.main() == 1


def test_validate_null_registry_fails_on_incomplete_null(tmp_path: Path, monkeypatch) -> None:
    """A registered null hypothesis missing its reject condition is an
    incomplete H0 and must be rejected fail-closed."""
    (tmp_path / "null_hypotheses.yaml").write_text(
        "nulls:\n"
        "  H1:\n"
        "    statement: signal has no nonlinear structure\n"
        "    tested_by: rank-order surrogate test\n"
        # 'reject_if' deliberately omitted
        "    failure_status: REFUTED\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(vnr, "ROOT", tmp_path)
    assert vnr.main() == 1


def test_validate_threshold_registry_fails_on_unprovenanced_threshold(
    tmp_path: Path, monkeypatch
) -> None:
    """A threshold declared without a source is a magic number without
    provenance; the registry gate must fail closed."""
    (tmp_path / "thresholds.yaml").write_text(
        "thresholds:\n"
        "  alpha:\n"
        "    value: 0.05\n"
        "    reason: conventional significance level\n"
        # 'source' deliberately omitted
        "",
        encoding="utf-8",
    )
    monkeypatch.setattr(vtr, "ROOT", tmp_path)
    assert vtr.main() == 1
