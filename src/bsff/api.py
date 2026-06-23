# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Stable programmatic API for BSFF.

This module is the supported integration surface. Everything re-exported or defined
here has a frozen signature guarded by ``tests/test_public_api_contract.py``: a
breaking change fails CI unless the version is bumped and the contract updated. Code
under ``bsff.*`` submodules is internal and may move; integrate through ``bsff.api``.

Example
-------
>>> import numpy as np
>>> from bsff.api import evaluate_claim_pipeline, load_policy_profile
>>> from bsff.synthetic import henon_series
>>> from bsff.schemas import ClaimSpec
>>> spec = ClaimSpec(
...     claim_id="demo", signal_type="EEG", task_type="nonlinear_structure",
...     sampling_rate_hz=250.0, n_channels=1, n_samples=768,
...     statistic="lagged_quadratic", alpha=0.05, surrogate_count=19,
... )
>>> verdict = evaluate_claim_pipeline(spec, henon_series(768, seed=11), policy="standard")
>>> verdict.verdict in {"REFUTED", "UNSUPPORTED", "SURVIVED"}
True
"""

from __future__ import annotations

from typing import Any

import jsonschema

from .evidence import stable_sha256
from .json_schema import verdict_json_schema
from .pipeline import PipelineVerdict, evaluate_claim_pipeline
from .policy import PolicyProfile, get_policy_profile
from .surrogate_engine import miaaft_surrogate, rank_order_surrogate_test

__all__ = [
    "evaluate_claim_pipeline",
    "generate_evidence_manifest",
    "load_policy_profile",
    "miaaft_surrogate",
    "rank_order_surrogate_test",
    "validate_verdict_json",
]


def load_policy_profile(name: str = "smoke") -> PolicyProfile:
    """Return a named policy profile (``smoke`` | ``standard`` | ``strict``).

    >>> load_policy_profile("strict").surrogate_count
    999
    """
    return get_policy_profile(name)


def validate_verdict_json(payload: dict[str, Any]) -> None:
    """Validate a verdict document against the published JSON Schema.

    Raises ``jsonschema.ValidationError`` if the payload does not conform. Use this
    before trusting a verdict document received from another process or run.

    >>> validate_verdict_json({
    ...     "claim_id": "x", "verdict": "UNSUPPORTED", "p_value": 0.5,
    ...     "original_statistic": 0.1, "surrogate_min": 0.0, "surrogate_max": 1.0,
    ...     "leakage_flags": {}, "evidence": {}, "caveats": [],
    ... })
    """
    jsonschema.validate(payload, verdict_json_schema())


def generate_evidence_manifest(verdict: PipelineVerdict) -> dict[str, Any]:
    """Build a deterministic, hash-stamped evidence manifest from a verdict.

    The manifest binds the claim id, verdict, contract hash, evidence graph, and
    caveats under a single ``manifest_sha256`` so downstream consumers can detect
    tampering or drift.

    >>> from bsff.synthetic import henon_series
    >>> from bsff.schemas import ClaimSpec
    >>> spec = ClaimSpec(claim_id="m", signal_type="EEG", task_type="nonlinear_structure",
    ...     sampling_rate_hz=250.0, n_channels=1, n_samples=768,
    ...     statistic="lagged_quadratic", alpha=0.05, surrogate_count=19)
    >>> v = evaluate_claim_pipeline(spec, henon_series(768, seed=11), policy="smoke")
    >>> m = generate_evidence_manifest(v)
    >>> len(m["manifest_sha256"]) == 64
    True
    """
    core = {
        "claim_id": verdict.claim_id,
        "verdict": verdict.verdict,
        "contract_sha256": verdict.contract_sha256,
        "evidence_graph": verdict.evidence_graph,
        "caveats": list(verdict.caveats),
        "policy": verdict.policy,
    }
    return {**core, "manifest_sha256": stable_sha256(core)}
