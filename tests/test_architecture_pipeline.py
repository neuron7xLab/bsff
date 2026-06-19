# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import pytest

from bsff.leakage_detector import detect_block_design_leakage
from bsff.pipeline import FalsificationPipeline, evaluate_claim_pipeline
from bsff.policy import adapt_policy_for_signal, get_policy_profile
from bsff.registry import StageRegistry
from bsff.schemas import ClaimSpec
from bsff.stages import LeakageStage
from bsff.synthetic import block_design_dataset, henon_series


def _henon_spec() -> ClaimSpec:
    return ClaimSpec(
        claim_id="pipeline-henon-smoke",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        surrogate_count=19,
    )


def test_policy_adapts_to_signal_geometry():
    spec = _henon_spec()
    policy = adapt_policy_for_signal(spec, henon_series(n_samples=768), "smoke")
    assert policy.alpha == spec.alpha
    assert policy.surrogate_count >= 19
    assert policy.miaaft_max_iter > 0
    assert policy.to_dict()["name"] == "smoke"


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        get_policy_profile("narrative-driven-development")


def test_stage_registry_rejects_duplicate_stage_ids():
    registry = StageRegistry()
    registry.register(LeakageStage())
    with pytest.raises(ValueError):
        registry.register(LeakageStage())


def test_pipeline_survives_henon_smoke_claim():
    result = evaluate_claim_pipeline(_henon_spec(), henon_series(n_samples=768, seed=11), seed=101)
    payload = result.to_dict()
    assert result.verdict == "SURVIVED"
    assert payload["evidence_graph"]["node_count"] == 4
    assert len(result.contract_sha256) == 64
    assert result.to_verdict_json().verdict == "SURVIVED"


def test_pipeline_run_is_alias_of_evaluate():
    pipeline = FalsificationPipeline()
    signal = henon_series(n_samples=768, seed=11)
    via_run = pipeline.run(_henon_spec(), signal, seed=101)
    via_evaluate = pipeline.evaluate(_henon_spec(), signal, seed=101)
    assert via_run.verdict == via_evaluate.verdict == "SURVIVED"
    assert via_run.contract_sha256 == via_evaluate.contract_sha256


def test_pipeline_refutes_leakage_before_surrogate():
    _features, labels, block_ids = block_design_dataset(n_blocks=12, block_len=16)
    flags = {"block_design": detect_block_design_leakage(labels, block_ids)}
    result = FalsificationPipeline().evaluate(
        _henon_spec(), henon_series(n_samples=768), leakage_flags=flags
    )
    nodes = result.evidence_graph["nodes"]
    assert result.verdict == "REFUTED"
    assert nodes[1]["stage_id"] == "leakage_gate"
    assert nodes[1]["fatal"] is True
    assert nodes[2]["status"] == "SKIP"
