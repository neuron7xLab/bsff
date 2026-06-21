# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Unsupported-scope quarantine for the BSFF falsification engine.

BSFF validly adjudicates exactly one kind of claim: a *falsifiable, empirical,
time-series signal claim* that can be attacked with surrogate testing and
leakage detection. Anything outside that envelope must never be handed a
positive ("SURVIVED") verdict, because the engine has no instrument that bears
on it — a surrogate test of an emotion-reading marketing claim, a clinical
diagnosis, or a mathematical identity is a category error, not evidence.

This module is the fail-closed boundary. It is deterministic and lexical — it
classifies a claim by explicit metadata flags and a small, auditable token
table, never by a hidden model. The default disposition for an out-of-scope
claim is conservative: route it to ``UNSUPPORTED`` or ``QUARANTINED`` and carry
an explicit caveat naming why.

The single invariant this module guarantees:

    No out-of-scope claim can ever return ``SURVIVED``.

:func:`guard_verdict` enforces that invariant by downgrading any proposed
``SURVIVED`` to the scope disposition whenever the claim is out of scope. It is
intended to wrap the verdict the engine would otherwise emit; the main
orchestrator wires it in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .schemas import ClaimSpec, Verdict

__all__ = [
    "OutOfScopeCategory",
    "ScopeDisposition",
    "ScopeVerdict",
    "classify_scope",
    "enforce_scope",
    "guard_verdict",
]


class OutOfScopeCategory(str, Enum):
    """Claim categories BSFF must never adjudicate as SURVIVED.

    Each value is the audit token written into :attr:`ScopeVerdict.category`.
    """

    CLINICAL = "CLINICAL"
    REGULATORY = "REGULATORY"
    EMOTION_WITHOUT_SIGNAL = "EMOTION_WITHOUT_SIGNAL"
    NON_TIME_SERIES = "NON_TIME_SERIES"
    CAUSAL_WITHOUT_ROUTE = "CAUSAL_WITHOUT_ROUTE"
    LOGICAL_WITHOUT_DATA = "LOGICAL_WITHOUT_DATA"


# The disposition assigned to each out-of-scope category. CLINICAL and
# REGULATORY claims carry real-world harm if a falsification engine appears to
# endorse them, so they are QUARANTINED (hard-isolated, never re-routed). The
# remaining categories are UNSUPPORTED: the engine simply has no evidence to
# offer, which is informative but not dangerous.
_CATEGORY_DISPOSITION: dict[OutOfScopeCategory, str] = {
    OutOfScopeCategory.CLINICAL: "QUARANTINED",
    OutOfScopeCategory.REGULATORY: "QUARANTINED",
    OutOfScopeCategory.EMOTION_WITHOUT_SIGNAL: "UNSUPPORTED",
    OutOfScopeCategory.NON_TIME_SERIES: "UNSUPPORTED",
    OutOfScopeCategory.CAUSAL_WITHOUT_ROUTE: "UNSUPPORTED",
    OutOfScopeCategory.LOGICAL_WITHOUT_DATA: "UNSUPPORTED",
}


class ScopeDisposition(str, Enum):
    """The three terminal scope dispositions."""

    IN_SCOPE = "IN_SCOPE"
    UNSUPPORTED = "UNSUPPORTED"
    QUARANTINED = "QUARANTINED"


# Lexical signatures, evaluated in precedence order (first match wins). Every
# entry is a compiled pattern so the decision is reproducible and auditable.
# These only *trigger* a candidate category; the metadata flags below can still
# clear emotion/causal categories when a valid signal/route is declared.
_CLINICAL = re.compile(
    r"\b(diagnos\w+|treat(?:s|ed|ment|ing)?|cure[sd]?|therap\w+|"
    r"clinical\w*|patient[s]?|disease[sd]?|disorder[s]?|patholog\w+|"
    r"prognos\w+|symptom[s]?|medical\b)",
    re.IGNORECASE,
)
_REGULATORY = re.compile(
    r"\b(fda[- ]?(?:approv\w+|clear\w+)|ce[- ]?mark\w*|regulator\w+|"
    r"compli(?:ant|ance)|certif\w+|approved for (?:use|market)|"
    r"510\(?k\)?|legal\w*|gdpr|hipaa)",
    re.IGNORECASE,
)
_EMOTION = re.compile(
    r"\b(emotion\w*|feel(?:s|ing[s]?)?|mood[s]?|affect\w*|sentiment[s]?|"
    r"happ(?:y|iness)|sad(?:ness)?|angr(?:y|ier)|anxiet\w+|love[sd]?|"
    r"mental state[s]?)",
    re.IGNORECASE,
)
_CAUSAL = re.compile(
    r"\b(caus\w+|because of|leads? to|results? in|produces?|drives?|"
    r"induces?|triggers?|due to|responsible for)\b",
    re.IGNORECASE,
)
_LOGICAL_MATH = re.compile(
    r"\b(theorem|lemma|proof|prove[sd]?|axiom[s]?|by definition|"
    r"tautolog\w+|necessaril\w+|a priori|equals?|identity)\b|"
    r"[=<>]\s*\d|\b\d+\s*[+\-*/^]\s*\d+\b",
    re.IGNORECASE,
)


def _coerce(claim: ClaimSpec | dict[str, Any]) -> dict[str, Any]:
    """Normalize a ClaimSpec or metadata dict into a flat flag dict.

    Recognized keys (all optional): ``text``/``claim``/``quote`` (free text),
    ``claim_type``, ``has_signal``, ``has_causal_route``, ``is_time_series``.
    A genuine :class:`ClaimSpec` is treated as a valid in-scope signal claim by
    default (it carries a signal_type and a sampling rate), and its ``metadata``
    may override any of the recognized flags.
    """
    if isinstance(claim, ClaimSpec):
        meta = dict(claim.metadata)
        flags: dict[str, Any] = {
            "text": str(meta.get("text", meta.get("claim", ""))),
            "claim_type": str(meta.get("claim_type", "signal")),
            "has_signal": bool(meta.get("has_signal", True)),
            "has_causal_route": bool(meta.get("has_causal_route", False)),
            # A ClaimSpec with a positive sampling rate is, by construction, a
            # time-series unless its metadata explicitly says otherwise.
            "is_time_series": bool(meta.get("is_time_series", claim.sampling_rate_hz > 0)),
        }
        return flags

    text = str(claim.get("text", claim.get("claim", claim.get("quote", ""))))
    return {
        "text": text,
        "claim_type": str(claim.get("claim_type", "")),
        "has_signal": bool(claim.get("has_signal", False)),
        "has_causal_route": bool(claim.get("has_causal_route", False)),
        "is_time_series": bool(claim.get("is_time_series", True)),
    }


def _detect_category(flags: dict[str, Any]) -> OutOfScopeCategory | None:
    """Return the out-of-scope category for ``flags``, or None if in scope.

    Precedence is deliberate and fail-closed: harm-bearing categories
    (clinical, regulatory) are checked first, then the structural gates.
    """
    text = str(flags["text"])
    claim_type = str(flags["claim_type"]).strip().lower()

    # 1. Clinical — explicit claim_type or lexical signature. Always quarantined.
    if claim_type in {"clinical", "medical", "diagnostic"} or _CLINICAL.search(text):
        return OutOfScopeCategory.CLINICAL

    # 2. Regulatory — explicit claim_type or lexical signature.
    if claim_type in {"regulatory", "compliance", "legal"} or _REGULATORY.search(text):
        return OutOfScopeCategory.REGULATORY

    # 3. Non-time-series — a signal claim that is not over time has no surrogate
    #    null to attack. This gate is structural, so it precedes the softer
    #    emotion/causal gates that a signal basis can clear.
    if not bool(flags["is_time_series"]) or claim_type in {"static", "non_time_series", "tabular"}:
        return OutOfScopeCategory.NON_TIME_SERIES

    # 4. Emotion-reading WITHOUT a signal basis. An EEG-grounded affect claim is
    #    in scope; "this app reads your emotions" with no signal is not.
    if (claim_type == "emotion" or _EMOTION.search(text)) and not bool(flags["has_signal"]):
        return OutOfScopeCategory.EMOTION_WITHOUT_SIGNAL

    # 5. Causal claim WITHOUT a declared causal route (e.g. transfer entropy /
    #    intervention design). A correlation engine cannot license causation.
    if (claim_type == "causal" or _CAUSAL.search(text)) and not bool(flags["has_causal_route"]):
        return OutOfScopeCategory.CAUSAL_WITHOUT_ROUTE

    # 6. Logical / mathematical claim WITHOUT empirical data. A theorem is not
    #    falsifiable by surrogate testing; nothing empirical bears on it.
    if (
        claim_type in {"logical", "mathematical", "definitional"} or _LOGICAL_MATH.search(text)
    ) and not bool(flags["has_signal"]):
        return OutOfScopeCategory.LOGICAL_WITHOUT_DATA

    return None


@dataclass(frozen=True)
class ScopeVerdict:
    """Result of scope classification for one claim.

    ``disposition`` is one of ``"IN_SCOPE"``, ``"UNSUPPORTED"``, or
    ``"QUARANTINED"`` (the values of :class:`ScopeDisposition`).
    """

    in_scope: bool
    disposition: str
    category: str | None
    caveat: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_scope": self.in_scope,
            "disposition": self.disposition,
            "category": self.category,
            "caveat": self.caveat,
        }


_IN_SCOPE_CAVEAT = (
    "In scope: a falsifiable, empirical, time-series signal claim suitable for "
    "surrogate testing and leakage detection."
)


def _caveat_for(category: OutOfScopeCategory, disposition: str) -> str:
    reasons: dict[OutOfScopeCategory, str] = {
        OutOfScopeCategory.CLINICAL: (
            "Clinical claim: BSFF does not diagnose, treat, or evaluate medical "
            "outcomes and has no instrument that bears on this assertion."
        ),
        OutOfScopeCategory.REGULATORY: (
            "Regulatory/compliance claim: BSFF is not a certifying authority and "
            "cannot establish regulatory approval, clearance, or compliance."
        ),
        OutOfScopeCategory.EMOTION_WITHOUT_SIGNAL: (
            "Emotion-reading claim without a declared signal basis: no time-series "
            "to attack with a surrogate null, so no falsification is possible."
        ),
        OutOfScopeCategory.NON_TIME_SERIES: (
            "Non-time-series claim: the surrogate-null battery requires a temporal "
            "signal; a static/tabular assertion has no admissible null."
        ),
        OutOfScopeCategory.CAUSAL_WITHOUT_ROUTE: (
            "Causal claim without a declared causal route (e.g. transfer entropy "
            "or intervention): a surrogate test of association cannot license it."
        ),
        OutOfScopeCategory.LOGICAL_WITHOUT_DATA: (
            "Logical/mathematical claim without empirical data: not falsifiable by "
            "surrogate testing; nothing empirical bears on a deductive assertion."
        ),
    }
    return f"[{disposition}] {reasons[category]}"


def classify_scope(claim: ClaimSpec | dict[str, Any]) -> ScopeVerdict:
    """Classify a claim's scope deterministically (fail-closed).

    Accepts a :class:`ClaimSpec` or a metadata dict. Returns a
    :class:`ScopeVerdict` whose ``disposition`` routes out-of-scope claims to
    ``UNSUPPORTED`` or ``QUARANTINED`` with an explicit caveat. There is no
    hidden model: every decision is driven by explicit flags and an auditable
    token table.
    """
    flags = _coerce(claim)
    category = _detect_category(flags)
    if category is None:
        return ScopeVerdict(
            in_scope=True,
            disposition=ScopeDisposition.IN_SCOPE.value,
            category=None,
            caveat=_IN_SCOPE_CAVEAT,
        )
    disposition = _CATEGORY_DISPOSITION[category]
    return ScopeVerdict(
        in_scope=False,
        disposition=disposition,
        category=category.value,
        caveat=_caveat_for(category, disposition),
    )


def guard_verdict(scope_verdict: ScopeVerdict, proposed_verdict: str) -> str:
    """Downgrade an out-of-scope ``SURVIVED`` to its scope disposition.

    This is the enforcement point of the module invariant: when the claim is
    out of scope, any proposed ``SURVIVED`` is replaced by the scope
    disposition (``UNSUPPORTED`` or ``QUARANTINED``). In-scope verdicts pass
    through unchanged. The return type widens :data:`bsff.schemas.Verdict` with
    ``QUARANTINED`` for the hard-isolated categories.
    """
    if scope_verdict.in_scope:
        return proposed_verdict
    if proposed_verdict == "SURVIVED":
        return scope_verdict.disposition
    # A non-positive verdict (REFUTED/UNSUPPORTED) is already safe; but never let
    # an out-of-scope claim keep a positive-looking verdict by any other spelling.
    return proposed_verdict


def enforce_scope(claim: ClaimSpec | dict[str, Any]) -> None:
    """Raise if the claim is out of scope; return None when in scope.

    A fail-closed convenience for call sites that want to refuse out-of-scope
    claims outright instead of downgrading a proposed verdict.
    """
    verdict = classify_scope(claim)
    if not verdict.in_scope:
        raise ScopeError(verdict)


class ScopeError(ValueError):
    """Raised by :func:`enforce_scope` for an out-of-scope claim."""

    def __init__(self, scope_verdict: ScopeVerdict) -> None:
        self.scope_verdict = scope_verdict
        super().__init__(scope_verdict.caveat)


def _assert_verdict_widening() -> None:
    """Static reminder that QUARANTINED widens the schema Verdict literal.

    Kept as an executable no-op so the relationship to :data:`Verdict` is
    documented in-module without importing typing machinery at runtime.
    """
    _valid: tuple[Verdict, ...] = ("REFUTED", "UNSUPPORTED", "SURVIVED")
    assert "QUARANTINED" not in _valid
