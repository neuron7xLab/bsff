# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Seed-stability certification: iterate across seeds, certify or fail closed."""

from __future__ import annotations

import pytest

from bsff.datasets import materialize
from bsff.stability import UNSTABLE, certify, certify_dataset

# --------------------------------- generic ----------------------------------


def test_certify_unanimous_is_stable():
    r = certify(lambda s: "SURVIVED", seeds=[1, 2, 3, 4])
    assert r.stable is True
    assert r.certified == "SURVIVED"
    assert r.agreement == 1.0


def test_certify_flipping_fails_closed():
    flip = {0: "SURVIVED", 1: "REFUTED"}
    r = certify(lambda s: flip[s % 2], seeds=[0, 1, 2, 3])
    assert r.stable is False
    assert r.certified == UNSTABLE
    assert r.agreement == 0.5


def test_certify_majority_with_relaxed_criterion():
    seq = {0: "A", 1: "A", 2: "A", 3: "B"}
    r = certify(lambda s: seq[s], seeds=[0, 1, 2, 3], min_agreement=0.6)
    assert r.stable is True
    assert r.certified == "A"
    assert r.agreement == 0.75


def test_certify_requires_two_seeds():
    with pytest.raises(ValueError, match=">= 2 seeds"):
        certify(lambda s: "X", seeds=[1])


def test_certify_rejects_bad_criterion():
    with pytest.raises(ValueError, match="min_agreement"):
        certify(lambda s: "X", seeds=[1, 2], min_agreement=0.4)


# ------------------------------ dataset-driven ------------------------------


def test_strong_nonlinear_is_stable_survived():
    spec, data = materialize("nonlinear_effect")
    out = certify_dataset(spec, data, seeds=[1, 2, 3], n_surrogates=49)
    assert out["stability"]["stable"] is True
    assert out["certified_verdict"] == "SURVIVED"


def test_null_never_certifies_survived():
    spec, data = materialize("nonlinear_null")
    out = certify_dataset(spec, data, seeds=[1, 2, 3], n_surrogates=49)
    assert out["certified_verdict"] != "SURVIVED"


def test_causal_pair_certifies_direction():
    spec, data = materialize("coupling_effect")
    out = certify_dataset(spec, data, seeds=[1, 2, 3], n_surrogates=49)
    assert out["certified_verdict"] in {"source->target", UNSTABLE}
    assert "stability" in out
