# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CI guard for BSFF-CASE-001.

These tests pin the harness to its pre-registered ground-truth behaviour: on
labelled synthetic data where the answer is fixed by construction, the case must
REFUTE an inflated within-subject claim, CONFIRM a genuinely shared signal, and stay
UNSUPPORTED on noise. They also pin the fail-closed controls and determinism. The
real PhysioNet path is never exercised in CI (network + mne); only the synthetic
ground-truth and the decision logic are asserted here.

Tests use small cohorts so the permutation null stays fast; the full-scale scientific
presets live in ``run_case.py`` and the committed dossier.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1] / "cases" / "001_physionet_eegnet"
if str(CASE_DIR) not in sys.path:
    sys.path.insert(0, str(CASE_DIR))

import run_case as rc  # noqa: E402
from splits import SplitReport  # noqa: E402
from synthetic_eeg import SyntheticConfig, make_cohort  # noqa: E402

# Small but sufficient cohort: keeps the permutation null fast in CI.
SMALL = SyntheticConfig(n_subjects=5, trials_per_subject=40, n_channels=8)
PERM = 40


def _verdict_for(cfg: SyntheticConfig) -> dict:
    cohort = make_cohort(cfg)
    report = rc._run_battery(
        "logvar_lda",
        cohort.x,
        cohort.y,
        cohort.subject,
        cfg.sfreq,
        n_permutations=PERM,
        seed=cfg.seed,
    )
    return {"report": report, "decision": rc._decide(report, cohort.n_trials)}


def test_headline_is_refuted_with_generalization_gap() -> None:
    """Subject-specific signal: within high, LOSO at chance -> REFUTED."""
    cfg = replace(SMALL, subject_effect=1.8, shared_effect=0.0)
    out = _verdict_for(cfg)
    report, decision = out["report"], out["decision"]
    assert decision["verdict"] == "REFUTED", decision["reason"]
    assert report.within_subject_acc > 0.6
    assert report.loso_acc <= 0.65
    assert report.generalization_gap > 0.05
    assert decision["within_subject_significant"] is True
    assert decision["loso_significant"] is False
    assert decision["evaluation_leakage_detected"] is False


def test_shared_signal_survives_loso() -> None:
    """A genuinely subject-shared pattern: LOSO recovers -> SURVIVED."""
    cfg = replace(SMALL, subject_effect=0.6, shared_effect=2.2)
    decision = _verdict_for(cfg)["decision"]
    assert decision["verdict"] == "SURVIVED", decision["reason"]
    assert decision["loso_significant"] is True


def test_null_is_unsupported() -> None:
    """No structure: nothing decodes -> UNSUPPORTED."""
    cfg = replace(SMALL, subject_effect=0.0, shared_effect=0.0)
    decision = _verdict_for(cfg)["decision"]
    assert decision["verdict"] == "UNSUPPORTED", decision["reason"]


def test_no_path_emits_true() -> None:
    for se, sh in [(1.8, 0.0), (0.6, 2.2), (0.0, 0.0)]:
        decision = _verdict_for(replace(SMALL, subject_effect=se, shared_effect=sh))["decision"]
        assert decision["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
        assert "TRUE" not in decision["verdict"]


def test_decision_is_fail_closed_on_leaky_evaluation() -> None:
    """If shuffled labels decode above chance, the verdict is withheld (UNSUPPORTED)."""
    report = SplitReport(
        within_subject_acc=0.9,
        loso_acc=0.85,
        generalization_gap=0.05,
        label_shuffle_within_acc=0.9,  # leak: shuffled labels still decodable
        loso_null={"p_value": 0.001, "null_mean": 0.5, "null_std": 0.05, "n_permutations": 100},
        per_subject_loso={},
        normalization={},
    )
    decision = rc._decide(report, n_total=400)
    assert decision["verdict"] == "UNSUPPORTED"
    assert decision["evaluation_leakage_detected"] is True


def test_cohort_is_deterministic() -> None:
    a = make_cohort(SMALL)
    b = make_cohort(SMALL)
    assert (a.x == b.x).all()
    assert (a.y == b.y).all()


def test_committed_reference_dossier_is_refuted() -> None:
    """The committed synthetic dossier in the case dir records the REFUTED headline."""
    verdict = json.loads((CASE_DIR / "VERDICT.json").read_text(encoding="utf-8"))
    assert verdict["verdict"] == "REFUTED"
    assert verdict["case_id"] == "BSFF-CASE-001"
    assert verdict["source"] == "synthetic"


def test_end_to_end_run_smoke() -> None:
    """One real end-to-end run() call on the scientific headline preset (low perms)."""
    from argparse import Namespace

    ns = Namespace(
        source="synthetic",
        config="headline",
        subjects="1-9",
        decoder="logvar_lda",
        permutations=25,
        seed=20260621,
        out=None,
    )
    art = rc.run(ns)
    assert art["verdict"] == "REFUTED"
    assert art["artifact_sha256"]
    assert art["n_subjects"] == 9
