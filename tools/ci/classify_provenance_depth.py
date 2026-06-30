#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.ci.common import ROOT, write_json


def classify(workflow_dir: Path = ROOT / ".github" / "workflows") -> dict[str, object]:
    text = "\n".join(p.read_text(encoding="utf-8") for p in sorted(workflow_dir.glob("*.y*ml")))
    lower = text.lower()
    sbom = "sbom" in lower
    provenance = "provenance" in lower
    sigstore = "sigstore" in lower
    attestation = "attest-build-provenance" in lower or "attestations:" in lower
    pr_skip = "github.event_name != 'pull_request'" in text or 'github.event_name != "pull_request"' in text
    classes: list[str] = []
    if sbom and provenance and sigstore and attestation and not pr_skip:
        classes.append("FULL_PROVENANCE")
    elif sbom and not provenance:
        classes.append("SBOM_ONLY")
    elif provenance and not sigstore:
        classes.append("PROVENANCE_WITHOUT_SIGSTORE")
    if sigstore and pr_skip:
        classes.append("SIGSTORE_SKIPPED_POLICY_GAP")
    if attestation and pr_skip:
        classes.append("ATTESTATION_SKIPPED_POLICY_GAP")
    if not classes:
        classes.append("UNKNOWN_UNACCEPTABLE")
    skipped = pr_skip
    skip_classification = "POLICY_GAP" if skipped else "INTENTIONAL_NOT_REQUIRED"
    verdict = "FAIL" if classes == ["UNKNOWN_UNACCEPTABLE"] else "PASS_WITH_POLICY_GAPS" if skipped else "PASS"
    return {
        "schema_version": 1,
        "sbom_present": sbom,
        "provenance_present": provenance,
        "sigstore_present": sigstore,
        "sigstore_skipped": bool(sigstore and skipped),
        "attestation_present": attestation,
        "attestation_skipped": bool(attestation and skipped),
        "classes": classes,
        "skip_classification": skip_classification,
        "verdict": verdict,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "ci" / "provenance_depth.json"))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    doc = classify()
    write_json(Path(args.output), doc)
    return 1 if args.strict and doc["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(run())
