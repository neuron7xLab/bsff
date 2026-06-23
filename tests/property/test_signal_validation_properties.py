# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Property gate — signal validation invariants (P1-P3).

These exercise the cheap, hot validators with >= 1000 Hypothesis examples each:

* P1: NaN/Inf never reaches a verdict — the surrogate/stationarity validators
      refuse non-finite input with ValueError.
* P2: too-short signals always fail closed (ValueError).
* P3: shape normalization is deterministic and total over the valid domain.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from bsff.policy import signal_shape
from bsff.stationarity import check_stationarity
from bsff.surrogate_engine import miaaft_surrogate

_CORE = settings(
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


def _finite(min_n: int = 16, max_n: int = 128):
    return arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(1, 4), st.integers(min_n, max_n)),
        elements=st.floats(-1e3, 1e3, allow_nan=False, allow_infinity=False, width=64),
    )


@given(x=_finite(), poison=st.sampled_from([np.nan, np.inf, -np.inf]), idx=st.integers(0, 3))
@_CORE
def test_p1_nonfinite_never_reaches_verdict(x: np.ndarray, poison: float, idx: int) -> None:
    corrupted = x.copy()
    corrupted[idx % x.shape[0], 0] = poison
    with pytest.raises(ValueError):
        check_stationarity(corrupted)
    with pytest.raises(ValueError):
        miaaft_surrogate(corrupted, seed=0)


@given(n=st.integers(1, 15), ch=st.integers(1, 3))
@_CORE
def test_p2_too_short_signal_fails_closed(n: int, ch: int) -> None:
    short = np.zeros((ch, n), dtype=float)
    with pytest.raises(ValueError):
        check_stationarity(short)
    with pytest.raises(ValueError):
        miaaft_surrogate(short, seed=0)


@given(x=_finite())
@_CORE
def test_p3_shape_normalization_is_deterministic(x: np.ndarray) -> None:
    a = signal_shape(x)
    b = signal_shape(x)
    assert a == b
    assert a == (x.shape[0], x.shape[1])
    # A 1-D view normalizes to a single channel, deterministically.
    flat = x[0]
    assert signal_shape(flat) == (1, flat.shape[0])
