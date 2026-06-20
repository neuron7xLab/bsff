# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""EDF / EDF+ / BDF reader and writer — pure Python, zero dependencies.

The first thing a real EEG/BCI signal arrives in is almost always EDF (or its
BioSemi 24-bit cousin, BDF). This module reads that raw format byte-for-byte —
no ``mne``, no ``pyedflib``, nothing to pin or trust — and normalizes it to a
plain ``(n_channels, n_samples)`` physical-units array that BSFF's engines can
test. It is deliberately literal about the EDF specification: the header is
parsed field by documented field, digital samples are scaled to physical units
by each signal's own calibration, the EDF+ annotations channel is dropped, and
channels that do not share the dominant sampling rate are set aside with a
recorded reason rather than silently resampled.

A matching :func:`write_edf` exists so the reader can be validated by round trip
on a file of known content — read and write are each other's proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .validation import sha256_bytes

FloatArray = NDArray[np.float64]

_FIXED_HEADER = 256
_SIGNAL_HEADER = 256
_ANNOTATION_LABEL = "EDF Annotations"


@dataclass(frozen=True)
class NormalizedSignal:
    """A raw signal normalized to physical units, with provenance."""

    data: FloatArray  # (n_channels, n_samples)
    sample_rate_hz: float
    labels: list[str]
    source_format: str
    provenance: dict[str, Any]

    def to_provenance(self) -> dict[str, Any]:
        return {
            "source_format": self.source_format,
            "sample_rate_hz": self.sample_rate_hz,
            "n_channels": int(self.data.shape[0]),
            "n_samples": int(self.data.shape[1]),
            "labels": self.labels,
            **self.provenance,
        }


def _ascii(raw: bytes) -> str:
    return raw.decode("ascii", errors="replace").strip()


def _read_int(raw: bytes, field: str) -> int:
    text = _ascii(raw)
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"EDF header field {field!r} is not an integer: {text!r}") from exc


def _read_floats(buf: bytes, count: int, width: int, field: str) -> list[float]:
    out: list[float] = []
    for i in range(count):
        chunk = _ascii(buf[i * width : (i + 1) * width])
        try:
            out.append(float(chunk))
        except ValueError as exc:
            raise ValueError(f"EDF field {field!r}[{i}] not a number: {chunk!r}") from exc
    return out


def read_edf(path: str | Path) -> NormalizedSignal:
    """Read an EDF / EDF+ / BDF file into a :class:`NormalizedSignal` (fail-closed)."""
    p = Path(path)
    raw = p.read_bytes()
    if len(raw) < _FIXED_HEADER:
        raise ValueError("file shorter than an EDF fixed header; not an EDF/BDF file")

    is_bdf = raw[0] == 0xFF
    bytes_per_sample = 3 if is_bdf else 2
    fmt = "BDF" if is_bdf else "EDF"

    ns = _read_int(raw[252:256], "num_signals")
    if ns < 1:
        raise ValueError(f"EDF declares {ns} signals; refuse to read")
    expected_header = _FIXED_HEADER + ns * _SIGNAL_HEADER
    if len(raw) < expected_header:
        raise ValueError("file truncated inside the signal headers; not a valid EDF/BDF")

    num_records = _read_int(raw[236:244], "num_data_records")
    duration = float(_ascii(raw[244:252]))
    if duration <= 0:
        raise ValueError(f"EDF data-record duration must be positive, got {duration}")

    # Per-signal header blocks (each field repeated ns times, in order). Read the
    # label block, then advance a cursor past the remaining fixed-width blocks.
    cur = _FIXED_HEADER
    label_buf = raw[cur : cur + 16 * ns]
    labels = [_ascii(label_buf[i * 16 : (i + 1) * 16]) for i in range(ns)]
    cur += 16 * ns
    cur += 80 * ns  # transducer
    cur += 8 * ns  # physical dimension
    phys_min = _read_floats(raw[cur : cur + 8 * ns], ns, 8, "physical_min")
    cur += 8 * ns
    phys_max = _read_floats(raw[cur : cur + 8 * ns], ns, 8, "physical_max")
    cur += 8 * ns
    dig_min = _read_floats(raw[cur : cur + 8 * ns], ns, 8, "digital_min")
    cur += 8 * ns
    dig_max = _read_floats(raw[cur : cur + 8 * ns], ns, 8, "digital_max")
    cur += 8 * ns
    cur += 80 * ns  # prefiltering
    samples_per_record = [
        _read_int(raw[cur + i * 8 : cur + (i + 1) * 8], f"samples_per_record[{i}]")
        for i in range(ns)
    ]
    cur += 8 * ns
    cur += 32 * ns  # reserved
    data_start = cur  # == expected_header

    record_samples = int(sum(samples_per_record))
    if record_samples <= 0:
        raise ValueError("EDF declares zero samples per data record")
    data_bytes = raw[data_start:]
    available_records = len(data_bytes) // (record_samples * bytes_per_sample)
    if num_records < 0:  # spec allows -1 (unknown) -> infer from file length
        num_records = available_records
    num_records = min(num_records, available_records)
    if num_records < 1:
        raise ValueError("EDF contains no complete data records")

    # Decode every digital sample into one flat int array, record by record.
    usable = data_bytes[: num_records * record_samples * bytes_per_sample]
    if is_bdf:
        triplets = np.frombuffer(usable, dtype=np.uint8).reshape(-1, 3).astype(np.int64)
        digital = triplets[:, 0] | (triplets[:, 1] << 8) | (triplets[:, 2] << 16)
        digital = np.where(digital >= 0x800000, digital - 0x1000000, digital)
    else:
        digital = np.frombuffer(usable, dtype="<i2").astype(np.int64)
    digital = digital.reshape(num_records, record_samples)

    # Split each record into its per-signal segments and scale to physical units.
    offsets = np.cumsum([0, *samples_per_record])
    channels: list[FloatArray] = []
    rates: list[float] = []
    kept_labels: list[str] = []
    dropped: list[dict[str, Any]] = []
    for i in range(ns):
        if labels[i] == _ANNOTATION_LABEL:
            dropped.append({"label": labels[i], "reason": "EDF+ annotations channel"})
            continue
        seg = digital[:, offsets[i] : offsets[i + 1]].reshape(-1).astype(float)
        span_dig = dig_max[i] - dig_min[i]
        span_phys = phys_max[i] - phys_min[i]
        if span_dig == 0:
            dropped.append({"label": labels[i], "reason": "degenerate digital range"})
            continue
        physical = phys_min[i] + (seg - dig_min[i]) * (span_phys / span_dig)
        channels.append(physical)
        rates.append(samples_per_record[i] / duration)
        kept_labels.append(labels[i])

    if not channels:
        raise ValueError("no usable signal channels in EDF (only annotations/degenerate)")

    # Keep the channels sharing the dominant sampling rate; set the rest aside.
    rate_values, counts = np.unique(np.round(rates, 6), return_counts=True)
    dominant = float(rate_values[int(np.argmax(counts))])
    final: list[FloatArray] = []
    final_labels: list[str] = []
    for ch, rate, lab in zip(channels, rates, kept_labels, strict=False):
        if round(rate, 6) == dominant:
            final.append(ch)
            final_labels.append(lab)
        else:
            dropped.append({"label": lab, "reason": f"sample rate {rate} != dominant {dominant}"})

    width = min(c.size for c in final)
    data = np.vstack([c[:width] for c in final])

    return NormalizedSignal(
        data=data,
        sample_rate_hz=dominant,
        labels=final_labels,
        source_format=fmt,
        provenance={
            "sha256": sha256_bytes(raw),
            "num_records": int(num_records),
            "record_duration_sec": duration,
            "dropped_channels": dropped,
        },
    )


def write_edf(
    path: str | Path,
    data: FloatArray,
    *,
    sample_rate_hz: float,
    labels: list[str] | None = None,
    record_duration_sec: float = 1.0,
    bdf: bool = False,
) -> None:
    """Write a minimal valid EDF (16-bit) or BDF (24-bit) for fixtures + round trip."""
    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data[np.newaxis, :]
    n_ch, n_samp = data.shape
    samples_per_record = round(sample_rate_hz * record_duration_sec)
    if samples_per_record < 1:
        raise ValueError("sample_rate_hz * record_duration_sec must be >= 1 sample")
    num_records = n_samp // samples_per_record
    if num_records < 1:
        raise ValueError("signal too short for one full data record")
    usable = num_records * samples_per_record
    data = data[:, :usable]
    labels = labels or [f"ch{i}" for i in range(n_ch)]

    def fld(value: object, width: int) -> bytes:
        return f"{value}".ljust(width)[:width].encode("ascii", errors="replace")

    version = b"\xffBIOSEMI" if bdf else fld("0", 8)
    reserved = fld("24BIT", 44) if bdf else fld("EDF+C", 44)
    header = b"".join(
        [
            version,
            fld("fixture", 80),
            fld("bsff round-trip", 80),
            fld("01.01.00", 8),
            fld("00.00.00", 8),
            fld(_FIXED_HEADER + n_ch * _SIGNAL_HEADER, 8),
            reserved,
            fld(num_records, 8),
            fld(_fmt_num(record_duration_sec), 8),
            fld(n_ch, 4),
        ]
    )
    dig_min, dig_max = (-8388608, 8388607) if bdf else (-32768, 32767)
    phys_min = [float(data[i].min()) for i in range(n_ch)]
    phys_max = [float(data[i].max()) for i in range(n_ch)]
    # Avoid a zero physical span (flat channel) which is non-invertible.
    phys_max = [
        pmax if pmax > pmin else pmin + 1.0 for pmin, pmax in zip(phys_min, phys_max, strict=False)
    ]

    sig_header = b"".join(
        [
            b"".join(fld(lab, 16) for lab in labels),
            b"".join(fld("", 80) for _ in range(n_ch)),
            b"".join(fld("uV", 8) for _ in range(n_ch)),
            b"".join(fld(_fmt_num(v), 8) for v in phys_min),
            b"".join(fld(_fmt_num(v), 8) for v in phys_max),
            b"".join(fld(dig_min, 8) for _ in range(n_ch)),
            b"".join(fld(dig_max, 8) for _ in range(n_ch)),
            b"".join(fld("", 80) for _ in range(n_ch)),
            b"".join(fld(samples_per_record, 8) for _ in range(n_ch)),
            b"".join(fld("", 32) for _ in range(n_ch)),
        ]
    )

    # Quantize physical -> digital and lay out record by record.
    records = bytearray()
    for r in range(num_records):
        for i in range(n_ch):
            seg = data[i, r * samples_per_record : (r + 1) * samples_per_record]
            span_phys = phys_max[i] - phys_min[i]
            digital = np.round(
                (seg - phys_min[i]) * ((dig_max - dig_min) / span_phys) + dig_min
            ).astype(np.int64)
            digital = np.clip(digital, dig_min, dig_max)
            if bdf:
                u = np.where(digital < 0, digital + 0x1000000, digital).astype(np.uint32)
                triplet = np.empty((u.size, 3), dtype=np.uint8)
                triplet[:, 0] = u & 0xFF
                triplet[:, 1] = (u >> 8) & 0xFF
                triplet[:, 2] = (u >> 16) & 0xFF
                records += triplet.tobytes()
            else:
                records += digital.astype("<i2").tobytes()

    Path(path).write_bytes(header + sig_header + bytes(records))


def _fmt_num(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"
