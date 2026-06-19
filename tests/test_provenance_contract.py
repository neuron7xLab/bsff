# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab

from __future__ import annotations

from pathlib import Path

from bsff.provenance import (
    build_provenance_manifest,
    claim_fingerprint,
    verify_attribution_manifest,
)


def test_claim_fingerprint_is_stable() -> None:
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert claim_fingerprint(a) == claim_fingerprint(b)


def test_provenance_manifest_preserves_author_and_license() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = build_provenance_manifest(root, ["README.md", "NOTICE", "src/bsff/provenance.py"])
    result = verify_attribution_manifest(manifest)
    assert result["ok"], result
    assert manifest["author"] == "Yaroslav Vasylenko / neuron7xLab"
    assert manifest["code_license"] == "GPL-3.0-or-later"
    assert manifest["docs_license"] == "CC-BY-4.0"
    assert len(manifest["records"]) >= 3
