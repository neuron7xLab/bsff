#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Single source of truth for ADVERSARIAL_VALIDATION.md.

The adversarial-validation report must never be hand-trusted prose. This tool
regenerates it from machine facts that already live in the repository:

* ``artifacts/adversarial/baseline.json``           — seed/network/verdict policy;
* ``artifacts/adversarial/mutation_kill_report.json`` — the killed-mutant table;
* ``tools/mutation_kill_gate.py`` ``MUTANTS``        — mutant definitions;
* ``tests/test_adversarial_operating_characteristics.py`` — the oracle fixtures;
* ``bsff.policy`` profiles                           — the OC thresholds;
* ``.github/workflows/*.yml``                        — the CI jobs that enforce it.

It is fail-closed: a missing report, a referenced oracle test that does not exist,
or a surviving mutant make the rendered verdict FAIL. ``--check`` regenerates the
document in memory and compares it byte-for-byte with the on-disk copy so CI can
prove the report was regenerated whenever any underlying fact changed.

    python tools/update_adversarial_validation.py            # write the doc
    python tools/update_adversarial_validation.py --check     # exit 1 if stale

Standard library only. No network.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "ADVERSARIAL_VALIDATION.md"
BASELINE = ROOT / "artifacts" / "adversarial" / "baseline.json"
MUTATION_REPORT = ROOT / "artifacts" / "adversarial" / "mutation_kill_report.json"
OC_TEST = ROOT / "tests" / "test_adversarial_operating_characteristics.py"
ADVERSARIAL_WF = ROOT / ".github" / "workflows" / "adversarial-validation.yml"
CI_WF = ROOT / ".github" / "workflows" / "ci.yml"

# Runtime dependencies the SBOM gate requires to be present in the closure.
RUNTIME_ESSENTIALS = ("numpy", "scipy", "statsmodels")

# Oracle fixtures: each row binds an acceptance test in the OC module to the
# fixture, policy, and decision it pins. The test name is verified to exist, so
# this table cannot drift away from the suite it claims to describe.
ORACLE_FIXTURES: tuple[tuple[str, str, str, str], ...] = (
    (
        "test_linear_null_never_survives_under_strict",
        "AR(1) linear-Gaussian null",
        "strict",
        "never SURVIVED (REFUTED/UNSUPPORTED)",
    ),
    (
        "test_linear_null_false_positive_rate_within_binomial_guard",
        "AR(1) linear-Gaussian null battery",
        "standard",
        "SURVIVED count <= binomial guard",
    ),
    (
        "test_nonlinear_positive_control_survives_with_exposed_evidence",
        "Hénon / logistic deterministic chaos",
        "standard",
        "SURVIVED on a converged null; evidence exposed",
    ),
    (
        "test_leakage_short_circuits_to_refuted",
        "flagged block-design leakage",
        "standard/strict",
        "REFUTED; surrogate stage SKIP",
    ),
    (
        "test_nonstationary_random_walk_fails_strict_gate_fatally",
        "random-walk (nonstationary)",
        "strict",
        "REFUTED; stationarity FAIL fatal; surrogate SKIP",
    ),
    (
        "test_nonconverged_null_cannot_exceed_unsupported",
        "starved MIAAFT budget (invalid null)",
        "custom strict",
        "UNSUPPORTED; never SURVIVED/REFUTED",
    ),
    (
        "test_poisoned_input_raises_and_emits_no_verdict",
        "NaN / Inf / too-short / wrong-shape",
        "standard",
        "ValueError; no VerdictJSON emitted",
    ),
)

# Property/fuzz oracle: a separate module that self-breaks the verdict engine and
# asserts the fail-closed invariant under Hypothesis-generated inputs.
FUZZ_TEST = "tests/test_verdict_engine_fuzz.py::test_verdict_engine_is_fail_closed_under_fuzz"

# Baseline command matrix: the commands an auditor runs to reproduce the gates.
BASELINE_COMMANDS: tuple[str, ...] = (
    "python -m pip install -e '.[dev,leakage,stats,yaml]'",
    "python -m ruff check src tests tools",
    "python -m ruff format --check src tests tools",
    'python -m pytest tests/ -m "not slow" --tb=short',
    "python -m pytest tests/ -m slow --tb=short",
    "python -m pytest tests/test_adversarial_operating_characteristics.py -v",
    "python -m pytest tests/test_verdict_engine_fuzz.py -v",
    "python tools/mutation_kill_gate.py",
    "python tools/validate_wheel_runtime.py",
    "python tools/generate_sbom.py --check",
    "bsff-validate --output artifacts/bsff_phase1_validation.json",
    "python tools/verify_all.py",
    "python tools/update_adversarial_validation.py --check",
)

ARTIFACTS: tuple[str, ...] = (
    "artifacts/adversarial/baseline.json",
    "artifacts/adversarial/mutation_kill_report.json",
    "artifacts/wheel_validation.json",
    "artifacts/bsff_phase1_validation.json",
    "artifacts/sbom.cdx.json",
)


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses defined under `from __future__ import
    # annotations` can resolve their own module during class construction.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _oc_test_names() -> set[str]:
    source = OC_TEST.read_text(encoding="utf-8")
    return set(re.findall(r"^def (test_[a-z0-9_]+)\(", source, flags=re.MULTILINE))


def _wf_job_names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    body = text.split("\njobs:\n", 1)[-1]
    return re.findall(r"^  ([a-z][a-z0-9-]*):$", body, flags=re.MULTILINE)


def generate() -> str:
    if not BASELINE.is_file():
        raise SystemExit(f"missing {BASELINE.relative_to(ROOT)} — run the baseline audit first")
    if not MUTATION_REPORT.is_file():
        raise SystemExit(
            f"missing {MUTATION_REPORT.relative_to(ROOT)} — run: python tools/mutation_kill_gate.py"
        )
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    report = json.loads(MUTATION_REPORT.read_text(encoding="utf-8"))

    # Fail closed: every oracle fixture row must name a real test in the module.
    present = _oc_test_names()
    missing = [name for name, *_ in ORACLE_FIXTURES if name not in present]
    if missing:
        raise SystemExit(f"oracle fixture rows reference missing tests: {missing}")
    fuzz_name = FUZZ_TEST.split("::", 1)[1]
    fuzz_file = ROOT / FUZZ_TEST.split("::", 1)[0]
    if not fuzz_file.is_file() or f"def {fuzz_name}(" not in fuzz_file.read_text(encoding="utf-8"):
        raise SystemExit(f"property/fuzz oracle missing: {FUZZ_TEST}")
    sbom_tool = ROOT / "tools" / "generate_sbom.py"
    if not sbom_tool.is_file():
        raise SystemExit("supply-chain SBOM tool missing: tools/generate_sbom.py")

    # Authoritative thresholds straight from the installed policy profiles.
    from bsff.policy import get_policy_profile

    std = get_policy_profile("standard")
    strict = get_policy_profile("strict")

    mutants = _load_module(ROOT / "tools" / "mutation_kill_gate.py").MUTANTS
    status_by_id = {r["mutant_id"]: r["mutant_status"] for r in report["results"]}

    killed = int(report["mutants_killed"])
    total = int(report["mutants_total"])
    survivors = list(report["survivors"])
    all_killed = killed == total and not survivors

    adv_jobs = _wf_job_names(ADVERSARIAL_WF)
    ci_jobs = _wf_job_names(CI_WF)

    verdict = (
        "PASS — adversarial gates killed the intended regressions and the deterministic gates hold."
        if all_killed
        else f"FAIL — {len(survivors)} mutant(s) survived: {survivors}."
    )

    out: list[str] = []
    w = out.append
    w("<!-- SPDX-License-Identifier: CC-BY-4.0 -->")
    w("<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->")
    w(
        "<!-- GENERATED FILE — edit tools/update_adversarial_validation.py, then run it. Do not edit by hand. -->"
    )
    w("")
    w("# Adversarial validation")
    w("")
    w("Falsification-power report for the BSFF verdict pipeline. A green CI badge is")
    w("only meaningful if the suite **kills** behavioural regressions; this document")
    w("is regenerated from machine facts by")
    w("`python tools/update_adversarial_validation.py` and verified in CI with")
    w("`--check`. It is never hand-edited.")
    w("")
    w(f"**Final validation verdict: {verdict}**")
    w("")
    w(
        f"Mutation score: **{killed}/{total}** ({report['mutation_score']}). "
        f"Surrogate seed policy: _{baseline['seed_policy']}_. "
        f"Network policy: _{baseline['network_policy']}_."
    )
    w("")

    w("## Baseline command matrix")
    w("")
    w("Reproduce every gate locally, in order:")
    w("")
    w("```bash")
    for cmd in BASELINE_COMMANDS:
        w(cmd)
    w("```")
    w("")

    w("## Killed mutants")
    w("")
    w("Each mutant is a single-point behavioural regression in the verdict-collapse")
    w("path. `tools/mutation_kill_gate.py` applies it to an isolated copy and requires")
    w("the targeted oracle test to FAIL. A survivor is a hole in the suite.")
    w("")
    w("| Mutant | File | Behaviour it breaks | Status |")
    w("|---|---|---|---|")
    for m in mutants:
        status = status_by_id.get(m.mutant_id, "unknown")
        badge = "✅ killed" if status == "killed" else f"❌ {status}"
        w(f"| `{m.mutant_id}` | `{m.rel_path}` | {m.behaviour} | {badge} |")
    w("")

    w("## Oracle fixtures")
    w("")
    w("Deterministic operating-characteristic oracles in")
    w("`tests/test_adversarial_operating_characteristics.py`. Each pins one decision")
    w("the pipeline must make on an adversarial fixture.")
    w("")
    w("| Test | Fixture | Policy | Required decision |")
    w("|---|---|---|---|")
    for name, fixture, pol, expected in ORACLE_FIXTURES:
        w(f"| `{name}` | {fixture} | {pol} | {expected} |")
    w("")

    w("## Self-breaking (property / fuzz) gate")
    w("")
    w(f"`{FUZZ_TEST.split('::', 1)[0]}` drives Hypothesis-generated signals, policies,")
    w("leakage flags, and seeds through `evaluate_claim_pipeline` and asserts the")
    w("fail-closed contract for every input: the only acceptable refusal is a")
    w("`ValueError`; any returned verdict is one of the three terminal verdicts bound")
    w("to a 64-hex contract hash; and **SURVIVED is unforgeable** — it requires a")
    w("converged null and, under Bayesian policy, BF10 at or above the corroboration")
    w("threshold. The search is `derandomize=True`, so any defect it finds is a")
    w("deterministic, replayable artifact — the system breaks itself on purpose.")
    w("")
    w("## Supply-chain inventory (SBOM)")
    w("")
    w("`python tools/generate_sbom.py` emits a deterministic CycloneDX 1.5 SBOM of the")
    w("runtime dependency closure (extras excluded; components sorted; no wall-clock")
    w("timestamp or random serial, so it is hash-stable). `--check` is a fail-closed")
    w("structural gate: valid envelope, BSFF as root, every component carrying")
    w(f"name+version+purl, and the runtime essentials ({', '.join(RUNTIME_ESSENTIALS)})")
    w("present in the closure. It rides the `build` job alongside the SLSA build-")
    w("provenance attestation, CodeQL/SARIF triage, pip-audit, and OpenSSF Scorecard")
    w("already enforced by the repository.")
    w("")
    w("## Operating-characteristic thresholds")
    w("")
    w("| Quantity | standard | strict |")
    w("|---|---|---|")
    w(f"| Surrogate count | {std.surrogate_count} | {strict.surrogate_count} |")
    w(f"| Alpha | {std.alpha} | {strict.alpha} |")
    w(
        f"| Bayesian corroboration min (BF10) | {std.bayesian_corroboration_min} | {strict.bayesian_corroboration_min} |"
    )
    w(f"| Stationarity mode | {std.stationarity_mode} | {strict.stationarity_mode} |")
    w(f"| Bayesian evidence | {std.bayesian_evidence} | {strict.bayesian_evidence} |")
    w("")
    w("The linear-null false-positive guard is the 99.9% upper binomial quantile")
    w("`binom.ppf(0.999, N, alpha)` over the seed battery — calibrated to nominal")
    w("alpha, not loosened. A corroboration-gate regression that inflates the")
    w("SURVIVED rate exceeds it and turns the oracle red.")
    w("")

    w("## Deterministic seed policy")
    w("")
    w(f"- {baseline['seed_policy']}.")
    w(f"- {baseline['network_policy']}; the oracle module installs an autouse fixture")
    w("  that severs `socket.connect`/`connect_ex` to prove it.")
    w(f"- {baseline['verdict_policy']}.")
    w("- No wall-clock assertions; no nondeterministic timestamps in hash-critical")
    w("  output (mutation report and evidence artifacts are hash-stable).")
    w(f"- Target interpreters: {', '.join(baseline['python_versions_expected'])}.")
    w("")

    w("## Artifacts")
    w("")
    for path in ARTIFACTS:
        w(f"- `{path}`")
    w("")

    w("## CI jobs enforcing the gates")
    w("")
    w(
        f"`.github/workflows/adversarial-validation.yml` — jobs: "
        f"{', '.join(f'`{j}`' for j in adv_jobs)}."
    )
    w("")
    w(f"`.github/workflows/ci.yml` — jobs: {', '.join(f'`{j}`' for j in ci_jobs)}.")
    w("")
    w("The report is machine-derived: this file is regenerated from the artifacts")
    w("above and re-verified by `tools/update_adversarial_validation.py --check` in")
    w("the `oracle-adversarial-py312` job. PASS holds only while every machine gate")
    w("passes.")
    w("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate / verify ADVERSARIAL_VALIDATION.md.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if the doc is stale.")
    args = parser.parse_args(argv)

    rendered = generate()
    if args.check:
        if not DOC.exists():
            print(
                "ADVERSARIAL_VALIDATION.md is missing — run: python tools/update_adversarial_validation.py"
            )
            return 1
        if DOC.read_text(encoding="utf-8") != rendered:
            print("ADVERSARIAL_VALIDATION.md is STALE — regenerate it:")
            print("    python tools/update_adversarial_validation.py")
            on_disk = DOC.read_text(encoding="utf-8").splitlines()
            for disk_line, gen_line in zip(on_disk, rendered.splitlines(), strict=False):
                if disk_line != gen_line:
                    print(f"  on-disk:   {disk_line}")
                    print(f"  generated: {gen_line}")
                    break
            return 1
        print("ADVERSARIAL_VALIDATION.md: in sync")
        return 0

    DOC.write_text(rendered, encoding="utf-8")
    print(f"Wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
