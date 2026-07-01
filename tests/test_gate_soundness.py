# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the gate-soundness meta-verifier, including a dogfood negative control."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "gate_soundness", ROOT / "tools" / "gate_soundness.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- positive
def test_evaluate_returns_schema_on_real_repo():
    gs = _load()
    result = gs.evaluate(ROOT)
    assert result["schema"] == "bsff.gate_soundness/v1"
    assert set(result) >= {
        "schema",
        "total_gates",
        "proven",
        "unproven",
        "new_unproven",
        "status",
    }
    assert result["total_gates"] >= 1
    assert 0 <= result["proven"] <= result["total_gates"]
    assert isinstance(result["unproven"], list)
    # The committed repo must not have grown its debt: the ratchet holds.
    assert result["new_unproven"] == []
    assert result["status"] == "PASS"


def test_proven_plus_unproven_covers_every_gate():
    gs = _load()
    result = gs.evaluate(ROOT)
    assert result["proven"] + len(result["unproven"]) == result["total_gates"]
    # unproven is deterministic and sorted.
    assert result["unproven"] == sorted(result["unproven"])


def test_check_passes_on_real_repo():
    gs = _load()
    assert gs.main(["--root", str(ROOT), "--check"]) == 0


# ---------------------------- negative control (dogfood the meta-tool) -----
def _make_gate(tools_dir: Path, name: str) -> None:
    (tools_dir / name).write_text("def main(argv=None):\n    return 0\n", encoding="utf-8")


def test_new_gate_without_negative_control_is_unproven_and_fails_ratchet(tmp_path):
    """Synthesize a root with a gate that has no negative control.

    The auditor must classify it as unproven, mark it as a ratchet violation
    (``new_unproven``), and the ``--check`` CLI must exit non-zero.
    """
    gs = _load()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    # A gate tool that has no registry entry and no frozen-debt grandfathering.
    _make_gate(tools_dir, "validate_fake_decorative.py")
    # An empty-but-valid registry: nothing proven, nothing grandfathered.
    (tools_dir / "gate_soundness_registry.json").write_text(
        json.dumps({"gates": {}, "unproven": []}), encoding="utf-8"
    )

    result = gs.evaluate(tmp_path)
    assert result["total_gates"] == 1
    assert result["proven"] == 0
    assert "tools/validate_fake_decorative.py" in result["unproven"]
    assert "tools/validate_fake_decorative.py" in result["new_unproven"]
    assert result["status"] == "FAIL"
    # The CLI must fail closed.
    assert gs.main(["--root", str(tmp_path), "--check"]) == 1


def test_grandfathered_unproven_gate_passes_ratchet(tmp_path):
    """A frozen (grandfathered) unproven gate does not grow the debt: PASS."""
    gs = _load()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    _make_gate(tools_dir, "validate_legacy_gate.py")
    (tools_dir / "gate_soundness_registry.json").write_text(
        json.dumps(
            {"gates": {}, "unproven": ["tools/validate_legacy_gate.py"]},
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = gs.evaluate(tmp_path)
    assert result["unproven"] == ["tools/validate_legacy_gate.py"]
    assert result["new_unproven"] == []
    assert result["status"] == "PASS"
    assert gs.main(["--root", str(tmp_path), "--check"]) == 0


def test_registry_entry_with_missing_test_file_is_not_proven(tmp_path):
    """A registry nodeid pointing at a non-existent test does NOT count as proven."""
    gs = _load()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    _make_gate(tools_dir, "validate_decorated.py")
    (tools_dir / "gate_soundness_registry.json").write_text(
        json.dumps(
            {
                "gates": {
                    "tools/validate_decorated.py": {
                        "negative_control_test": "tests/does_not_exist.py::test_x",
                        "rationale": "points at a ghost test",
                    }
                },
                "unproven": [],
            }
        ),
        encoding="utf-8",
    )

    result = gs.evaluate(tmp_path)
    assert result["proven"] == 0
    assert "tools/validate_decorated.py" in result["new_unproven"]
    assert result["status"] == "FAIL"


def test_registry_negative_control_files_exist():
    """Every proven gate in the committed registry cites a real test file."""
    reg = json.loads((ROOT / "tools" / "gate_soundness_registry.json").read_text(encoding="utf-8"))
    assert reg["gates"], "registry must record at least one proven gate"
    for gate, entry in reg["gates"].items():
        nodeid = entry["negative_control_test"]
        test_file = nodeid.split("::", 1)[0]
        assert (ROOT / test_file).is_file(), f"{gate}: missing {test_file}"
        assert entry["rationale"].strip()


def test_registry_entry_with_missing_function_is_not_proven(tmp_path):
    """A nodeid whose FILE exists but whose function is not defined does NOT
    count as proven — file existence alone is not a negative control (AST check)."""
    gs = _load()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    _make_gate(tools_dir, "validate_decorated.py")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    # The file exists but does NOT define the cited function.
    (tests_dir / "test_real_file.py").write_text(
        "def test_something_else():\n    assert True\n", encoding="utf-8"
    )
    (tools_dir / "gate_soundness_registry.json").write_text(
        json.dumps(
            {
                "gates": {
                    "tools/validate_decorated.py": {
                        "negative_control_test": "tests/test_real_file.py::test_ghost_function",
                        "rationale": "file exists, function does not",
                    }
                },
                "unproven": [],
            }
        ),
        encoding="utf-8",
    )

    result = gs.evaluate(tmp_path)
    assert result["proven"] == 0
    assert "tools/validate_decorated.py" in result["new_unproven"]
    assert result["status"] == "FAIL"
