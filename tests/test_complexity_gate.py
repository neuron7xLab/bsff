# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the cyclomatic-complexity ratchet gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import complexity_gate as gate  # noqa: E402


def _write_allowlist(tmp_path, mapping):
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps({"allowlist": mapping}), encoding="utf-8")
    return path


def test_repo_gate_passes():
    """The live repo must satisfy the ratchet (allowlist covers the debt)."""
    report = gate.evaluate()
    assert report["status"] == "PASS", report["violations"]
    assert report["schema"] == "bsff.complexity/v1"
    assert report["ceiling"] == 15


def test_schema_shape():
    report = gate.evaluate()
    assert set(report) == {
        "schema",
        "ceiling",
        "violations",
        "allowlisted",
        "status",
    }
    assert isinstance(report["violations"], list)
    assert isinstance(report["allowlisted"], list)


def test_evaluated_evaluate_under_ceiling():
    """The refactored proof_gate.evaluate must not be an offender anymore."""
    report = gate.evaluate()
    keys = [i["target"] for i in report["violations"] + report["allowlisted"]]
    assert "src/bsff/statistics/proof_gate.py::evaluate" not in keys


def _fixture_src(tmp_path, body):
    src = tmp_path / "pkg"
    src.mkdir()
    (src / "mod.py").write_text(body, encoding="utf-8")
    return src


_COMPLEX_FN = (
    "def hard(x):\n"
    + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(20))
    + "    return -1\n"
)


def test_flags_non_allowlisted_offender(tmp_path):
    _fixture_src(tmp_path, _COMPLEX_FN)
    allow = _write_allowlist(tmp_path, {})
    report = gate.evaluate(root=tmp_path, paths=("pkg",), allowlist_path=allow)
    assert report["status"] == "FAIL"
    targets = {v["target"] for v in report["violations"]}
    assert "pkg/mod.py::hard" in targets
    assert all(v["complexity"] > gate.CEILING for v in report["violations"])


def test_allowlisted_offender_is_tolerated(tmp_path):
    _fixture_src(tmp_path, _COMPLEX_FN)
    # Record the offender's real CC so the ratchet freezes it.
    live = gate.evaluate(
        root=tmp_path, paths=("pkg",), allowlist_path=_write_allowlist(tmp_path, {})
    )
    cc = live["violations"][0]["complexity"]
    allow = _write_allowlist(tmp_path, {"pkg/mod.py::hard": cc})
    report = gate.evaluate(root=tmp_path, paths=("pkg",), allowlist_path=allow)
    assert report["status"] == "PASS"
    assert not report["violations"]
    assert report["allowlisted"][0]["target"] == "pkg/mod.py::hard"


def test_ratchet_regression_beyond_allowlist(tmp_path):
    """A live CC above the frozen value is a violation even if allowlisted."""
    _fixture_src(tmp_path, _COMPLEX_FN)
    allow = _write_allowlist(tmp_path, {"pkg/mod.py::hard": gate.CEILING + 1})
    report = gate.evaluate(root=tmp_path, paths=("pkg",), allowlist_path=allow)
    assert report["status"] == "FAIL"
    v = report["violations"][0]
    assert v["target"] == "pkg/mod.py::hard"
    assert v["complexity"] > v["allowed"]


def test_simple_code_has_no_violations(tmp_path):
    _fixture_src(tmp_path, "def easy(x):\n    return x + 1\n")
    allow = _write_allowlist(tmp_path, {})
    report = gate.evaluate(root=tmp_path, paths=("pkg",), allowlist_path=allow)
    assert report["status"] == "PASS"
    assert report["violations"] == []
    assert report["allowlisted"] == []


def test_method_qualified_name(tmp_path):
    body = (
        "class C:\n"
        + "    "
        + _COMPLEX_FN.replace("def hard(x):", "def hard(self, x):").replace("\n", "\n    ")
    )
    _fixture_src(tmp_path, body)
    allow = _write_allowlist(tmp_path, {})
    report = gate.evaluate(root=tmp_path, paths=("pkg",), allowlist_path=allow)
    targets = {v["target"] for v in report["violations"]}
    assert "pkg/mod.py::C.hard" in targets


def test_cli_check_exit_code(capsys):
    # main() scans DEFAULT_PATHS under the repo root; the live repo passes.
    rc = gate.main(["--check"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMPLEXITY_GATE:" in out
