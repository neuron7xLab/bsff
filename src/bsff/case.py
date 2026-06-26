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
from .datasets import check_rawness
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


def load_signal(path: str | Path, spec: ClaimSpec, *, require_raw: bool = True) -> np.ndarray:
    """Load a signal array and fail-closed verify it against the contract.

    Accepts ``.npy`` (native) or delimited text (``.csv``/``.tsv``/``.txt``).
    The returned array is shaped ``(n_channels, n_samples)``; a 1-D file is
    accepted only for a single-channel claim. Channel/sample counts must match
    the ``ClaimSpec`` exactly — a mismatch is an aborted run, never a reshape.

    With ``require_raw`` (the default) the oriented array is passed through the
    raw-signal guard (``datasets.check_rawness``): a feature table, accuracy/metric
    matrix, or label array is refused so BSFF tests a neural signal, not someone's
    preprocessing — the same INV-6 guard ``datasets.load_series`` enforces. Pass
    ``require_raw=False`` (``bsff falsify --allow-nonraw``) only with a recorded,
    on-the-record assertion that the input really is raw.
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
    if require_raw:
        reasons = check_rawness(array)
        if reasons:
            raise ValueError(
                "signal does not look raw (" + "; ".join(reasons) + "). BSFF tests neural "
                "signals, not preprocessing artefacts. If this truly is raw, re-run with "
                "require_raw=False / `bsff falsify --allow-nonraw` to record the override."
            )
    return array


def run_case(
    claim_path: str | Path,
    signal_path: str | Path,
    *,
    policy: PolicyProfile | str = "strict",
    seed: int = 123,
    out_path: str | Path | None = None,
    require_raw: bool = True,
) -> dict[str, Any]:
    """Falsify an external claim and return (and optionally write) the dossier.

    The verdict is produced by the standard fail-closed pipeline; this function
    only adds an auditable envelope: byte-level signal provenance, the contract
    hash, and a canonical ``artifact_sha256`` over the whole case file.
    """
    spec = load_claim(claim_path)
    signal = load_signal(signal_path, spec, require_raw=require_raw)
    signal_bytes = Path(signal_path).read_bytes()
    # When the raw-guard is overridden, record the override AND the reasons it would
    # have fired, so a non-raw run is never silent — it is on the record in the dossier.
    raw_reasons = [] if require_raw else check_rawness(signal)

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
            "raw_override": not require_raw,
            "raw_check_reasons": raw_reasons,
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


def reproduce_case(
    case_path: str | Path,
    *,
    signal_path: str | Path | None = None,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Re-run a saved verdict case-file and confirm the verdict is reproducible.

    Loads a previously written ``bsff falsify`` dossier, reconstructs the claim
    and re-runs the identical policy/seed against the original signal (or a
    ``signal_path`` override), and checks the recomputed ``artifact_sha256``
    against the recorded one. This is the reviewer's one-command reproduction:
    same inputs + same code must yield the same verdict digest, or the run is
    flagged ``NOT_REPRODUCIBLE``.
    """
    case = json.loads(Path(case_path).read_text(encoding="utf-8"))
    if not isinstance(case, dict) or "claim" not in case or "verdict" not in case:
        raise ValueError(f"{case_path} is not a bsff falsify case-file")

    recorded_sha = case.get("artifact_sha256")
    claim_dict = case["claim"]
    allowed = {f.name for f in fields(ClaimSpec)}
    spec = ClaimSpec(**{k: v for k, v in claim_dict.items() if k in allowed})
    spec.validate()

    recorded_signal = case.get("signal_provenance", {}).get("path")
    sig = Path(signal_path) if signal_path is not None else Path(str(recorded_signal))
    if not sig.is_file():
        raise FileNotFoundError(
            f"signal not found for reproduction: {sig}. Pass --signal to point at the "
            "original signal file recorded in signal_provenance."
        )

    # Verify signal byte-identity before recomputing, so a moved/edited signal is
    # reported as the cause rather than silently producing a different verdict.
    recorded_signal_sha = case.get("signal_provenance", {}).get("sha256")
    actual_signal_sha = sha256_bytes(sig.read_bytes())
    signal_matches = recorded_signal_sha is None or actual_signal_sha == recorded_signal_sha

    rerun = run_case(
        _claim_to_tempfile(spec),
        sig,
        policy=case.get("policy", "strict"),
        seed=int(case.get("seed", 123)),
    )
    rerun_sha = rerun.get("artifact_sha256")
    reproducible = bool(signal_matches and recorded_sha is not None and rerun_sha == recorded_sha)

    report: dict[str, Any] = {
        "schema": "bsff.reproduce/v1",
        "tool": "bsff",
        "tool_version": __version__,
        "case_path": str(case_path),
        "recorded_artifact_sha256": recorded_sha,
        "recomputed_artifact_sha256": rerun_sha,
        "signal_sha256_recorded": recorded_signal_sha,
        "signal_sha256_actual": actual_signal_sha,
        "signal_matches": signal_matches,
        "verdict_label": rerun["verdict"]["verdict"],
        "reproducible": reproducible,
        "status": "REPRODUCIBLE" if reproducible else "NOT_REPRODUCIBLE",
    }
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _claim_to_tempfile(spec: ClaimSpec) -> Path:
    """Write a ClaimSpec to a deterministic temp JSON for re-running run_case."""
    import tempfile

    tmp = Path(tempfile.gettempdir()) / f"bsff_reproduce_{spec.claim_id}.json"
    tmp.write_text(json.dumps(spec.to_dict(), ensure_ascii=False), encoding="utf-8")
    return tmp
