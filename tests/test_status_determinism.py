# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""STATUS.md checks stay cheap; live pytest collection is an explicit slow gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_update_status():
    spec = importlib.util.spec_from_file_location("update_status", ROOT / "tools" / "update_status.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["update_status"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_status_check_does_not_collect_tests(tmp_path, monkeypatch, capsys):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)

    def forbidden_collect():  # pragma: no cover - failure path
        raise AssertionError("--check must not run pytest --collect-only")

    monkeypatch.setattr(tool, "collect_test_count", forbidden_collect)
    assert tool.main(["--check"]) == 0
    assert "STATUS.md: in sync" in capsys.readouterr().out


def test_status_verify_count_is_the_explicit_collection_gate(tmp_path, monkeypatch, capsys):
    tool = _load_update_status()
    status = tmp_path / "STATUS.md"
    status.write_text(tool.generate(test_count=701), encoding="utf-8")
    monkeypatch.setattr(tool, "STATUS", status)
    monkeypatch.setattr(tool, "collect_test_count", lambda: 123)

    assert tool.main(["--verify-count"]) == 0
    out = capsys.readouterr().out
    assert "pytest collect-only: 123 tests collected" in out
    assert "STATUS.md committed live count: 701" in out
