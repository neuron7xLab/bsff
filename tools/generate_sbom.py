#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Generate / verify a CycloneDX SBOM for the BSFF runtime closure.

Supply-chain trust needs a machine-readable inventory of exactly what code runs,
not a hand-waved "we use numpy". This tool resolves BSFF's *runtime* dependency
closure from installed distribution metadata (extras excluded), and emits a
deterministic CycloneDX 1.5 SBOM: components sorted, no wall-clock timestamp and
no random serial number, so the document is hash-stable and diffable.

    python tools/generate_sbom.py --output artifacts/sbom.cdx.json
    python tools/generate_sbom.py --check    # structural gate, exit 1 on a gap

``--check`` regenerates the SBOM in memory and asserts the supply-chain invariants
that MUST hold regardless of exact pinned versions (so a routine dependency bump
does not turn it red): valid CycloneDX envelope, BSFF as the root component, every
component carrying name+version+purl, and the runtime essentials (numpy, scipy,
statsmodels) present in the closure. It is fail-closed — any missing field aborts.

Standard library + ``packaging`` only (already a transitive runtime dependency).
No network.
"""

from __future__ import annotations

import argparse
import importlib.metadata as im
import json
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


def generate() -> dict:
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


def _validate(sbom: dict) -> list[str]:
    failures: list[str] = []
    if sbom.get("bomFormat") != "CycloneDX":
        failures.append("bomFormat is not CycloneDX")
    if not sbom.get("specVersion"):
        failures.append("specVersion is missing")
    root = sbom.get("metadata", {}).get("component", {})
    if root.get("name") != ROOT_PACKAGE or not root.get("purl"):
        failures.append("root component is not a purl-bearing bsff")
    names = {c.get("name") for c in sbom.get("components", [])}
    for field in ("name", "version", "purl"):
        if any(not c.get(field) for c in sbom.get("components", [])):
            failures.append(f"a component is missing required field: {field}")
    for essential in RUNTIME_ESSENTIALS:
        if canonicalize_name(essential) not in {canonicalize_name(n) for n in names if n}:
            failures.append(f"runtime essential absent from SBOM closure: {essential}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate / verify the BSFF CycloneDX SBOM.")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "sbom.cdx.json")
    parser.add_argument("--check", action="store_true", help="Validate structure; exit 1 on a gap.")
    args = parser.parse_args(argv)

    sbom = generate()
    failures = _validate(sbom)
    if failures:
        print("SBOM validation FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    if args.check:
        print(f"SBOM: PASS ({len(sbom['components'])} runtime components, root {ROOT_PACKAGE})")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        display = args.output.resolve().relative_to(ROOT)
    except ValueError:
        display = args.output
    print(f"Wrote {display} ({len(sbom['components'])} runtime components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
