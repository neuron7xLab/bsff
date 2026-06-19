# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The artifact's self-hash must be verifiable, not a decorative trust-me string.

The validation artifact embeds ``artifact_sha256``. If nothing recomputes it, the
field can hold any value and a tampered artifact passes review. These tests pin
that the hash is canonical and that mutating any gate value is detected.
"""

from __future__ import annotations

from bsff.cli import validate_kernel
from bsff.validation import canonical_artifact_sha256, validate_phase1_artifact


def test_generated_artifact_hash_is_canonical(tmp_path):
    report = validate_kernel(tmp_path / "phase1.json")
    assert report["artifact_sha256"] == canonical_artifact_sha256(report)
    assert validate_phase1_artifact(report) == []


def test_tampered_artifact_is_detected(tmp_path):
    report = validate_kernel(tmp_path / "phase1.json")
    # Flip a verdict value without recomputing the hash: tampering must surface.
    report["gates"]["henon_power_smoke"]["p_value"] = 0.99
    failures = validate_phase1_artifact(report)
    assert any("artifact_sha256 mismatch" in f for f in failures)


def test_nonconverged_null_cannot_claim_survived(tmp_path):
    report = validate_kernel(tmp_path / "phase1.json")
    # Force a non-converged null in the henon gate, then re-stamp the canonical
    # hash so the only remaining failure is the convergence contract itself.
    report["gates"]["henon_power_smoke"]["surrogate_convergence"]["all_converged"] = False
    report.pop("artifact_sha256", None)
    report["artifact_sha256"] = canonical_artifact_sha256(report)
    failures = validate_phase1_artifact(report)
    assert any("did not converge" in f for f in failures)
