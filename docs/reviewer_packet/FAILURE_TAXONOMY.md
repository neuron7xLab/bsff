# OpenAI-2026 Validation Grid — Failure Taxonomy

> **Disclaimer.** The "OpenAI-2026 Validation Grid" is an **internal
> OpenAI-grade research-validation target**, **NOT** an OpenAI certification.
> BSFF is **not affiliated with, certified by, or endorsed by OpenAI.**

The grid is fail-closed: any of the failure classes below forces `verdict ==
FAIL`. Each surfaces as one or more strings in the verdict's
`blocking_failures` array (`artifacts/final/openai_2026_validation_verdict.json`)
and, where it maps to a gate, as a `gate <id> FAIL` entry. `blocking_failures`
is empty **iff** the verdict is PASS.

| Class | Definition | How the grid catches it | Owning gate |
| --- | --- | --- | --- |
| **unknown** | A sub-verdict cannot be determined (validator emitted no parseable result). | Validators return FAIL on unparseable output (e.g. claim gate "did not emit JSON"); roll-up treats absence as FAIL. | 13-final-verdict / 17-claim-integrity |
| **missing** | A required artifact or required schema key is absent. | `_artifact_digests()` adds "artifact missing for digest: …"; schema validation adds "missing required key: …"; both force FAIL. | 18-artifact-digest-binding, 13-final-verdict |
| **stale** | Committed evidence does not match the current code. | Mutation gate compares the report's mutant ids against the **live** mutant set; mismatch ⇒ "mutation report is stale vs live mutant set". | 06-mutation-kill |
| **non-deterministic** | Output differs across runs / seeds. | Replayability requires `verdict_class_stable` and `artifact_hashes_match`; divergence ⇒ FAIL. Verdict JSON is `sort_keys=True` so spurious diffs are real. | 14-replayability |
| **underpowered** | Statistical power profile below threshold. | `validate_power_profile.py` fails ⇒ "power profile below threshold" (or "power profile missing"). | 10-statistical-power |
| **unverifiable** | Supply-chain / build evidence cannot be re-derived. | Lock validation, SBOM `--check`, provenance validation, or wheel offline-run failing ⇒ FAIL. | 01-lock-integrity, 07-wheel-runtime, 08-sbom-provenance |
| **contradicted** | Evidence is internally inconsistent (e.g. claims PASS but survivors present, or categories killed ≠ total). | Mutation: `verdict != PASS` or non-empty `survivors`. Red team: `killed != total` or `total <= 0`. | 06-mutation-kill, 16-red-team-corpus |
| **forbidden-claim** | A prohibited or unsupported claim string is present in the repo. | `validate_openai_2026_claims.py --json` returns non-empty `forbidden_violations` ⇒ "claim integrity violations". | 17-claim-integrity |
| **forged-evidence** | An evidence artifact was altered or hand-crafted to self-certify. | Dedicated validators re-check the artifact (`validate_redteam_matrix.py`, `validate_mutation_report.py`); a malformed/forged matrix ⇒ "redteam matrix invalid". Artifact sha256 binding detects post-hoc edits. | 16-red-team-corpus, 06-mutation-kill, 18-artifact-digest-binding |
| **network-access** | Correctness suite touched the network. | Tests run `--disable-network`; `offline_evidence.json` must record `network_denied == true`, else "network not denied" / "offline evidence missing". | 02-hermetic-offline-tests |
| **replay-divergence** | The deterministic subset is not seed-stable across ≥3 seeds. | `_replayability()` requires `len(seeds) >= 3`, stable verdict class, and matching artifact hashes; otherwise "fewer than 3 seed sets" / "verdict class not seed-stable" / "replay artifact hashes diverge". | 14-replayability |

---

## How a failure surfaces (worked example)

A stale mutation report produces, in the verdict:

```json
{
  "verdict": "FAIL",
  "mutation_score": 0.93,
  "blocking_failures": [
    "gate 06-mutation-kill FAIL",
    "mutation report is stale vs live mutant set"
  ]
}
```

Each blocking string is deduplicated and sorted
(`sorted(set(blocking))`). A reviewer reads `blocking_failures` top-to-bottom,
maps each entry to its owning gate via the table above, and re-runs that gate's
local command (see [`GATE_MATRIX.md`](GATE_MATRIX.md)) to reproduce.

---

## Schema-level fail-closed backstop

Independent of the gate roll-up, `tools/final_validation_verdict.py` validates
the assembled verdict against
[`schemas/openai_2026_verdict.schema.json`](../../schemas/openai_2026_verdict.schema.json).
Any missing required key or schema violation is merged into `blocking_failures`
and forces FAIL — even if `jsonschema` is unavailable, a hard required-key check
runs. A structurally incomplete verdict therefore can never PASS.
