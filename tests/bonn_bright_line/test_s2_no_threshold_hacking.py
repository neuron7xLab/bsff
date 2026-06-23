# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Frozen S2 constants cannot drift, and a G2 failure cannot be hidden."""

from __future__ import annotations

import s2_metrics as m


def test_frozen_constants():
    assert m.ALPHA == 0.05
    assert m.G1_MIN == 0.80
    assert m.G2_MAX_FPR == 0.05


def test_g2_fail_blocks_bright_line_regardless_of_g1():
    # Even a perfect G1 cannot rescue a combined FPR above alpha.
    perfect_g1 = m.g1_pass(1.0, 1.0, 1.0)
    assert perfect_g1
    for fpr in (0.051, 0.065, 0.08, 0.10):
        assert not m.g2_pass(fpr)
        assert not (perfect_g1 and m.g2_pass(fpr))


def test_combined_fpr_boundary():
    assert m.g2_pass(0.05)  # exactly at alpha passes
    assert not m.g2_pass(0.0501)  # just above fails
