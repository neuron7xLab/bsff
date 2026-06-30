# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_current_truth",
        ROOT / "tools" / "validate_current_truth.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_current_truth_gate_requires_status_token(tmp_path, monkeypatch):
    validator = _load_validator()
    release = tmp_path / "artifacts" / "release"
    release.mkdir(parents=True)
    truth = release / "CURRENT_TRUTH.json"
    truth.write_text(
        json.dumps(
            {
                "latest_validation_state": TOKEN,
                "BNCI_chain_state": "UNLOCKED_FOR_PREREGISTRATION_ONLY",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "STATUS.md").write_text("# status\n", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "TRUTH", truth)
    monkeypatch.setattr(validator, "OUT", release / "TRUTH_CONSISTENCY_CHECK.json")
    monkeypatch.setattr(validator, "SURFACES", ["STATUS.md"])
    monkeypatch.setattr(
        validator,
        "MUST_AFFIRM",
        ["STATUS.md", "artifacts/release/CURRENT_TRUTH.json"],
    )
    assert validator.main([]) == 1
