# SPDX-License-Identifier: GPL-3.0-or-later
"""The intent-contract gate must fail closed on an unclosed meaning edge.

Positive: the real registry is fully closed. Negative controls prove the gate
can and does fail when an intent is unratified, unbound, or points at a ghost
negative control — otherwise meaning-closure would itself be decorative.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load():
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("intent_contract", TOOLS / "intent_contract.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_registry(tmp_path: Path, intents: dict) -> Path:
    (tmp_path / "intents").mkdir(parents=True, exist_ok=True)
    (tmp_path / "intents" / "registry.json").write_text(
        json.dumps({"schema": "bsff.intent_contract/v1", "intents": intents}), encoding="utf-8"
    )
    (tmp_path / "tools").mkdir(exist_ok=True)
    (tmp_path / "tools" / "real_gate.py").write_text(
        "def main():\n    return 0\n", encoding="utf-8"
    )
    (tmp_path / "tests").mkdir(exist_ok=True)
    # The test file must reference the gate module (static linkage) or the gate
    # is treated as a decorative, unlinked control.
    (tmp_path / "tests" / "test_real.py").write_text(
        "import real_gate  # noqa: F401\n\n\ndef test_real_negative_control():\n    assert True\n",
        encoding="utf-8",
    )
    return tmp_path


_GOOD = {
    "statement": "a falsifiable thing holds",
    "verification": {
        "gate": "tools/real_gate.py",
        "negative_control": "tests/test_real.py::test_real_negative_control",
    },
    "ratified_by": "operator",
    "status": "ratified",
}


# ---- positive: the live registry is fully closed --------------------------


def test_real_registry_is_fully_closed():
    ic = _load()
    report = ic.evaluate(ROOT)
    assert report["status"] == "PASS", report["violations"]
    assert report["intents_total"] >= 5
    assert report["ratified"] == report["intents_total"]


def test_synthetic_good_intent_passes(tmp_path):
    ic = _load()
    root = _write_registry(tmp_path, {"INTENT-OK": dict(_GOOD)})
    assert ic.evaluate(root)["status"] == "PASS"


# ---- negative controls ----------------------------------------------------


def test_unratified_intent_fails(tmp_path):
    ic = _load()
    bad = dict(_GOOD)
    bad["ratified_by"] = ""
    bad["status"] = "draft"
    root = _write_registry(tmp_path, {"INTENT-UNRATIFIED": bad})
    report = ic.evaluate(root)
    assert report["status"] == "FAIL"
    assert any("not ratified" in v for v in report["violations"])


def test_intent_with_ghost_negative_control_fails(tmp_path):
    ic = _load()
    bad = dict(_GOOD)
    bad["verification"] = {
        "gate": "tools/real_gate.py",
        "negative_control": "tests/test_real.py::test_does_not_exist",
    }
    root = _write_registry(tmp_path, {"INTENT-GHOST": bad})
    report = ic.evaluate(root)
    assert report["status"] == "FAIL"
    assert any("negative_control does not resolve" in v for v in report["violations"])


def test_intent_with_missing_gate_fails(tmp_path):
    ic = _load()
    bad = dict(_GOOD)
    bad["verification"] = {
        "gate": "tools/nonexistent_gate.py",
        "negative_control": "tests/test_real.py::test_real_negative_control",
    }
    root = _write_registry(tmp_path, {"INTENT-NOGATE": bad})
    report = ic.evaluate(root)
    assert report["status"] == "FAIL"
    assert any("verification gate missing" in v for v in report["violations"])


def test_empty_registry_fails(tmp_path):
    ic = _load()
    (tmp_path / "intents").mkdir()
    (tmp_path / "intents" / "registry.json").write_text(
        json.dumps({"schema": "bsff.intent_contract/v1", "intents": {}}), encoding="utf-8"
    )
    report = ic.evaluate(tmp_path)
    assert report["status"] == "FAIL"
    assert any("no intent contracts" in v for v in report["violations"])
