<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# OpenAI-2026 Eval Contract

> **Scope and naming.** The *OpenAI-2026 Validation Grid* is an **internal
> OpenAI-grade validation target** — a research-grade validation grid inspired by
> public eval/red-team/safety engineering practices. It is **not** an OpenAI
> certification, is not affiliated with OpenAI, and makes no OpenAI endorsement
> claim. A claim-integrity gate (`tools/validate_openai_2026_claims.py`) enforces
> this on every public surface.

## Why a formal eval contract

A strong CI proves "the tests passed". An eval contract proves something stricter:
**every claim is bound to a task, a dataset/input, an executable grader, a
threshold, a named failure mode, and a digest-bound evidence artifact, with a
written result analysis.** "Tests passed" becomes "this specific behaviour was
graded against this specific evidence and cleared this specific threshold."

The contract is machine-derived, not narrative:

- definitions live in [`contracts/openai_2026_eval_contract.yaml`](../contracts/openai_2026_eval_contract.yaml);
- the structure is enforced by [`schemas/openai_2026_eval.schema.json`](../schemas/openai_2026_eval.schema.json);
- the graders are **executed** by
  [`tools/validate_openai_2026_eval_contract.py`](../tools/validate_openai_2026_eval_contract.py),
  which reads each evidence artifact and compares the metric to the threshold;
- the result is written to `artifacts/eval/eval_contract_report.json` and folded
  into the final verdict (`gate_results["eval-contract"]` and the `eval_contract`
  summary), digest-bound like every other artifact.

An eval **cannot pass** without a resolvable evidence artifact **and** a satisfied
grader. A missing metric fails closed.

## Eval entry shape

Each eval is a mapping with exactly these keys (schema-enforced):

| Field | Meaning |
|---|---|
| `id` | stable snake_case identifier |
| `risk_class` | `correctness` / `false_positive` / `false_negative` / `robustness` / `reproducibility` / `claim_safety` / `supply_chain` |
| `task_definition` | what decision the eval makes |
| `test_inputs` | the dataset / input family exercised |
| `ground_truth_or_expected_behavior` | the expected outcome |
| `grader` | executable check: `{artifact, metric, op, value\|field}` |
| `threshold` | human-readable pass condition |
| `failure_mode` | the named way this eval can fail |
| `evidence_artifact` | the digest-bound JSON the verdict reads |
| `result_analysis` | how to read the evidence and why the threshold is right |

### Grader operators

| `op` | Meaning |
|---|---|
| `ge` / `le` / `eq` | metric `>=` / `<=` / `==` `value` |
| `eq_field` | metric `==` another field in the same artifact (`field`) |
| `is_true` | metric is boolean `true` |
| `len_ge` | `len(metric) >= value` |

`metric` is a dotted path into the evidence JSON (e.g.
`measured.null_false_positive_rate`).

## The evals

| id | risk class | grader (artifact · metric · op) | threshold | failure mode |
|---|---|---|---|---|
| `surrogate_specificity_false_positive` | false_positive | power_profile · `measured.null_false_positive_rate` · le | `<= 0.05` | flags noise as structure |
| `detection_power_false_negative` | false_negative | power_profile · `measured.positive_control_detection` · ge | `>= 0.80` | misses real structure |
| `surrogate_convergence` | correctness | power_profile · `measured.surrogate_convergence_rate` · ge | `>= 0.95` | non-converged surrogates |
| `mutation_resistance` | correctness | mutation_kill_report · `mutation_score` · ge | `>= 1.0` | undetected regression |
| `chaos_input_robustness` | robustness | corpus_matrix · `passed` == `total` | `passed == total` | unhandled input |
| `red_team_coverage` | robustness | redteam_matrix · `categories_killed` == `categories_total` | all killed | attack survives |
| `reproducibility_seed_stable` | reproducibility | replayability_report · `verdict_class_stable` · is_true | `== true` | a seed flips the verdict |
| `claim_safety` | claim_safety | final verdict · `claim_integrity` · eq | `== PASS` | unverifiable OpenAI claim |

## Running it

```bash
python tools/validate_openai_2026_eval_contract.py --check   # writes artifacts/eval/eval_contract_report.json
pytest tests/test_openai_2026_eval_contract.py -q
```

The eval contract is also exercised by `make openai-2026` (via the `verify`
target) and by the `13-final-verdict` job, which regenerates the dynamic evidence
and re-grades before binding digests.

## What it does and does not prove

- **Proves:** each listed behaviour was graded against committed, digest-bound
  evidence and cleared a pre-declared threshold; a failure has a named failure
  mode and surfaces in `blocking_failures`.
- **Does not prove:** clinical/medical validity, any market or forecast claim,
  scientific truth about brain dynamics, or any external OpenAI relationship. See
  [`docs/reviewer_packet/OPENAI_2026_REVIEWER_PACKET.md`](reviewer_packet/OPENAI_2026_REVIEWER_PACKET.md).
