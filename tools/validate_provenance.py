#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Verify the SBOM / provenance binding is sound and signing is configured.

Signed provenance is only trustworthy if (a) the SBOM is structurally valid, (b)
the recorded subject hashes actually match the bytes they claim, and (c) the build
workflow is configured to emit a keyless Sigstore attestation. This gate proves all
three without needing the live signature (which is minted on push/release), so the
binding is verifiable on every pull request.

    python tools/validate_provenance.py

Fail-closed: any structural gap, hash mismatch, or missing signing configuration
exits non-zero. Standard library + ``packaging`` (via generate_sbom). No network.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SBOM_DIR = ROOT / "artifacts" / "sbom"
SUBJECTS = ROOT / "artifacts" / "provenance" / "subjects.sha256"
WORKFLOW = ROOT / ".github" / "workflows" / "provenance-sbom.yml"


def _load_sbom_tool():
    path = ROOT / "tools" / "generate_sbom.py"
    spec = importlib.util.spec_from_file_location("generate_sbom", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _check_sha256_manifest(manifest: Path, base: Path) -> list[str]:
    """Verify each `<digest>  <name>` line matches the bytes of base/<name>."""
    failures: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        target = base / name.strip()
        if not target.is_file():
            failures.append(f"{manifest.name}: subject not found: {name.strip()}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest.strip():
            failures.append(f"{manifest.name}: hash mismatch for {name.strip()}")
    return failures


def main() -> int:
    failures: list[str] = []

    # 1. SBOM structure (both formats) must validate.
    sbom = _load_sbom_tool()
    cdx = sbom.generate_cyclonedx()
    spdx = sbom.generate_spdx()
    failures.extend(sbom._validate_cyclonedx(cdx))
    failures.extend(sbom._validate_spdx(spdx))

    # 2. If the dual-format SBOM has been materialised, its sha256 manifest must
    #    match the bytes on disk (binding integrity).
    sbom_manifest = SBOM_DIR / "bsff.sbom.sha256"
    if sbom_manifest.is_file():
        failures.extend(_check_sha256_manifest(sbom_manifest, SBOM_DIR))
    if SUBJECTS.is_file():
        # subjects.sha256 mixes dist/ and sbom/ entries; verify the sbom ones.
        for line in SUBJECTS.read_text(encoding="utf-8").splitlines():
            digest, _, name = line.strip().partition("  ")
            candidate = SBOM_DIR / Path(name.strip()).name
            if candidate.is_file():
                if hashlib.sha256(candidate.read_bytes()).hexdigest() != digest.strip():
                    failures.append(f"subjects.sha256: hash mismatch for {name.strip()}")

    # 3. The provenance workflow must be configured to sign keyless.
    if not WORKFLOW.is_file():
        failures.append("provenance-sbom.yml workflow is missing")
    else:
        text = WORKFLOW.read_text(encoding="utf-8")
        for needed in ("id-token: write", "attestations: write", "attest-build-provenance@"):
            if needed not in text:
                failures.append(f"provenance-sbom.yml missing signing config: {needed!r}")

    if failures:
        print("Provenance/SBOM binding FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1
    print(
        f"Provenance/SBOM binding: PASS ({len(cdx['components'])} components, signing configured)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
