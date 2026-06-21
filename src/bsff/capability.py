# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Runtime capability and dependency reporting.

Optional dependencies change *which evidence paths are available*, and therefore
which verdicts BSFF is entitled to emit. A surrogate test that silently degrades
its Bayes factor from a JZS Cauchy prior to a BIC approximation — or skips
mutual-information leakage detection because scikit-learn is absent — is not a
neutral convenience: it changes the strength of the evidence behind a SURVIVED.

This module makes that explicit and machine-readable. ``capability_report`` is
the data behind ``bsff capabilities``; ``doctor_report`` is the human-facing
``bsff doctor`` health check; ``strict_readiness`` is the fail-closed gate that
forbids a ``--policy strict`` run when the publication-grade evidence path cannot
actually be computed in the current environment.
"""

from __future__ import annotations

import importlib
import importlib.metadata as importlib_metadata
import platform
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    """One optional dependency and the evidence path it unlocks."""

    name: str
    module: str
    extra: str
    enables: str
    required_for_strict: bool
    installed: bool
    version: str | None
    degraded_without: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "module": self.module,
            "extra": self.extra,
            "enables": self.enables,
            "required_for_strict": self.required_for_strict,
            "installed": self.installed,
            "version": self.version,
            "degraded_without": self.degraded_without,
        }


# The capability matrix. Each row is a real branch in the codebase:
#   pingouin  -> bsff.bayesian.jzs_bayes_factor (JZS Cauchy vs BIC fallback)
#   sklearn   -> bsff.leakage_detector deep MI-permutation leakage detection
#   yaml      -> ClaimSpec loading from .yaml/.yml
#   mne/moabb -> raw EDF normalization and MOABB external-benchmark ingestion
_CAPABILITY_SPECS: tuple[dict[str, object], ...] = (
    {
        "name": "bayesian-jzs",
        "module": "pingouin",
        "extra": "stats",
        "enables": "JZS Cauchy Bayes factor for the SURVIVED corroboration gate",
        "required_for_strict": True,
        "degraded_without": "Bayes factor falls back to a BIC normal approximation",
    },
    {
        "name": "deep-leakage",
        "module": "sklearn",
        "extra": "leakage",
        "enables": "mutual-information label-permutation leakage detection",
        "required_for_strict": True,
        "degraded_without": "MI-based feature-selection leakage detection is unavailable",
    },
    {
        "name": "yaml-claims",
        "module": "yaml",
        "extra": "yaml",
        "enables": "ClaimSpec loading from YAML files",
        "required_for_strict": False,
        "degraded_without": "claims must be supplied as JSON instead of YAML",
    },
    {
        "name": "edf-ingest",
        "module": "mne",
        "extra": "moabb",
        "enables": "raw EDF/BDF normalization to canonical signal arrays",
        "required_for_strict": False,
        "degraded_without": "raw EDF/BDF files cannot be read (use .npy/.csv inputs)",
    },
    {
        "name": "moabb-benchmark",
        "module": "moabb",
        "extra": "moabb",
        "enables": "MOABB external EEG benchmark ingestion",
        "required_for_strict": False,
        "degraded_without": "MOABB datasets cannot be adjudicated directly",
    },
)


def _probe(module: str) -> tuple[bool, str | None]:
    """Return (installed, version) for one optional module, never raising."""
    try:
        importlib.import_module(module)
    except Exception:
        return False, None
    # Distribution name can differ from the import name (sklearn -> scikit-learn).
    for dist in (module, module.replace("_", "-"), {"sklearn": "scikit-learn"}.get(module, module)):
        try:
            return True, importlib_metadata.version(dist)
        except importlib_metadata.PackageNotFoundError:
            continue
    return True, None


def detect_capabilities() -> list[Capability]:
    """Probe every optional dependency in the capability matrix."""
    out: list[Capability] = []
    for spec in _CAPABILITY_SPECS:
        module = str(spec["module"])
        installed, version = _probe(module)
        out.append(
            Capability(
                name=str(spec["name"]),
                module=module,
                extra=str(spec["extra"]),
                enables=str(spec["enables"]),
                required_for_strict=bool(spec["required_for_strict"]),
                installed=installed,
                version=version,
                degraded_without=str(spec["degraded_without"]),
            )
        )
    return out


def strict_readiness() -> tuple[bool, list[str]]:
    """Return (ready, missing_extras) for the publication-grade strict policy.

    Fail-closed: a ``--policy strict`` run claims a publication-grade evidence
    path. If a dependency that path depends on is absent, the run must be refused
    rather than silently emitting a weaker verdict wearing a strict label.
    """
    missing: list[str] = []
    for cap in detect_capabilities():
        if cap.required_for_strict and not cap.installed:
            missing.append(cap.extra)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped = [e for e in missing if not (e in seen or seen.add(e))]
    return (len(deduped) == 0), deduped


@dataclass(frozen=True)
class StrictCapabilityError(Exception):
    """Raised when a strict-policy run is requested without its evidence path."""

    missing_extras: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        extras = ",".join(self.missing_extras)
        return (
            "strict policy requires the full evidence path, but these extras are "
            f'missing: [{extras}]. Install them with `pip install -e ".[{extras}]"` '
            "or run `bsff doctor`. Refusing to emit a strict verdict on a degraded "
            "evidence path (see docs/CLI_CONTRACT.md)."
        )


def require_strict_capabilities() -> None:
    """Fail-closed guard for strict-policy entry points."""
    ready, missing = strict_readiness()
    if not ready:
        raise StrictCapabilityError(missing_extras=missing)


def _extra_states(caps: list[Capability]) -> tuple[list[str], list[str]]:
    """Classify each extra as fully installed vs partially/not installed.

    An extra can back more than one capability (e.g. ``moabb`` backs both the
    ``mne`` EDF reader and the ``moabb`` benchmark loader). It counts as installed
    only when *every* capability under it is importable, so an extra can never be
    reported as both installed and missing.
    """
    by_extra: dict[str, list[Capability]] = {}
    for cap in caps:
        by_extra.setdefault(cap.extra, []).append(cap)
    installed = sorted(e for e, group in by_extra.items() if all(c.installed for c in group))
    missing = sorted(e for e, group in by_extra.items() if not all(c.installed for c in group))
    return installed, missing


def capability_report() -> dict[str, object]:
    """Machine-readable capability report — the data behind ``bsff capabilities``."""
    caps = detect_capabilities()
    ready, missing = strict_readiness()
    installed_extras, missing_extras = _extra_states(caps)
    return {
        "schema": "bsff.capabilities/v1",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "capabilities": [c.to_dict() for c in caps],
        "installed_extras": installed_extras,
        "missing_extras": missing_extras,
        "strict_policy_ready": ready,
        "strict_missing_extras": missing,
        "joss_ready": ready,
    }


def doctor_report() -> dict[str, object]:
    """Health check — capabilities plus an actionable strict-readiness verdict."""
    report = capability_report()
    ready = bool(report["strict_policy_ready"])
    report["status"] = "READY" if ready else "DEGRADED"
    report["recommendation"] = (
        "All strict-policy evidence paths are available."
        if ready
        else (
            "Install the missing extras to enable the strict publication-grade "
            f'evidence path: pip install -e ".[{",".join(report["strict_missing_extras"])}]"'  # type: ignore[arg-type]
        )
    )
    return report
