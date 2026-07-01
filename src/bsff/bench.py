# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Public execution layer: repo-aware wrappers behind ``bsff benchmark`` /
``bsff evidence verify`` / ``bsff reproduce bonn-s2``.

The Bonn bright-line logic lives in the repository (``examples/bonn_bright_line`` and
``tools/``), present in a clone but NOT in a bare ``pip install``. These helpers locate the
repo root and shell out to those scripts; if the surface is absent they return a fail-closed
``BLOCKED_RUNTIME`` state instead of a fake success.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# Allowed terminal states (no other state may be emitted).
STATES = {"PASS", "FAIL", "BLOCKED_DATA", "BLOCKED_RUNTIME"}


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` (or CWD) for the repo surface this layer needs."""
    here = (start or Path.cwd()).resolve()
    for cand in (here, *here.parents):
        if (cand / "pyproject.toml").is_file() and (
            cand / "examples" / "bonn_bright_line"
        ).is_dir():
            return cand
    return None


def _run(root: Path, *cmd: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, *cmd], cwd=root, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _blocked_runtime(detail: str) -> dict[str, object]:
    return {
        "command": "bsff",
        "state": "BLOCKED_RUNTIME",
        "detail": detail,
        "hint": "Run from a BSFF repository clone (needs examples/bonn_bright_line and tools/).",
    }


def verify_evidence(root: Path | None = None) -> dict[str, object]:
    """`bsff evidence verify` — coherence, hashes, release gate, raw-data hygiene."""
    repo = find_repo_root(root)
    if repo is None:
        return _blocked_runtime("repository surface not found")
    checks: list[dict[str, object]] = []

    def add(name: str, rc: int, out: str = "") -> None:
        checks.append(
            {"check": name, "ok": rc == 0, "detail": out.splitlines()[-1:] if out else []}
        )

    add("current_truth_fresh", *_run(repo, "tools/generate_current_truth.py", "--check"))
    add("docs_truth_coherent", *_run(repo, "tools/validate_current_truth.py"))
    add(
        "release_check",
        *_run(repo, "examples/bonn_bright_line/release_check.py", "--root", str(repo)),
    )
    if (repo / "tools" / "validate_artifact_schema.py").is_file():
        add("artifact_schema", *_run(repo, "tools/validate_artifact_schema.py"))

    hashes = repo / "artifacts" / "release" / "bonn_bright_line" / "HASHES.sha256"
    hash_ok, bad = True, []
    if hashes.is_file():
        for line in hashes.read_text().splitlines():
            if not line.strip():
                continue
            digest, _, rel = line.partition("  ")
            fp = repo / rel
            if not fp.is_file() or hashlib.sha256(fp.read_bytes()).hexdigest() != digest:
                hash_ok = False
                bad.append(rel)
    else:
        hash_ok, bad = False, ["HASHES.sha256 missing"]
    checks.append({"check": "hash_verification", "ok": hash_ok, "detail": bad[:5]})

    tracked = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True).stdout
    raw_ok = not any("bonn_data/" in ln for ln in tracked.splitlines())
    checks.append({"check": "raw_data_not_tracked", "ok": raw_ok, "detail": []})

    state = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    truth = repo / "artifacts" / "release" / "CURRENT_TRUTH.json"
    latest = json.loads(truth.read_text())["latest_validation_state"] if truth.is_file() else None
    return {
        "command": "bsff evidence verify",
        "state": state,
        "canonical_state": latest,
        "checks": checks,
        "failed": [c["check"] for c in checks if not c["ok"]],
    }


def reproduce_bonn_s2(
    root: Path | None = None, execute: bool = False, n_segments: int = 100, n_surrogates: int = 199
) -> dict[str, object]:
    """`bsff reproduce bonn-s2` — dry-run verification (default) or full re-execution."""
    repo = find_repo_root(root)
    if repo is None:
        return _blocked_runtime("repository surface not found")
    truth = repo / "artifacts" / "release" / "CURRENT_TRUTH.json"
    latest = json.loads(truth.read_text())["latest_validation_state"] if truth.is_file() else None
    if not execute:
        ver = verify_evidence(repo)
        return {
            "command": "bsff reproduce bonn-s2",
            "mode": "dry-run",
            "state": ver["state"],
            "canonical_state": latest,
            "evidence_verify": ver["state"],
            "note": "Verified committed S2 artifacts + hashes + coherence. "
            "Pass --execute to re-run the confirmatory (~30-100 min).",
        }
    data = repo / "examples" / "bonn_bright_line" / "bonn_data"
    if not (data / "E").is_dir():
        return {
            "command": "bsff reproduce bonn-s2",
            "mode": "execute",
            "state": "BLOCKED_DATA",
            "detail": "bonn_data/{E,A,B} not staged; see docs/DATA_POLICY.md / download_bonn.sh",
        }
    rc, out = _run(
        repo,
        "examples/bonn_bright_line/s2_confirmatory.py",
        "--data-dir",
        str(data),
        "--n-segments",
        str(n_segments),
        "--n-surrogates",
        str(n_surrogates),
        "--output",
        "artifacts/bonn_bright_line/s2_CONFIRMATORY_VERDICT.json",
    )
    return {
        "command": "bsff reproduce bonn-s2",
        "mode": "execute",
        "state": "PASS" if rc == 0 else "FAIL",
        "log_tail": out.splitlines()[-3:],
    }


def run_benchmark(
    target: str,
    root: Path | None = None,
    mode: str = "confirmatory",
    n_segments: int = 100,
    n_surrogates: int = 199,
) -> dict[str, object]:
    """`bsff benchmark bonn-bright-line` — execute the S2 benchmark and emit its verdict."""
    if target != "bonn-bright-line":
        return {
            "command": "bsff benchmark",
            "state": "FAIL",
            "detail": f"unknown target {target!r}",
        }
    repo = find_repo_root(root)
    if repo is None:
        return _blocked_runtime("repository surface not found")
    data = repo / "examples" / "bonn_bright_line" / "bonn_data"
    if not (data / "E").is_dir():
        return {
            "command": "bsff benchmark bonn-bright-line",
            "state": "BLOCKED_DATA",
            "detail": "bonn_data/{E,A,B} not staged; see docs/DATA_POLICY.md",
        }
    if mode == "exploratory":
        rc, out = _run(
            repo,
            "examples/bonn_bright_line/s2_evaluate_candidates.py",
            "--data-dir",
            str(data),
            "--n-segments",
            str(min(n_segments, 30)),
            "--n-surrogates",
            str(n_surrogates),
            "--output",
            "artifacts/bonn_bright_line/s2_EXPLORATORY_RESULTS.json",
        )
    else:
        rc, out = _run(
            repo,
            "examples/bonn_bright_line/s2_confirmatory.py",
            "--data-dir",
            str(data),
            "--n-segments",
            str(n_segments),
            "--n-surrogates",
            str(n_surrogates),
            "--output",
            "artifacts/bonn_bright_line/s2_CONFIRMATORY_VERDICT.json",
        )
    return {
        "command": "bsff benchmark bonn-bright-line",
        "mode": mode,
        "state": "PASS" if rc == 0 else "FAIL",
        "log_tail": out.splitlines()[-3:],
    }
