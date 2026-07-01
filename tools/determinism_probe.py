#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Byte-determinism probe for BSFF's committed, deterministic generators.

Several committed artifacts are supposed to be *byte-reproducible*: regenerating
them from the same source tree must yield identical bytes. Hidden nondeterminism
(wall-clock timestamps, unordered ``dict``/``set`` iteration, an RNG used without
a fixed seed) silently breaks that guarantee and turns every "check" gate into a
coin flip. This probe catches it directly.

For each registered generator the probe:

  1. snapshots the *current committed bytes* of every output file it owns,
  2. records the pre-run state of the working tree (via ``git status`` in a git
     work tree, or a bounded directory scan otherwise),
  3. runs the generator (writing in place) **twice**,
  4. compares the two regenerated payloads byte-for-byte (the determinism gate)
     and, for transparency, records whether the regeneration matched the
     committed bytes,
  5. **checks hermeticity**: any path the generator changed that is NOT one of
     its declared ``outputs`` is a *side effect* — the generator is not hermetic,
     it may embed undetected nondeterminism in an untracked location, and it has
     dirtied the tree. Such generators are flagged ``impure`` (a FAIL), and the
     stray write is restored,
  6. **restores the original committed bytes** — always, even on error — so the
     working tree is left exactly as it was found.

Scope (be honest about it). This probe does NOT prove whole-tree byte
reproducibility: it guards the **registered set** below, nothing more. The
repository contains ~100 committed artifacts; only the generators listed in
``REGISTRY`` — each independently verified to be deterministic, single-purpose,
and free of embedded wall-clock/commit data — are covered. Registration IS the
ratchet: when a new committed, deterministic generator lands, it must be added
here or it is simply unguarded. Only SOURCE-PURE generators qualify — output is a pure function of the committed
source tree. ENVIRONMENT-DEPENDENT producers are deliberately EXCLUDED and have
their own same-environment ``--check`` gate instead: the SBOM (installed
dependency closure, gated by ``generate_sbom.py --check`` in the build job) and
fixed-seed numeric nulls (float results can shift across numpy/scipy versions).
Timestamp/commit-embedding producers (provenance manifests, current-truth) are
also out of scope and must NOT be registered.
Environment isolation is the hard invariant: a registered generator's output
must be a pure function of the COMMITTED SOURCE BYTES, independent of any
installed library version. Anything touching numpy/scipy floats, the dependency
closure (SBOM), or the analysis pipeline is env-dependent -- its committed bytes
would drift under a different lock (e.g. the hermetic offline env) and is
EXCLUDED. Only stdlib hash / schema / count generators qualify.

    python tools/determinism_probe.py            # print JSON report
    python tools/determinism_probe.py --check     # exit 1 if any generator is nondeterministic

The probe never mutates the working tree on success or failure (declared outputs
AND any stray side-effect writes are restored, always).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Directories whose contents are never a "side effect": build/cache detritus that
# a plain ``import`` legitimately produces (git already ignores these).
_SCAN_IGNORE = frozenset(
    {".git", "__pycache__", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
)

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = "bsff.determinism/v1"

# Per-generator subprocess timeout (seconds). Generous; these are pure,
# offline, CPU-only producers.
_TIMEOUT = 600


@dataclass(frozen=True)
class Generator:
    """A deterministic generator and the committed artifact(s) it writes."""

    name: str
    # argv appended after the Python interpreter, resolved relative to root.
    argv: tuple[str, ...]
    # Repo-relative output files the generator writes *in place*.
    outputs: tuple[str, ...] = field(default_factory=tuple)


# Registry of generators known (and required) to be byte-deterministic. Each
# writes a committed artifact in place with no embedded wall-clock/commit data.
REGISTRY: tuple[Generator, ...] = (
    Generator(
        name="generate_manifest",
        argv=("tools/generate_manifest.py",),
        outputs=("artifacts/MANIFEST.json",),
    ),
    Generator(
        name="statistical_proof_gate",
        argv=("tools/validate_statistical_proof_gate.py",),
        outputs=("artifacts/release/STATISTICAL_PROOF_GATE_REPORT.json",),
    ),
    Generator(
        name="export_schemas",
        argv=("tools/export_schemas.py",),
        outputs=(
            "artifacts/schemas/claim_spec.schema.json",
            "artifacts/schemas/verdict.schema.json",
        ),
    ),
    # Scorecard computed as a pure function over committed evidence JSON; no
    # wall-clock/commit data. ``--check`` in CI already asserts committed==computed.
    Generator(
        name="compute_scorecard",
        argv=("tools/compute_scorecard.py",),
        outputs=("artifacts/actions_99_scorecard.json",),
    ),
)


def _read_snapshot(root: Path, outputs: tuple[str, ...]) -> dict[str, bytes]:
    """Capture the current bytes of every output. Missing files raise."""
    snap: dict[str, bytes] = {}
    for rel in outputs:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(f"expected committed artifact is missing: {rel}")
        snap[rel] = path.read_bytes()
    return snap


def _restore(root: Path, snapshot: dict[str, bytes]) -> None:
    """Write the snapshotted bytes back, byte-for-byte."""
    for rel, data in snapshot.items():
        (root / rel).write_bytes(data)


def _run(root: Path, argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *argv],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def _capture_outputs(root: Path, outputs: tuple[str, ...]) -> dict[str, bytes]:
    return {rel: (root / rel).read_bytes() for rel in outputs}


def _is_git_worktree(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_dirty_set(root: Path) -> set[str]:
    """Repo-relative paths git reports as changed (modified / added / untracked).

    Git already excludes ignored paths (``__pycache__`` and friends), which is
    exactly right: importing a module writes ``.pyc`` files but that is not a
    tree mutation we should attribute to the generator.
    """
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {(result.stderr or result.stdout).strip()[:200]}")
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        entry = line[3:]
        # Renames/copies render as "R  old -> new"; the post-change path is ours.
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.add(entry.strip())
    return paths


def _dir_bytes(root: Path) -> dict[str, bytes]:
    """Bounded content snapshot of ``root`` for non-git trees (e.g. tmp dirs)."""
    out: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if any(part in _SCAN_IGNORE for part in path.parts):
            continue
        if path.is_file():
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def _detect_side_effects(
    root: Path,
    outputs: tuple[str, ...],
    git_baseline: set[str] | None,
    dir_baseline: dict[str, bytes] | None,
) -> list[str]:
    """Paths changed by the generator that are NOT among its declared outputs.

    Only files that were *clean before the generator ran* can surface here: git's
    pre-run dirty set is subtracted (so a concurrently-edited file is not
    misattributed), and the directory snapshot is taken immediately before the
    run. That keeps restoration from clobbering unrelated work.
    """
    outset = set(outputs)
    if git_baseline is not None:
        current = _git_dirty_set(root)
        return sorted(p for p in (current - git_baseline) if p not in outset)
    assert dir_baseline is not None
    current_files = _dir_bytes(root)
    changed: set[str] = {
        rel for rel, data in current_files.items() if dir_baseline.get(rel) != data
    }
    changed |= {rel for rel in dir_baseline if rel not in current_files}
    return sorted(p for p in changed if p not in outset)


def _restore_side_effects(
    root: Path,
    paths: list[str],
    dir_baseline: dict[str, bytes] | None,
) -> None:
    """Undo stray writes: restore captured/committed bytes, or remove new files."""
    for rel in paths:
        target = root / rel
        if dir_baseline is not None:
            if rel in dir_baseline:
                target.write_bytes(dir_baseline[rel])
            else:
                target.unlink(missing_ok=True)
            continue
        # git work tree: tracked -> restore committed bytes; untracked -> remove.
        tracked = (
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", rel],
                cwd=root,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )
        if tracked:
            subprocess.run(
                ["git", "checkout", "--", rel],
                cwd=root,
                capture_output=True,
                text=True,
            )
        else:
            target.unlink(missing_ok=True)


def _probe_one(root: Path, gen: Generator) -> dict[str, object]:
    """Probe a single generator; the working tree is restored before return."""
    committed = _read_snapshot(root, gen.outputs)
    use_git = _is_git_worktree(root)
    git_baseline: set[str] | None = _git_dirty_set(root) if use_git else None
    dir_baseline: dict[str, bytes] | None = None if use_git else _dir_bytes(root)
    entry: dict[str, object] = {
        "name": gen.name,
        "command": "python " + " ".join(gen.argv),
        "outputs": list(gen.outputs),
        "deterministic": False,
        "committed_match": False,
        "side_effects": [],
    }
    run1: dict[str, bytes] | None = None
    run2: dict[str, bytes] | None = None
    side_effects: list[str] = []
    try:
        first = _run(root, gen.argv)
        if first.returncode != 0:
            entry["reason"] = (
                f"generator exited {first.returncode}: "
                f"{(first.stderr or first.stdout).strip()[:400]}"
            )
            return entry
        run1 = _capture_outputs(root, gen.outputs)

        second = _run(root, gen.argv)
        if second.returncode != 0:
            entry["reason"] = (
                f"generator exited {second.returncode} on second run: "
                f"{(second.stderr or second.stdout).strip()[:400]}"
            )
            return entry
        run2 = _capture_outputs(root, gen.outputs)
    finally:
        # Fail-closed on tree hygiene: detect stray writes, then restore committed
        # outputs AND any side effects, no matter what (error, timeout, success).
        side_effects = _detect_side_effects(root, gen.outputs, git_baseline, dir_baseline)
        _restore(root, committed)
        _restore_side_effects(root, side_effects, dir_baseline)
        entry["side_effects"] = side_effects
        if side_effects and "reason" not in entry:
            entry["reason"] = "wrote outside declared outputs (not hermetic): " + ", ".join(
                side_effects
            )

    deterministic = run1 == run2
    committed_match = run1 == committed
    entry["deterministic"] = deterministic
    entry["committed_match"] = committed_match
    if not deterministic and run1 is not None and run2 is not None:
        differing = sorted(k for k in run1 if run1.get(k) != run2.get(k))
        det_reason = f"run-twice bytes differ for: {', '.join(differing)}"
        prior = entry.get("reason")
        entry["reason"] = f"{det_reason}; {prior}" if prior else det_reason
    return entry


def evaluate(
    root: Path = ROOT,
    registry: tuple[Generator, ...] = REGISTRY,
) -> dict[str, object]:
    """Run every registered generator twice and report byte-determinism.

    Three failure modes, all fail-closed, because artifact-bound verification needs
    them: (1) *nondeterministic* — two consecutive regenerations differ, or the
    generator fails to run; (2) *stale* — the committed bytes do not match a fresh
    regeneration, so the repository ships an artifact that no longer reflects its
    source (a deterministic-but-drifted artifact is still a broken proof);
    (3) *impure* — the generator wrote outside its declared outputs, so it is not
    hermetic (an undeclared write can hide nondeterminism the byte-check never
    sees, and it dirties the tree). The working tree is always restored.
    """
    checked: list[dict[str, object]] = []
    nondeterministic: list[str] = []
    stale: list[str] = []
    impure: list[str] = []
    for gen in registry:
        entry = _probe_one(root, gen)
        checked.append(entry)
        if not entry["deterministic"]:
            nondeterministic.append(str(entry["name"]))
        elif not entry["committed_match"]:
            stale.append(str(entry["name"]))
        if entry["side_effects"]:
            impure.append(str(entry["name"]))
    status = "PASS" if not nondeterministic and not stale and not impure else "FAIL"
    return {
        "schema": SCHEMA,
        "checked": checked,
        "nondeterministic": nondeterministic,
        "stale": stale,
        "impure": impure,
        "status": status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any registered generator is nondeterministic.",
    )
    args = parser.parse_args(argv)

    report = evaluate(ROOT)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.check and report["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
