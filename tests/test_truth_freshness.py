# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Falsification battery for the Truth Freshness Gate in tools/validate_current_truth.py.

Each negative control proves the gate is not vacuous: a stale pointer, an unreasoned
freeze, or drifted/forged evidence must each flip the verdict to FAIL. The positive
control asserts the live repository truth passes as a hash-backed FROZEN anchor.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD_A = "a" * 40
HEAD_B = "b" * 40


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_current_truth", ROOT / "tools" / "validate_current_truth.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _frozen_truth() -> dict:
    return {
        "main_commit": HEAD_A,
        "hash_manifest_path": "artifacts/release/bonn_bright_line/HASHES.sha256",
        "freshness": {
            "frozen_evidence_commit": HEAD_A,
            "reason": "evidence frozen; backed by manifest",
            "evidence_hash_manifest": "artifacts/release/bonn_bright_line/HASHES.sha256",
        },
    }


def test_live_repo_truth_is_fresh_or_frozen():
    mod = _load()
    truth = json.loads((ROOT / "artifacts" / "release" / "CURRENT_TRUTH.json").read_text())
    head = mod._head_commit()
    result = mod.evaluate_freshness(truth, head)
    assert result["status"] == "PASS", result["problems"]
    assert result["mode"] in {"FRESH", "FROZEN"}


def test_fresh_when_main_commit_equals_head():
    mod = _load()
    truth = _frozen_truth()
    result = mod.evaluate_freshness(truth, HEAD_A)  # main_commit == head
    assert result["mode"] == "FRESH"
    assert result["status"] == "PASS", result["problems"]


def test_stale_pointer_without_freeze_fails():
    mod = _load()
    truth = {"main_commit": HEAD_A}  # != head, no freshness block at all
    result = mod.evaluate_freshness(truth, HEAD_B)
    assert result["status"] == "FAIL"
    assert any("stale truth" in p for p in result["problems"])


def test_freeze_without_reason_fails():
    mod = _load()
    truth = _frozen_truth()
    truth["freshness"]["reason"] = "   "  # whitespace-only reason is not a reason
    result = mod.evaluate_freshness(truth, HEAD_B)
    assert result["status"] == "FAIL"
    assert any("reason is empty" in p for p in result["problems"])


def test_freeze_anchor_must_match_main_commit():
    mod = _load()
    truth = _frozen_truth()
    truth["freshness"]["frozen_evidence_commit"] = HEAD_B  # anchors a different commit
    result = mod.evaluate_freshness(truth, "c" * 40)
    assert result["status"] == "FAIL"
    assert any("does not anchor it" in p for p in result["problems"])


def test_drifted_evidence_breaks_the_freeze(tmp_path, monkeypatch):
    mod = _load()
    # Build a manifest whose recorded digest will not match the on-disk bytes.
    evidence = tmp_path / "artifacts" / "release" / "bonn_bright_line"
    evidence.mkdir(parents=True)
    target = evidence / "VERDICT.json"
    target.write_text('{"verdict": "DRIFTED"}', encoding="utf-8")
    wrong_digest = hashlib.sha256(b"original bytes").hexdigest()
    manifest = evidence / "HASHES.sha256"
    manifest.write_text(
        f"{wrong_digest}  artifacts/release/bonn_bright_line/VERDICT.json\n", encoding="utf-8"
    )
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    truth = _frozen_truth()
    result = mod.evaluate_freshness(truth, HEAD_B)
    assert result["status"] == "FAIL"
    assert any("drift" in p for p in result["problems"])


def test_missing_manifest_breaks_the_freeze(tmp_path, monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "ROOT", tmp_path)  # manifest path will not exist
    result = mod.evaluate_freshness(_frozen_truth(), HEAD_B)
    assert result["status"] == "FAIL"
    assert any("manifest missing" in p for p in result["problems"])
