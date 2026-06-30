# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_update_status():
    spec = importlib.util.spec_from_file_location(
        "update_status",
        ROOT / "tools" / "update_status.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["update_status"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_committed_metadata_gate_is_cheap(tmp_path, monkeypatch, capsys):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)

    def fail_collect():
        raise RuntimeError

    monkeypatch.setattr(tool, "collect_test_count", fail_collect)
    assert tool.main(["--check"]) == 0
    assert "metadata in sync" in capsys.readouterr().out


def test_collection_gate_reports_live_count(tmp_path, monkeypatch, capsys):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)
    monkeypatch.setattr(tool, "collect_test_count", lambda: 123)
    assert tool.main(["--verify-count"]) == 0
    out = capsys.readouterr().out
    assert "123 tests collected" in out
    assert "committed_test_count: 701" in out


def test_strict_count_gate_rejects_different_count(tmp_path, monkeypatch):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)
    monkeypatch.setattr(tool, "collect_test_count", lambda: 123)
    assert tool.main(["--verify-count", "--strict-status"]) == 1


def test_strict_count_gate_accepts_same_count(tmp_path, monkeypatch, capsys):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)
    monkeypatch.setattr(tool, "collect_test_count", lambda: 701)
    assert tool.main(["--verify-count", "--strict-status"]) == 0
    assert "strict count sync: PASS" in capsys.readouterr().out
