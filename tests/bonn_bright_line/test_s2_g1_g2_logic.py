# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""S2 G1/G2 gate logic: G1 needs all three ≥0.80; G2 needs combined FPR ≤0.05."""

from __future__ import annotations

import s2_metrics as m


def test_g1_requires_all_three():
    assert m.g1_pass(0.96, 0.86, 0.91)
    assert not m.g1_pass(0.96, 0.75, 0.91)  # Set A below 0.80
    assert not m.g1_pass(0.50, 0.90, 0.90)  # Set E below 0.80


def test_g2_threshold():
    assert m.g2_pass(0.05)
    assert m.g2_pass(0.02)
    assert not m.g2_pass(0.065)  # the S1 failure value


def test_bright_line_requires_both():
    # G1 pass alone cannot pass the bright line.
    g1 = m.g1_pass(0.96, 0.86, 0.91)
    assert g1 and not m.g2_pass(0.065)
    assert not (g1 and m.g2_pass(0.065))


def test_fraction_helpers():
    v = ["SURVIVED", "SURVIVED", "REFUTED", "UNSUPPORTED"]
    assert m.frac_survived(v) == 0.5
    assert m.frac_not_survived(v) == 0.5
