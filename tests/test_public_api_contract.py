# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The public API surface is frozen: a breaking change must fail CI.

``bsff.api`` is the supported integration boundary. This snapshots the exported
names and each function's ordered parameter list. A rename, removal, or reorder of
a public parameter turns this red — an explicit, reviewed signal that downstream
integrators are about to break, not a silent surprise. Every public callable must
also carry a docstring and a return annotation.
"""

from __future__ import annotations

import inspect

from bsff import api

# Frozen contract. Update ONLY together with a version bump + API_CONTRACT.md.
_EXPECTED_EXPORTS = {
    "evaluate_claim_pipeline",
    "generate_evidence_manifest",
    "load_policy_profile",
    "miaaft_surrogate",
    "rank_order_surrogate_test",
    "validate_verdict_json",
}

_EXPECTED_PARAMS = {
    "evaluate_claim_pipeline": ["spec", "signal", "policy", "leakage_flags", "seed"],
    "load_policy_profile": ["name"],
    "validate_verdict_json": ["payload"],
    "generate_evidence_manifest": ["verdict"],
    "miaaft_surrogate": [
        "signal",
        "n_iter",
        "max_iter",
        "tol",
        "seed",
        "return_diagnostics",
        "fallback",
    ],
    "rank_order_surrogate_test": [
        "signal",
        "statistic",
        "n_surrogates",
        "alpha",
        "seed",
        "max_iter",
        "tol",
        "fallback",
        "max_relative_spectrum_error",
        "max_covariance_relative_rmsd",
    ],
}


def test_exported_names_are_frozen():
    assert set(api.__all__) == _EXPECTED_EXPORTS


def test_every_export_is_callable_documented_and_annotated():
    for name in _EXPECTED_EXPORTS:
        fn = getattr(api, name)
        assert callable(fn), f"{name} is not callable"
        assert (fn.__doc__ or "").strip(), f"{name} has no docstring"
        sig = inspect.signature(fn)
        assert sig.return_annotation is not inspect.Signature.empty, f"{name} lacks a return type"


def test_public_signatures_match_frozen_contract():
    for name, expected in _EXPECTED_PARAMS.items():
        fn = getattr(api, name)
        actual = list(inspect.signature(fn).parameters)
        assert actual == expected, f"{name} signature drifted: {actual} != {expected}"


def test_api_functions_execute_end_to_end():
    import jsonschema
    import pytest

    from bsff.schemas import ClaimSpec
    from bsff.synthetic import henon_series

    assert api.load_policy_profile("strict").surrogate_count == 999
    spec = ClaimSpec(
        claim_id="api",
        signal_type="EEG",
        task_type="nonlinear_structure",
        sampling_rate_hz=250.0,
        n_channels=1,
        n_samples=768,
        statistic="lagged_quadratic",
        alpha=0.05,
        surrogate_count=19,
    )
    verdict = api.evaluate_claim_pipeline(spec, henon_series(768, seed=11), policy="smoke")
    manifest = api.generate_evidence_manifest(verdict)
    assert len(manifest["manifest_sha256"]) == 64
    api.validate_verdict_json(verdict.to_verdict_json().to_dict())
    with pytest.raises(jsonschema.ValidationError):
        api.validate_verdict_json({"verdict": "nonsense"})


def test_api_contract_doc_documents_every_export():
    import pathlib

    doc = (pathlib.Path(api.__file__).resolve().parents[2] / "docs" / "API_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    for name in _EXPECTED_EXPORTS:
        assert name in doc, f"API_CONTRACT.md omits {name}"
