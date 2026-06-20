# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Aim BSFF at an *external* claim + signal and emit a verdict case-file.

The rest of the package validates BSFF against synthetic ground truth. This
module is the barrel of the weapon: it loads a third-party falsifiable claim
(``ClaimSpec`` as JSON/YAML) and the raw signal it stands on (``.npy``/``.csv``),
runs the fail-closed falsification pipeline, and writes a provenance-stamped,
machine-readable verdict dossier. Every load is fail-closed: a shape that does
not match the contract, an unknown field, or an unreadable file aborts the run
rather than silently coercing a claim into a passing verdict.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .evidence import stable_sha256
from .pipeline import FalsificationPipeline
from .policy import PolicyProfile
from .schemas import ClaimSpec
from .validation import sha256_bytes

CASE_SCHEMA = "bsff.case/v1"
_SIGNAL_SUFFIXES = (".npy", ".csv", ".txt", ".tsv")
_CLAIM_SUFFIXES = (".json", ".yaml", ".yml")


def load_claim(path: str | Path) -> ClaimSpec:
    """Load and validate a :class:`ClaimSpec` from a JSON or YAML file.

    Fail-closed: unknown keys are rejected (a typo'd field must not silently
    fall back to a permissive default), and ``ClaimSpec.validate`` runs before
    the spec is returned.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"claim file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in _CLAIM_SUFFIXES:
        raise ValueError(f"unsupported claim format '{suffix}'; expected one of {_CLAIM_SUFFIXES}")
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # optional dependency; only required for YAML claims
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "PyYAML is required to read YAML claims; install bsff with the 'yaml' "
                "extra or convert the claim to JSON"
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"claim file must decode to a mapping, got {type(data).__name__}")
    allowed = {f.name for f in fields(ClaimSpec)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown claim field(s): {sorted(unknown)}; allowed: {sorted(allowed)}")
    spec = ClaimSpec(**data)
    spec.validate()
    return spec


def load_signal(path: str | Path, spec: ClaimSpec) -> np.ndarray:
    """Load a signal array and fail-closed verify it against the contract.

    Accepts ``.npy`` (native) or delimited text (``.csv``/``.tsv``/``.txt``).
    The returned array is shaped ``(n_channels, n_samples)``; a 1-D file is
    accepted only for a single-channel claim. Channel/sample counts must match
    the ``ClaimSpec`` exactly — a mismatch is an aborted run, never a reshape.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"signal file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in _SIGNAL_SUFFIXES:
        raise ValueError(
            f"unsupported signal format '{suffix}'; expected one of {_SIGNAL_SUFFIXES}"
        )
    if suffix == ".npy":
        array = np.load(path)
    else:
        delimiter = "\t" if suffix == ".tsv" else ","
        array = np.loadtxt(path, delimiter=delimiter, ndmin=2)
    array = np.asarray(array, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError("signal contains non-finite values (NaN/Inf); refuse to falsify")

    if array.ndim == 1:
        array = array[np.newaxis, :]
    elif array.ndim != 2:
        raise ValueError(f"signal must be 1-D or 2-D, got {array.ndim}-D")

    # Orient to (n_channels, n_samples). A delimited file is naturally row=time;
    # disambiguate using the declared channel count rather than guessing.
    if array.shape[0] != spec.n_channels and array.shape[1] == spec.n_channels:
        array = array.T
    if array.shape[0] != spec.n_channels:
        raise ValueError(
            f"signal channel count {array.shape} does not match claim n_channels={spec.n_channels}"
        )
    if array.shape[1] != spec.n_samples:
        raise ValueError(
            f"signal length {array.shape[1]} does not match claim n_samples={spec.n_samples}"
        )
    return array


def run_case(
    claim_path: str | Path,
    signal_path: str | Path,
    *,
    policy: PolicyProfile | str = "strict",
    seed: int = 123,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Falsify an external claim and return (and optionally write) the dossier.

    The verdict is produced by the standard fail-closed pipeline; this function
    only adds an auditable envelope: byte-level signal provenance, the contract
    hash, and a canonical ``artifact_sha256`` over the whole case file.
    """
    spec = load_claim(claim_path)
    signal = load_signal(signal_path, spec)
    signal_bytes = Path(signal_path).read_bytes()

    pipeline_verdict = FalsificationPipeline().evaluate(spec, signal, policy=policy, seed=seed)
    verdict_json = pipeline_verdict.to_verdict_json()

    policy_name = policy.name if isinstance(policy, PolicyProfile) else str(policy)
    artifact: dict[str, Any] = {
        "schema": CASE_SCHEMA,
        "tool": "bsff",
        "tool_version": __version__,
        "generated_by": "bsff falsify",
        "policy": policy_name,
        "seed": seed,
        "claim": spec.to_dict(),
        "signal_provenance": {
            "path": str(Path(signal_path)),
            "sha256": sha256_bytes(signal_bytes),
            "shape": list(signal.shape),
            "dtype": str(signal.dtype),
        },
        "verdict": verdict_json.to_dict(),
        "contract_sha256": pipeline_verdict.contract_sha256,
        "caveats": list(pipeline_verdict.caveats),
    }
    # artifact_sha256 is computed over the verdict-bearing content above so the
    # dossier is self-verifying and reproducible (no wall-clock in the digest).
    artifact["artifact_sha256"] = stable_sha256(artifact)

    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact
