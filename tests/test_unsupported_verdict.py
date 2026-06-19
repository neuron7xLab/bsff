# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The three terminal verdicts must be deterministically reachable.

UNSUPPORTED is not a softened REFUTED. It is the honest outcome when a claim is
neither survived nor positively falsified: the test simply lacks the power to
decide. This module pins one deterministic fixture per verdict so the trichotomy
cannot silently collapse into a dichotomy in a future refactor.
"""

from __future__ import annotations

from bsff.schemas import ClaimSpec
from bsff.synthetic import ar1_multichannel, henon_series
from bsff.verdict_engine import evaluate_claim


def _spec(claim_id: str) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=512,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
        metadata={"bayesian_evidence": True},
    )


def test_nonlinear_signal_survives():
    signal = henon_series(n_samples=768, seed=11)
    verdict = evaluate_claim(_spec("survived-henon"), signal, seed=101)
    assert verdict.verdict == "SURVIVED"


def test_ar1_null_with_strong_null_evidence_is_refuted():
    # seed=0: p=0.350 (not rejected) AND BF01=3.84 > 3 -> positive evidence for null.
    signal = ar1_multichannel(n_channels=1, n_samples=512, seed=0)[0]
    verdict = evaluate_claim(_spec("refuted-strong-null"), signal, seed=101)
    assert verdict.verdict == "REFUTED"
    assert verdict.evidence["bayesian_evidence"]["BF01"] > 3.0


def test_underpowered_claim_gets_unsupported():
    # seed=4: p=0.200 (not rejected) BUT BF01=2.19 <= 3 -> no power to decide.
    signal = ar1_multichannel(n_channels=1, n_samples=512, seed=4)[0]
    verdict = evaluate_claim(_spec("unsupported-underpowered"), signal, seed=101)
    assert verdict.verdict == "UNSUPPORTED"
    assert verdict.evidence["bayesian_evidence"]["BF01"] <= 3.0
    assert verdict.p_value > 0.05
