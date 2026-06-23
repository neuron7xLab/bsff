# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Wall-time benchmarks for schema serialization + evidence hashing."""

from __future__ import annotations

from bsff.evidence import stable_sha256
from bsff.json_schema import claim_spec_schema
from bsff.schemas import ClaimSpec

_SPEC = ClaimSpec(
    claim_id="bench",
    signal_type="EEG",
    task_type="nonlinear_structure",
    sampling_rate_hz=250.0,
    n_channels=8,
    n_samples=4096,
    statistic="lagged_quadratic",
    alpha=0.05,
    surrogate_count=99,
)
_EVIDENCE = {"surrogate_statistics": list(range(256)), "p_value": 0.01, "nested": {"a": [1, 2, 3]}}


def test_bench_claimspec_roundtrip(benchmark) -> None:
    benchmark(lambda: ClaimSpec(**_SPEC.to_dict()).to_dict())


def test_bench_claim_spec_schema(benchmark) -> None:
    benchmark(claim_spec_schema)


def test_bench_evidence_hash(benchmark) -> None:
    benchmark(lambda: stable_sha256(_EVIDENCE))
