# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import json
from pathlib import Path

from .schemas import VerdictJSON


def write_verdict_json(verdict: VerdictJSON, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(verdict.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return out
