from pathlib import Path

from tools.ci.emit_cache_telemetry import run
from tools.ci.common import write_json


def test_unknown_cache_without_reason_fails(tmp_path: Path) -> None:
    telemetry = tmp_path / "install.json"
    write_json(telemetry, {"wall_time_seconds": 1.0, "max_rss_kb": 1})
    code = run(["--workflow", "wf", "--job", "job", "--dependency-manager", "pip", "--cache-key", "k", "--cache-hit", "unknown", "--install-command", "pip install", "--install-telemetry", str(telemetry), "--output-root", str(tmp_path)])
    assert code == 1
