# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""The Bonn provenance pin must be load-bearing, not decorative.

``DATASET_MANIFEST.json`` pins a per-file sha256 for every canonical segment, but
``load_set`` previously never checked staged data against it — a reviewer could
stage plausibly-shaped but different data and silently compute a different result.
These tests prove the fail-closed verification: matching data loads, tampered or
unlisted data raises, and a missing set in the manifest refuses to proceed.
"""

import hashlib

import numpy as np
import pytest
from loader import ManifestMismatchError, load_set


def _write_segment(path, values):
    np.savetxt(path, np.asarray(values, dtype=float).reshape(1, -1))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(tmp_path, set_label, n=3, n_samples=4097):
    set_dir = tmp_path / set_label
    set_dir.mkdir(parents=True)
    files = []
    rng = np.random.default_rng(0)
    for i in range(n):
        p = set_dir / f"S{i:03d}.txt"
        sha = _write_segment(p, rng.normal(size=n_samples))
        files.append((p, sha))
    return files


def _manifest_for(set_label, files):
    return {
        "sets": {
            set_label: {
                "n_files": len(files),
                "files": [
                    {"path": f"bonn_data/{set_label}/{p.name}", "sha256": sha, "n_samples": 4097}
                    for p, sha in files
                ],
            }
        }
    }


def test_matching_data_passes_verification(tmp_path):
    files = _stage(tmp_path, "E")
    manifest = _manifest_for("E", files)
    segments = load_set(tmp_path, "E", n_segments=3, manifest=manifest)
    assert len(segments) == 3


def test_tampered_file_is_rejected(tmp_path):
    files = _stage(tmp_path, "E")
    manifest = _manifest_for("E", files)
    # Overwrite one staged file with different bytes after pinning its hash.
    _write_segment(files[1][0], np.zeros(4097))
    with pytest.raises(ManifestMismatchError, match="sha256 mismatch"):
        load_set(tmp_path, "E", n_segments=3, manifest=manifest)


def test_unlisted_file_is_rejected(tmp_path):
    files = _stage(tmp_path, "E")
    # Manifest pins only the first two files; the third is staged but unlisted.
    manifest = _manifest_for("E", files[:2])
    with pytest.raises(ManifestMismatchError, match="not in DATASET_MANIFEST"):
        load_set(tmp_path, "E", n_segments=3, manifest=manifest)


def test_missing_set_in_manifest_fails_closed(tmp_path):
    files = _stage(tmp_path, "E")
    manifest = _manifest_for("A", files)  # wrong set label
    with pytest.raises(ManifestMismatchError, match="no pinned hashes for set"):
        load_set(tmp_path, "E", n_segments=3, manifest=manifest)


def test_no_manifest_keeps_legacy_behaviour(tmp_path):
    """Without a manifest, load_set still works (back-compatible) — but unverified."""
    _stage(tmp_path, "E")
    segments = load_set(tmp_path, "E", n_segments=3)
    assert len(segments) == 3


def test_committed_manifest_pins_real_segments():
    """The committed manifest must actually carry per-file sha256 pins to enforce."""
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (repo / "artifacts" / "bonn_bright_line" / "DATASET_MANIFEST.json").read_text()
    )
    for label in ("E", "A", "B"):
        files = manifest["sets"][label]["files"]
        assert files, f"manifest set {label} has no pinned files"
        assert all(len(f["sha256"]) == 64 for f in files)
