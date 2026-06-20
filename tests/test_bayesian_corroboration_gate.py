# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The frequentist-AND-Bayesian conjunction gate must demote uncorroborated wins.

A rank-order surrogate p-value is anti-conservative for strongly autocorrelated
linear-Gaussian nulls (finite-N IAAFT bias): a near-zero nonlinear effect can
clear alpha by chance. The shipped verdict logic therefore demotes a frequentist
rejection to UNSUPPORTED unless it is corroborated by an effect-size Bayes factor
BF10 >= policy threshold. These fixtures pin that gate deterministically so a
future refactor cannot silently re-open the false-positive hole.
"""

from __future__ import annotations

import pytest

from bsff.pipeline import FalsificationPipeline
from bsff.policy import PolicyProfile
from bsff.schemas import ClaimSpec
from bsff.synthetic import ar1_multichannel, henon_series
from bsff.verdict_engine import evaluate_claim


def _spec(claim_id: str, n_samples: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=n_samples,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
        metadata={"bayesian_evidence": True},
    )


def test_uncorroborated_rejection_is_demoted_to_unsupported():
    # AR(1) phi=0.75 seed=18: frequentist rejects (p=0.05) but BF10=0.62 < 3.
    # A pure linear-Gaussian process must NOT be certified as nonlinear structure.
    signal = ar1_multichannel(n_channels=1, n_samples=512, phi=0.75, seed=18)[0]
    verdict = evaluate_claim(_spec("ar1-uncorroborated", 512), signal, seed=101)
    assert verdict.verdict == "UNSUPPORTED"
    assert verdict.p_value is not None and verdict.p_value <= 0.05
    corro = verdict.evidence["bayesian_corroboration"]
    assert corro["corroborated"] is False
    assert corro["observed_bf10"] < corro["required_bf10"]


def test_corroborated_rejection_survives():
    # Henon chaos: frequentist rejects AND BF10 >> 3 -> the gate keeps SURVIVED.
    signal = henon_series(n_samples=768, seed=11)
    verdict = evaluate_claim(_spec("henon-corroborated", 768), signal, seed=101)
    assert verdict.verdict == "SURVIVED"
    assert verdict.evidence["bayesian_evidence"]["BF10"] >= 3.0
    assert "bayesian_corroboration" not in verdict.evidence


def test_pipeline_path_applies_the_same_gate():
    pipeline = FalsificationPipeline()
    ar = ar1_multichannel(n_channels=1, n_samples=512, phi=0.75, seed=18)[0]
    henon = henon_series(n_samples=768, seed=11)
    assert pipeline.evaluate(_spec("p-ar", 512), ar, policy="standard", seed=101).verdict == (
        "UNSUPPORTED"
    )
    assert pipeline.evaluate(_spec("p-henon", 768), henon, policy="standard", seed=101).verdict == (
        "SURVIVED"
    )


def test_smoke_policy_without_bayes_keeps_frequentist_verdict():
    # The gate only fires when bayesian evidence is enabled; smoke stays fast.
    pipeline = FalsificationPipeline()
    henon = henon_series(n_samples=768, seed=11)
    verdict = pipeline.evaluate(_spec("smoke-henon", 768), henon, policy="smoke", seed=101)
    assert verdict.verdict == "SURVIVED"


def test_threshold_is_configurable_and_strictness_scales():
    signal = henon_series(n_samples=768, seed=11)
    # An absurd threshold demotes even genuine structure -> the knob is real.
    verdict = evaluate_claim(
        _spec("henon-strict", 768), signal, seed=101, bayesian_corroboration_min=1e30
    )
    assert verdict.verdict == "UNSUPPORTED"


def test_policy_rejects_loosening_threshold():
    with pytest.raises(ValueError):
        PolicyProfile(name="bad", bayesian_corroboration_min=0.5).validate()
