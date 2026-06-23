# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Loader: per-set glob, 4096/4097 tolerance, SHA256, finite check."""

from __future__ import annotations

import numpy as np
import pytest
from loader import N_SAMPLES_OK, load_segment, load_set


def _write(path, n):
    np.savetxt(path, np.random.default_rng(0).normal(size=n))


def test_loads_4096_and_4097(tmp_path):
    for n in (4096, 4097):
        f = tmp_path / f"S{n}.txt"
        _write(f, n)
        seg = load_segment(f, "E")
        assert seg.n_samples == n and n in N_SAMPLES_OK
        assert seg.data.shape == (n,)
        assert len(seg.file_sha256) == 64


def test_wrong_sample_count_raises(tmp_path):
    f = tmp_path / "bad.txt"
    _write(f, 1000)
    with pytest.raises(ValueError):
        load_segment(f, "A")


def test_load_set_globs_all_txt(tmp_path):
    d = tmp_path / "E"
    d.mkdir()
    for i in range(3):
        _write(d / f"S00{i}.txt", 4097)
    segs = load_set(tmp_path, "E", n_segments=10)
    assert len(segs) == 3 and all(s.set_label == "E" for s in segs)


def test_missing_set_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_set(tmp_path, "E", n_segments=1)
