# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Property gate — surrogate engine determinism (P4).

A fixed seed must yield byte-identical surrogate diagnostics, so any evidence built
on them is reproducible. The engine is moderately costly, so this runs fewer
examples than the cheap validators — determinism is exact, not statistical.
"""

from __future__ import annotations

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from bsff.surrogate_engine import miaaft_surrogate

_SETTINGS = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


def _finite():
    return arrays(
        dtype=np.float64,
        shape=st.tuples(st.integers(1, 3), st.integers(32, 96)),
        elements=st.floats(-1e3, 1e3, allow_nan=False, allow_infinity=False, width=64),
    )


@given(x=_finite(), seed=st.integers(0, 2**16))
@_SETTINGS
def test_p4_fixed_seed_gives_identical_diagnostics(x: np.ndarray, seed: int) -> None:
    a, da = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=seed, return_diagnostics=True)
    b, db = miaaft_surrogate(x, max_iter=60, tol=1e-3, seed=seed, return_diagnostics=True)
    assert np.array_equal(a, b)
    assert da == db
    # And the diagnostics are finite and self-consistent.
    assert da["converged"] in (True, False)
    assert da["n_iter_actual"] >= 1
