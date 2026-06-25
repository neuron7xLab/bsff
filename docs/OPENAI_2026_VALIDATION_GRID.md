<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# OpenAI-2026 Validation Grid

> **Disclaimer — read first.** The "OpenAI-2026 Validation Grid" is an
> **internal OpenAI-grade research-validation target** for the BSFF project. It
> is **NOT** an external OpenAI certification. This project is **not affiliated
> with, not certified by, not endorsed by, and not reviewed by OpenAI.** The
> name denotes an internally chosen quality bar — a research-grade validation
> grid inspired by public eval / red-team / safety principles — and nothing
> more. No claim in this document should be read as implying any relationship
> with OpenAI.

This is the authoritative specification for the validation grid. The grid emits
a single **machine-derived PASS/FAIL** verdict over committed evidence and cheap
static gates. There is no hand-written verdict: the JSON is computed by
`tools/final_validation_verdict.py` and is independently re-verifiable.

---

## 1. What the grid is — and is NOT

**It is:**

- A consolidated, fail-closed CI gate (`.github/workflows/openai-2026-validation-grid.yml`)
  named exactly `OpenAI-2026 Validation Grid`.
- 18 per-dimension jobs plus a final roll-up that machine-derives one verdict.
- Hermetic: every install is hash-pinned (`pip install --require-hashes`),
  correctness tests run with the network denied.
- Replayable: the deterministic subset is re-run across ≥3 seeds and the verdict
  class must be seed-stable.
- An **internal OpenAI-grade research-validation target**.

**It is NOT:**

- An OpenAI certification, OpenAI review, or any OpenAI-affiliated process.
- A claim of scientific truth, clinical/medical validity, or any market /
  forecast claim. Passing the grid proves the engineering and evidence
  invariants below — nothing about real-world efficacy.
- A substitute for domain peer review.

---

## 2. The v2 verdict schema

Source of truth: [`schemas/openai_2026_verdict.schema.json`](../schemas/openai_2026_verdict.schema.json).
The schema is the **fail-closed evidence contract**: PASS is forbidden if any
required key is absent or schema-invalid. The canonical instance is
`artifacts/final/openai_2026_validation_verdict.json`.

### Required keys

| Key | Meaning |
| --- | --- |
| `workflow_name` | Frozen grid name; const `"OpenAI-2026 Validation Grid"`. |
| `project` | Project identifier; const `"bsff"`. |
| `verdict` | `PASS` or `FAIL`; PASS only if `blocking_failures` is empty and all required keys present. |
| `grid_version` | Calendar-versioned grid revision (e.g. `2026.1`). |
| `head_sha` | Commit the verdict was computed against. |
| `run_context` | Where produced (`ci`/`local`/`scheduled`/`dispatch`/`unknown`); provenance only, never affects PASS/FAIL. |
| `python_version` | Interpreter that produced the verdict. |
| `dependency_lock_hashes` | sha256 of every `requirements/*.lock`; binds verdict to a hermetic dependency closure. |
| `gate_results` | Per-gate PASS/FAIL roll-up keyed by gate id. |
| `artifact_digests` | sha256 of every evidence artifact the verdict depends on. |
| `dataset_manifest` | Datasets bound by content hash; empty array allowed (synthetic-only) but the key is mandatory. |
| `seed_manifest` | Pinned RNG seeds the deterministic gates ran under. |
| `mutation_report` | Mutation score, total mutants, survivors, verdict. |
| `power_profile` | Embedded statistical power profile (effect size, CI, FPR/FNR, sample/surrogate/permutation counts, null convergence). |
| `red_team_summary` | Red-team corpus result: verdict, categories total, categories killed. |
| `claim_audit` | Claim gate result: verdict and `forbidden_violations` list. |
| `blocking_failures` | List of blocking reasons; empty iff `verdict == PASS`. |
| `evidence_complete` | All required artifacts present and digest-bound. |
| `network_denied` | Correctness suite ran with the network denied. |
| `replayable` | Verdict class is seed-stable and replay artifact hashes match. |
| `mutation_score` | Mutation kill ratio in `[0,1]`; PASS requires `1.0`. |
| `statistical_power` | `PASS`/`FAIL` of the power profile. |
| `artifact_digests_present` | All required artifact digests were computed. |
| `claim_integrity` | `PASS`/`FAIL` of the forbidden-claim gate. |

### Schema-level PASS conditions (`allOf`)

When `verdict == PASS` the schema additionally requires: `blocking_failures`
empty, `evidence_complete == true`, `network_denied == true`,
`replayable == true`, `artifact_digests_present == true`,
`statistical_power == "PASS"`, `claim_integrity == "PASS"`, and
`mutation_score == 1.0`.

---

## 3. The 18 gates

Jobs 01–13 exist in the workflow today; 14–18 are derived in the final verdict
roll-up (`gate_results`) and run from their dedicated artifacts/validators.

| ID | What it proves | Fail condition |
| --- | --- | --- |
| 01-lock-integrity | Dependency locks are valid and hash-pinned (`--require-hashes --dry-run`). | Lockfile invalid or unresolvable under hashes. |
| 02-hermetic-offline-tests | Correctness suite passes offline (`--disable-network`). | Any non-slow test fails, or network was reachable. |
| 03-adversarial-oracles | Adversarial operating-characteristic + chaos oracles hold. | Any adversarial test fails or `update_adversarial_validation.py --check` drifts. |
| 04-property-tests | Property-based invariants hold (`tests/property`). | Any property test fails. |
| 05-fuzz-smoke | Fuzzers find no crash on signal inputs, verdict JSON, policy profiles. | Any fuzz target crashes within the seeded run budget. |
| 06-mutation-kill | Mutation score is 1.0 against the live mutant set. | Any survivor, score `< 1.0`, `< 8` mutants, or report stale vs live mutant set. |
| 07-wheel-runtime | Built wheel imports and runs offline. | Wheel import/run fails under `--offline`. |
| 08-sbom-provenance | SBOM is reproducible and provenance binding verifies. | SBOM `--check` mismatch or provenance validation fails. |
| 09-security | No secrets, GitHub Actions policy holds, `pip-audit --strict` clean. | Secret detected, policy violation, or known vulnerability. |
| 10-statistical-power | Power profile meets threshold (effect size, CI, FPR/FNR, counts, null convergence). | Profile missing or below threshold. |
| 11-degradation | Benchmark baseline is structurally valid; no regression vs baseline. | Baseline missing/malformed (`< 4` benches or empty stats) or regression detected. |
| 12-api-cli-contract | Public API surface and CLI contract are frozen and importable. | `bsff.api.__all__` drift, a non-callable symbol, or contract test failure. |
| 13-final-verdict | Machine-derives the consolidated PASS/FAIL over all evidence. | Any sub-gate FAIL or schema validation error. |
| 14-replayability | Deterministic subset is seed-stable across ≥3 seeds with matching artifact hashes. | `< 3` seed sets, verdict class not stable, or replay hashes diverge. |
| 15-meta-validation | The validators themselves are tested (`tests/meta_validation`). | Meta-validation suite absent or failing. |
| 16-red-team-corpus | Every red-team category is killed (`redteam_matrix.json`). | Matrix missing/invalid, or any category not killed. |
| 17-claim-integrity | No forbidden / unsupported claim is present in the repo. | Any forbidden-claim violation. |
| 18-artifact-digest-binding | Every required evidence artifact is present and sha256-bound. | Any required artifact missing from the digest map. |

---

## 4. Fail-closed philosophy

The grid PASSes only when **every** dimension below is satisfied. Any unknown,
missing, stale, non-deterministic, underpowered, unverifiable, or contradicted
piece of evidence forces FAIL.

- **Deterministic** — verdict is computed, never authored; identical inputs give
  identical output (`sort_keys=True`).
- **Offline** — correctness tests run with the network denied; `network_denied`
  is recorded as evidence.
- **Replayable** — deterministic subset re-run across ≥3 seeds; verdict class
  and artifact hashes must be stable.
- **Adversarial** — adversarial oracles, fuzzers, chaos corpus, and a red-team
  category corpus that must be fully killed.
- **Statistically powered** — embedded power profile must meet threshold.
- **Mutation-resistant** — mutation score must be exactly `1.0` against the
  live mutant set; a stale report cannot certify changed code.
- **Supply-chain-verifiable** — hash-pinned locks, reproducible SBOM, provenance
  binding, secret scan, `pip-audit`.
- **Artifact-bound** — every evidence artifact is sha256-bound into the verdict.
- **Claim-bound** — forbidden-claim gate blocks any unsupported or prohibited
  claim (including any phrasing implying OpenAI certification/endorsement).
- **Machine-verdict-only** — the verdict JSON is the sole source of truth; it is
  schema-validated fail-closed.

### Final verdict rule

**PASS** = all gates PASS **and** all artifacts digest-bound **and** no stale
evidence **and** no forbidden claim **and** replay stable **and**
`mutation_score == 1.0` **and** `statistical_power == PASS`.

**FAIL** = any unknown, missing, stale, non-deterministic, underpowered,
unverifiable, or contradicted evidence.

---

## 5. Running locally

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --require-hashes -r requirements/ci.lock
python -m pip install --no-deps -e .
make openai-2026
```

`make openai-2026` chains `lock`, `verify-offline`, `build-proof`, and `verify`,
ending on `tools/final_validation_verdict.py`. See the Makefile targets `lock`,
`verify`, `verify-offline`, `build-proof`, and `openai-2026`.

---

## 6. Source-of-truth artifacts

| Artifact | Produced by |
| --- | --- |
| `artifacts/final/openai_2026_validation_verdict.json` | `make openai-2026` / `tools/final_validation_verdict.py` (the canonical verdict). |
| `artifacts/adversarial/mutation_kill_report.json` | `tools/mutation_kill_gate.py`. |
| `artifacts/adversarial/corpus_matrix.json` | Chaos/adversarial corpus run. |
| `artifacts/statistics/power_profile.json` | `tools/statistical_power_profile.py`. |
| `artifacts/benchmarks/baseline.json` | Degradation baseline. |
| `artifacts/redteam/redteam_matrix.json` | Red-team corpus; validated by `tools/validate_redteam_matrix.py`. |
| `artifacts/replay/replayability_report.json` | Replayability gate. |
| `artifacts/hermetic/offline_evidence.json` | Offline-evidence (network-denied) proof. |
| `artifacts/sbom/*` | `tools/generate_sbom.py`. |

The schema is `schemas/openai_2026_verdict.schema.json`. The reviewer packet
lives under [`docs/reviewer_packet/`](reviewer_packet/).

## Sanctioned phrasings (claim firewall)

These are the only sanctioned ways to describe the grid's standing. They are an
internal OpenAI-grade research-validation target — not an OpenAI certification,
endorsement, or affiliation. The claim-integrity gate
(`tools/validate_openai_2026_claims.py`) treats these as allowed and rejects any
external-OpenAI-relationship assertion:

- OpenAI-2026 Validation Grid
- internal OpenAI-grade research-validation target
- research-grade validation grid inspired by public eval/red-team/safety principles
- machine-derived PASS/FAIL evidence
