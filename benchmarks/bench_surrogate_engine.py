# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Wall-time + peak-memory benchmarks for the surrogate engine."""

from __future__ import annotations

from bsff.surrogate_engine import miaaft_surrogate, rank_order_surrogate_test
from bsff.synthetic import henon_series

from ._bench_util import peak_memory_bytes


def test_bench_miaaft_surrogate(benchmark) -> None:
    signal = henon_series(768, seed=11)
    benchmark.extra_info["peak_memory_bytes"] = peak_memory_bytes(
        lambda: miaaft_surrogate(signal, max_iter=200, tol=1e-3, seed=7)
    )
    benchmark(lambda: miaaft_surrogate(signal, max_iter=200, tol=1e-3, seed=7))


def test_bench_rank_order_test(benchmark) -> None:
    signal = henon_series(768, seed=11)
    benchmark(lambda: rank_order_surrogate_test(signal, n_surrogates=19, alpha=0.05, seed=101))
