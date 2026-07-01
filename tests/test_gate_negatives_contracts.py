# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Executable NEGATIVE CONTROLS for the contract/verification gates.

Each test feeds a *known-bad* state to a gate and asserts the gate FAILS
(non-zero exit / FAIL status). A gate that cannot distinguish bad from good is a
banner, not an instrument; these tests prove each gate discriminates. They pass
by asserting failure, so the real repository stays green while the gates remain
honest under adversarial input.

Gates covered:
  tools/validate_architecture_contract.py
  tools/validate_forbidden_claims.py
  tools/validate_r6_contracts.py
  tools/validate_openai_2026_eval_contract.py
  tools/check_contracts.py            (delegates to run_contract_conformance)
  tools/validate_validation_corpus.py
  tools/validate_mutation_report.py
  tools/decision_gate.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    """Load a gate tool as a fresh module so monkeypatching does not leak."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# 1. validate_architecture_contract.py
#    Known-bad: a tampered pipeline whose stage topology, verdict, contract
#    digest, and evidence-graph size all deviate from the required contract.
# --------------------------------------------------------------------------- #
def test_architecture_contract_gate_fails_on_tampered_pipeline(tmp_path, monkeypatch):
    mod = _load("validate_architecture_contract")

    class _BadRegistry:
        def ids(self):
            return ["tampered_stage"]

    class _BadResult:
        verdict = "REFUTED"
        contract_sha256 = "not_a_sha256_digest"

        def to_dict(self):
            return {"evidence_graph": {"node_count": 0}}

    class _BadPipeline:
        registry = _BadRegistry()

        def evaluate(self, *args, **kwargs):
            return _BadResult()

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "FalsificationPipeline", lambda: _BadPipeline())

    assert mod.main() == 1


# --------------------------------------------------------------------------- #
# 2. validate_forbidden_claims.py
#    Known-bad: a public surface asserting a forbidden clinical/FDA claim with
#    no negating context.
# --------------------------------------------------------------------------- #
def test_forbidden_claims_gate_fails_on_injected_forbidden_claim(tmp_path, monkeypatch):
    mod = _load("validate_forbidden_claims")
    bad = tmp_path / "BAD_SURFACE.md"
    bad.write_text(
        "BSFF is clinically validated for diagnosis and is FDA cleared for the clinic.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "TRUTH", tmp_path / "no_such_truth.json")
    monkeypatch.setattr(mod, "SURFACES", ["BAD_SURFACE.md"])

    out = tmp_path / "claim_safety_report.json"
    assert mod.main(["--output", str(out)]) == 1
    report = json.loads(out.read_text())
    assert report["status"] == "FAIL"
    assert report["violations"]


# --------------------------------------------------------------------------- #
# 3. validate_r6_contracts.py
#    Known-bad: a repo root missing all R6/R7 scaffolding, with empty claim and
#    dataset registries (so no rank-boundary language or reproduce tokens exist).
# --------------------------------------------------------------------------- #
def test_r6_contract_gate_fails_on_missing_scaffold(tmp_path, monkeypatch):
    mod = _load("validate_r6_contracts")
    (tmp_path / "claims.yaml").write_text('{"claims": {}}', encoding="utf-8")
    (tmp_path / "data_registry.json").write_text('{"datasets": {}}', encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)

    errors = mod.evaluate()
    assert errors, "empty R6 scaffold must produce contract violations"
    assert mod.main() == 1


# --------------------------------------------------------------------------- #
# 4. validate_openai_2026_eval_contract.py
#    Known-bad: the committed contract with one eval re-pointed at a missing
#    evidence artifact — the grader can no longer resolve, so the eval FAILs.
# --------------------------------------------------------------------------- #
def test_openai_eval_contract_gate_fails_on_missing_evidence(tmp_path, monkeypatch):
    mod = _load("validate_openai_2026_eval_contract")
    contract = yaml.safe_load(
        (ROOT / "contracts" / "openai_2026_eval_contract.yaml").read_text(encoding="utf-8")
    )
    assert contract["evals"], "real contract should declare evals"
    contract["evals"][0]["evidence_artifact"] = "artifacts/negative_control_missing_evidence.json"
    tampered = tmp_path / "contract.yaml"
    tampered.write_text(yaml.safe_dump(contract), encoding="utf-8")

    monkeypatch.setattr(mod, "CONTRACT", tampered)
    monkeypatch.setattr(mod, "REPORT", tmp_path / "report.json")

    assert mod.main([]) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["verdict"] == "FAIL"


# --------------------------------------------------------------------------- #
# 5. check_contracts.py -> run_contract_conformance
#    Known-bad: a contract whose declared command exits non-zero while claiming
#    expect_exit 0 -> NONCONFORMANT -> gate exit 1.
# --------------------------------------------------------------------------- #
def test_check_contracts_gate_fails_on_nonconformant_command(tmp_path):
    mod = _load("check_contracts")
    contract = tmp_path / "bad_contract.yaml"
    contract.write_text(
        yaml.safe_dump(
            {
                "contract_id": "negative_control_conformance",
                "items": [
                    {
                        "id": "intentional_nonconformance",
                        "kind": "command",
                        "run": 'python -c "import sys; sys.exit(7)"',
                        "expect_exit": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "conformance"
    rc = mod.main(["--contract", str(contract), "--output", str(out)])
    assert rc == 1
    verdict = json.loads((out / "CONFORMANCE_VERDICT.json").read_text())
    assert verdict["overall"] == "NONCONFORMANT"


# --------------------------------------------------------------------------- #
# 6. validate_validation_corpus.py
#    Known-bad: a manifest declaring clinical data / non-synthetic and pointing
#    at a missing artifact.
# --------------------------------------------------------------------------- #
def test_validation_corpus_gate_fails_on_clinical_manifest(tmp_path, monkeypatch):
    mod = _load("validate_validation_corpus")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifact": "negative_control_missing_corpus.npz",
                "sha256": "0" * 64,
                "arrays": {},
                "clinical_data": True,
                "synthetic_only": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "MANIFEST", manifest)
    assert mod.main() == 1


# --------------------------------------------------------------------------- #
# 7. validate_mutation_report.py
#    Known-bad: a mutation report with surviving mutants and a sub-1.0 score.
# --------------------------------------------------------------------------- #
def test_mutation_report_gate_fails_on_survivors(tmp_path):
    mod = _load("validate_mutation_report")
    report = tmp_path / "mutation_kill_report.json"
    report.write_text(
        json.dumps(
            {
                "mutants_total": 8,
                "mutants_killed": 6,
                "survivors": ["mut-3", "mut-7"],
                "mutation_score": 0.75,
                "verdict": "FAIL",
                "results": [
                    {"mutant_id": f"m{i}", "mutant_status": "killed" if i < 6 else "survived"}
                    for i in range(8)
                ],
            }
        ),
        encoding="utf-8",
    )
    assert mod.main([str(report)]) == 1


# --------------------------------------------------------------------------- #
# 8. decision_gate.py --check
#    Known-bad: a DECISION.md that has drifted from the evidence-derived render.
#    (_run is stubbed so no subprocess regeneration mutates the real repo; the
#    freshness comparison — the gate's only non-zero exit path — is exercised.)
# --------------------------------------------------------------------------- #
def test_decision_gate_check_fails_on_stale_decision(tmp_path, monkeypatch):
    mod = _load("decision_gate")
    monkeypatch.setattr(mod, "_run", lambda cmd: 0)
    stale = tmp_path / "DECISION.md"
    stale.write_text("STALE — this does not match the evidence-derived render.\n", encoding="utf-8")
    monkeypatch.setattr(mod, "DECISION", stale)
    monkeypatch.setattr(mod, "BUNDLE", tmp_path / "bundle")

    assert mod.main(["--check"]) == 1
