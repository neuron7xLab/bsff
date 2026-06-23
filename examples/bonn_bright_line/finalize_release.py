#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Finalize the Bonn bright-line evidence artifact (Phases 7-10).

Runs the aggregator, writes FORMAL_VERDICT.md / STATUS.md, assembles the
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
REL = ROOT / "artifacts" / "release"
BL = ROOT / "artifacts" / "bonn_bright_line"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _tests_json() -> dict:
    t0 = time.time()
    r = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/bonn_bright_line"])
    out = r.stdout + r.stderr
    import re
    m = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    s = re.search(r"(\d+) skipped", out)
    return {"command": "pytest -q tests/bonn_bright_line", "exit_code": r.returncode,
            "duration_sec": round(time.time() - t0, 1),
            "passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0,
            "skipped": int(s.group(1)) if s else 0, "log_tail": out.strip().splitlines()[-1:] }


def main() -> int:
    REL.mkdir(parents=True, exist_ok=True)
    import aggregate_verdict
    agg_rc = aggregate_verdict.main()
    summary = json.loads((BL / "BRIGHT_LINE_SUMMARY.json").read_text())
    verdict = summary["verdict"]
    g1, g2 = summary.get("G1", {}), summary.get("G2", {})
    commit = _run(["git", "rev-parse", "HEAD"]).stdout.strip()

    # FORMAL_VERDICT.md
    (ROOT / "FORMAL_VERDICT.md").write_text(f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BSFF — formal verdict (Bonn bright line)

**{verdict}** · statistic `{summary.get('statistic_id')}` · commit `{commit[:12]}` · {summary.get('timestamp_utc')}

| gate | metric | threshold | result |
|------|--------|-----------|--------|
| G1 power | Set E SURVIVED = {g1.get('frac_survived_E')} | ≥ 0.80 | {('PASS' if g1.get('frac_survived_E',0)>=0.8 else 'FAIL')} |
| G1 specificity | A not-SURVIVED = {g1.get('frac_A_not_survived')} | ≥ 0.80 | {('PASS' if g1.get('frac_A_not_survived',0)>=0.8 else 'FAIL')} |
| G1 specificity | B not-SURVIVED = {g1.get('frac_B_not_survived')} | ≥ 0.80 | {('PASS' if g1.get('frac_B_not_survived',0)>=0.8 else 'FAIL')} |
| G2 specificity | combined AR FPR = {g2.get('combined_fpr')} | ≤ 0.05 | {('PASS' if g2.get('G2_PASS') else 'FAIL')} |

**BRIGHT_LINE_PASSED = {summary.get('BRIGHT_LINE_PASSED')}** → chain to BNCI2014-001 is **{summary.get('chain_to_bnci2014_001')}**.

## Proven / refuted / unsupported / forbidden
- **proven:** the executed G1/G2 metrics above (reproducible via `REPRODUCE.md`).
- **refuted (preserved):** `lagged_quadratic` statistic — ~20% Set-E power (insufficient).
- **unsupported:** any nonlinearity claim on data/statistics not in this run.
- **forbidden (never claimed):** clinical diagnosis, medical use, regulatory validation,
  final proof of brain nonlinear dynamics, universal BCI benchmark authority.
""", encoding="utf-8")

    # STATUS.md
    (ROOT / "STATUS.md").write_text(f"""<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# STATUS

- Bonn bright line: **{verdict}** (commit `{commit[:12]}`).
- G1: E={g1.get('frac_survived_E')}, A_not={g1.get('frac_A_not_survived')}, B_not={g1.get('frac_B_not_survived')} (≥0.80).
- G2: combined AR FPR={g2.get('combined_fpr')} (≤0.05), G2_PASS={g2.get('G2_PASS')}.
- BNCI2014-001 chain: **{summary.get('chain_to_bnci2014_001')}**.
- Evidence: `artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json`, `docs/validation/BRIGHT_LINE_VERDICT.md`.
- Reproduce: `REPRODUCE.md`. Tests: `artifacts/release/TESTS.json`.
""", encoding="utf-8")

    # Release bundle
    (REL / "VERDICT.json").write_text(json.dumps(summary, indent=2) + "\n")
    (REL / "VERDICT.md").write_text((ROOT / "FORMAL_VERDICT.md").read_text())
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

    # Hashes
    files = sorted([p for p in REL.glob("*") if p.is_file() and p.name != "HASHES.sha256"])
    (REL / "HASHES.sha256").write_text("".join(f"{_sha(p)}  {p.relative_to(ROOT)}\n" for p in files))
    bl_files = sorted([p for p in BL.rglob("*") if p.is_file() and p.suffix in (".json", ".log")])
    (BL / "HASHES.sha256").write_text("".join(f"{_sha(p)}  {p.relative_to(ROOT/'artifacts')}\n" for p in bl_files))
    (REL / "MANIFEST.json").write_text(json.dumps({
        "verdict": verdict, "git_commit": commit,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release_files": [p.name for p in files] + ["HASHES.sha256", "MANIFEST.json"],
    }, indent=2))

    import release_check
    rc = release_check.main()
    print(f"\nfinalize: verdict={verdict} agg_rc={agg_rc} release_check_rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
