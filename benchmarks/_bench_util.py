# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Shared helpers for the BSFF benchmark suite."""

from __future__ import annotations

import tracemalloc
from collections.abc import Callable

import numpy as np


def peak_memory_bytes(fn: Callable[[], object]) -> int:
    """Peak Python-heap bytes allocated while running ``fn`` (machine-independent)."""
    tracemalloc.start()
    try:
        fn()
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return int(peak)


def calibration_op() -> float:
    """A fixed unit of numerical work; its time normalizes away machine speed."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=(8, 4096))
    acc = 0.0
    for _ in range(16):
        acc += float(np.abs(np.fft.rfft(x, axis=1)).sum())
    return acc
