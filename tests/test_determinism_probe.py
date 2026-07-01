# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Tests for the byte-determinism probe.

Guarantees exercised:

  * positive: the real registered generators are byte-deterministic, the probe
    reports ``PASS``, and it leaves the working tree untouched;
  * negative control (nondeterminism): a "generator" that writes the current
    wall-clock time is flagged nondeterministic;
  * negative control (staleness): a deterministic generator whose committed bytes
    drift from a fresh regeneration is flagged stale;
  * negative control (hermeticity / Hole 4): a generator that writes an undeclared
    sibling file is flagged ``impure`` and the stray write is restored.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import determinism_probe as dp  # noqa: E402


def _git_status_lines(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_registry_is_nonempty_and_well_formed() -> None:
    assert dp.REGISTRY, "determinism registry must not be empty"
    for gen in dp.REGISTRY:
        assert gen.argv, f"{gen.name}: empty argv"
        assert gen.outputs, f"{gen.name}: no committed outputs declared"
        for rel in gen.outputs:
            assert (ROOT / rel).is_file(), f"{gen.name}: missing committed output {rel}"


@pytest.mark.slow
def test_evaluate_pass_and_tree_unchanged() -> None:
    """Real generators are deterministic, hermetic, and the probe does not dirty
    the tree. Marked ``slow``: it spawns every registered generator twice (one of
    them, the analytic-uniformity null, runs for minutes)."""
    tracked_before = {rel: (ROOT / rel).read_bytes() for gen in dp.REGISTRY for rel in gen.outputs}
    status_before = _git_status_lines(ROOT)

    report = dp.evaluate(ROOT)

    assert report["schema"] == "bsff.determinism/v1"
    assert report["status"] == "PASS", report
    assert report["nondeterministic"] == []
    assert report["stale"] == []
    assert report["impure"] == []
    assert len(report["checked"]) == len(dp.REGISTRY)
    for entry in report["checked"]:
        assert entry["deterministic"] is True, entry
        assert entry["side_effects"] == [], entry

    # Every probed artifact must be byte-identical to what we started with.
    for rel, original in tracked_before.items():
        assert (ROOT / rel).read_bytes() == original, f"probe left {rel} modified"

    # And git must see no new changes attributable to the probe.
    assert _git_status_lines(ROOT) == status_before


def test_negative_control_flags_nondeterministic_generator(tmp_path: Path) -> None:
    """A generator that writes the current time is flagged nondeterministic."""
    gen_script = tmp_path / "flaky_gen.py"
    gen_script.write_text(
        "import time\n"
        "from pathlib import Path\n"
        "# Nondeterministic on purpose: high-resolution wall clock.\n"
        "Path('out.txt').write_text(str(time.time_ns()))\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.txt"
    out.write_text("committed-placeholder", encoding="utf-8")
    original_bytes = out.read_bytes()

    flaky = dp.Generator(
        name="flaky_time_writer",
        argv=("flaky_gen.py",),
        outputs=("out.txt",),
    )

    report = dp.evaluate(tmp_path, registry=(flaky,))

    assert report["status"] == "FAIL", report
    assert report["nondeterministic"] == ["flaky_time_writer"]
    (entry,) = report["checked"]
    assert entry["deterministic"] is False
    assert "run-twice bytes differ" in entry["reason"]

    # The probe must still have restored the committed bytes of the temp output.
    assert out.read_bytes() == original_bytes


def test_deterministic_temp_generator_passes(tmp_path: Path) -> None:
    """Control's control: a fixed-output generator is reported deterministic."""
    gen_script = tmp_path / "fixed_gen.py"
    gen_script.write_text(
        "from pathlib import Path\nPath('out.txt').write_text('always-the-same')\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.txt"
    # Committed bytes MUST match the regeneration for a clean PASS (fresh + det.).
    out.write_text("always-the-same", encoding="utf-8")
    original_bytes = out.read_bytes()

    fixed = dp.Generator(
        name="fixed_writer",
        argv=("fixed_gen.py",),
        outputs=("out.txt",),
    )

    report = dp.evaluate(tmp_path, registry=(fixed,))

    assert report["status"] == "PASS", report
    assert report["nondeterministic"] == []
    assert report["stale"] == []
    assert report["impure"] == []
    (entry,) = report["checked"]
    assert entry["deterministic"] is True
    assert entry["committed_match"] is True
    assert entry["side_effects"] == []  # hermetic: only the declared output written
    assert out.read_bytes() == original_bytes


def test_stale_committed_artifact_is_flagged(tmp_path: Path) -> None:
    """A deterministic generator whose committed bytes differ from regeneration
    is STALE (drift) and must FAIL — a byte-reproducible artifact that no longer
    reflects its source is still a broken proof. Negative control for the stale
    dimension."""
    gen_script = tmp_path / "fixed_gen.py"
    gen_script.write_text(
        "from pathlib import Path\nPath('out.txt').write_text('regenerated')\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.txt"
    out.write_text("STALE-committed-value", encoding="utf-8")  # != regeneration
    original_bytes = out.read_bytes()

    gen = dp.Generator(name="stale_writer", argv=("fixed_gen.py",), outputs=("out.txt",))
    report = dp.evaluate(tmp_path, registry=(gen,))

    assert report["status"] == "FAIL", report
    assert report["nondeterministic"] == []
    assert report["stale"] == ["stale_writer"]
    assert out.read_bytes() == original_bytes  # tree restored


def test_failing_generator_is_flagged(tmp_path: Path) -> None:
    """A generator that errors out is treated as nondeterministic (fail-closed)."""
    gen_script = tmp_path / "boom.py"
    gen_script.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    out.write_text("committed", encoding="utf-8")

    boom = dp.Generator(name="boom", argv=("boom.py",), outputs=("out.txt",))
    report = dp.evaluate(tmp_path, registry=(boom,))

    assert report["status"] == "FAIL", report
    assert report["nondeterministic"] == ["boom"]
    (entry,) = report["checked"]
    assert entry["deterministic"] is False
    assert "exited 3" in entry["reason"]
    assert out.read_bytes() == b"committed"


def test_negative_control_flags_undeclared_sibling_write(tmp_path: Path) -> None:
    """Hole 4 negative control. A generator that writes its declared output
    deterministically but ALSO writes to an *undeclared* sibling is not hermetic:
    it is flagged ``impure`` (a FAIL) and the stray sibling is restored, leaving
    the tree clean. The declared output is deliberately deterministic AND fresh so
    the ONLY defect is the undeclared write — proving side-effect detection, not
    some other dimension, is what fails it."""
    gen_script = tmp_path / "leaky_gen.py"
    gen_script.write_text(
        "import random\n"
        "from pathlib import Path\n"
        "# Declared output: deterministic constant.\n"
        "Path('out.txt').write_text('always-the-same')\n"
        "# Undeclared sibling: nondeterministic AND outside the declared outputs.\n"
        "Path('sibling.txt').write_text(str(random.random()))\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.txt"
    out.write_text("always-the-same", encoding="utf-8")  # committed == regeneration
    original_bytes = out.read_bytes()
    sibling = tmp_path / "sibling.txt"
    assert not sibling.exists()

    leaky = dp.Generator(name="leaky_writer", argv=("leaky_gen.py",), outputs=("out.txt",))
    report = dp.evaluate(tmp_path, registry=(leaky,))

    assert report["status"] == "FAIL", report
    assert report["impure"] == ["leaky_writer"]
    assert report["nondeterministic"] == []
    assert report["stale"] == []
    (entry,) = report["checked"]
    assert entry["deterministic"] is True  # the declared output is deterministic
    assert entry["side_effects"] == ["sibling.txt"]
    assert "not hermetic" in entry["reason"]

    # Tree hygiene: the stray sibling is removed and the declared output restored.
    assert not sibling.exists(), "probe left the undeclared sibling write behind"
    assert out.read_bytes() == original_bytes


def test_missing_output_raises(tmp_path: Path) -> None:
    """Snapshotting a nonexistent committed artifact fails loudly."""
    gen_script = tmp_path / "noop.py"
    gen_script.write_text("pass\n", encoding="utf-8")
    missing = dp.Generator(name="missing", argv=("noop.py",), outputs=("nope.txt",))
    with pytest.raises(FileNotFoundError):
        dp.evaluate(tmp_path, registry=(missing,))
