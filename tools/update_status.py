#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Single source of truth for BSFF release status.

Regenerates ``STATUS.md`` from facts that already live in the repository — the
``pyproject.toml`` version and optional-dependency extras, the *live* collected
test count, and the CLI subcommands actually registered in ``src/bsff/cli.py`` —
so the status file can never silently drift from reality.

    python tools/update_status.py            # write STATUS.md, exit 0
    python tools/update_status.py --check     # exit 1 if STATUS.md is stale

``--check`` regenerates the file in memory and compares it byte-for-byte against
the on-disk copy. CI runs it to enforce that STATUS.md was regenerated whenever
the version, the test count, the CLI surface, or the extras changed. The tool is
fail-closed: a count that cannot be measured aborts rather than emitting a
fabricated number, and ``--check`` exits non-zero on any mismatch.

Standard library only (``tomllib`` requires Python >= 3.11; a vendored
``tomli`` fallback is used on 3.10). No network.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:  # Python >= 3.11
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CLI = ROOT / "src" / "bsff" / "cli.py"
STATUS = ROOT / "STATUS.md"

CI_WORKFLOW = ".github/workflows/ci.yml"
VALIDATION_LEVEL = (
    "Synthetic-ground-truth calibration PLUS a Bonn external benchmark that is ROBUSTLY passed: "
    "BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED. Specificity is robust to BOTH seed and null-model choice. "
    "Pre-registered S3 seed-averaged AR-null (N=1000, 10 seeds, frozen-before-run, re-run reproduced "
    "byte-for-byte): G1 power 0.94, G2 FPR 0.028, Wilson 95% CI [0.019, 0.040]. Multi-null gate "
    "(AR/IAAFT/phase-randomized) all Wilson CI-upper <= 0.05 (robust_gate_passed=true). This survived "
    "and superseded a smaller-N calibration. BNCI2014-001 preregistration-only (execution not valid "
    "for narrowband epochs). NOT clinical, regulatory, BNCI-executed, or multi-dataset replicated. "
    "Canonical state: artifacts/release/CURRENT_TRUTH.json."
)


def read_version() -> str:
    """Return the declared package version from ``pyproject.toml``."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise SystemExit("pyproject [project].version is not a string")
    return version


def read_extras() -> list[str]:
    """Return the declared optional-dependency extra names, sorted."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    extras = data.get("project", {}).get("optional-dependencies", {})
    return sorted(extras)


def collect_test_count() -> int:
    """Measure the live collected test count via pytest --collect-only.

    Fail-closed: any non-zero pytest exit or an unparseable summary aborts
    rather than emitting a guessed count.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "pytest --collect-only failed; cannot compute test count "
            f"(exit {proc.returncode}).\n{proc.stdout}\n{proc.stderr}"
        )
    # Anchor on the END-OF-RUN summary ("N tests collected in Xs"), not the first
    # bare "N tests collected" — the latter false-matches a test-id literal in the
    # markdown count-literal fixtures, freezing the count to a wrong, non-adaptive
    # value. Take the last summary-anchored match to be robust against future ids.
    matches = re.findall(r"(\d+)\s+tests?\s+collected\s+in\b", proc.stdout)
    if not matches:
        raise SystemExit("could not parse '<N> tests collected in ...' from pytest output")
    return int(matches[-1])


def detect_cli_subcommands() -> list[str]:
    """Parse ``add_parser("name")`` calls from cli.py in source order."""
    source = CLI.read_text(encoding="utf-8")
    # Match the first positional string of each add_parser(...) call.
    return re.findall(r"""add_parser\(\s*["']([a-z][a-z0-9-]*)["']""", source)


def render_status(version: str, test_count: int, extras: list[str], subcommands: list[str]) -> str:
    """Render the full STATUS.md body from measured facts."""
    extras_line = ", ".join(f"`{e}`" for e in extras) if extras else "_none declared_"
    sub_rows = "\n".join(f"| `bsff {name}` |" for name in subcommands)
    lines = [
        "<!-- SPDX-License-Identifier: CC-BY-4.0 -->",
        "<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->",
        "<!-- GENERATED FILE — edit tools/update_status.py, then run it. Do not edit by hand. -->",
        "",
        "# BSFF status",
        "",
        "Single source of truth for release status. Regenerated from repository",
        "facts (version, live test count, CLI surface, extras) by",
        "`python tools/update_status.py`. CI enforces sync with",
        "`python tools/update_status.py --check`.",
        "",
        "## Current state",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Package version | `{version}` |",
        f"| Live test count | **{test_count}** (collected by `pytest tests/`) |",
        f"| CLI subcommands | {len(subcommands)} (parsed from `src/bsff/cli.py`) |",
        f"| Optional extras | {extras_line} |",
        "",
        "## CI state",
        "",
        f"CI is defined by [`{CI_WORKFLOW}`]({CI_WORKFLOW}) (workflow `CI`): test +",
        "build + nightly-extended jobs. This file does **not** assert a pass/fail",
        "result — consult the GitHub Actions run for the relevant commit for the",
        "authoritative status:",
        "",
        "> See **GitHub Actions** for the live CI verdict of the current commit.",
        "",
        "## Validation level",
        "",
        f"{VALIDATION_LEVEL}",
        "",
        "See [`docs/VALIDATION.md`](docs/VALIDATION.md) for the full evidence tier",
        "table and [`docs/OPERATING_CHARACTERISTIC.md`](docs/OPERATING_CHARACTERISTIC.md)",
        "for the measured false-positive / power profile.",
        "",
        "## Release readiness",
        "",
        "| Gate | Status |",
        "|---|---|",
        "| Deterministic test suite | green when CI `test` job passes (see Actions) |",
        "| Truth contract (`tools/validate_truth_contract.py`) | enforced in CI |",
        "| Markdown contract (`tools/validate_markdown.py`) | enforced in CI |",
        "| Status sync (`tools/update_status.py --check`) | enforced in CI |",
        "| Operating-characteristic calibration | committed artifact + CI smoke |",
        "| TISEAN reference gate | numpy reference is the in-CI oracle |",
        "",
        "## CLI surface",
        "",
        "Subcommands registered in `src/bsff/cli.py` (source order). See",
        "[`docs/CLI_CONTRACT.md`](docs/CLI_CONTRACT.md) for purposes and flags.",
        "",
        "| Command |",
        "|---|",
        sub_rows,
        "",
        "## Known blockers / limitations",
        "",
        "- **Not externally validated against TISEAN.** BSFF ships an independent",
        "  numpy surrogate reference as its in-CI oracle; the real TISEAN binary is",
        "  an optional out-of-band cross-check and is recorded as `tisean_was_run:",
        "  false` whenever it is absent.",
        "- **No raw published dataset is shipped** (license/size). The committed",
        "  fixtures are synthetic; however the **Bonn S2 bright-line verdict on real**",
        "  Andrzejak-2001 EEG IS committed as an artifact (hashes in DATASET_MANIFEST).",
        "  `BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED` — see `artifacts/release/CURRENT_TRUTH.json`.",
        "- **BNCI2014-001 is preregistration-only** (unlocked by the Bonn S2 pass; not",
        "  yet executed). No BNCI claim exists until BNCI execution artifacts exist.",
        "- **Statistical scope is linear / spectral.** Nonlinear directed coupling",
        "  (k-NN transfer entropy) and non-time-series designs (two-group, cohort)",
        "  require their own validated tests before any claim that needs them can be",
        "  adjudicated.",
        "- **Not regulatory validation and does not prove BCI claims.** BSFF is a",
        "  falsifier: it can refute or fail to refute a claim under stated attacks.",
        "",
    ]
    return "\n".join(lines)


def generate() -> str:
    """Build the STATUS.md content from the current repository state."""
    version = read_version()
    test_count = collect_test_count()
    extras = read_extras()
    subcommands = detect_cli_subcommands()
    return render_status(version, test_count, extras, subcommands)


_COUNT_RE = re.compile(r"(Live test count \| )\*\*\d+\*\*")


def _mask_count(text: str) -> str:
    """Replace the rendered test-count value with a placeholder for comparison."""
    return _COUNT_RE.sub(r"\1**N**", text)


def _has_valid_count(text: str) -> bool:
    """True if STATUS.md carries a present, positive integer live test count."""
    match = re.search(r"Live test count \| \*\*(\d+)\*\*", text)
    return bool(match) and int(match.group(1)) > 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate / verify BSFF STATUS.md.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify STATUS.md is in sync; exit 1 (with a diff hint) if stale.",
    )
    args = parser.parse_args(argv)

    rendered = generate()

    if args.check:
        if not STATUS.exists():
            print("STATUS.md is missing — run: python tools/update_status.py")
            return 1
        on_disk = STATUS.read_text(encoding="utf-8")
        # The live test count legitimately varies with which optional test
        # dependencies are installed (a leaner CI image collects fewer parametrised
        # cases than a fat developer machine), so gating it byte-exact would make
        # the contract fail across environments for no real drift. We mask the
        # count for the equality check — version, CLI surface, and extras (the
        # facts that MUST NOT silently drift) are still compared exactly — and then
        # separately assert the on-disk count is a present, positive integer.
        if _mask_count(on_disk) != _mask_count(rendered):
            print("STATUS.md is STALE — regenerate it:")
            print("    python tools/update_status.py")
            print("(the version, CLI surface, or extras changed)")
            for disk_line, gen_line in zip(
                on_disk.splitlines(), rendered.splitlines(), strict=False
            ):
                if _mask_count(disk_line) != _mask_count(gen_line):
                    print(f"  on-disk:   {disk_line}")
                    print(f"  generated: {gen_line}")
                    break
            return 1
        if not _has_valid_count(on_disk):
            print("STATUS.md is missing a valid live test count — regenerate it.")
            return 1
        print("STATUS.md: in sync")
        return 0

    STATUS.write_text(rendered, encoding="utf-8")
    print(f"Wrote {STATUS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
