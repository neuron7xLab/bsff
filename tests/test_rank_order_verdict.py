# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.surrogate_engine import rank_order_surrogate_test
from bsff.synthetic import ar1_multichannel, henon_series


def test_ar1_null_is_not_rejected_by_smoke_surrogates():
    x = ar1_multichannel(n_channels=1, n_samples=512, seed=1)[0]
    result = rank_order_surrogate_test(x, n_surrogates=19, alpha=0.05, seed=99)
    assert result["p_value"] > 0.05


def test_henon_smoke_fixture_is_more_nonlinear_than_surrogates():
    x = henon_series(n_samples=768, seed=11)
    result = rank_order_surrogate_test(x, n_surrogates=19, alpha=0.05, seed=101)
    assert result["p_value"] <= 0.05
