# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

StageStatus = Literal["PASS", "FAIL", "WARN", "SKIP"]


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def stable_sha256(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    status: StageStatus
    fatal: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_sha256"] = stable_sha256(self.evidence)
        return payload


@dataclass(frozen=True)
class EvidenceGraph:
    """Ordered, hashable evidence graph for one falsification run."""

    nodes: tuple[StageResult, ...]

    def to_dict(self) -> dict[str, Any]:
        node_payload = [node.to_dict() for node in self.nodes]
        return {
            "node_count": len(node_payload),
            "nodes": node_payload,
            "graph_sha256": stable_sha256(node_payload),
        }

    @property
    def fatal(self) -> bool:
        return any(node.fatal for node in self.nodes)

    @property
    def caveats(self) -> list[str]:
        out: list[str] = []
        for node in self.nodes:
            out.extend(node.caveats)
        return out
