#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Finalize the Bonn bright-line evidence artifact (Phases 7-10).

Runs the aggregator, writes the S1 bundle verdict + docs/validation/BONN_STATUS.md, assembles the
artifacts/release/ bundle, regenerates HASHES, and runs release_check.
Idempotent; verdict comes only from executed confirmatory bundles.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "artifacts" / "release" / "bonn_bright_line"  # dedicated; do not clobber package release/
BL = ROOT / "artifacts" / "bonn_bright_line"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _tests_json() -> dict:
    """Run the bonn suite and count outcomes from JUnit XML (robust: pytest -q emits no
    summary line in non-tty here, so dot/regex parsing yields 0 — XML is authoritative)."""
    import tempfile
    import xml.etree.ElementTree as ET

    t0 = time.time()
    xml = str(Path(tempfile.gettempdir()) / "bonn_junit.xml")
    log = BL / "logs" / "pytest_bonn_bright_line.log"
    r = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
              f"--junit-xml={xml}", "tests/bonn_bright_line"])
    out = r.stdout + r.stderr
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(out, encoding="utf-8")
    root = ET.parse(xml).getroot()
    ts = root.find("testsuite")
    ts = root if ts is None else ts
    tests = int(ts.get("tests", 0))
    fails = int(ts.get("failures", 0))
    errs = int(ts.get("errors", 0))
    skip = int(ts.get("skipped", 0))
    passed = tests - fails - errs - skip
    return {
        "command": "python -m pytest -q tests/bonn_bright_line",
        "exit_code": r.returncode,
        "status": "PASS" if (r.returncode == 0 and fails == 0 and errs == 0) else "FAIL",
        "passed": passed, "failed": fails, "errors": errs, "skipped": skip, "total": tests,
        "duration_seconds": round(time.time() - t0, 1),
        "log_path": str(log.relative_to(ROOT)),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": _run(["git", "rev-parse", "HEAD"]).stdout.strip(),
    }


def main() -> int:
    REL.mkdir(parents=True, exist_ok=True)
    import aggregate_verdict
    agg_rc = aggregate_verdict.main()
    summary = json.loads((BL / "BRIGHT_LINE_SUMMARY.json").read_text())
    verdict = summary["verdict"]
    g1, g2 = summary.get("G1", {}), summary.get("G2", {})
    commit = _run(["git", "rev-parse", "HEAD"]).stdout.strip()

    # S1-scoped verdict only — the root FORMAL_VERDICT.md is the canonical multi-phase doc
    # (S1 history + S2 current) and must not be clobbered by this S1 finalizer.
    (REL / "S1_FORMAL_VERDICT.md").write_text(f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF — formal verdict (Bonn bright line)

**{verdict}** · statistic `{summary.get('statistic_id')}` · commit `{commit[:12]}` · {summary.get('timestamp_utc')}

| gate | metric | threshold | result |
|------|--------|-----------|--------|
| G1 power | Set E SURVIVED = {g1.get('frac_survived_E')} | ≥ 0.80 | {('PASS' if g1.get('frac_survived_E',0)>=0.8 else 'FAIL')} |
| G1 specificity | A not-SURVIVED = {g1.get('frac_A_not_survived')} | ≥ 0.80 | {('PASS' if g1.get('frac_A_not_survived',0)>=0.8 else 'FAIL')} |
| G1 specificity | B not-SURVIVED = {g1.get('frac_B_not_survived')} | ≥ 0.80 | {('PASS' if g1.get('frac_B_not_survived',0)>=0.8 else 'FAIL')} |
| G2 specificity | AR FPR A={g2.get('fpr_A')}, B={g2.get('fpr_B')}, combined={g2.get('combined_fpr')} | ≤ 0.05 | {('PASS' if g2.get('G2_PASS') else 'FAIL')} |

**BRIGHT_LINE_PASSED = {summary.get('BRIGHT_LINE_PASSED')}** → chain to BNCI2014-001 is **{summary.get('chain_to_bnci2014_001')}**.

## Proven / refuted / unsupported / forbidden
- **proven:** the executed G1/G2 metrics above (reproducible via `REPRODUCE.md`).
- **refuted (preserved):** `lagged_quadratic` statistic — ~20% Set-E power (insufficient).
- **unsupported:** any nonlinearity claim on data/statistics not in this run.
- **forbidden (never claimed):** no clinical diagnosis, no medical use, no regulatory validation, no final proof of brain nonlinear dynamics, no universal BCI benchmark authority.

## Methodological interpretation
SampEn is a **regularity** statistic. Ictal EEG can be more regular than healthy or noisy
segments, so Set E detection (G1) is plausible. But regularity also arises in spectrum-matched
**linear** processes — exactly what **G2** (the AR-null specificity guard) exists to catch.
Since the combined AR-null FPR ({g2.get('combined_fpr')}) exceeds alpha (0.05), the current
statistic is **sensitive but not sufficiently specific**, and is not acceptable as a complete
bright-line statistic.

> This result is scientifically useful **because it prevents an unsupported success claim.**

## Reproduction
See `REPRODUCE.md` (copy-pasteable, relative paths). Verify hashes against
`artifacts/release/bonn_bright_line/HASHES.sha256`.

## Next valid research step
Open the **S2** specificity-method branch (`docs/validation/NEXT_METHOD_CONTRACT_S2.md`).
**Do not** proceed to BNCI2014-001 until G2 passes under the same pre-declared protocol.
""", encoding="utf-8")

    # Bonn status -> dedicated file (do NOT clobber the repo's generated STATUS.md).
    (ROOT / "docs" / "validation" / "BONN_STATUS.md").write_text(f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Bonn bright-line STATUS

**S1 (historical) snapshot.** Current canonical state lives in
`artifacts/release/CURRENT_TRUTH.json` and `FORMAL_VERDICT.md`. The lines below are S1 only.

- Bonn bright line (S1, historical): **{verdict}** (commit `{commit[:12]}`).
- G1: E={g1.get('frac_survived_E')}, A_not={g1.get('frac_A_not_survived')}, B_not={g1.get('frac_B_not_survived')} (≥0.80).
- G2: AR FPR A={g2.get('fpr_A')}, B={g2.get('fpr_B')}, combined={g2.get('combined_fpr')} (≤0.05), G2_PASS={g2.get('G2_PASS')}.
- BNCI2014-001 chain at S1 (historical): **{summary.get('chain_to_bnci2014_001')}**.
- Evidence: `artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json`, `docs/validation/BRIGHT_LINE_VERDICT.md`.
- Reproduce: `REPRODUCE.md`. Tests: `artifacts/release/TESTS.json`.
""", encoding="utf-8")

    # Release bundle
    (REL / "VERDICT.json").write_text(json.dumps(summary, indent=2) + "\n")
    (REL / "VERDICT.md").write_text((REL / "S1_FORMAL_VERDICT.md").read_text())
    (REL / "ENVIRONMENT.txt").write_text(
        f"python={platform.python_version()}\nplatform={platform.platform()}\n"
        f"git_commit={commit}\ntimestamp_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    deps = _run([sys.executable, "-m", "pip", "freeze"]).stdout.strip().splitlines()
    (REL / "DEPENDENCIES.json").write_text(json.dumps({"pip_freeze": deps}, indent=2))
    (REL / "CAPABILITIES.json").write_text(json.dumps({
        "statistic_ids": ["sampen_lower_tail_m2_r015_v1", "lagged_quadratic (refuted, preserved)"],
        "null": "MIAAFT (convergence-gated)", "verdict_states": list(
            ["BRIGHT_LINE_PASSED", "BRIGHT_LINE_NOT_PASSED", "BLOCKED_DATA"]),
        "not_capable_of": ["clinical diagnosis", "medical use", "regulatory validation",
                           "final proof of brain nonlinear dynamics", "universal BCI benchmark"],
    }, indent=2))
    (REL / "TESTS.json").write_text(json.dumps(_tests_json(), indent=2))

    # MANIFEST first, THEN hashes (so HASHES.sha256 covers MANIFEST.json — avoids a stale hash).
    bundle_files = sorted(p.name for p in REL.glob("*") if p.is_file() and p.name != "HASHES.sha256")
    (REL / "MANIFEST.json").write_text(json.dumps({
        "verdict": verdict, "git_commit": commit,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release_files": bundle_files + ["HASHES.sha256"],
    }, indent=2))
    # Hashes (computed last; cover every bundle file except HASHES.sha256 itself).
    files = sorted(p for p in REL.glob("*") if p.is_file() and p.name != "HASHES.sha256")
    (REL / "HASHES.sha256").write_text("".join(f"{_sha(p)}  {p.relative_to(ROOT)}\n" for p in files))
    bl_files = sorted(p for p in BL.rglob("*") if p.is_file() and p.suffix in (".json", ".log"))
    (BL / "HASHES.sha256").write_text("".join(f"{_sha(p)}  {p.relative_to(ROOT / 'artifacts')}\n" for p in bl_files))

    import check_consistency
    cons_rc = check_consistency.main(["--output", "artifacts/release/CONSISTENCY_CHECK.json"])
    import release_check
    rc = release_check.main(["--root", str(ROOT), "--output", "artifacts/release/RELEASE_CHECK.json"])
    print(f"\nfinalize: verdict={verdict} agg_rc={agg_rc} consistency_rc={cons_rc} release_check_rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
