# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Executable NEGATIVE CONTROLS for the provenance / policy gate battery.

Each gate is a fail-closed validator: it must exit non-zero (status FAIL) when fed
a KNOWN-BAD state. A gate that stays green on a broken input is a fail-open gate and
proves nothing. These tests inject the *smallest* deliberately-broken state for each
gate and assert the gate FAILS, so the gates' fail-closed contract is itself under
test — without touching the real repository (a bad state is materialised in a temp
root or via monkeypatched module globals, never on disk in-tree).

The real repository stays green; these tests PASS because the gates correctly reject
the bad input.

One gate resists offline negative-controlling and is documented as such below.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"


def _load_tool(name: str):
    """Load a gate tool as a fresh, uniquely-named module so monkeypatching its
    globals cannot leak between tests and does not touch the cached import."""
    path = TOOLS_DIR / f"{name}.py"
    mod_name = f"_gate_neg_{name}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# 1. validate_ip_provenance.py  — missing required provenance files            #
# --------------------------------------------------------------------------- #
def test_ip_provenance_fails_on_missing_files(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_ip_provenance")
    # KNOWN-BAD: an empty root has NONE of the required provenance/attribution
    # files (LICENSE, NOTICE, provenance_manifest.json, ...).
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "missing required provenance file" in out


# --------------------------------------------------------------------------- #
# 2. validate_provenance.py  — altered SBOM subject hash (binding broken)       #
# --------------------------------------------------------------------------- #
def test_provenance_fails_on_sbom_hash_mismatch(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_provenance")
    # Keep ROOT real so the (valid) SBOM generator + signing workflow still pass;
    # inject the bad state ONLY in the sha256 binding manifest.
    sbom_dir = tmp_path / "sbom"
    sbom_dir.mkdir()
    (sbom_dir / "payload.txt").write_text("real bytes\n", encoding="utf-8")
    # A manifest that claims a WRONG digest for payload.txt => binding is broken.
    wrong = "0" * 64
    (sbom_dir / "bsff.sbom.sha256").write_text(f"{wrong}  payload.txt\n", encoding="utf-8")
    monkeypatch.setattr(mod, "SBOM_DIR", sbom_dir)
    # Skip the subjects.sha256 branch so the mismatch above is the sole failure.
    monkeypatch.setattr(mod, "SUBJECTS", tmp_path / "does_not_exist.sha256")
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "hash mismatch for payload.txt" in out


# --------------------------------------------------------------------------- #
# 3. validate_lockfiles.py  — a pinned requirement carrying NO hash             #
# --------------------------------------------------------------------------- #
def test_lockfiles_fails_on_unhashed_pin(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_lockfiles")
    lock_dir = tmp_path / "requirements"
    lock_dir.mkdir()
    good_hash = "sha256:" + "a" * 64
    # ci.lock: runtime essentials are pinned+hashed, but one extra pin has NO hash.
    (lock_dir / "ci.lock").write_text(
        f"numpy==1.26.4\n    --hash={good_hash}\n"
        f"scipy==1.11.4\n    --hash={good_hash}\n"
        f"statsmodels==0.14.1\n    --hash={good_hash}\n"
        "unhashedpkg==9.9.9\n",  # KNOWN-BAD: pinned but not hashed
        encoding="utf-8",
    )
    for other in ("dev.lock", "fuzz.lock", "security.lock"):
        (lock_dir / other).write_text(f"somepkg==1.0.0\n    --hash={good_hash}\n", encoding="utf-8")
    monkeypatch.setattr(mod, "LOCK_DIR", lock_dir)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "not hashed: unhashedpkg==9.9.9" in out


# --------------------------------------------------------------------------- #
# 4. validate_release_notes.py  — a forbidden unqualified claim in release notes #
# --------------------------------------------------------------------------- #
def test_release_notes_fails_on_forbidden_claim(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_release_notes")
    # KNOWN-BAD: affirmative (non-negated) forbidden overreach claim.
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## v9.9.9\n\nThis release proves BCI claims.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "forbidden claim" in out


# --------------------------------------------------------------------------- #
# 5. validate_open_source_readiness.py  — required OSS-hygiene files missing     #
# --------------------------------------------------------------------------- #
def test_open_source_readiness_fails_on_missing_files(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_open_source_readiness")
    # README must exist (it is read unconditionally); give it the truth markers so
    # the SOLE failure class is the missing required files (LICENSE, SECURITY.md...).
    readme = "\n".join(mod.TRUTH_MARKERS) + "\n"
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "missing required file" in out


# --------------------------------------------------------------------------- #
# 6. validate_tisean_reference.py  — the two IAAFT engines DISAGREE              #
# --------------------------------------------------------------------------- #
def _disagreeing_report() -> dict[str, Any]:
    """A realistic per-fixture comparison report whose engines disagree."""
    return {
        "schema": "bsff.reference_surrogate.v1",
        "agrees": False,  # KNOWN-BAD: engines disagree beyond tolerance
        "n_samples": 512,
        "n_iter": 100,
        "amplitude_spectrum_error_bsff": 1.0,
        "amplitude_spectrum_error_reference": 1.0,
        "spectrum_error_gap": 9.9,
        "marginal_ks_bsff": 0.9,
        "marginal_ks_reference": 0.9,
        "covariance_rmsd_bsff": 1.0,
        "covariance_rmsd_reference": 1.0,
        "covariance_rmsd_gap": 9.9,
        "rank_order_p_bsff": 0.0,
        "rank_order_p_reference": 0.0,
        "rank_correlation_p_stability": 0.0,
        "reference_converged": False,
        "reference_n_iter_actual": 100,
        "tisean_reference": None,
        "tisean_was_run": False,
        "tolerances": {},
    }


def test_tisean_reference_fails_on_engine_disagreement(tmp_path, monkeypatch, capsys):
    mod = _load_tool("validate_tisean_reference")
    # Redirect artifact writes into the temp root (never mutate real artifacts/).
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    # KNOWN-BAD: substitute a comparison that reports disagreement.
    monkeypatch.setattr(mod, "compare_against_reference", lambda *a, **k: _disagreeing_report())
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "TISEAN reference validation: FAIL" in out


# --------------------------------------------------------------------------- #
# 7. check_github_actions_policy.py  — a policy-violating workflow yaml          #
# --------------------------------------------------------------------------- #
def test_github_actions_policy_fails_on_bad_workflow(tmp_path, monkeypatch, capsys):
    mod = _load_tool("check_github_actions_policy")
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    # KNOWN-BAD: no permissions block, forbidden pull_request_target trigger, and a
    # third-party action neither SHA-pinned nor on the stable-tag allowlist.
    (workflows / "bad.yml").write_text(
        "name: bad\n"
        "on:\n"
        "  pull_request_target:\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: evilorg/malicious-action@v1\n"
        "      - run: echo hi\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "WORKFLOWS", workflows)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "GitHub Actions policy failures" in out
    assert "pull_request_target:" in out


# --------------------------------------------------------------------------- #
# 8. validate_wheel_runtime.py — the gate must FAIL when no wheel is produced    #
# --------------------------------------------------------------------------- #
def test_wheel_runtime_fails_when_build_produces_no_wheel(tmp_path, monkeypatch, capsys):
    """The wheel-runtime gate's PASS/FAIL DECISION is negative-controlled without a
    real build: stub the subprocess seam so `python -m build` is a no-op (its
    behavioral proof is the build-package CI job), so the dist dir holds no .whl.
    The gate must detect the missing wheel and return 1 — proving its failure path
    is live, not decorative."""
    import types

    mod = _load_tool("validate_wheel_runtime")
    monkeypatch.setattr(
        mod, "_run", lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr="")
    )
    rc = mod.validate_wheel(tmp_path / "out.json")
    out = capsys.readouterr().out
    assert rc == 1
    assert "no wheel produced" in out
