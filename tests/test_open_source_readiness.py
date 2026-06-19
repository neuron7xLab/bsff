# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_tool(name: str):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / name)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_open_source_readiness_tool_passes():
    result = run_tool("validate_open_source_readiness.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_github_actions_policy_tool_passes():
    result = run_tool("check_github_actions_policy.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_secret_scan_tool_passes():
    result = run_tool("scan_secrets.py")
    assert result.returncode == 0, result.stdout + result.stderr
