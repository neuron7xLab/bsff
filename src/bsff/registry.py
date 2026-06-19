# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Iterator
from typing import Protocol

from .evidence import StageResult


class PipelineStage(Protocol):
    stage_id: str

    def run(self, context: object) -> StageResult: ...


class StageRegistry:
    """Small deterministic plugin registry for falsification stages."""

    def __init__(self) -> None:
        self._stages: OrderedDict[str, PipelineStage] = OrderedDict()

    def register(self, stage: PipelineStage) -> None:
        if not stage.stage_id:
            raise ValueError("stage_id must be non-empty")
        if stage.stage_id in self._stages:
            raise ValueError(f"duplicate stage_id: {stage.stage_id}")
        self._stages[stage.stage_id] = stage

    def extend(self, stages: Iterable[PipelineStage]) -> None:
        for stage in stages:
            self.register(stage)

    def __iter__(self) -> Iterator[PipelineStage]:
        return iter(self._stages.values())

    def __len__(self) -> int:
        return len(self._stages)

    def ids(self) -> list[str]:
        return list(self._stages.keys())
