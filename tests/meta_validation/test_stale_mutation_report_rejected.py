# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: a STALE mutation report cannot certify fresh code.

The mutation gate is only honest if the committed report covers EXACTLY the live
``MUTANTS`` set. A report whose ``results`` mutant_id set drifts from the live set
describes code that no longer exists, so ``tools/final_validation_verdict._mutation``
must flag it as stale/blocking. This drives the real derivation against a temp
artifact tree and proves the stale report is rejected; the control (the live set,
perfect score) proves the freshness check is not vacuous.
"""

from __future__ import annotations

import importlib.util
import json
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
    # Register before exec so dataclass field resolution (which looks the module up
    # in sys.modules via cls.__module__) works for tools that define dataclasses.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _live_mutant_ids() -> set[str]:
    mkg = _load("mutation_kill_gate")
    return {m.mutant_id for m in mkg.MUTANTS}


def _report(mutant_ids: list[str], score: float = 1.0) -> dict[str, Any]:
    return {
        "mutants_total": max(len(mutant_ids), 8),
        "mutants_killed": len(mutant_ids),
        "mutation_score": score,
        "survivors": [],
        "verdict": "PASS",
        "results": [{"mutant_id": mid, "mutant_status": "killed"} for mid in mutant_ids],
    }


def _run_mutation_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, report: dict[str, Any]):
    """Point the verdict tool's artifact root at tmp_path and call _mutation()."""
    fvv = _load("final_validation_verdict")
    adv = tmp_path / "adversarial"
    adv.mkdir(parents=True, exist_ok=True)
    (adv / "mutation_kill_report.json").write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setattr(fvv, "A", tmp_path)
    return fvv._mutation()


def test_stale_report_with_drifted_mutant_set_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report covering a wrong/old mutant set must produce a stale blocking failure."""
    stale_ids = ["MUT-OLD-001", "MUT-OLD-002", "MUT-OLD-003"]
    assert set(stale_ids) != _live_mutant_ids()
    _score, fails = _run_mutation_check(tmp_path, monkeypatch, _report(stale_ids))
    assert any("stale" in f for f in fails), f"stale report not rejected; fails={fails}"


def test_stale_report_missing_one_live_mutant_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dropping a single live mutant from the report still trips the freshness check."""
    live = sorted(_live_mutant_ids())
    truncated = live[:-1]  # one mutant unaccounted for
    assert set(truncated) != _live_mutant_ids()
    _score, fails = _run_mutation_check(tmp_path, monkeypatch, _report(truncated))
    assert any("stale" in f for f in fails), f"truncated report not rejected; fails={fails}"


def test_control_fresh_report_passes_freshness_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control: the exact live mutant set with a perfect score has no stale failure."""
    live = sorted(_live_mutant_ids())
    _score, fails = _run_mutation_check(tmp_path, monkeypatch, _report(live))
    assert not any("stale" in f for f in fails), f"fresh report wrongly flagged; fails={fails}"
