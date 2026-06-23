# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Wall-time + peak-memory benchmarks for the falsification pipeline."""

from __future__ import annotations

from bsff import ClaimSpec, evaluate_claim_pipeline
from bsff.synthetic import henon_series

from ._bench_util import calibration_op, peak_memory_bytes


def _spec() -> ClaimSpec:
    return ClaimSpec(
        claim_id="bench",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )


def test_bench_calibration(benchmark) -> None:
    # The normalizer: a fixed numerical workload whose time cancels machine speed.
    benchmark(calibration_op)


def test_bench_pipeline_standard(benchmark) -> None:
    spec = _spec()
    signal = henon_series(768, seed=11)
    benchmark.extra_info["peak_memory_bytes"] = peak_memory_bytes(
        lambda: evaluate_claim_pipeline(spec, signal, policy="standard", seed=101)
    )
    benchmark(lambda: evaluate_claim_pipeline(spec, signal, policy="standard", seed=101))


def test_bench_pipeline_large_signal(benchmark) -> None:
    spec = ClaimSpec(
        claim_id="bench-large",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=4096,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )
    signal = henon_series(4096, seed=11)
    benchmark(lambda: evaluate_claim_pipeline(spec, signal, policy="smoke", seed=101))
