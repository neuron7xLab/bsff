# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from bsff.leakage_detector import detect_block_design_leakage
from bsff.synthetic import block_design_dataset


def test_block_design_fixture_is_flagged():
    _x, labels, block_ids = block_design_dataset(n_blocks=12, block_len=16)
    result = detect_block_design_leakage(labels, block_ids)
    assert result["flagged"] is True
    assert result["mean_block_label_purity"] >= 0.95
