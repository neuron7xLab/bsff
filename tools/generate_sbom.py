#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate / verify a dual-format SBOM (SPDX 2.3 + CycloneDX 1.5) for BSFF.

Supply-chain trust needs a machine-readable inventory of exactly what code runs,
not a hand-waved "we use numpy". This tool resolves BSFF's *runtime* dependency
closure from installed distribution metadata (extras excluded), and emits two
deterministic SBOMs — components sorted, no wall-clock timestamp and no random
serial/namespace — so the documents are hash-stable and diffable.

    python tools/generate_sbom.py                       # artifacts/sbom/{spdx,cyclonedx,sha256}
    python tools/generate_sbom.py --output sbom.cdx.json # legacy single CycloneDX file
    python tools/generate_sbom.py --check               # structural gate, exit 1 on a gap

``--check`` regenerates both SBOMs in memory and asserts the supply-chain invariants
that MUST hold regardless of exact pinned versions (so a routine dependency bump
does not turn it red): valid SPDX + CycloneDX envelopes, BSFF as the root, every
component carrying name+version+purl, and the runtime essentials (numpy, scipy,
statsmodels) present in the closure. It is fail-closed — any missing field aborts.

Standard library + ``packaging`` only (already a transitive runtime dependency).
No network.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as im
import json
import re
from collections import deque
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
ROOT_PACKAGE = "bsff"
RUNTIME_ESSENTIALS = ("numpy", "scipy", "statsmodels")


def _runtime_requirements(dist_name: str) -> list[Requirement]:
    """Parsed Requires-Dist for a distribution, excluding extra-gated (optional) ones."""
    try:
        raw = im.distribution(dist_name).requires or []
    except im.PackageNotFoundError:
        return []
    reqs: list[Requirement] = []
    for line in raw:
        try:
            req = Requirement(line)
        except Exception:
            continue
        marker = str(req.marker) if req.marker else ""
        # Skip optional dependencies (anything gated behind an extra); keep core
        # runtime deps and platform/python markers that evaluate true here.
        if "extra ==" in marker:
            continue
        if req.marker is not None and not req.marker.evaluate():
            continue
        reqs.append(req)
    return reqs


def _license_id(dist_name: str) -> str | None:
    """Best-effort SPDX-ish license string from distribution metadata."""
    try:
        meta = im.metadata(dist_name)
    except im.PackageNotFoundError:
        return None
    expr = meta.get("License-Expression")
    if expr:
        return str(expr)
    classifiers = meta.get_all("Classifier") or []
    for c in classifiers:
        if c.startswith("License :: OSI Approved ::"):
            return c.split("::")[-1].strip()
    lic = meta.get("License")
    if lic and "\n" not in lic and len(lic) < 64:
        return str(lic)
    return None


def _resolve_closure(root: str) -> list[str]:
    """BFS over the runtime dependency closure; return canonical names (sorted)."""
    seen: set[str] = set()
    queue: deque[str] = deque([canonicalize_name(root)])
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        for req in _runtime_requirements(name):
            child = canonicalize_name(req.name)
            if child not in seen:
                queue.append(child)
    seen.discard(canonicalize_name(root))
    return sorted(seen)


def _component(name: str, *, comp_type: str) -> dict:
    version = im.version(name)
    comp: dict[str, object] = {
        "type": comp_type,
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
    }
    license_id = _license_id(name)
    if license_id:
        comp["licenses"] = [{"license": {"id": license_id}}]
    return comp


def generate_cyclonedx() -> dict:
    root_version = im.version(ROOT_PACKAGE)
    components = [_component(name, comp_type="library") for name in _resolve_closure(ROOT_PACKAGE)]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": ROOT_PACKAGE,
                "version": root_version,
                "purl": f"pkg:pypi/{ROOT_PACKAGE}@{root_version}",
                "licenses": [{"license": {"id": "GPL-3.0-or-later"}}],
            },
            "tools": [{"name": "generate_sbom.py", "vendor": "neuron7xLab"}],
        },
        "components": components,
    }


def _spdx_id(name: str) -> str:
    """SPDX identifiers allow only letters, digits, '.', and '-'."""
    return "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", name)


def generate_spdx() -> dict:
    """Deterministic SPDX 2.3 JSON SBOM of the same runtime closure.

    A fixed creation timestamp and a version-derived namespace keep the document
    hash-stable; uniqueness is traded for reproducibility on purpose.
    """
    root_version = im.version(ROOT_PACKAGE)
    closure = _resolve_closure(ROOT_PACKAGE)
    root_spdx_id = _spdx_id(ROOT_PACKAGE)

    packages = [
        {
            "SPDXID": root_spdx_id,
            "name": ROOT_PACKAGE,
            "versionInfo": root_version,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "GPL-3.0-or-later",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/{ROOT_PACKAGE}@{root_version}",
                }
            ],
        }
    ]
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": root_spdx_id,
        }
    ]
    for name in closure:
        version = im.version(name)
        pkg_id = _spdx_id(name)
        license_id = _license_id(name) or "NOASSERTION"
        packages.append(
            {
                "SPDXID": pkg_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": license_id,
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{name}@{version}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": root_spdx_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": pkg_id,
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{ROOT_PACKAGE}-{root_version}",
        "documentNamespace": f"https://github.com/neuron7xLab/bsff/spdx/{ROOT_PACKAGE}-{root_version}",
        "creationInfo": {
            "created": "1970-01-01T00:00:00Z",
            "creators": ["Tool: tools/generate_sbom.py", "Organization: neuron7xLab"],
        },
        "packages": packages,
        "relationships": relationships,
    }


def _validate_cyclonedx(sbom: dict) -> list[str]:
    failures: list[str] = []
    if sbom.get("bomFormat") != "CycloneDX":
        failures.append("cyclonedx: bomFormat is not CycloneDX")
    if not sbom.get("specVersion"):
        failures.append("cyclonedx: specVersion is missing")
    root = sbom.get("metadata", {}).get("component", {})
    if root.get("name") != ROOT_PACKAGE or not root.get("purl"):
        failures.append("cyclonedx: root component is not a purl-bearing bsff")
    names = {c.get("name") for c in sbom.get("components", [])}
    for field in ("name", "version", "purl"):
        if any(not c.get(field) for c in sbom.get("components", [])):
            failures.append(f"cyclonedx: a component is missing required field: {field}")
    for essential in RUNTIME_ESSENTIALS:
        if canonicalize_name(essential) not in {canonicalize_name(n) for n in names if n}:
            failures.append(f"cyclonedx: runtime essential absent from closure: {essential}")
    return failures


def _validate_spdx(sbom: dict) -> list[str]:
    failures: list[str] = []
    if sbom.get("spdxVersion") != "SPDX-2.3":
        failures.append("spdx: spdxVersion is not SPDX-2.3")
    if sbom.get("SPDXID") != "SPDXRef-DOCUMENT":
        failures.append("spdx: document SPDXID missing")
    pkgs = sbom.get("packages", [])
    names = {p.get("name") for p in pkgs}
    if ROOT_PACKAGE not in names:
        failures.append("spdx: root package bsff missing")
    for field in ("SPDXID", "name", "versionInfo", "externalRefs"):
        if any(not p.get(field) for p in pkgs):
            failures.append(f"spdx: a package is missing required field: {field}")
    for essential in RUNTIME_ESSENTIALS:
        if canonicalize_name(essential) not in {canonicalize_name(n) for n in names if n}:
            failures.append(f"spdx: runtime essential absent from closure: {essential}")
    return failures


def _dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate / verify the BSFF SBOM (SPDX + CycloneDX)."
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "artifacts" / "sbom",
        help="dual-format output directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="legacy single-file CycloneDX output path (back-compat)",
    )
    parser.add_argument(
        "--check", action="store_true", help="Validate both formats; exit 1 on a gap."
    )
    args = parser.parse_args(argv)

    cdx = generate_cyclonedx()
    spdx = generate_spdx()
    failures = _validate_cyclonedx(cdx) + _validate_spdx(spdx)
    if failures:
        print("SBOM validation FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1
    n = len(cdx["components"])

    if args.check:
        print(f"SBOM: PASS (SPDX + CycloneDX, {n} runtime components, root {ROOT_PACKAGE})")
        return 0

    if args.output is not None:
        # Back-compat: write only the CycloneDX document to the given path.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(_dump(cdx), encoding="utf-8")
        print(f"Wrote {args.output} ({n} runtime components, CycloneDX)")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    cdx_path = args.outdir / "bsff.cyclonedx.json"
    spdx_path = args.outdir / "bsff.spdx.json"
    cdx_path.write_text(_dump(cdx), encoding="utf-8")
    spdx_path.write_text(_dump(spdx), encoding="utf-8")
    # Deterministic sha256 manifest binding both documents.
    lines = []
    for path in (cdx_path, spdx_path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    (args.outdir / "bsff.sbom.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.outdir}/ (SPDX + CycloneDX + sha256, {n} runtime components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
