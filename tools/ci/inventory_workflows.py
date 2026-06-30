#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tools.ci.common import ROOT, write_json

WORKFLOW_DIR = ROOT / ".github" / "workflows"


def workflow_name(text: str, path: Path) -> str:
    m = re.search(r"^name:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip('"\'') if m else path.stem


def job_blocks(text: str) -> dict[str, str]:
    marker = re.search(r"^jobs:\s*$", text, re.M)
    if not marker:
        return {}
    tail = text[marker.end() :]
    matches = list(re.finditer(r"^  ([A-Za-z0-9_-]+):\s*$", tail, re.M))
    blocks: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tail)
        blocks[match.group(1)] = tail[start:end]
    return blocks


def inspect_workflow(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    jobs = []
    for job_id, block in sorted(job_blocks(text).items()):
        lower = block.lower()
        uses_python = "setup-python" in lower or "python " in lower or "python -m" in lower
        uses_uv = "uv " in lower
        uses_pip = " pip " in f" {lower} " or "pip install" in lower or "python -m pip" in lower
        has_sbom = "sbom" in lower or "provenance" in lower
        jobs.append(
            {
                "job_id": job_id,
                "uses_python": uses_python,
                "uses_uv": uses_uv,
                "uses_pip": uses_pip,
                "uses_cache": "cache:" in lower or "actions/cache" in lower,
                "has_step_telemetry": "tools/ci/measure_step.py" in block,
                "has_cache_telemetry": "tools/ci/emit_cache_telemetry.py" in block,
                "has_sbom_or_provenance": has_sbom,
                "uses_sigstore": "sigstore" in lower,
                "uses_attestation": "attest" in lower,
                "skip_policy_declared": "ci_provenance_skip" in lower or "classify_provenance_depth" in lower,
            }
        )
    return {"path": str(path.relative_to(ROOT)), "name": workflow_name(text, path), "jobs": jobs}


def build_inventory() -> dict[str, object]:
    workflows = [inspect_workflow(p) for p in sorted(WORKFLOW_DIR.glob("*.y*ml"))]
    errors: list[str] = []
    for wf in workflows:
        for job in wf["jobs"]:  # type: ignore[index]
            if job["uses_python"] and not job["has_step_telemetry"]:  # type: ignore[index]
                errors.append(f"{wf['path']}:{job['job_id']} missing step telemetry")
            if (job["uses_pip"] or job["uses_uv"]) and not job["has_cache_telemetry"]:  # type: ignore[index]
                errors.append(f"{wf['path']}:{job['job_id']} missing cache telemetry")
            if job["uses_attestation"] and not job["skip_policy_declared"]:  # type: ignore[index]
                errors.append(f"{wf['path']}:{job['job_id']} missing provenance skip policy")
    return {"schema_version": 1, "workflows": workflows, "errors": errors, "verdict": "PASS" if not errors else "FAIL"}


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "ci" / "workflow_inventory.json"))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    doc = build_inventory()
    write_json(Path(args.output), doc)
    if args.check and doc["verdict"] != "PASS":
        for err in doc["errors"]:
            print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
