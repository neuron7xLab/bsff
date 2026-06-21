# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Deterministic BIDS-style EEG ingestion for fail-closed claim falsification.

This module is the *real-data* entry point: it reads a minimal `BIDS-EEG
<https://bids-specification.readthedocs.io/>`_ layout with pure stdlib + numpy
(no mandatory ``mne``), validates it fail-closed, and converts a recording into a
:class:`~bsff.schemas.ClaimSpec` that the standard falsification engine can
falsify.

Honesty contract enforced here:

* **No hidden labels.** If the EEG data file carries a column named like a class
  label (``label``, ``target``, ``class``, ``y`` ...), ingestion is *refused* —
  a falsifier must never silently read a leaked label channel. See
  ``docs/INVALID_USE.md``.
* **No feature-table leakage.** If the file looks like a precomputed feature
  table (engineered-feature column names such as ``mean_*``/``psd_*``/``feat_*``
  rather than electrode-channel names), ingestion is refused. BSFF falsifies the
  *raw signal*, not someone's already-leaked feature matrix.
* **Fail-closed layout.** A missing sidecar, missing ``*_channels.tsv``, missing
  sampling rate, channel/header mismatch, or non-finite sample aborts the run
  rather than coercing a recording into a passing verdict.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from . import __version__
from .schemas import ClaimSpec, TaskType
from .verdict_engine import evaluate_claim

INVALID_USE_DOC = "docs/INVALID_USE.md"

# Column names that betray a leaked classification/regression target. Matched
# case-insensitively against the EEG data file's header so a hidden label column
# can never be smuggled in as if it were an electrode channel.
_LABEL_COLUMN_NAMES: frozenset[str] = frozenset(
    {
        "label",
        "labels",
        "target",
        "targets",
        "class",
        "classes",
        "y",
        "outcome",
        "condition",
        "stimulus",
        "event",
        "event_id",
        "trial_type",
        "marker",
        "annotation",
    }
)

# Prefixes/tokens that betray a precomputed feature table rather than a raw EEG
# trace. A real BIDS-EEG ``*_eeg.tsv`` holds electrode channels (Fz, Cz, EEG001
# ...), never engineered features.
_FEATURE_COLUMN_TOKENS: tuple[str, ...] = (
    "feat",
    "feature",
    "mean_",
    "std_",
    "var_",
    "rms_",
    "psd_",
    "bandpower",
    "band_power",
    "spectral_",
    "wavelet_",
    "csp_",
    "ica_comp",
    "embedding",
)


class BidsLayoutError(ValueError):
    """Raised when a BIDS-EEG layout is missing a fail-closed-required artifact."""


class InvalidUseError(ValueError):
    """Raised when the input is a leaked-label file or a precomputed feature table.

    The message always points at :data:`INVALID_USE_DOC` so an operator who trips
    this guard is told *why* and *where* the contract is documented, instead of
    receiving a silent or generic failure.
    """


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class BidsRecording:
    """A validated raw EEG recording loaded from a minimal BIDS-EEG layout."""

    subject: str
    task: str
    channels: tuple[str, ...]
    fs: float
    data: FloatArray
    source_path: str
    sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_samples(self) -> int:
        return int(self.data.shape[1])


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_text(path: Path) -> str:
    """Read a ``.tsv`` or ``.tsv.gz`` file as UTF-8 text."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return handle.read()
    return path.read_text(encoding="utf-8")


def _parse_tsv(text: str) -> tuple[list[str], list[list[str]]]:
    """Parse a TSV into (header, rows) with no pandas dependency."""
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        raise BidsLayoutError("EEG TSV is empty")
    header = lines[0].split("\t")
    rows = [ln.split("\t") for ln in lines[1:]]
    return header, rows


def _guard_columns(columns: list[str]) -> None:
    """Refuse leaked-label or feature-table inputs, fail-closed.

    A real raw BIDS-EEG ``_eeg.tsv`` holds electrode channels only. Any column
    that names a class label or an engineered feature means the file is not a raw
    recording and BSFF must not falsify it as if it were.
    """
    lowered = [c.strip().lower() for c in columns]

    leaked = sorted({c for c in lowered if c in _LABEL_COLUMN_NAMES})
    if leaked:
        raise InvalidUseError(
            "Refusing input: EEG data file carries label-like column(s) "
            f"{leaked}. BSFF falsifies the raw signal and must not read hidden "
            f"labels. See {INVALID_USE_DOC} (no-hidden-labels policy)."
        )

    featured = sorted({c for c in lowered if any(tok in c for tok in _FEATURE_COLUMN_TOKENS)})
    if featured:
        raise InvalidUseError(
            "Refusing input: EEG data file looks like a precomputed feature table "
            f"(feature-like column(s) {featured}). BSFF falsifies the raw signal, "
            f"not an already-engineered feature matrix. See {INVALID_USE_DOC} "
            "(no-feature-table-leakage policy)."
        )


def _find_one(directory: Path, pattern: str, what: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise BidsLayoutError(f"missing {what}: no file matching '{pattern}' in {directory}")
    if len(matches) > 1:
        raise BidsLayoutError(
            f"ambiguous {what}: {len(matches)} files match '{pattern}' in {directory}; "
            "pass an explicit task= to disambiguate"
        )
    return matches[0]


def load_bids_eeg(
    bids_dir: str | Path,
    *,
    subject: str,
    task: str | None = None,
) -> BidsRecording:
    """Load and fail-closed validate one recording from a minimal BIDS-EEG tree.

    Expected layout (``.tsv`` or ``.tsv.gz`` accepted for the data file)::

        <bids_dir>/sub-<subject>/eeg/
            sub-<subject>_task-<task>_eeg.tsv[.gz]   # raw channels x time
            sub-<subject>_task-<task>_eeg.json       # sidecar: SamplingFrequency
            sub-<subject>_task-<task>_channels.tsv   # channel names

    Validation is fail-closed: a missing sidecar, missing channels file, missing
    sampling rate, header/channel-count mismatch, leaked label column, feature
    table, or non-finite sample aborts the load. ``sha256`` is the digest of the
    raw data file for byte-level provenance.
    """
    bids_dir = Path(bids_dir)
    sub = subject if subject.startswith("sub-") else f"sub-{subject}"
    eeg_dir = bids_dir / sub / "eeg"
    if not eeg_dir.is_dir():
        raise BidsLayoutError(f"missing EEG directory for {sub}: {eeg_dir}")

    if task is None:
        # Discover the task from any *_eeg.json sidecar; refuse if ambiguous.
        sidecars = sorted(eeg_dir.glob(f"{sub}_task-*_eeg.json"))
        if not sidecars:
            raise BidsLayoutError(f"no *_eeg.json sidecar found in {eeg_dir}")
        if len(sidecars) > 1:
            raise BidsLayoutError(
                f"multiple tasks present in {eeg_dir}; pass an explicit task= "
                f"(found {[p.name for p in sidecars]})"
            )
        name = sidecars[0].name
        task = name[len(f"{sub}_task-") : -len("_eeg.json")]
    task_tag = task if task.startswith("task-") else f"task-{task}"
    task_name = task_tag[len("task-") :]

    stem = f"{sub}_{task_tag}"
    data_path = _find_one(eeg_dir, f"{stem}_eeg.tsv*", "EEG data file")
    sidecar_path = eeg_dir / f"{stem}_eeg.json"
    channels_path = eeg_dir / f"{stem}_channels.tsv"

    if not sidecar_path.is_file():
        raise BidsLayoutError(f"missing EEG sidecar: {sidecar_path}")
    if not channels_path.is_file():
        raise BidsLayoutError(f"missing channels file: {channels_path}")

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    fs = sidecar.get("SamplingFrequency")
    if fs is None:
        raise BidsLayoutError(f"sidecar {sidecar_path} is missing required 'SamplingFrequency'")
    fs = float(fs)
    if fs <= 0:
        raise BidsLayoutError(f"SamplingFrequency must be positive, got {fs}")

    chan_header, chan_rows = _parse_tsv(_open_text(channels_path))
    if "name" not in [c.strip().lower() for c in chan_header]:
        raise BidsLayoutError(
            f"channels file {channels_path} must have a 'name' column (BIDS-EEG required)"
        )
    name_idx = [c.strip().lower() for c in chan_header].index("name")
    declared_channels = tuple(row[name_idx] for row in chan_rows if row)
    if not declared_channels:
        raise BidsLayoutError(f"channels file {channels_path} declares no channels")

    data_header, data_rows = _parse_tsv(_open_text(data_path))
    # Fail-closed honesty guards: no hidden labels, no feature tables.
    _guard_columns(data_header)

    if list(data_header) != list(declared_channels):
        raise BidsLayoutError(
            f"channel mismatch: {data_path.name} header {list(data_header)} does not "
            f"match {channels_path.name} names {list(declared_channels)}"
        )

    try:
        matrix = np.array([[float(x) for x in row] for row in data_rows], dtype=float)
    except ValueError as exc:
        raise BidsLayoutError(
            f"non-numeric value in {data_path.name}; raw EEG must be numeric: {exc}"
        ) from exc
    if matrix.ndim != 2 or matrix.shape[1] != len(declared_channels):
        raise BidsLayoutError(
            f"data shape {matrix.shape} inconsistent with {len(declared_channels)} channels"
        )
    if matrix.shape[0] < 16:
        raise BidsLayoutError(
            f"too few samples ({matrix.shape[0]}); need >= 16 for a falsifiable claim"
        )
    if not np.all(np.isfinite(matrix)):
        raise BidsLayoutError("EEG data contains non-finite values (NaN/Inf); refuse to falsify")

    # Orient to (n_channels, n_samples): the TSV is row=time, column=channel.
    data = np.ascontiguousarray(matrix.T)

    return BidsRecording(
        subject=sub,
        task=task_name,
        channels=declared_channels,
        fs=fs,
        data=data,
        source_path=str(data_path),
        sha256=_sha256_file(data_path),
        metadata={
            "sidecar": {k: sidecar[k] for k in sorted(sidecar)},
            "channels_file": channels_path.name,
            "data_file": data_path.name,
        },
    )


def bids_to_claim(
    rec: BidsRecording,
    *,
    statistic: str = "lagged_quadratic",
    task_type: TaskType = "nonlinear_structure",
    surrogate_count: int = 19,
    alpha: float = 0.05,
    bayesian_evidence: bool = True,
) -> ClaimSpec:
    """Build a falsifiable :class:`ClaimSpec` from a validated BIDS recording.

    The claim binds the recording's true shape and sampling rate so the surrogate
    null and stationarity gate operate on the data as recorded. ``metadata`` keeps
    the source-file sha256 so the claim is reproducibly tied to its bytes.
    """
    claim_id = f"bids-{rec.subject}-task-{rec.task}"
    spec = ClaimSpec(
        claim_id=claim_id,
        signal_type="EEG",
        task_type=task_type,
        sampling_rate_hz=rec.fs,
        n_channels=rec.n_channels,
        n_samples=rec.n_samples,
        statistic=statistic,
        alpha=alpha,
        surrogate_count=surrogate_count,
        metadata={
            "source": "bids",
            "source_sha256": rec.sha256,
            "channels": list(rec.channels),
            "bayesian_evidence": bayesian_evidence,
        },
    )
    spec.validate()
    return spec


def _software_versions() -> dict[str, str]:
    """Best-effort software version manifest via importlib.metadata."""
    from importlib import metadata as importlib_metadata

    versions: dict[str, str] = {"bsff": __version__}
    for pkg in ("numpy", "scipy", "statsmodels"):
        try:
            versions[pkg] = importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:  # pragma: no cover - env dependent
            versions[pkg] = "absent"
    return versions


def run_bids_case(
    bids_dir: str | Path,
    *,
    subject: str,
    task: str | None = None,
    seed: int = 123,
    policy: str = "standard",
    statistic: str = "lagged_quadratic",
    task_type: TaskType = "nonlinear_structure",
    leakage_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load a BIDS recording, build the claim, falsify it, and stamp a manifest.

    Returns a dict with the machine-readable ``verdict`` plus a reproducibility
    ``manifest`` (input hashes, software versions, command, and the resolved
    claim). The verdict is produced by the *real* fail-closed engine
    (:func:`bsff.verdict_engine.evaluate_claim`); ``policy`` is recorded in the
    manifest for the orchestrator-wired CLI but does not alter the engine call.
    """
    rec = load_bids_eeg(bids_dir, subject=subject, task=task)
    spec = bids_to_claim(rec, statistic=statistic, task_type=task_type)
    verdict = evaluate_claim(spec, rec.data, leakage_flags=leakage_flags, seed=seed)

    command = (
        f"bsff bids-app --bids-dir {Path(bids_dir)} "
        f"--participant-label {rec.subject.removeprefix('sub-')} --task {rec.task}"
    )
    manifest: dict[str, Any] = {
        "schema": "bsff.bids_manifest/v1",
        "command": command,
        "policy": policy,
        "seed": seed,
        "subject": rec.subject,
        "task": rec.task,
        "inputs": {
            "bids_dir": str(Path(bids_dir)),
            "data_file": rec.source_path,
            "data_sha256": rec.sha256,
            "sampling_frequency": rec.fs,
            "channels": list(rec.channels),
        },
        "software_versions": _software_versions(),
        "claim": spec.to_dict(),
    }
    return {
        "verdict": verdict.to_dict(),
        "manifest": manifest,
    }
