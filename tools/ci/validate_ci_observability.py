#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import argparse
import sys

import jsonschema
from tools.ci.common import ROOT, read_json

SCHEMA_MAP = {
    "schemas/ci_step_telemetry.schema.json": "artifacts/ci/steps/**/*.json",
    "schemas/ci_cache_telemetry.schema.json": "artifacts/ci/cache/**/*.json",
    "schemas/ci_workflow_inventory.schema.json": "artifacts/ci/workflow_inventory.json",
    "schemas/ci_observability_summary.schema.json": "artifacts/ci/ci_observability_summary.json",
    "schemas/provenance_depth.schema.json": "artifacts/ci/provenance_depth.json",
}


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(sys.argv[1:] if argv is None else argv)
    errors: list[str] = []
    for schema_rel, pattern in SCHEMA_MAP.items():
        schema = read_json(ROOT / schema_rel)
        paths = sorted(ROOT.glob(pattern))
        if not paths:
            errors.append(f"missing artifacts for {pattern}")
            continue
        for path in paths:
            try:
                jsonschema.validate(read_json(path), schema)
            except jsonschema.ValidationError as exc:
                errors.append(f"{path}: {exc.message}")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
