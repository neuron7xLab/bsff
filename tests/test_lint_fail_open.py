# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the fail-open static analyzer (tools/lint_fail_open.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "lint_fail_open", ROOT / "tools" / "lint_fail_open.py"
)
assert _spec is not None and _spec.loader is not None
lint_fail_open = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lint_fail_open)


def test_evaluate_schema_and_determinism() -> None:
    report = lint_fail_open.evaluate(ROOT)
    assert report["schema"] == "bsff.fail_open_lint/v1"
    assert report["status"] in {"PASS", "FAIL"}
    assert isinstance(report["findings"], list)
    for finding in report["findings"]:
        assert set(finding) == {"file", "line", "rule", "snippet"}
        assert isinstance(finding["line"], int)
        assert finding["rule"] in {"fail_open_except", "unfailable_gate"}
    # Deterministic: identical input -> identical output.
    assert lint_fail_open.evaluate(ROOT) == report


def test_repo_check_residual_is_clean() -> None:
    """Every real finding must be either fixed or allowlisted (ratchet)."""
    report = lint_fail_open.evaluate(ROOT)
    allowed = lint_fail_open._load_allowlist(lint_fail_open.ALLOWLIST)
    residual = [f for f in report["findings"] if f"{f['file']}:{f['rule']}" not in allowed]
    assert residual == [], f"unexpected fail-open findings: {residual}"


def test_negative_control_except_returns_zero_is_flagged() -> None:
    source = (
        "def check_thing():\n    try:\n        risky()\n    except Exception:\n        return 0\n"
    )
    findings = lint_fail_open.analyze_source(source)
    rules = {f["rule"] for f in findings}
    assert "fail_open_except" in rules


def test_negative_control_except_returns_true_is_flagged() -> None:
    source = (
        "def validate():\n    try:\n        risky()\n    except Exception:\n        return True\n"
    )
    findings = lint_fail_open.analyze_source(source)
    assert any(f["rule"] == "fail_open_except" for f in findings)


def test_negative_control_except_prints_pass_is_flagged() -> None:
    source = (
        "def check():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        '        print("all checks PASS")\n'
    )
    findings = lint_fail_open.analyze_source(source)
    assert any(f["rule"] == "fail_open_except" for f in findings)


def test_fail_closed_except_reraise_not_flagged() -> None:
    source = (
        "def check():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        raise\n"
        "    return 0\n"
    )
    findings = lint_fail_open.analyze_source(source)
    assert all(f["rule"] != "fail_open_except" for f in findings)


def test_fail_closed_except_returns_one_not_flagged() -> None:
    source = (
        "def check():\n"
        "    try:\n"
        "        risky()\n"
        "        return 0\n"
        "    except Exception:\n"
        "        return 1\n"
    )
    findings = lint_fail_open.analyze_source(source)
    assert findings == []


def test_gate_with_failure_branch_not_flagged() -> None:
    """A gate that can return nonzero is a real gate; do not flag it."""
    source = "def main():\n    if not ok():\n        return 1\n    return 0\n"
    findings = lint_fail_open.analyze_source(source)
    assert all(f["rule"] != "unfailable_gate" for f in findings)


def test_gate_delegating_return_not_flagged() -> None:
    """Returning a callee's code can propagate failure; not unfailable."""
    source = "def main():\n    return run_checks()\n"
    findings = lint_fail_open.analyze_source(source)
    assert findings == []


def test_unfailable_gate_is_flagged() -> None:
    source = 'def main():\n    print("done")\n    return 0\n'
    findings = lint_fail_open.analyze_source(source)
    assert any(f["rule"] == "unfailable_gate" for f in findings)


def test_non_gate_function_returning_zero_not_flagged() -> None:
    source = "def helper():\n    return 0\n"
    findings = lint_fail_open.analyze_source(source)
    assert findings == []


def test_gate_with_assert_not_flagged() -> None:
    source = "def check():\n    assert invariant()\n    return 0\n"
    findings = lint_fail_open.analyze_source(source)
    assert all(f["rule"] != "unfailable_gate" for f in findings)
