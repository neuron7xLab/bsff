from pathlib import Path

from tools.ci.aggregate_ci_observability import run


def test_require_baseline_fails_when_absent(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    assert run(["--check", "--require-baseline", "--baseline", str(missing)]) == 1
