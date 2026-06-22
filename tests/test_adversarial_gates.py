# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Adversarial mutation battery: prove each gate rejects a RANGE of violations.

A single hand-picked tamper test proves nothing — it can be a softball. For every
guarded invariant this module injects multiple distinct violations and asserts the
gate fires on each, plus a clean control that must pass. If any mutation slips
through, the gate is decorative and this suite goes red.

All checks are in-process (no tool subprocesses), so they run in the fast matrix.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- claim audit
CA = _load("validate_claim_audit")
_HDR = "## status coupling\n\n| # | Claim | Evidence | Command | Value | Status |\n|-|-|-|-|-|-|\n"


def _audit_text(row: str, tmp_path: Path, *, header: bool = True) -> dict:
    p = tmp_path / "CLAIM_AUDIT.md"
    p.write_text(
        (_HDR if header else "| # | a | b | c | d | e |\n|-|-|-|-|-|-|\n") + row, encoding="utf-8"
    )
    return CA.audit(p)


@pytest.mark.parametrize(
    "row",
    [
        "| 1 | x | e | none | v | **VERIFIED** |",  # VERIFIED, no command
        "| 2 | x | e | `cmd` |  | **VERIFIED** |",  # VERIFIED, no value
        "| 3 | x | e | `cmd` | v | **LIKELY** |",  # soft state
        "| 4 | x | e | `cmd` | v | **PASS** |",  # soft state
        "| 5 | x | e | `cmd` | v | **PROBABLY** |",  # soft state
        "| 6 | x | e | `cmd` | v | **MAYBE-OK** |",  # out-of-vocab
        "| 7 | x |  | none |  | **UNPROVEN** |",  # UNPROVEN, no reason
        "| 8 | x |  | none |  | **NEEDS_EXTERNAL_CHECK** |",  # no reason
    ],
)
def test_claim_audit_rejects_each_violation(row, tmp_path):
    assert _audit_text(row, tmp_path)["failures"], f"gate missed: {row}"


def test_claim_audit_rejects_missing_coupling_section(tmp_path):
    res = _audit_text("| 1 | x | e | `cmd` | v | **VERIFIED** |", tmp_path, header=False)
    assert any("status coupling" in f for f in res["failures"])


def test_claim_audit_accepts_clean_row(tmp_path):
    assert _audit_text("| 1 | x | e | `cmd` | 42 | **VERIFIED** |", tmp_path)["failures"] == []


# ---------------------------------------------------------------- grounding
GR = _load("verify_grounding")
_SRC = "research/bci_generalization/result_bnci2014_001_sub1-2.json"


@pytest.mark.parametrize("key", ["within_mean", "cross_subject_loso_mean", "loso_gap"])
def test_grounding_rejects_wrong_number(key):
    bogus = [{"label": key, "doc": "docs/MANUSCRIPT.md", "source": _SRC, "key": key, "dp": 9}]
    assert GR.check(facts=bogus, readme_check=False), f"grounding missed wrong {key}"


def test_grounding_accepts_real_numbers():
    assert GR.check() == []


# ---------------------------------------------------------------- certificate
CR = _load("certify_release")


def _good_chain() -> dict:
    prev = CR.GENESIS
    chain = []
    for seq, name in enumerate(["a", "b", "c"]):
        payload = {"seq": seq, "stream": name, "exit": 0, "ok": True, "evidence_sha256": ""}
        h = CR.stable_sha256({"prev": prev, "payload": payload})
        chain.append({**payload, "prev_hash": prev, "link_hash": h})
        prev = h
    return {"root_hash": prev, "all_streams_green": True, "overall": "CERTIFIED", "chain": chain}


def test_certificate_clean_chain_verifies():
    assert CR.verify_chain(_good_chain())[0] is True


def test_certificate_rejects_flipped_verdict():
    c = _good_chain()
    c["chain"][1]["ok"] = False
    assert CR.verify_chain(c)[0] is False


def test_certificate_rejects_reordered_links():
    c = _good_chain()
    c["chain"][0], c["chain"][1] = c["chain"][1], c["chain"][0]
    assert CR.verify_chain(c)[0] is False


def test_certificate_rejects_corrupted_link_hash():
    c = _good_chain()
    c["chain"][2]["link_hash"] = "0" * 64
    assert CR.verify_chain(c)[0] is False


def test_certificate_rejects_forged_root():
    c = _good_chain()
    c["root_hash"] = "f" * 64
    assert CR.verify_chain(c)[0] is False


def test_certificate_rejects_dropped_link():
    c = _good_chain()
    del c["chain"][1]
    assert CR.verify_chain(c)[0] is False


# ---------------------------------------------------------------- conformance
CONF = _load("run_contract_conformance")


def test_conformance_flags_missing_required_file():
    r = CONF._check_item({"id": "x", "kind": "file", "path": "does/not/exist.json"})
    assert r["status"] == "NONCONFORMANT"


def test_conformance_flags_failing_command():
    r = CONF._check_item(
        {"id": "x", "kind": "command", "run": "python -c 'import sys;sys.exit(3)'"}
    )
    assert r["status"] == "NONCONFORMANT"


def test_conformance_blocked_is_unverifiable_never_silent_pass():
    r = CONF._check_item({"id": "x", "kind": "blocked", "blocker": "network", "why": "w"})
    assert r["status"] == "UNVERIFIABLE"


# ------------------------------------------------ markdown count-literal guard
MD = _load("validate_markdown")


@pytest.mark.parametrize(
    "body",
    [
        "The suite has 310 passed today.",  # bare `<N> passed`
        "Test suite | 80 / 80 passed | ok",  # `N/N passed`
        "python -m pytest tests/ | grep collected   # 389 tests collected",  # collect form
        "full suite — expect 310 passed",  # `expect <N> passed`
        "the live tree collects and passes **310**.",  # prose `passes <N>`
    ],
)
def test_markdown_gate_rejects_each_count_literal(body, tmp_path):
    (tmp_path / "DOC.md").write_text(body + "\n", encoding="utf-8")
    assert MD.find_count_literals(tmp_path), f"gate missed: {body!r}"


@pytest.mark.parametrize(
    "body",
    [
        "See [STATUS.md](STATUS.md) for the live count.",  # the canonical reference
        "`bsff selftest` runs and 6 tests pass here.",  # single-digit per-file count
        'example "80/80 passed" <!-- count-literal-ok -->',  # auditable escape hatch
    ],
)
def test_markdown_gate_allows_clean_text(body, tmp_path):
    (tmp_path / "DOC.md").write_text(body + "\n", encoding="utf-8")
    assert not MD.find_count_literals(tmp_path), f"false positive on: {body!r}"


def test_markdown_gate_exempts_generated_status_file(tmp_path):
    (tmp_path / "STATUS.md").write_text("| Live test count | **386** |\n", encoding="utf-8")
    # STATUS.md is the generated single source; even an adjacent form is exempt.
    (tmp_path / "STATUS.md").write_text("389 tests collected\n", encoding="utf-8")
    assert not MD.find_count_literals(tmp_path)
