# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 candidate registry: structure + statistic behaviour."""

from __future__ import annotations

import numpy as np
from s2_candidate_registry import CANDIDATES, FAMILIES, permutation_entropy

from bsff.synthetic import henon_series, white_noise_series


def test_registry_structure():
    ids = [c["id"] for c in CANDIDATES]
    assert len(ids) == len(set(ids))  # unique
    for c in CANDIDATES:
        assert {"id", "family", "rule", "params", "implemented", "hypothesis"} <= set(c)
        if c["implemented"]:
            assert c["family"] in FAMILIES
            assert c["rule"] in {"pvalue", "pvalue_half", "zgate", "fdr", "strictconv"}


def test_permutation_entropy_separates_chaos_from_noise():
    assert permutation_entropy(henon_series(1024, seed=11)) < permutation_entropy(
        white_noise_series(1024, seed=11)
    )


def test_permutation_entropy_bounded_and_deterministic():
    x = henon_series(1024, seed=11)
    h = permutation_entropy(x)
    assert 0.0 <= h <= 1.0
    assert h == permutation_entropy(x)


def test_family_callables_return_floats():
    x = white_noise_series(512, seed=3)
    for fn, tail in FAMILIES.values():
        assert isinstance(float(fn(np.asarray(x))), float)
        assert tail == "lower"
