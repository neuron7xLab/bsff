#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Emit the public JSON Schemas for ClaimSpec and VerdictJSON.

Writes artifacts/schemas/*.schema.json. Re-running must be a no-op when the
dataclasses are unchanged, so the committed schemas are a verifiable contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsff.json_schema import claim_spec_schema, verdict_json_schema  # noqa: E402

OUT_DIR = ROOT / "artifacts" / "schemas"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, schema in (
        ("claim_spec.schema.json", claim_spec_schema()),
        ("verdict.schema.json", verdict_json_schema()),
    ):
        (OUT_DIR / name).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        print(f"wrote {OUT_DIR.relative_to(ROOT) / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
