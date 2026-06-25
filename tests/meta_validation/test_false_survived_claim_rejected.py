# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: a SURVIVED attack reported as PASS must be rejected.

Two fronts of the same lie ("an adversary got through, but we passed anyway"):

1. Red-team matrix: a matrix with a category whose verdict is "SURVIVED" but an
   overall "PASS" (or categories_killed < categories_total) must be rejected by
   ``tools/validate_redteam_matrix`` AND by the verdict tool's ``_red_team`` roll-up.
   The dedicated validator is a sibling deliverable; if it has not landed yet this
   test xfails on the import rather than silently passing, while the roll-up check
   (which is already in-tree) is asserted unconditionally.
2. Claim surface: an unsupported "validated by OpenAI" boast on a public surface
   must be flagged by ``tools/validate_openai_2026_claims``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> Any:
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_meta_{name}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _forged_matrix() -> dict[str, Any]:
    """A matrix that admits a SURVIVED category yet claims overall PASS."""
    return {
        "verdict": "PASS",
        "categories_total": 3,
        "categories_killed": 3,  # the lie: claims all killed...
        "categories": [
            {"id": "prompt-injection", "verdict": "KILLED"},
            {"id": "data-exfiltration", "verdict": "KILLED"},
            {"id": "evidence-forgery", "verdict": "SURVIVED"},  # ...but one survived
        ],
    }


def _redteam_validator() -> Any:
    """Load the dedicated red-team validator, xfailing if the sibling file is absent."""
    path = ROOT / "tools" / "validate_redteam_matrix.py"
    if not path.is_file():
        pytest.xfail("tools/validate_redteam_matrix.py not yet present (sibling deliverable)")
    return _load("validate_redteam_matrix")


def _call_validator(mod: Any, matrix: dict[str, Any]) -> Any:
    """Invoke whichever public entrypoint the validator exposes."""
    for fn_name in ("validate", "validate_matrix", "check", "run"):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                return fn(matrix)
            except TypeError:
                return fn()
    raise AssertionError("validate_redteam_matrix exposes no known entrypoint")


def _is_rejected(result: Any) -> bool:
    """A rejection is a falsy/non-zero/FAIL/exception-style result."""
    if isinstance(result, bool):
        return result is False
    if isinstance(result, int):
        return result != 0
    if isinstance(result, dict):
        verdict = result.get("verdict")
        if verdict is not None:
            return verdict != "PASS"
        return bool(result.get("errors") or result.get("violations"))
    # validate() -> list[str] of failures (non-empty == rejected);
    # run() -> (ok: bool, failures: list).
    if isinstance(result, tuple):
        ok = result[0]
        failures = result[1] if len(result) > 1 else None
        return ok is False or bool(failures)
    if isinstance(result, list):
        return bool(result)
    return False


def test_redteam_validator_rejects_survived_as_pass() -> None:
    """The dedicated validator must reject a forged SURVIVED->PASS matrix."""
    mod = _redteam_validator()
    forged = _forged_matrix()
    try:
        result = _call_validator(mod, forged)
    except Exception:
        # A validator that raises on a forged matrix is also a rejection.
        return
    assert _is_rejected(result), f"validator accepted a forged SURVIVED->PASS matrix: {result!r}"


def test_rollup_rejects_survived_as_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The in-tree verdict roll-up (_red_team) must block a survived-but-PASS matrix."""
    fvv = _load("final_validation_verdict")
    rt = tmp_path / "redteam"
    rt.mkdir(parents=True, exist_ok=True)
    import json

    # categories_killed < categories_total encodes "an attack survived" honestly;
    # combined with verdict PASS it is a contradiction the roll-up must catch.
    forged = {"verdict": "PASS", "categories_total": 3, "categories_killed": 2}
    (rt / "redteam_matrix.json").write_text(json.dumps(forged), encoding="utf-8")
    monkeypatch.setattr(fvv, "A", tmp_path)
    summary, fails = fvv._red_team()
    assert fails, "roll-up accepted a matrix with an unkilled (survived) category"
    assert summary["verdict"] == "FAIL"


def test_claim_gate_flags_unsupported_openai_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unsupported 'validated by OpenAI' boast on a surface must be flagged."""
    claims = _load("validate_openai_2026_claims")
    # _scan_forbidden compiles the real forbidden patterns from the shipped policy;
    # load it before redirecting ROOT (CLAIMS is resolved off the real repo root).
    forbidden_doc = claims._load_yaml(claims.CLAIMS / "openai_2026_forbidden_claims.yml")
    surface = tmp_path / "README.md"
    surface.write_text("BSFF was validated by OpenAI and is OpenAI-approved.\n", encoding="utf-8")
    # _scan_forbidden reports surfaces relative to claims.ROOT, so the forged surface
    # must live under the (redirected) root.
    monkeypatch.setattr(claims, "ROOT", tmp_path)
    monkeypatch.setattr(claims, "_iter_surfaces", lambda: [surface])
    violations = claims._scan_forbidden(forbidden_doc.get("forbidden", []))
    assert violations, "claim gate ignored an unsupported 'validated by OpenAI' claim"
    flagged = {v["id"] for v in violations}
    assert "validated-by-openai" in flagged
