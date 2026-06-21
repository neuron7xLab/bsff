<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# NEXT_10_PR_PLAN

Ten PRs to take BSFF v0.4.0 from a strong repository to a reviewer-proof,
public claim-killer. Each PR ships a file, a command, and a hash or a status.

| PR | title | deliverable | gate |
|----|-------|-------------|------|
| 1 | claim audit | `CLAIM_AUDIT.md` — every claim with evidence/command/hash/status | no claim without a status |
| 2 | evidence index | `EVIDENCE_INDEX.md` — locator + reproduce command per artifact | every artifact reachable in one command |
| 3 | release/provenance verification | verify v0.4.0 `.intoto.jsonl` (download + sha256 + decode subjects) | provenance hash recorded; subject cross-check or `NEEDS_EXTERNAL_CHECK` |
| 4 | test-count reconciliation | `TEST_COUNT_RECONCILIATION.md` + `STATUS.md` regenerated; CI `--check` on merged main | no hand-typed counts |
| 5 | public showcase | `PUBLIC_SHOWCASE.md` | plain-language, no overclaim |
| 6 | reviewer packet | `REVIEWER_PACKET.md` incl. "what would falsify BSFF itself" | install→run→reproduce→falsify in one doc |
| 7 | BSFF-CASE-001 scaffold | `BSFF_CASE_001_PLAN.md` + `examples/case_001/` skeleton | step table with per-step status |
| 8 | PhysioNet/EEGNet baseline | reproduce within-session accuracy (needs network; EEGNet needs GPU) | baseline `result.json` + hash |
| 9 | LOSO + leakage attacks | cross-subject + label-shuffle + leakage-probe results | gap measured; negative controls at chance |
| 10 | final case report + hash ledger | `verdict.json` + `report.md` + `MANIFEST.json` + ledger | `bsff ledger-verify` green; receipt complete |

## Status of this batch
PRs 1, 2, 4, 5, 6, 7 (plan), and the limitations doc are delivered in the
evidence-pack change. PR 3 is partially done (asset present + sha256 verified;
DSSE subject decode = `NEEDS_EXTERNAL_CHECK`). PRs 8–10 are network/GPU-bound and
documented as such; the method is already proven on `BNCI2014_001`.

## Acceptance criterion (whole plan)
No strong sentence in any BSFF document survives without a file, a command, a
hash, or a `UNPROVEN` / `NEEDS_EXTERNAL_CHECK` status. Decorative confidence is a
defect, tracked like any other.
