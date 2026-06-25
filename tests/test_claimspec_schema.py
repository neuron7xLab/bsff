# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import pytest

from bsff import ClaimSpec


def test_claimspec_minimum_surrogates_for_alpha():
    spec = ClaimSpec(
        claim_id="demo",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=4,
        n_samples=512,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )
    assert spec.to_dict()["claim_id"] == "demo"


def test_claimspec_rejects_too_few_surrogates():
    spec = ClaimSpec(
        claim_id="bad",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=4,
        n_samples=512,
        statistic="lagged_quadratic",
        alpha=0.01,
        surrogate_count=19,
    )
    with pytest.raises(ValueError):
        spec.validate()


def _spec(alpha: float, n_surrogates: int) -> ClaimSpec:
    return ClaimSpec(
        claim_id="c",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=4,
        n_samples=512,
        statistic="lagged_quadratic",
        alpha=alpha,
        surrogate_count=n_surrogates,
    )


def test_claimspec_rejects_under_budget_noninteger_alpha():
    # Regression: the bound was int(1/alpha)-1 (floor). At alpha=0.03 it admitted
    # surrogate_count=32, whose p_floor=1/33=0.0303 > 0.03 — a test that can never
    # reject yet validated as well-formed. The ceil bound (33) must reject 32.
    with pytest.raises(ValueError):
        _spec(0.03, 32).validate()
    # 33 resolves alpha (p_floor = 1/34 < 0.03) and must be accepted.
    assert _spec(0.03, 33).to_dict()["surrogate_count"] == 33
