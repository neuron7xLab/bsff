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
  2. runs the generator (writing in place) **twice**,
  3. compares the two regenerated payloads byte-for-byte (the determinism gate)
     and, for transparency, records whether the regeneration matched the
     committed bytes,
  4. **restores the original committed bytes** — always, even on error — so the
     working tree is left exactly as it was found.

Only generators that write a *committed, deterministic* artifact and do NOT
embed timestamps or git commit hashes are registered here; known-nondeterministic
producers (provenance manifests, current-truth snapshots) are deliberately out of
scope.

    python tools/determinism_probe.py            # print JSON report
    python tools/determinism_probe.py --check     # exit 1 if any generator is nondeterministic

The probe never mutates the working tree on success or failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

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
    Generator(
        name="generate_sbom",
        argv=("tools/generate_sbom.py",),
        outputs=(
            "artifacts/sbom/bsff.cyclonedx.json",
            "artifacts/sbom/bsff.spdx.json",
            "artifacts/sbom/bsff.sbom.sha256",
        ),
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


def _probe_one(root: Path, gen: Generator) -> dict[str, object]:
    """Probe a single generator; the working tree is restored before return."""
    committed = _read_snapshot(root, gen.outputs)
    entry: dict[str, object] = {
        "name": gen.name,
        "command": "python " + " ".join(gen.argv),
        "outputs": list(gen.outputs),
        "deterministic": False,
        "committed_match": False,
    }
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
        # Fail-closed on tree hygiene: restore committed bytes no matter what.
        _restore(root, committed)

    deterministic = run1 == run2
    committed_match = run1 == committed
    entry["deterministic"] = deterministic
    entry["committed_match"] = committed_match
    if not deterministic:
        differing = sorted(k for k in run1 if run1.get(k) != run2.get(k))
        entry["reason"] = f"run-twice bytes differ for: {', '.join(differing)}"
    return entry


def evaluate(
    root: Path = ROOT,
    registry: tuple[Generator, ...] = REGISTRY,
) -> dict[str, object]:
    """Run every registered generator twice and report byte-determinism.

    The gate is *run-twice byte identity*: a generator is nondeterministic if two
    consecutive regenerations produce different bytes, or if it fails to run. The
    committed-bytes match is recorded per generator for transparency but does not
    by itself drive the status (a stale-but-deterministic artifact is a drift
    problem, not a nondeterminism problem). The working tree is always restored.
    """
    checked: list[dict[str, object]] = []
    nondeterministic: list[str] = []
    for gen in registry:
        entry = _probe_one(root, gen)
        checked.append(entry)
        if not entry["deterministic"]:
            nondeterministic.append(str(entry["name"]))
    status = "PASS" if not nondeterministic else "FAIL"
    return {
        "schema": SCHEMA,
        "checked": checked,
        "nondeterministic": nondeterministic,
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
