# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Transfer-entropy estimator + directed surrogate test, with calibration."""

import numpy as np
import pytest

from bsff.synthetic import (
    coupled_ar_common_drive,
    coupled_ar_unidirectional,
    independent_ar_pair,
)
from bsff.te_operating_characteristic import te_operating_characteristic
from bsff.transfer_entropy import gaussian_transfer_entropy, transfer_entropy_test

# ----------------------------- estimator ------------------------------------


def test_causal_te_is_directional():
    x, y = coupled_ar_unidirectional(n_samples=1024, coupling=0.6, seed=3)
    te_fwd = gaussian_transfer_entropy(x, y)
    te_rev = gaussian_transfer_entropy(y, x)
    assert te_fwd > te_rev
    assert te_fwd > 0.02


def test_independent_te_is_small():
    x, y = independent_ar_pair(n_samples=1024, seed=3)
    assert gaussian_transfer_entropy(x, y) < 0.02


def test_te_is_nonnegative():
    x, y = independent_ar_pair(n_samples=256, seed=9)
    assert gaussian_transfer_entropy(x, y) >= 0.0


def test_conditioning_removes_common_drive_te():
    x, y, z = coupled_ar_common_drive(n_samples=1024, seed=3)
    te_pairwise = gaussian_transfer_entropy(x, y, k=2)
    te_conditional = gaussian_transfer_entropy(x, y, k=2, conditions=[z], cond_lag=3)
    assert te_conditional < te_pairwise


# ----------------------------- guards ---------------------------------------


def test_rejects_non_finite():
    x = np.zeros(128)
    x[0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        gaussian_transfer_entropy(x, np.zeros(128))


def test_rejects_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        gaussian_transfer_entropy(np.zeros(128), np.zeros(96))


def test_rejects_too_short():
    with pytest.raises(ValueError, match="64 samples"):
        gaussian_transfer_entropy(np.zeros(16), np.zeros(16))


def test_test_rejects_low_surrogate_count():
    x, y = independent_ar_pair(n_samples=128, seed=1)
    with pytest.raises(ValueError, match="n_surrogates must be"):
        transfer_entropy_test(x, y, n_surrogates=5, alpha=0.05)


def test_test_direction_called_for_causal():
    x, y = coupled_ar_unidirectional(n_samples=512, coupling=0.5, seed=2)
    r = transfer_entropy_test(x, y, k=2, n_surrogates=99, alpha=0.05, seed=7)
    assert r.direction == "source->target"
    assert r.p_value <= 0.05 < r.p_value_reverse or r.p_value_reverse > 0.05


# ----------------------- operating characteristic ---------------------------


def test_operating_characteristic_contract():
    """Measured calibration: the instrument's behaviour against ground truth.

    Fast CI params (n=512, 99 surrogates, 15 seeds). Encodes the contract,
    including the documented common-drive failure of pairwise TE and its
    repair under conditioning.
    """
    oc = te_operating_characteristic(n_samples=512, n_surrogates=99, alpha=0.05, seeds=15)

    # nominal specificity on the directed-null regime
    assert oc.independent_fpr <= 0.20
    # power and correct direction on genuine coupling
    assert oc.causal_power >= 0.85
    assert oc.causal_reverse_fpr <= 0.20
    # pairwise TE is fooled by a common drive — this MUST be visible, not hidden
    assert oc.common_drive_pairwise_fpr >= 0.6
    # conditioning repairs it (substantially below pairwise, back toward alpha)
    assert oc.common_drive_conditional_fpr < oc.common_drive_pairwise_fpr
    assert oc.common_drive_conditional_fpr <= 0.20
