# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import numpy as np
import pytest

from bsff.leakage_detector import detect_feature_selection_leakage

sklearn = pytest.importorskip("sklearn")


def test_feature_selection_leakage_flags_label_encoded_feature():
    rng = np.random.default_rng(3)
    labels = np.repeat([0, 1], 80)
    features = rng.normal(size=(labels.size, 6))
    features[:, 0] = labels + 0.01 * rng.normal(size=labels.size)
    result = detect_feature_selection_leakage(features, labels, n_permutations=30, seed=3)
    assert result["flagged"] is True
    assert result["p_value"] < 0.05
