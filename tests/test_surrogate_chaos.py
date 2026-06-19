# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Chaos / property-based hardening of the surrogate engine.

Example-based tests confirm the cases we thought of. These bombard the engine
with machine-generated inputs to confirm the invariants we *claim* hold for all
inputs: marginal preservation, finiteness, determinism, and — most importantly —
fail-closed behaviour on non-finite data. A surrogate engine that launders NaN
into a confident-looking statistic is worse than one that crashes.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from bsff.surrogate_engine import (
    covariance_relative_rmsd,
    miaaft_surrogate,
    var_phase_randomized_surrogate,
)

_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


def _finite_signals(min_ch=1, max_ch=6, min_n=16, max_n=96):
    """Finite, well-scaled multichannel signals: the engine's valid domain."""
    return st.builds(
        lambda a: a,
        arrays(
            dtype=np.float64,
            shape=st.tuples(st.integers(min_ch, max_ch), st.integers(min_n, max_n)),
            elements=st.floats(
                min_value=-1e3,
                max_value=1e3,
                allow_nan=False,
                allow_infinity=False,
                width=64,
            ),
        ),
    )


@given(x=_finite_signals())
@_SETTINGS
def test_miaaft_finite_in_finite_out(x):
    s = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=7)
    assert np.all(np.isfinite(s))
    assert s.shape == x.shape


@given(x=_finite_signals())
@_SETTINGS
def test_miaaft_preserves_per_channel_marginal(x):
    # The final rank-match step guarantees each channel's multiset of values is
    # exactly the original's: a permutation, not an approximation.
    s = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=7)
    assert np.allclose(np.sort(s, axis=1), np.sort(x, axis=1))


@given(x=_finite_signals())
@_SETTINGS
def test_miaaft_is_deterministic_under_fixed_seed(x):
    a = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=11)
    b = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=11)
    assert np.array_equal(a, b)


@given(x=_finite_signals(min_ch=2))
@_SETTINGS
def test_var_phase_finite_in_finite_out(x):
    s = var_phase_randomized_surrogate(x, seed=3)
    assert np.all(np.isfinite(s))
    assert np.isfinite(covariance_relative_rmsd(x, s))


@given(
    x=_finite_signals(),
    poison=st.sampled_from([np.nan, np.inf, -np.inf]),
)
@_SETTINGS
def test_non_finite_input_is_rejected_fail_closed(x, poison):
    corrupted = x.copy()
    corrupted[0, 0] = poison
    with pytest.raises(ValueError, match="finite"):
        miaaft_surrogate(corrupted, seed=0)
    with pytest.raises(ValueError, match="finite"):
        var_phase_randomized_surrogate(corrupted, seed=0)


def test_too_short_signal_is_rejected():
    with pytest.raises(ValueError, match="16"):
        miaaft_surrogate(np.ones((4, 8)), seed=0)
