# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import math

import pytest

from bsff.calibration import calibrate_miaaft_budget, required_rank_order_surrogates
from bsff.surrogate_engine import min_surrogates_for_alpha
from bsff.synthetic import ar1_multichannel

# A reasonably dense alpha grid that exercises both integer and non-integer 1/alpha.
_ALPHA_GRID = [round(0.001 * k, 3) for k in range(1, 500)]


def test_required_rank_order_surrogates_alpha_005():
    assert required_rank_order_surrogates(0.05) == 19


def test_resolution_law_is_ceil_single_source_and_actually_resolves_alpha():
    # The surrogate-budget bound is one law: schema/calibration/engine all delegate
    # to min_surrogates_for_alpha. (1) the two named surfaces must agree everywhere,
    # (2) the minimum must ACTUALLY resolve alpha — p_floor = 1/(n+1) <= alpha — which
    # the old floor bound (int(1/alpha)-1) violates for every non-integer 1/alpha.
    floor_violations = 0
    for alpha in _ALPHA_GRID:
        n = min_surrogates_for_alpha(alpha)
        assert n == required_rank_order_surrogates(alpha)
        assert n == math.ceil(1.0 / alpha) - 1
        assert 1.0 / (n + 1) <= alpha + 1e-12, f"under-budget at alpha={alpha}"
        if (int(1.0 / alpha) - 1) != n:  # the old floor bound would have been wrong here
            floor_violations += 1
    # The defect was not a corner case: the floor bound fails for the vast majority.
    assert floor_violations > 400


def test_min_surrogates_rejects_invalid_alpha():
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            min_surrogates_for_alpha(bad)


def test_miaaft_budget_calibration_selects_accepted_budget():
    x = ar1_multichannel(n_channels=4, n_samples=512, seed=42)
    result = calibrate_miaaft_budget(
        x,
        candidate_iters=(20, 40, 80, 120),
        tol=1e-3,
        max_relative_spectrum_error=0.1,
        max_covariance_relative_rmsd=0.05,
        seed=42,
    )
    assert result.accepted
    assert result.selected_max_iter in {20, 40, 80, 120}
    assert result.candidates[-1].accepted
