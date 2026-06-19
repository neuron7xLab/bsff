# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.calibration import calibrate_miaaft_budget, required_rank_order_surrogates
from bsff.synthetic import ar1_multichannel


def test_required_rank_order_surrogates_alpha_005():
    assert required_rank_order_surrogates(0.05) == 19


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
