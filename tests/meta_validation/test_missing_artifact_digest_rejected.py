# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: a PASS verdict without artifact digests is rejected.

Evidence digests bind the verdict to the artifacts it claims to have checked. A PASS
that admits ``artifact_digests_present=false`` is asserting "I verified nothing" and
the schema must refuse it (allOf const true). The ``artifact_digests`` key itself is
mandatory (in ``required``) and must hold at least one sha256 (``minProperties: 1``).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import jsonschema

_SK_PATH = Path(__file__).resolve().parent / "_skeleton.py"
_spec = importlib.util.spec_from_file_location("_meta_skeleton", _SK_PATH)
assert _spec is not None and _spec.loader is not None
_sk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sk)


def _errors(bad: dict[str, Any]) -> list[jsonschema.ValidationError]:
    schema = _sk.load_schema()
    return list(jsonschema.Draft202012Validator(schema).iter_errors(bad))


def test_pass_with_artifact_digests_present_false_rejected() -> None:
    """artifact_digests_present false + verdict PASS violates the allOf const true."""
    bad = _sk.valid_pass_skeleton()
    bad["artifact_digests_present"] = False
    assert _errors(bad), "schema accepted PASS while disclaiming artifact digests"


def test_empty_artifact_digests_map_rejected() -> None:
    """An empty artifact_digests object violates minProperties: 1."""
    bad = _sk.valid_pass_skeleton()
    bad["artifact_digests"] = {}
    assert _errors(bad), "schema accepted an empty artifact_digests map"


def test_artifact_digests_key_is_required() -> None:
    """Removing artifact_digests entirely must fail the schema's required check."""
    bad = _sk.valid_pass_skeleton()
    del bad["artifact_digests"]
    errors = _errors(bad)
    assert errors, "schema accepted a verdict missing artifact_digests"
    assert any("artifact_digests" in e.message for e in errors)


def test_artifact_digest_must_be_sha256() -> None:
    """A non-sha256 digest value violates the per-value hex64 pattern."""
    bad = _sk.valid_pass_skeleton()
    bad["artifact_digests"] = {"mutation_kill_report": "deadbeef"}
    assert _errors(bad), "schema accepted a non-sha256 artifact digest"
