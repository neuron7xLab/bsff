# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Single-command release evidence bundle.

A repository can have a dozen green gates and still have no single artifact a
reviewer can pick up and verify. ``bsff release-check`` runs the canonical gate
battery, collects the evidence each gate emits, hashes every output, and writes
one self-describing bundle: ``artifacts/release/MANIFEST.json`` (machine-readable,
every gate + every artifact hash) and ``artifacts/release/VERDICT.md`` (the human
summary). The bundle is fail-closed — if any required gate fails, the release
verdict is BLOCKED and the command exits non-zero.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .capability import capability_report, require_strict_capabilities


@dataclass(frozen=True)
class Gate:
    """One release gate: a label, the argv to run, and whether it is required."""

    label: str
    argv: tuple[str, ...]
    required: bool = True


def _repo_gates() -> tuple[Gate, ...]:
    py = sys.executable
    return (
        Gate("operational-kernel-selftest", (py, "-m", "bsff.cli", "selftest")),
        Gate("architecture-contract", (py, "tools/validate_architecture_contract.py")),
        Gate("truth-contract", (py, "tools/validate_truth_contract.py")),
        Gate("open-source-readiness", (py, "tools/validate_open_source_readiness.py")),
        Gate("ip-provenance", (py, "tools/validate_ip_provenance.py")),
        Gate("markdown", (py, "tools/validate_markdown.py")),
        Gate("github-actions-policy", (py, "tools/check_github_actions_policy.py")),
        Gate("secret-scan", (py, "tools/scan_secrets.py")),
        Gate("provenance-manifest", (py, "tools/generate_provenance_manifest.py")),
        Gate("tisean-reference", (py, "tools/validate_tisean_reference.py")),
        Gate("real-eeg-case", (py, "tools/validate_real_eeg_case.py")),
        Gate("status-sync", (py, "tools/update_status.py", "--check")),
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run_gate(gate: Gate, repo_root: Path) -> dict[str, object]:
    try:
        # argv is a fixed, repo-internal command list; no shell, no user input.
        proc = subprocess.run(
            gate.argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=600,
        )
        passed = proc.returncode == 0
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
        return {
            "label": gate.label,
            "required": gate.required,
            "returncode": proc.returncode,
            "passed": passed,
            "summary": tail[0][:200],
        }
    except Exception as exc:  # pragma: no cover - environment failure path
        return {
            "label": gate.label,
            "required": gate.required,
            "returncode": None,
            "passed": False,
            "summary": f"gate execution failed: {exc}"[:200],
        }


# Artifacts the bundle pins by hash when present. Absence of an optional artifact
# is recorded, not fatal.
_PINNED_ARTIFACTS: tuple[str, ...] = (
    "artifacts/bsff_phase1_validation.json",
    "artifacts/provenance_manifest.json",
    "artifacts/tisean_validation.json",
    "artifacts/real_eeg_case/verdict.json",
    "artifacts/real_eeg_case/manifest.json",
    "STATUS.md",
)


def run_release_check(
    output_dir: str | Path = "artifacts/release",
    *,
    strict: bool = False,
    repo_root: str | Path | None = None,
) -> dict[str, object]:
    """Run the gate battery, collect + hash evidence, write the release bundle.

    Returns the manifest dict. ``release_verdict`` is ``RELEASE_READY`` only when
    every required gate passed (and, under ``strict``, the strict evidence path
    is installed).
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if strict:
        require_strict_capabilities()

    gate_results = [_run_gate(g, root) for g in _repo_gates()]
    required_failed = [g for g in gate_results if g["required"] and not g["passed"]]

    pinned: list[dict[str, object]] = []
    for rel in _PINNED_ARTIFACTS:
        path = root / rel
        if path.exists() and path.is_file():
            pinned.append({"path": rel, "present": True, "sha256": _sha256_file(path)})
        else:
            pinned.append({"path": rel, "present": False, "sha256": None})

    caps = capability_report()
    verdict = "RELEASE_READY" if not required_failed else "RELEASE_BLOCKED"

    manifest: dict[str, object] = {
        "schema": "bsff.release/v1",
        "tool": "bsff",
        "tool_version": __version__,
        "command": "bsff release-check" + (" --strict" if strict else ""),
        "strict": strict,
        "python_version": caps["python_version"],
        "platform": caps["platform"],
        "capabilities": caps,
        "gates": gate_results,
        "artifacts": pinned,
        "required_gate_failures": [g["label"] for g in required_failed],
        "release_verdict": verdict,
    }
    manifest_path = out / "MANIFEST.json"
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    manifest_path.write_text(serialized, encoding="utf-8")
    # Self-pin: a digest of the manifest itself, written alongside (not inside).
    (out / "MANIFEST.sha256").write_text(
        hashlib.sha256(serialized.encode("utf-8")).hexdigest() + "\n", encoding="utf-8"
    )
    _write_verdict_md(out / "VERDICT.md", manifest)
    return manifest


def _write_verdict_md(path: Path, manifest: dict[str, object]) -> None:
    gates = manifest["gates"]
    assert isinstance(gates, list)
    lines = [
        "# BSFF Release Evidence Bundle",
        "",
        f"- Tool version: `{manifest['tool_version']}`",
        f"- Command: `{manifest['command']}`",
        f"- Python: `{manifest['python_version']}`",
        f"- Strict evidence path: `{manifest['strict']}`",
        f"- **Release verdict: {manifest['release_verdict']}**",
        "",
        "## Gates",
        "",
        "| Gate | Required | Result |",
        "| --- | --- | --- |",
    ]
    for g in gates:
        assert isinstance(g, dict)
        result = "PASS" if g["passed"] else "FAIL"
        lines.append(f"| {g['label']} | {g['required']} | {result} |")
    lines += [
        "",
        "## Pinned artifacts",
        "",
        "| Artifact | Present | sha256 |",
        "| --- | --- | --- |",
    ]
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    for a in artifacts:
        assert isinstance(a, dict)
        digest = str(a["sha256"])[:16] + "…" if a["sha256"] else "—"
        lines.append(f"| `{a['path']}` | {a['present']} | `{digest}` |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
