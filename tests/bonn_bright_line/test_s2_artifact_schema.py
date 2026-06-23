# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 decision rules emit valid verdicts; FDR controls a pure-null family."""

from __future__ import annotations

import numpy as np
import s2_metrics as m


def test_segment_verdict_values():
    rng = np.random.default_rng(0)
    surr = rng.normal(size=199)
    for rule, params in (
        ("pvalue", {}),
        ("pvalue_half", {"alpha_eff": 0.025}),
        ("zgate", {"z_min": 2.0}),
        ("strictconv", {}),
    ):
        v, p = m.segment_verdict(rule, -5.0, surr, n_nonconv=0, n_surr=199, params=params)
        assert v in {"SURVIVED", "REFUTED", "UNSUPPORTED"}
        assert 0.0 < p <= 1.0


def test_nonconverged_is_unsupported():
    surr = np.zeros(199)
    v, _ = m.segment_verdict("pvalue", -1.0, surr, n_nonconv=199, n_surr=199, params={})
    assert v == "UNSUPPORTED"


def test_strong_lower_outlier_survives_pvalue():
    surr = np.random.default_rng(1).normal(size=199)
    v, _ = m.segment_verdict("pvalue", float(surr.min()) - 10.0, surr, 0, 199, {})
    assert v == "SURVIVED"


def test_zgate_demotes_marginal_effect():
    # orig just below the surrogate cloud: low p but small z -> zgate refutes.
    surr = np.random.default_rng(2).normal(loc=0.0, scale=1.0, size=199)
    orig = float(np.quantile(surr, 0.01))  # ~1st percentile: p small, z modest
    v_p, _ = m.segment_verdict("pvalue", orig, surr, 0, 199, {})
    v_z, _ = m.segment_verdict("zgate", orig, surr, 0, 199, {"z_min": 2.5})
    assert v_p == "SURVIVED"
    assert v_z == "REFUTED"


def test_fdr_controls_pure_null():
    # Uniform-ish p-values (pure null) -> BH at q=0.05 should reject few/none.
    rng = np.random.default_rng(3)
    pvals = list(rng.uniform(size=100))
    conv = [True] * 100
    verdicts = m.apply_fdr(pvals, conv, q=0.05)
    fpr = sum(v == "SURVIVED" for v in verdicts) / len(verdicts)
    assert fpr <= 0.05
