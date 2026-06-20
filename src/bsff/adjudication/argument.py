# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Argument-structure detection for deductive claims.

This is a *structural* detector, not a soundness oracle. It reports whether a
quoted claim exposes the parts of an argument — at least one premise marker and
a conclusion connective — so a bare assertion dressed as a deduction
("therefore X") can be separated from a stated inference ("because A, therefore
X"). It never asserts that an argument is true or its premises correct; that
remains a human judgement. Reporting structure honestly is the most this layer
can earn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

_CONCLUSION = re.compile(
    r"\btherefore\b|\bthus\b|\bhence\b|\bit follows\b|\bconsequently\b|\bso\b|\bimpl(?:y|ies)\b",
    re.IGNORECASE,
)
_PREMISE = re.compile(
    r"\bbecause\b|\bsince\b|\bgiven (?:that)?\b|\bas\b|\bif\b|\bdue to\b|\bfrom (?:the )?fact\b",
    re.IGNORECASE,
)


class ArgumentStructure(str, Enum):
    STRUCTURE_PRESENT = "STRUCTURE_PRESENT"
    STRUCTURE_INCOMPLETE = "STRUCTURE_INCOMPLETE"
    NO_ARGUMENT_STRUCTURE = "NO_ARGUMENT_STRUCTURE"


@dataclass(frozen=True)
class ArgumentReport:
    structure: ArgumentStructure
    has_conclusion_marker: bool
    has_premise_marker: bool
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure": self.structure.value,
            "has_conclusion_marker": self.has_conclusion_marker,
            "has_premise_marker": self.has_premise_marker,
            "note": self.note,
        }


def lint_argument(quote: str) -> ArgumentReport:
    """Detect the presence of deductive structure (premise + conclusion)."""
    has_concl = _CONCLUSION.search(quote) is not None
    has_prem = _PREMISE.search(quote) is not None
    if has_concl and has_prem:
        structure = ArgumentStructure.STRUCTURE_PRESENT
        note = "premise and conclusion markers both present; structure is inspectable (not proven sound)"
    elif has_concl and not has_prem:
        structure = ArgumentStructure.STRUCTURE_INCOMPLETE
        note = (
            "conclusion asserted without a stated premise; inference rests on unstated assumptions"
        )
    else:
        structure = ArgumentStructure.NO_ARGUMENT_STRUCTURE
        note = "no deductive connective detected; not an argument in inspectable form"
    return ArgumentReport(
        structure=structure,
        has_conclusion_marker=has_concl,
        has_premise_marker=has_prem,
        note=note,
    )
