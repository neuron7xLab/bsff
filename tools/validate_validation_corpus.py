#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "validation" / "bsff_validation_corpus_manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    failures: list[str] = []
    if not MANIFEST.exists():
        print("Validation corpus: FAIL")
        print("- missing manifest")
        return 1
    manifest = json.loads(MANIFEST.read_text())
    artifact = ROOT / manifest["artifact"]
    if not artifact.exists():
        failures.append(f"missing artifact: {artifact}")
    else:
        if sha256_file(artifact) != manifest["sha256"]:
            failures.append("artifact sha256 mismatch")
        arrays = np.load(artifact)
        for name, shape in manifest["arrays"].items():
            if name not in arrays:
                failures.append(f"missing array: {name}")
                continue
            if list(arrays[name].shape) != shape:
                failures.append(f"shape mismatch for {name}: {arrays[name].shape} != {shape}")
    if manifest.get("clinical_data") is not False or manifest.get("synthetic_only") is not True:
        failures.append("corpus must be synthetic-only and non-clinical")
    if failures:
        print("Validation corpus: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Validation corpus: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
