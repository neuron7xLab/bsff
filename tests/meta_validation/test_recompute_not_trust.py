# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Meta-validation: the verdict RECOMPUTES replay/offline — it never trusts the
self-declared flags in a committed artifact (adversarial audit BYPASS-1 / BYPASS-2).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(stem: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / "tools" / f"{stem}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[stem] = mod
    spec.loader.exec_module(mod)
    return mod


def test_replayability_recompute_catches_divergent_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """A forged per_seed divergence cannot pass: derive() recomputes class stability."""
    gate = _load("run_replayability_gate")
    real = gate._run_once

    def diverging(signal, seed):
        out = real(signal, seed)
        if seed == gate.SEEDS[-1]:
            out = dict(out)
            out["verdict_class"] = (
                "RETAIN_NULL" if out["verdict_class"] == "REJECT_NULL" else "REJECT_NULL"
            )
        return out

    monkeypatch.setattr(gate, "_run_once", diverging)
    report = gate.derive()
    assert report["verdict"] == "FAIL"
    assert report["verdict_class_stable"] is False


def test_replayability_is_pass_on_honest_recompute() -> None:
    gate = _load("run_replayability_gate")
    assert gate.derive()["verdict"] == "PASS"


def test_offline_evidence_reprobes_independent_of_committed_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_offline_evidence re-probes the network guard; it does not read the committed flag."""
    fvv = _load("final_validation_verdict")
    # Point the artifacts root at an EMPTY dir: if the check trusted a committed
    # offline_evidence.json it would now fail; because it re-probes, it still passes.
    monkeypatch.setattr(fvv, "A", tmp_path)
    denied, fails = fvv._offline_evidence()
    assert denied is True, fails
