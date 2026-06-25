# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the red-team corpus gate and its self-protecting validator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "artifacts" / "redteam" / "redteam_matrix.json"
VALIDATOR_PATH = ROOT / "tools" / "validate_redteam_matrix.py"


def _load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("validate_redteam_matrix", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _load_matrix() -> dict[str, Any]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _write(path: Path, matrix: dict[str, Any]) -> Path:
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_committed_matrix_validates_and_passes() -> None:
    assert MATRIX_PATH.is_file(), "generate the matrix with tools/generate_redteam_matrix.py"
    ok, failures = validator.run(MATRIX_PATH)
    assert ok, f"committed matrix should validate, got: {failures}"
    matrix = _load_matrix()
    assert matrix["verdict"] == "PASS"
    assert matrix["categories_total"] == 14
    assert matrix["categories_killed"] == 14
    assert validator.main(["--path", str(MATRIX_PATH)]) == 0


def test_all_fourteen_categories_present() -> None:
    matrix = _load_matrix()
    present = {c["category"] for c in matrix["categories"]}
    assert present == set(validator.EXPECTED_CATEGORIES)


def test_tampered_hash_is_rejected(tmp_path: Path) -> None:
    matrix = _load_matrix()
    # Mutate an observed_result but keep the stored hash -> forgery.
    matrix["categories"][0]["observed_result"] = "totally different observed text"
    forged = _write(tmp_path / "forged.json", matrix)
    ok, failures = validator.run(forged)
    assert not ok
    assert any("hash mismatch" in f for f in failures)
    assert validator.main(["--path", str(forged)]) != 0


def test_flipping_verdict_to_survived_fails_overall(tmp_path: Path) -> None:
    matrix = _load_matrix()
    entry = matrix["categories"][0]
    entry["verdict"] = "SURVIVED"
    # Re-hash so the per-entry hash is consistent; the survivor must still fail the gate.
    entry["hash"] = validator._canonical_hash(entry)
    matrix["categories_killed"] = 13
    matrix["verdict"] = "FAIL"
    flipped = _write(tmp_path / "flipped.json", matrix)
    ok, failures = validator.run(flipped)
    assert not ok
    assert any("not PASS" in f for f in failures)


def test_flipping_verdict_but_lying_about_pass_is_caught(tmp_path: Path) -> None:
    matrix = _load_matrix()
    entry = matrix["categories"][0]
    entry["verdict"] = "SURVIVED"
    entry["hash"] = validator._canonical_hash(entry)
    # Attacker keeps the stored count/verdict as PASS to hide the survivor.
    melded = _write(tmp_path / "lying.json", matrix)
    ok, failures = validator.run(melded)
    assert not ok
    assert any("categories_killed mismatch" in f for f in failures)
    assert any("disagrees with recompute" in f for f in failures)


def test_missing_category_is_rejected(tmp_path: Path) -> None:
    matrix = _load_matrix()
    matrix["categories"] = matrix["categories"][:-1]
    matrix["categories_total"] = 13
    matrix["categories_killed"] = 13
    missing = _write(tmp_path / "missing.json", matrix)
    ok, failures = validator.run(missing)
    assert not ok
    assert any("missing required category" in f for f in failures)
    assert any("categories_total" in f for f in failures)


@pytest.mark.parametrize("bad_severity", ["", "extreme", None, 5])
def test_invalid_severity_is_rejected(tmp_path: Path, bad_severity: Any) -> None:
    matrix = _load_matrix()
    entry = matrix["categories"][0]
    entry["severity"] = bad_severity
    entry["hash"] = validator._canonical_hash(entry)
    bad = _write(tmp_path / "sev.json", matrix)
    ok, failures = validator.run(bad)
    assert not ok
    assert any("severity invalid" in f for f in failures)
