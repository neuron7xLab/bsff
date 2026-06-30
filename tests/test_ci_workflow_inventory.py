from pathlib import Path

from tools.ci.inventory_workflows import inspect_workflow


def test_python_workflow_without_telemetry_detected(tmp_path: Path) -> None:
    wf = tmp_path / "x.yml"
    wf.write_text("name: X\njobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v6\n      - run: python -m pip install -e .\n", encoding="utf-8")
    doc = inspect_workflow(wf)
    job = doc["jobs"][0]
    assert job["uses_python"] is True
    assert job["has_step_telemetry"] is False
