# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Mutation-kill gate: prove the adversarial oracle suite has teeth.

A green test suite is meaningless unless it *kills* regressions. This gate copies
the repository into a throwaway directory, applies each of four single-point
behavioural mutants to the verdict-collapse path, and runs a targeted adversarial
test against the mutated tree. A mutant is ``killed`` only if those tests FAIL. A
surviving mutant is a hole in the suite, so the gate exits non-zero.

The mutated tree is fully isolated from the working tree (a temp copy whose ``src``
shadows the editable install via ``PYTHONPATH``), so a crash can never leave the
real source patched — unlike a mutate-in-place/restore scheme.

    python tools/mutation_kill_gate.py [--output PATH] [--keep]

Mutants (each targets one fail-closed behaviour the pipeline must preserve):

  MUT-001  remove convergence demotion      -> a nonconverged null must be UNSUPPORTED
  MUT-002  disable leakage fatality          -> flagged leakage must REFUTE
  MUT-003  weaken Bayesian corroboration     -> uncorroborated rejection must not promote
  MUT-004  invert rank-order p-value         -> p<=alpha rejects; the inequality must hold
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OC = "tests/test_adversarial_operating_characteristics.py"

# Directories that must never be copied into the mutation sandbox: VCS state,
# virtualenvs, build outputs, caches, and large committed artifacts. Excluding
# them keeps the copy fast and the sandbox import path clean.
_IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "venv",
    "artifacts",
    "dist",
    "build",
    "*.egg-info",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".benchmarks",
    ".mypy_cache",
    "node_modules",
    "uv.lock",
)


@dataclass(frozen=True)
class Mutant:
    mutant_id: str
    rel_path: str
    old: str
    new: str
    behaviour: str
    targets: tuple[str, ...]


PROP_SIGNAL = "tests/property/test_signal_validation_properties.py"
SCHEMA = "tests/test_claimspec_schema.py"

MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        mutant_id="MUT-001",
        rel_path="src/bsff/pipeline.py",
        old='        if convergence and not bool(convergence.get("all_converged", True)):',
        new='        if False and convergence and not bool(convergence.get("all_converged", True)):',
        behaviour="a nonconverged surrogate null must demote the verdict to UNSUPPORTED",
        targets=(f"{OC}::test_nonconverged_null_cannot_exceed_unsupported",),
    ),
    Mutant(
        mutant_id="MUT-002",
        rel_path="src/bsff/stages.py",
        old='        flagged = any(bool(v.get("flagged")) for v in flags.values() if isinstance(v, dict))',
        new="        flagged = False  # MUT-002: leakage fatality disabled",
        behaviour="flagged leakage must short-circuit claim promotion to REFUTED",
        targets=(f"{OC}::test_leakage_short_circuits_to_refuted",),
    ),
    Mutant(
        mutant_id="MUT-003",
        rel_path="src/bsff/stages.py",
        old='        fatal = context.policy.stationarity_mode == "fail_closed"',
        new="        fatal = False  # MUT-003: stationarity fatality disabled",
        behaviour="a nonstationary signal under fail_closed must REFUTE before surrogates",
        targets=(f"{OC}::test_nonstationary_random_walk_fails_strict_gate_fatally",),
    ),
    Mutant(
        mutant_id="MUT-004",
        rel_path="src/bsff/surrogate_engine.py",
        old="    rejected = bool(p_value <= alpha)",
        new="    rejected = bool(p_value >= alpha)  # MUT-004: inverted p-value inequality",
        behaviour="rank-order rejection requires p_value <= alpha (correct one-sided semantics)",
        targets=(f"{OC}::test_nonlinear_positive_control_survives_with_exposed_evidence",),
    ),
    Mutant(
        mutant_id="MUT-005",
        rel_path="src/bsff/pipeline.py",
        old="                context.policy.bayesian_corroboration_min",
        new="                0.0  # MUT-005: corroboration threshold neutralised",
        behaviour="an uncorroborated frequentist rejection (BF10 < threshold) must not promote",
        targets=(
            f"{OC}::test_linear_null_never_survives_under_strict",
            f"{OC}::test_linear_null_false_positive_rate_within_binomial_guard",
        ),
    ),
    Mutant(
        mutant_id="MUT-006",
        rel_path="src/bsff/surrogate_engine.py",
        old="    if not np.all(np.isfinite(arr)):",
        new="    if False and not np.all(np.isfinite(arr)):  # MUT-006: NaN/Inf gate disabled",
        behaviour="NaN/Inf input must be refused before any statistic is computed",
        targets=(f"{PROP_SIGNAL}::test_p1_nonfinite_never_reaches_verdict",),
    ),
    Mutant(
        mutant_id="MUT-007",
        rel_path="src/bsff/pipeline.py",
        old="            contract_sha256=stable_sha256(contract),",
        new='            contract_sha256="",  # MUT-007: evidence contract hash removed',
        behaviour="every verdict must carry a 64-hex evidence contract hash",
        targets=(f"{OC}::test_nonlinear_positive_control_survives_with_exposed_evidence",),
    ),
    Mutant(
        mutant_id="MUT-008",
        rel_path="src/bsff/schemas.py",
        old="        if self.surrogate_count < minimum:",
        new="        if False and self.surrogate_count < minimum:  # MUT-008: schema drift accepted",
        behaviour="ClaimSpec must reject an underpowered surrogate_count (no silent schema drift)",
        targets=(f"{SCHEMA}::test_claimspec_rejects_too_few_surrogates",),
    ),
    Mutant(
        mutant_id="MUT-009",
        rel_path="src/bsff/surrogate_engine.py",
        old="    exceed = int(np.sum(surrogate_stats_arr >= original_stat))",
        new="    exceed = int(np.sum(surrogate_stats_arr > original_stat))  # MUT-009: tie semantics",
        behaviour="rank-order ties must count as not-exceeded, so a flat signal is never rejected",
        targets=(f"{OC}::test_degenerate_signal_not_falsely_rejected",),
    ),
)


def _pytest(sandbox: Path, targets: tuple[str, ...]) -> tuple[int, str]:
    """Run targeted tests inside the sandbox; sandbox src shadows the editable install."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(sandbox / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider"],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def run(output: Path, keep: bool = False) -> int:
    sandbox = Path(tempfile.mkdtemp(prefix="bsff-mutation-"))
    commands: list[str] = []
    try:
        shutil.copytree(ROOT, sandbox, dirs_exist_ok=True, ignore=_IGNORE)

        # Baseline guard: the targeted tests must be GREEN on the unmutated sandbox,
        # otherwise a "killed" verdict would be indistinguishable from a flaky test.
        baseline_targets = tuple(t for m in MUTANTS for t in m.targets)
        commands.append("pytest " + " ".join(baseline_targets))
        code, log = _pytest(sandbox, baseline_targets)
        if code != 0:
            print("BASELINE NOT GREEN — mutation results would be meaningless.\n")
            print(log[-3000:])
            return 2

        results = []
        for m in MUTANTS:
            target = sandbox / m.rel_path
            original = target.read_text(encoding="utf-8")
            if m.old not in original:
                print(f"[ERROR] {m.mutant_id}: anchor not found in {m.rel_path}")
                return 2
            mutated = original.replace(m.old, m.new, 1)
            if mutated == original:
                print(f"[ERROR] {m.mutant_id}: mutation was a no-op")
                return 2
            commands.append("pytest " + " ".join(m.targets))
            try:
                target.write_text(mutated, encoding="utf-8")
                code, _log = _pytest(sandbox, m.targets)
            finally:
                target.write_text(original, encoding="utf-8")
            # A genuine kill is an ASSERTION firing (pytest exit 1 = tests ran and
            # failed/errored), NOT the mutant breaking collection (exit 2), a missing
            # target (4/5), or an internal error (3). Counting a collection-break as
            # "killed" would let the mutation score LIE about the suite's real teeth.
            if code not in (0, 1):
                print(
                    f"[ERROR] {m.mutant_id}: pytest exit {code} is a non-behavioral failure "
                    "(broken collection / missing target), not a clean kill"
                )
                return 2
            killed = code == 1
            results.append(
                {
                    "mutant_id": m.mutant_id,
                    "file": m.rel_path,
                    "behaviour": m.behaviour,
                    "targets": list(m.targets),
                    "mutant_status": "killed" if killed else "survived",
                }
            )
            print(f"  [{'KILLED' if killed else 'SURVIVED'}] {m.mutant_id} — {m.behaviour}")

        killed = sum(r["mutant_status"] == "killed" for r in results)
        survivors = [r["mutant_id"] for r in results if r["mutant_status"] != "killed"]
        report = {
            "mutants_total": len(results),
            "mutants_killed": killed,
            "mutation_score": round(killed / len(results), 3),
            "survivors": survivors,
            "verdict": "PASS" if not survivors else "FAIL",
            "results": results,
            "commands": commands,
            "timestamp_policy": "no nondeterministic timestamp in hash-critical output",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nMUTATION SCORE: {killed}/{len(results)} (={report['mutation_score']})")
        print(f"report: {output}")
        if survivors:
            print("SURVIVORS (suite gaps):", survivors)
            return 1
        return 0
    finally:
        if keep:
            print(f"sandbox kept at: {sandbox}")
        else:
            shutil.rmtree(sandbox, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "--report",
        dest="output",
        type=Path,
        default=ROOT / "artifacts" / "adversarial" / "mutation_kill_report.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="explicit affirmation of the default: any survivor exits non-zero",
    )
    parser.add_argument(
        "--keep", action="store_true", help="keep the mutation sandbox for debugging"
    )
    args = parser.parse_args(argv)
    return run(args.output, keep=args.keep)


if __name__ == "__main__":
    raise SystemExit(main())
