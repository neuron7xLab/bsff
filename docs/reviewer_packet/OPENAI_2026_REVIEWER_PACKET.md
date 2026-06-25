# OpenAI-2026 Validation Grid — Reviewer Packet

> **Disclaimer — read first.** The "OpenAI-2026 Validation Grid" is an
> **internal OpenAI-grade research-validation target**. It is **NOT** an OpenAI
> certification. BSFF is **not affiliated with, not certified by, not endorsed
> by, and not reviewed by OpenAI.** The name is an internally chosen quality bar
> (a research-grade validation grid inspired by public eval / red-team / safety
> principles). Nothing here implies any relationship with OpenAI.

This packet is for an **external reviewer**. It states precisely what the grid
proves, what it does not, how to reproduce the verdict, what claims are
forbidden, and how to file a counterexample.

---

## 1. What the grid PROVES

A `PASS` verdict in `artifacts/final/openai_2026_validation_verdict.json` is
**machine-derived PASS/FAIL evidence** that, at the recorded `head_sha`:

- Dependencies are hash-pinned and resolvable (`--require-hashes`).
- The correctness suite passes **with the network denied**.
- Adversarial oracles, property tests, fuzzers, and the chaos corpus hold.
- Mutation score is **exactly 1.0** against the live mutant set (no survivors,
  no stale report).
- The statistical power profile meets threshold.
- No performance regression vs the committed benchmark baseline.
- The public API / CLI contract is frozen and importable.
- SBOM is reproducible, provenance verifies, no secrets, `pip-audit` is clean.
- Every red-team category is killed.
- The deterministic subset is **seed-stable across ≥3 seeds**.
- No forbidden / unsupported claim is present.
- Every evidence artifact is **sha256-bound** into the verdict.

In short: it proves a set of **engineering and evidence invariants**, computed
not asserted, and independently re-verifiable.

---

## 2. What the grid explicitly does NOT prove

Be rigorous and humble. A `PASS` does **not** establish any of the following:

- **Not clinical or medical validity.** Nothing here demonstrates diagnostic,
  therapeutic, or any health-related efficacy.
- **Not a market, trading, or forecast claim.** The grid says nothing about
  predictive performance on real-world or financial outcomes.
- **Not scientific truth.** Passing means the invariants hold and the evidence
  is internally consistent and powered — not that any underlying scientific
  hypothesis is true. Domain peer review is separate.
- **Not an OpenAI certification, review, endorsement, or affiliation.**
- **Not external validity beyond the committed datasets/seeds.** If
  `dataset_manifest.datasets` is empty, the evidence is synthetic-only and bound
  as such.
- **Not a guarantee for future commits.** The verdict is bound to one
  `head_sha`; re-run on any change.

---

## 3. How to locally reproduce

See [`REPLAY_INSTRUCTIONS.md`](REPLAY_INSTRUCTIONS.md) for exact, copy-pasteable
steps. Summary:

```bash
git clone <repo-url> bsff && cd bsff
python -m venv .venv && source .venv/bin/activate
python -m pip install --require-hashes -r requirements/ci.lock
python -m pip install --no-deps -e .
make openai-2026
```

The canonical artifact `artifacts/final/openai_2026_validation_verdict.json` is
written deterministically (`sort_keys=True`); diff it against the CI artifact.

---

## 4. Forbidden claims

The claim-integrity gate (`tools/validate_openai_2026_claims.py`, gate
`17-claim-integrity`) blocks any forbidden or unsupported claim. The
authoritative, machine-checked deny-list lives in that tool; the gate fails the
build if any prohibited phrasing appears anywhere in the repo. The prohibited
family covers any wording asserting that OpenAI *certified*, *validated*,
*approved*, *endorsed*, *officially benchmarked*, *reviewed*, or entered a
*partnership / collaboration* with this project — in any spelling or hyphenation.
(The exact strings are intentionally not reproduced here so this document itself
stays clean under the gate; consult `tools/validate_openai_2026_claims.py` for
the canonical list.)

**Allowed** phrasings: "OpenAI-2026 Validation Grid", "internal OpenAI-grade
validation target", "research-grade validation grid inspired by public
eval/red-team/safety principles", "machine-derived PASS/FAIL evidence". Any
OpenAI-relationship mention must carry a negating qualifier (e.g. "this is NOT
an OpenAI certification").

---

## 5. How to add a counterexample

We want adversarial input. If you can make a `PASS` verdict that should be
`FAIL` (or vice versa), or break an invariant:

1. Add a failing test under [`tests/redteam/`](../../tests/redteam) or
   [`tests/adversarial/`](../../tests/adversarial) (e.g.
   `tests/adversarial/test_chaos_corpus.py`) that encodes the counterexample.
2. File an issue using the **Adversarial Counterexample** template:
   [`.github/ISSUE_TEMPLATE/adversarial_counterexample.yml`](../../.github/ISSUE_TEMPLATE/adversarial_counterexample.yml).
   (Related templates: `falsification_claim.yml`,
   `scientific_validity_issue.yml`.)
3. The red-team corpus (`artifacts/redteam/redteam_matrix.json`, gate
   `16-red-team-corpus`) tracks categories; an un-killed category forces FAIL.

---

## 6. Source-of-truth artifacts

| Artifact | Role |
| --- | --- |
| `artifacts/final/openai_2026_validation_verdict.json` | The canonical machine verdict. |
| `schemas/openai_2026_verdict.schema.json` | The v2 fail-closed evidence contract. |
| `artifacts/adversarial/mutation_kill_report.json` | Mutation evidence. |
| `artifacts/statistics/power_profile.json` | Statistical power evidence. |
| `artifacts/redteam/redteam_matrix.json` | Red-team corpus evidence. |
| `artifacts/replay/replayability_report.json` | Replay / seed-stability evidence. |
| `artifacts/hermetic/offline_evidence.json` | Network-denied proof. |
| `artifacts/sbom/*` | SBOM / supply-chain evidence. |

Authoritative spec: [`../OPENAI_2026_VALIDATION_GRID.md`](../OPENAI_2026_VALIDATION_GRID.md).
Gate-by-gate matrix: [`GATE_MATRIX.md`](GATE_MATRIX.md).
Failure classes: [`FAILURE_TAXONOMY.md`](FAILURE_TAXONOMY.md).
