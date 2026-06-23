# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""SampEn statistic + lower-tail surrogate test invariants (synthetic, deterministic)."""

from __future__ import annotations

import numpy as np
import pytest
from statistics_sampen import STATISTIC_ID, sampen_lower_tail_test, sample_entropy

from bsff.synthetic import henon_series, white_noise_series


def test_determinism_has_lower_entropy_than_noise():
    assert sample_entropy(henon_series(1024, seed=11)) < sample_entropy(
        white_noise_series(1024, seed=11)
    )


def test_sample_entropy_is_deterministic_and_scale_invariant():
    x = henon_series(1024, seed=11)
    assert sample_entropy(x) == sample_entropy(x)
    assert sample_entropy(x) == pytest.approx(sample_entropy(3.0 * x + 5.0), rel=1e-9)


def test_lower_tail_detects_nonlinear_and_not_linear():
    # Deterministic-chaos -> excess regularity vs spectrum-matched null -> SURVIVED.
    assert (
        sampen_lower_tail_test(henon_series(1024, seed=11), n_surrogates=49, seed=1)["verdict"]
        == "SURVIVED"
    )
    # White noise -> no excess regularity -> not SURVIVED.
    assert (
        sampen_lower_tail_test(white_noise_series(1024, seed=11), n_surrogates=49, seed=1)[
            "verdict"
        ]
        == "REFUTED"
    )


def test_nonconverged_null_is_unsupported():
    # A starved MIAAFT budget cannot converge -> verdict must fail closed.
    out = sampen_lower_tail_test(
        henon_series(768, seed=11),
        n_surrogates=19,
        seed=1,
        max_iter=1,
        tol=1e-12,
        max_nonconverged_frac=0.0,
    )
    assert out["verdict"] == "UNSUPPORTED"
    assert out["surrogate_converged"] is False


def test_result_schema_and_id():
    out = sampen_lower_tail_test(white_noise_series(512, seed=3), n_surrogates=19, seed=1)
    assert out["statistic_id"] == STATISTIC_ID and out["tail"] == "lower"
    assert {"orig", "surr_mean", "p_value", "verdict", "surrogate_converged"} <= set(out)
    assert out["verdict"] in {"SURVIVED", "REFUTED", "UNSUPPORTED"}


def test_too_short_signal_raises():
    with pytest.raises(ValueError):
        sample_entropy(np.zeros(3))
