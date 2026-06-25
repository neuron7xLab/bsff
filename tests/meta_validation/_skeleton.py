# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Shared helpers for the meta-validation gate.

These tests validate the VALIDATION GRID ITSELF: each asserts that a known-bad
artifact is REJECTED by the grid's own validators. ``valid_pass_skeleton`` is the
single fully-correct PASS verdict every "known-bad" case mutates away from; it is
the control that proves the validators are not vacuously rejecting everything.

Tools are loaded by absolute path (no reliance on ``tools/`` being on ``sys.path``)
so the suite is hermetic regardless of install layout.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "openai_2026_verdict.schema.json"

_SIXTYFOUR_HEX = "a" * 64


def load_tool(name: str) -> ModuleType:
    """Import a repo tool module by absolute path under ``tools/``."""
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_meta_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load tool {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def valid_pass_skeleton() -> dict[str, Any]:
    """A minimal but fully schema-valid PASS verdict (the control).

    Mirrors the keys and PASS-side ``allOf`` constraints of
    ``schemas/openai_2026_verdict.schema.json``: empty ``blocking_failures``, every
    boolean gate true, ``statistical_power``/``claim_integrity`` PASS, and
    ``mutation_score == 1.0``.
    """
    return {
        "workflow_name": "OpenAI-2026 Validation Grid",
        "project": "bsff",
        "verdict": "PASS",
        "grid_version": "2026.1",
        "head_sha": "abcdef1",
        "run_context": "ci",
        "python_version": "3.12.0",
        "dependency_lock_hashes": {"core.lock": _SIXTYFOUR_HEX},
        "gate_results": {"01-lock-integrity": "PASS"},
        "artifact_digests": {"mutation_kill_report": _SIXTYFOUR_HEX},
        "dataset_manifest": {"datasets": []},
        "seed_manifest": {"seeds": [1, 2, 3]},
        "mutation_report": {
            "mutation_score": 1.0,
            "mutants_total": 9,
            "survivors": [],
            "verdict": "PASS",
        },
        "power_profile": {"verdict": "PASS"},
        "red_team_summary": {
            "verdict": "PASS",
            "categories_total": 6,
            "categories_killed": 6,
        },
        "claim_audit": {"verdict": "PASS", "forbidden_violations": []},
        "blocking_failures": [],
        "evidence_complete": True,
        "network_denied": True,
        "replayable": True,
        "mutation_score": 1.0,
        "statistical_power": "PASS",
        "artifact_digests_present": True,
        "claim_integrity": "PASS",
    }
