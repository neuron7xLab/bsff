import sys
from pathlib import Path

from tools.ci.common import read_json
from tools.ci.measure_step import run


def test_measure_step_writes_wall_time(tmp_path: Path) -> None:
    code = run([
        "--step-id",
        "unit",
        "--workflow",
        "wf",
        "--job",
        "job",
        "--output-root",
        str(tmp_path),
        "--",
        sys.executable,
        "--version",
    ])
    assert code == 0
    doc = read_json(tmp_path / "wf" / "job" / "unit.json")
    assert doc["wall_time_seconds"] >= 0
    assert doc["max_rss_kb"] >= 0
    assert doc["verdict"] == "PASS"
