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
