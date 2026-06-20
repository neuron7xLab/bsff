# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Falsifiability tier classification.

Before a claim can be judged it must be sorted by the *kind* of scrutiny it
admits. This classifier is deterministic and lexical — never an opinion engine.
Every tier decision carries the exact signal tokens that triggered it, so the
classification is auditable and reproducible.

The default is :data:`FalsifiabilityTier.NON_FALSIFIABLE`: a claim must earn a
falsifiable tier by exhibiting an empirical, quantitative, or deductive
signature. This is the fail-closed direction for a falsification engine — an
untestable assertion must never masquerade as something that was tested.

Precedence (first match wins), with rationale:

1. ``DEFINITIONAL``  — a stipulation, not a claim about the world; nothing to test.
2. ``EMPIRICAL_STATISTICAL`` — carries quantitative/statistical content; routable
   to the signal-falsification battery.
3. ``EMPIRICAL_GENERAL`` — empirical but qualitative; falsifiable only once an
   operationalization + data are supplied.
4. ``LOGICAL`` — deductive structure; routable to the argument-structure check.
5. ``NORMATIVE`` — a value/ought claim; not empirically falsifiable, quarantined.
6. ``NON_FALSIFIABLE`` — default; quarantined.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FalsifiabilityTier(str, Enum):
    DEFINITIONAL = "DEFINITIONAL"
    EMPIRICAL_STATISTICAL = "EMPIRICAL_STATISTICAL"
    EMPIRICAL_GENERAL = "EMPIRICAL_GENERAL"
    LOGICAL = "LOGICAL"
    NORMATIVE = "NORMATIVE"
    NON_FALSIFIABLE = "NON_FALSIFIABLE"


# Each entry: (tier, signal_name, compiled_pattern). Order encodes precedence.
_SIGNATURES: list[tuple[FalsifiabilityTier, str, re.Pattern[str]]] = [
    (
        FalsifiabilityTier.DEFINITIONAL,
        "definition_marker",
        re.compile(
            r"\b(is|are) defined as\b|\bwe define\b|\bby definition\b|\bdenotes?\b|"
            r"\brefers? to\b|\bwe (?:call|term)\b",
            re.IGNORECASE,
        ),
    ),
    (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        "p_value",
        re.compile(r"\bp\s*[<>=]\s*0?\.\d+|\bp[ -]?value", re.IGNORECASE),
    ),
    (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        "significance",
        re.compile(r"\bstatistically significant\b|\bsignifican(?:t|ce)\b", re.IGNORECASE),
    ),
    (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        "metric",
        re.compile(
            r"\b(accuracy|auc|auroc|sensitivity|specificity|f1|precision|recall|"
            r"correlation|r\s*=\s*-?0?\.\d+|effect size|cohen'?s d|odds ratio)\b",
            re.IGNORECASE,
        ),
    ),
    (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        "quantity",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*%|\bn\s*=\s*\d+|\b\d+(?:\.\d+)?\s*"
            r"(?:hz|ms|s|mv|µv|uv|db|fold)\b",
            re.IGNORECASE,
        ),
    ),
    # A bare number immediately followed by an UPPERCASE acronym is a reported
    # benchmark metric (e.g. "28.4 BLEU", "92 AUC"). Case-sensitive on purpose:
    # the uppercase acronym is the signal, and IGNORECASE would match any word.
    (
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        "benchmark_metric",
        re.compile(r"\b\d+(?:\.\d+)?\s+[A-Z]{2,}\b"),
    ),
    (
        FalsifiabilityTier.EMPIRICAL_GENERAL,
        "empirical_verb",
        re.compile(
            r"\b(observ\w+|measur\w+|found that|results? show|demonstrat\w+|"
            r"increas\w+|decreas\w+|predict\w+|classif\w+|caus\w+|"
            r"lead(?:s|ing)? to|associated with|correlat\w+)\b",
            re.IGNORECASE,
        ),
    ),
    (
        FalsifiabilityTier.LOGICAL,
        "deductive_connective",
        re.compile(
            r"\btherefore\b|\bthus\b|\bhence\b|\bit follows\b|\bimpl(?:y|ies)\b|"
            r"\bif\b.+\bthen\b",
            re.IGNORECASE,
        ),
    ),
    (
        FalsifiabilityTier.NORMATIVE,
        "normative_modal",
        re.compile(
            r"\b(should|ought to|must be|we recommend|it is (?:better|worse)|"
            r"the best (?:way|approach)|preferable)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class Classification:
    tier: FalsifiabilityTier
    rationale: str
    signals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "rationale": self.rationale,
            "signals": list(self.signals),
        }


def classify(quote: str) -> Classification:
    """Classify a claim quote into a :class:`FalsifiabilityTier` (fail-closed)."""
    matched: dict[FalsifiabilityTier, list[str]] = {}
    for tier, name, pattern in _SIGNATURES:
        if pattern.search(quote):
            matched.setdefault(tier, []).append(name)

    for tier in (
        FalsifiabilityTier.DEFINITIONAL,
        FalsifiabilityTier.EMPIRICAL_STATISTICAL,
        FalsifiabilityTier.EMPIRICAL_GENERAL,
        FalsifiabilityTier.LOGICAL,
        FalsifiabilityTier.NORMATIVE,
    ):
        if tier in matched:
            signals = tuple(matched[tier])
            return Classification(
                tier=tier,
                rationale=f"matched {tier.value} signature(s): {', '.join(signals)}",
                signals=signals,
            )

    return Classification(
        tier=FalsifiabilityTier.NON_FALSIFIABLE,
        rationale="no empirical, quantitative, or deductive signature detected; "
        "default fail-closed tier",
        signals=(),
    )
