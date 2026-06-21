# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Closes a gap the mutation probe found: the low-surrogate caveat was untested."""

from __future__ import annotations

from bsff.schemas import ClaimSpec
from bsff.synthetic import henon_series
from bsff.verdict_engine import evaluate_claim

_CAVEAT = "Low surrogate count"


def _verdict(surrogate_count: int):
    sig = henon_series(512, seed=3)
    cs = ClaimSpec(
        claim_id="c",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=len(sig),
        statistic="lagged_quadratic",
        surrogate_count=surrogate_count,
    )
    return evaluate_claim(cs, sig, seed=7)


def test_low_surrogate_count_emits_caveat():
    caveats = _verdict(49).caveats
    assert any(_CAVEAT in c for c in caveats), caveats


def test_sufficient_surrogate_count_has_no_low_caveat():
    caveats = _verdict(99).caveats
    assert not any(_CAVEAT in c for c in caveats), caveats
