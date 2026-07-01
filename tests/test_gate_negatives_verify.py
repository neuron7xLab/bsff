# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Executable NEGATIVE CONTROLS for the meta-verification gate battery.

A gate that only ever passes is indistinguishable from a gate that does nothing.
Each test here constructs the *smallest known-bad state* a gate is meant to catch
and asserts the gate FAILS (non-zero exit / verdict FAIL). If any of these ever
starts passing, the corresponding gate has lost its teeth.

All controls are hermetic: they operate on temp roots / monkeypatched seams and
never mutate the real source tree, the real artifacts, or invoke git or network.
"""

from __future__ import annotations

import json
import shutil

import pytest

# --------------------------------------------------------------------------- #
# mutation_kill_gate.py — survivors (toothless tests) must FAIL the gate.
# --------------------------------------------------------------------------- #


def test_mutation_kill_gate_fails_when_every_mutant_survives(monkeypatch, tmp_path):
    import tools.mutation_kill_gate as g

    # Build a minimal sandbox source tree carrying the real anchor lines so the
    # gate's anchor lookup resolves, without copying the whole 77 MB repo.
    fake_root = tmp_path / "root"
    for rel in {m.rel_path for m in g.MUTANTS}:
        dst = fake_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(g.ROOT / rel, dst)
    monkeypatch.setattr(g, "ROOT", fake_root)

    # KNOWN-BAD: simulate a suite with no teeth — pytest is green on the baseline
    # AND on every mutated tree, so each mutant SURVIVES (killed requires exit 1).
    monkeypatch.setattr(g, "_pytest", lambda sandbox, targets: (0, ""))

    out = tmp_path / "mutation_kill_report.json"
    rc = g.run(out)

    assert rc == 1, "gate must exit non-zero when mutants survive"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"
    assert report["mutants_killed"] == 0
    assert len(report["survivors"]) == len(g.MUTANTS)


# --------------------------------------------------------------------------- #
# mutation_probe.py — survivors (below-threshold kill ratio) must FAIL.
# --------------------------------------------------------------------------- #


def test_mutation_probe_fails_when_every_mutant_survives(monkeypatch, tmp_path):
    import tools.mutation_probe as g

    fake_root = tmp_path / "root"
    dst = fake_root / "src" / "bsff" / "verdict_engine.py"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(g.ROOT / "src" / "bsff" / "verdict_engine.py", dst)
    monkeypatch.setattr(g, "ROOT", fake_root)

    # KNOWN-BAD: pytest always green -> baseline passes AND no mutant is noticed.
    monkeypatch.setattr(g, "_run", lambda: 0)

    out = tmp_path / "mutation_probe.json"
    rc = g.main(["--output", str(out)])

    assert rc == 1, "probe must exit non-zero when mutants survive"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["killed"] == 0
    assert len(report["survivors"]) == report["mutants"] > 0


# --------------------------------------------------------------------------- #
# run_replayability_gate.py — a divergent re-run must FAIL.
# --------------------------------------------------------------------------- #


def test_replayability_gate_fails_on_divergent_rerun(monkeypatch, tmp_path):
    import tools.run_replayability_gate as g

    # KNOWN-BAD: hidden nondeterminism — the SAME seed produces a different
    # artifact hash on re-run, so the determinism check must trip.
    counter = {"n": 0}

    def fake_run_once(signal, seed):
        i = counter["n"]
        counter["n"] += 1
        return {
            "seed": seed,
            "verdict_class": "REJECT_NULL",  # class stable; only the hash diverges
            "p_value": 0.01,
            "artifact_hash": f"hash-{i}",
        }

    monkeypatch.setattr(g, "_run_once", fake_run_once)

    out = tmp_path / "replayability_report.json"
    rc = g.main(["--output", str(out)])

    assert rc == 1, "gate must exit non-zero when a re-run hash diverges"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "FAIL"
    assert report["artifact_hashes_match"] is False
    assert any("diverged" in f for f in report["failures"])


# --------------------------------------------------------------------------- #
# verify_all.py — meta-runner: one unmet MUST criterion must FAIL the apex.
# --------------------------------------------------------------------------- #


def test_verify_all_fails_when_a_must_criterion_is_unmet(monkeypatch, tmp_path):
    import tools.verify_all as g

    # KNOWN-BAD decision artifact: a MUST criterion is unmet.
    dec_dir = tmp_path / "artifacts" / "decision"
    dec_dir.mkdir(parents=True)
    decision = {
        "criteria": [
            {"id": "C-CONTROLS", "met": False, "must": True, "title": "controls pass"},
        ],
        "certificate_root": "0" * 64,
        "conformance": {"overall": "FAIL", "unverifiable": 0},
        "recommendation": "NO GO",
        "must_criteria_met": False,
    }
    (dec_dir / "decision.json").write_text(json.dumps(decision), encoding="utf-8")

    monkeypatch.setattr(g, "ROOT", tmp_path)

    class _Proc:
        stdout = ""
        stderr = ""
        returncode = 0

    # Neutralise the heavy decision_gate subprocess; we supply the artifact above.
    monkeypatch.setattr(g.subprocess, "run", lambda *a, **k: _Proc())

    rc = g.main()
    assert rc == 1, "apex must exit non-zero when a MUST criterion is unmet"


# --------------------------------------------------------------------------- #
# verify_controls.py — a violated self-falsification contract must FAIL.
# --------------------------------------------------------------------------- #


def test_verify_controls_fails_on_violated_contract(monkeypatch, tmp_path):
    import tools.verify_controls as g

    # KNOWN-BAD: the negative control SURVIVED (instrument passes white noise)
    # and the contract is violated -> controls_ok is False.
    def fake_verify_controls(*, seed, n_surrogates):
        return {
            "negative": {"verdict": "SURVIVED", "control_passed": False},
            "positive": {"verdict": "REFUTED", "control_passed": False},
            "contract": "VIOLATED",
            "controls_ok": False,
        }

    monkeypatch.setattr(g, "verify_controls", fake_verify_controls)

    rc = g.main(["--output", str(tmp_path / "controls")])
    assert rc == 1, "gate must exit non-zero when controls violate the contract"


# --------------------------------------------------------------------------- #
# verify_honesty.py — a single failing sub-check must FAIL the conjunction.
# --------------------------------------------------------------------------- #


def test_verify_honesty_fails_when_one_subcheck_fails(monkeypatch, tmp_path):
    import tools.verify_honesty as g

    # KNOWN-BAD: the first honesty sub-check exits non-zero; the gate is the
    # conjunction, so the whole gate must fail.
    def fake_run(cmd, **kwargs):
        joined = " ".join(str(c) for c in cmd)

        class _Proc:
            returncode = 1 if "validate_claim_audit.py" in joined else 0
            stdout = "FAIL" if returncode == 1 else "ok"
            stderr = ""

        return _Proc()

    monkeypatch.setattr(g.subprocess, "run", fake_run)

    out = tmp_path / "HONESTY_GATE.json"
    rc = g.main(["--output", str(out)])

    assert rc == 1, "honesty gate must exit non-zero when any sub-check fails"
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["all_ok"] is False
    assert any(not c["ok"] for c in report["checks"])


# --------------------------------------------------------------------------- #
# verify_branch_protection.py — an admin-bypass path must NOT be VERIFIED.
# The live GitHub API leg is RESISTANT offline, but the invariant itself is
# testable by feeding a known-bad ruleset through the gh seam.
# --------------------------------------------------------------------------- #


def test_branch_protection_fails_on_admin_bypass(monkeypatch, tmp_path):
    import tools.verify_branch_protection as g

    # Avoid invoking git for the commit sha (kept fully offline / no VCS calls).
    monkeypatch.setattr(g, "_git_sha", lambda: "")

    declared = g._declared_checks()
    assert declared, "precondition: governance doc must declare required checks"

    # KNOWN-BAD ruleset: every declared check is required (missing == empty) BUT
    # an always-on admin bypass path exists -> a bypassable gate does not block.
    def fake_gh_json(args):
        endpoint = args[0]
        if endpoint.endswith("/rulesets"):
            return [{"name": "main-integrity-gate", "id": 4242}], ""
        return (
            {
                "enforcement": "active",
                "bypass_actors": [{"bypass_mode": "always"}],
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [{"context": c} for c in declared]
                        },
                    }
                ],
            },
            "",
        )

    monkeypatch.setattr(g, "_gh_json", fake_gh_json)

    out = tmp_path / "governance_status.json"
    rc = g.main(["--repo", "neuron7xLab/bsff", "--output", str(out)])

    assert rc == 1, "governance must NOT verify while an admin bypass path exists"
    status = json.loads(out.read_text(encoding="utf-8"))
    assert status["admin_bypass_allowed"] is True
    assert status["verdict"] == "NOT_VERIFIED"
    assert status["required_checks_verified"] is False


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
