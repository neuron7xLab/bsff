# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""CI guard for BSFF-CASE-001 (hardened inferential core).

On labelled synthetic data where the answer is fixed by construction, the case must
REFUTE an inflated within-subject claim *with positive gap evidence*, CONFIRM a
genuinely shared signal, and stay UNSUPPORTED on noise. The tests also pin the
upgraded epistemics: REFUTED requires a significant, MC-resolved generalization gap
(a non-significant LOSO alone is never enough), the leak control withholds the verdict
fail-closed, and the committed dossier is digest-verifiable.

Small cohorts + a feature-precomputed decoder keep the permutation battery fast.
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

SMALL = SyntheticConfig(n_subjects=5, trials_per_subject=40, n_channels=8)
PERM = 150  # enough for the headline gap p to resolve away from alpha


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
    return {"report": report, "decision": rc._decide(report)}


def _report(**over) -> SplitReport:
    base = dict(
        within_subject_acc=0.9,
        loso_acc=0.5,
        generalization_gap=0.4,
        permutation={
            "p_within": 0.005,
            "p_loso": 0.8,
            "p_gap": 0.005,
            "null_within_mean": 0.5,
            "null_loso_mean": 0.5,
            "null_gap_mean": 0.0,
            "gap_p_mc_se": 0.002,
            "gap_p_resolved": True,
            "n_permutations": 200,
        },
        per_subject_loso={},
        normalization={},
        block_aware_within=False,
    )
    perm = {**base["permutation"], **over.pop("permutation", {})}
    base.update(over)
    base["permutation"] = perm
    return SplitReport(**base)


def test_headline_is_refuted_with_significant_gap() -> None:
    out = _verdict_for(replace(SMALL, subject_effect=1.8, shared_effect=0.0))
    report, decision = out["report"], out["decision"]
    assert decision["verdict"] == "REFUTED", decision["reason"]
    assert report.within_subject_acc > 0.6
    assert report.loso_acc <= 0.65
    assert decision["within_subject_significant"] is True
    assert decision["generalization_gap_significant"] is True
    assert decision["gap_p_resolved"] is True
    assert decision["loso_significant"] is False
    assert decision["evaluation_leakage_detected"] is False


def test_shared_signal_survives_loso() -> None:
    decision = _verdict_for(replace(SMALL, subject_effect=0.6, shared_effect=2.2))["decision"]
    assert decision["verdict"] == "SURVIVED", decision["reason"]
    assert decision["loso_significant"] is True


def test_null_is_unsupported() -> None:
    decision = _verdict_for(replace(SMALL, subject_effect=0.0, shared_effect=0.0))["decision"]
    assert decision["verdict"] == "UNSUPPORTED", decision["reason"]


def test_nonsignificant_loso_alone_does_not_refute() -> None:
    """THE epistemic fix: within significant + LOSO not significant but gap NOT significant
    must be UNSUPPORTED, not REFUTED (absence of evidence != evidence of absence)."""
    decision = rc._decide(_report(permutation={"p_within": 0.001, "p_loso": 0.7, "p_gap": 0.4}))
    assert decision["verdict"] == "UNSUPPORTED"
    assert decision["generalization_gap_significant"] is False


def test_unresolved_gap_is_not_refuted() -> None:
    """A significant-but-unresolved gap p (Monte-Carlo noise near alpha) is withheld."""
    decision = rc._decide(_report(permutation={"p_gap": 0.04, "gap_p_resolved": False}))
    assert decision["verdict"] == "UNSUPPORTED"


def test_leaky_evaluation_is_fail_closed() -> None:
    """If labels-permuted within-CV still decodes above chance, the verdict is withheld."""
    decision = rc._decide(_report(permutation={"null_within_mean": 0.9}))
    assert decision["verdict"] == "UNSUPPORTED"
    assert decision["evaluation_leakage_detected"] is True


def test_no_path_emits_true() -> None:
    for se, sh in [(1.8, 0.0), (0.6, 2.2), (0.0, 0.0)]:
        decision = _verdict_for(replace(SMALL, subject_effect=se, shared_effect=sh))["decision"]
        assert decision["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
        assert "TRUE" not in decision["verdict"]


def test_cohort_is_deterministic() -> None:
    a, b = make_cohort(SMALL), make_cohort(SMALL)
    assert (a.x == b.x).all() and (a.y == b.y).all()


def test_committed_dossier_refuted_and_digest_verifies() -> None:
    vpath = CASE_DIR / "VERDICT.json"
    verdict = json.loads(vpath.read_text(encoding="utf-8"))
    assert verdict["verdict"] == "REFUTED"
    assert verdict["case_id"] == "BSFF-CASE-001"
    assert verdict["source"] == "synthetic"
    result = rc.verify(vpath)
    assert result["ok"] is True, result
    assert result["status"] == "REPRODUCIBLE"


def test_verify_detects_tampering(tmp_path) -> None:
    case = json.loads((CASE_DIR / "VERDICT.json").read_text(encoding="utf-8"))
    case["verdict"] = "SURVIVED"  # tamper after signing
    p = tmp_path / "tampered.json"
    p.write_text(json.dumps(case), encoding="utf-8")
    result = rc.verify(p)
    assert result["ok"] is False
    assert result["status"] == "TAMPERED"


def test_end_to_end_run_smoke() -> None:
    from argparse import Namespace

    ns = Namespace(
        source="synthetic",
        config="headline",
        subjects="1-9",
        decoder="logvar_lda",
        permutations=150,
        seed=20260621,
        stability_seeds=1,
        out=None,
        verify=None,
    )
    art = rc.run(ns)
    assert art["verdict"] == "REFUTED"
    assert art["artifact_sha256"]
    assert art["n_subjects"] == 9
