# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Public execution layer: bsff benchmark / evidence verify / reproduce bonn-s2."""

from __future__ import annotations

from pathlib import Path

from bsff import bench

REPO = Path(__file__).resolve().parents[1]


def test_find_repo_root_locates_repo():
    assert bench.find_repo_root(REPO) == REPO


def test_find_repo_root_none_outside_repo(tmp_path):
    assert bench.find_repo_root(tmp_path) is None


def test_blocked_runtime_outside_repo(tmp_path):
    assert bench.verify_evidence(tmp_path)["state"] == "BLOCKED_RUNTIME"
    assert bench.reproduce_bonn_s2(tmp_path)["state"] == "BLOCKED_RUNTIME"


def test_benchmark_blocked_when_no_data(tmp_path):
    # A repo-shaped root with no staged bonn_data -> BLOCKED_DATA, never a fake PASS.
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
    (tmp_path / "examples" / "bonn_bright_line").mkdir(parents=True)
    out = bench.run_benchmark("bonn-bright-line", root=tmp_path)
    assert out["state"] == "BLOCKED_DATA"


def test_benchmark_unknown_target():
    assert bench.run_benchmark("nope", root=REPO)["state"] == "FAIL"


def test_states_are_bounded():
    assert bench.STATES == {"PASS", "FAIL", "BLOCKED_DATA", "BLOCKED_RUNTIME"}


def test_evidence_verify_on_repo_passes():
    # Integration: the committed bundle must verify clean on the canonical repo.
    out = bench.verify_evidence(REPO)
    assert out["state"] == "PASS", out.get("failed")
    assert out["canonical_state"] == "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED"


def test_reproduce_bonn_s2_dry_run_passes():
    out = bench.reproduce_bonn_s2(REPO, execute=False)
    assert out["mode"] == "dry-run"
    assert out["state"] == "PASS"
