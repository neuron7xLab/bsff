<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF Adjudication Kernel

> Aim BSFF at the claims of an external source — a paper, a preprint, a report —
> and let each claim earn its standing or be quarantined. The kernel does not
> trust. It sorts, tests, and records.

## Why this exists

The rest of BSFF falsifies a **signal** claim against a spectral surrogate null.
That is narrow by design. The adjudication kernel widens the aperture without
loosening the rigor: it takes assertions extracted from a publication and routes
each to the strongest scrutiny it admits — and refuses to invent scrutiny it
cannot apply.

The honest boundary, stated up front: **a general "claim killer" cannot decide
the empirical truth of an arbitrary interdisciplinary claim without that claim's
data and a computational test.** The integrity of this system is that it never
pretends otherwise. A claim that cannot be tested here is labelled as such, not
waved through.

## The epistemic contract

1. **No claim is promoted to "true".** The strongest disposition an empirical
   claim can earn is `SURVIVED_FALSIFICATION` — *under stated conditions, and
   only when real data drove the falsification battery*. Survival is information,
   not coronation.
2. **A claim must earn a falsifiable tier.** The default tier is
   `NON_FALSIFIABLE`. Falsifiability is the thing demonstrated, never assumed.
3. **The proposer never adjudicates.** Whoever extracts a claim — a human, or an
   LLM acting purely as a parser — may only point at verbatim text. Every claim
   is anchored to a span that actually occurs in the source; a quote the source
   does not contain is quarantined as `UNANCHORED`. This is the anti-fabrication
   floor, and it is what makes an LLM safe to use as an extractor: it can
   structure, never assert.
4. **Every verdict is provenance-bound and tamper-evident.** Source text is
   hashed; each record is chained into an append-only ledger. Silently softening
   a recorded verdict breaks the chain.

## Falsifiability tiers (deterministic, auditable)

Classification is lexical and deterministic — never an opinion engine. Each
decision carries the exact signal tokens that triggered it. Precedence,
first match wins:

| # | Tier | Meaning | Route |
|---|------|---------|-------|
| 1 | `DEFINITIONAL` | a stipulation, not a claim about the world | quarantine |
| 2 | `EMPIRICAL_STATISTICAL` | quantitative/statistical content | signal-falsification battery |
| 3 | `EMPIRICAL_GENERAL` | empirical but qualitative | pending operationalization |
| 4 | `LOGICAL` | deductive structure | argument-structure check |
| 5 | `NORMATIVE` | a value/ought claim | quarantine |
| 6 | `NON_FALSIFIABLE` | default | quarantine |

Empirical content outranks deductive form on purpose: a claim with measurable
content is sent to the stricter empirical route rather than being judged only on
the shape of its sentence.

## Dispositions

| Disposition | When |
|-------------|------|
| `SURVIVED_FALSIFICATION` | empirical-statistical claim with data; battery did not refute it |
| `REFUTED` | leakage or null analysis refuted it |
| `UNSUPPORTED` | the null was mis-specified, or rejection was not corroborated |
| `PENDING_EVIDENCE` | falsifiable in principle, but no data/operationalization supplied |
| `DIRECTED_COUPLING_SURVIVED` | causal claim; conditional transfer-entropy test found the claimed direction |
| `DIRECTED_COUPLING_UNCONDITIONED` | same, but no confounder supplied — provisional (a common drive cannot be excluded) |
| `ARGUMENT_STRUCTURE_DETECTED` / `ARGUMENT_STRUCTURE_INCOMPLETE` / `NOT_AN_ARGUMENT` | argument-structure result (structure only — soundness/truth not established) |
| `QUARANTINED_*` | definitional, normative, non-falsifiable, or unanchored |

`SURVIVED_FALSIFICATION` and `DIRECTED_COUPLING_SURVIVED` are the only
dispositions that touch empirical data, and neither means "true".

## The causal route (transfer entropy)

A claim with a causal verb ("drives", "causes", "leads to", "modulates") that
carries a `transfer_entropy` operationalization is routed to the directed
transfer-entropy test (see `docs/TRANSFER_ENTROPY.md`):

```json
{
  "claim_id": "x-drives-y",
  "quote": "activity in region X drives the response in region Y",
  "proposer": "human:yaroslav",
  "operationalization": {
    "test": "transfer_entropy",
    "source": "data/x.npy",
    "target": "data/y.npy",
    "conditions": ["data/z.npy"],
    "k": 2, "cond_lag": 3
  }
}
```

The measured boundary is encoded in the disposition: a survival **without** a
conditioning series is downgraded to `DIRECTED_COUPLING_UNCONDITIONED`, because
pairwise transfer entropy cannot tell a direct coupling from a common drive
(measured false-positive rate ~1.0). A coupling found in the *opposite*
direction `REFUTED`s the claim; none found leaves it `UNSUPPORTED`.

## The argument-structure check

For `LOGICAL` claims the kernel reports whether a quote exposes the parts of an
argument — a premise marker and a conclusion connective. It is a **structural
detector, not a soundness oracle**: it separates a stated inference from a bare
assertion dressed as one. It never rules on whether the premises are correct.

## The truth ledger

Records append to a JSONL ledger whose every entry chains
`stable_sha256(prev_hash, seq, payload)`. `bsff ledger-verify` walks the chain
and reports the first break. The ledger is storage with integrity; it produces
no verdicts of its own.

## Ingestion

`bsff ingest --arxiv <id>` fetches a paper's title and abstract from the arXiv
API and returns them as a provenance-stamped source (byte hash over the
retrieved text). Ingestion supplies text only — it never extracts or judges
claims. Only the abstract is ingested: the highest-density, reliably retrievable
claim surface. Claims stated only in the body require supplying that text
directly; the adapter never fabricates coverage it does not have. Network access
is injected, so the adapter is deterministic and unit-tested offline.

```bash
# Fetch a paper's abstract with provenance
bsff ingest --arxiv 1706.03762 --out source.txt

# Adjudicate claims directly against a freshly ingested arXiv abstract
bsff adjudicate --arxiv 1706.03762 --claims claims.json --ledger ledger.jsonl
```

## Usage

```bash
# Adjudicate the claims of a source against its extracted text
bsff adjudicate \
  --source-text paper.txt \
  --source-id "arXiv:2401.00001" --kind arxiv --uri https://arxiv.org/abs/2401.00001 \
  --claims claims.json \
  --ledger ledger.jsonl \
  --out report.json

# Confirm nothing in the ledger was altered after the fact
bsff ledger-verify --ledger ledger.jsonl
```

`claims.json` is a list of proposed claims:

```json
[
  {
    "claim_id": "c1",
    "quote": "decoding accuracy was 84% (p < 0.01)",
    "proposer": "human:yaroslav",
    "operationalization": {
      "claim_spec": "specs/c1.json",
      "signal": "data/c1.npy",
      "policy": "strict"
    }
  }
]
```

When an empirical-statistical claim carries an `operationalization` (a
`ClaimSpec` plus a signal file), the kernel runs the full fail-closed
falsification battery and embeds the resulting verdict and its case-file hash.
Without it, the claim is honestly held at `PENDING_EVIDENCE` with a manifest of
what is required to test it.

## Batch: a corpus, and accountability for the extraction

Running BSFF against one paper is a spot check; `bsff adjudicate-batch` runs it
against a corpus and consolidates the result into one report and one ledger.

```bash
bsff adjudicate-batch --manifest corpus.json --ledger ledger.jsonl --out batch.json
```

```json
{
  "sources": [
    {"source_id": "arXiv:1706.03762", "source_text": "papers/a.txt", "claims": "claims/a.json"},
    {"arxiv": "2401.00001", "claims": [ {"claim_id": "c1", "quote": "...", "proposer": "llm:gpt"} ]}
  ]
}
```

The report consolidates dispositions and tiers across the corpus **and turns the
lens on the extraction process itself**. A source whose claims mostly fail to
anchor, or a proposer whose proposals are mostly fabricated or non-falsifiable,
is flagged in `integrity_flags` (`HIGH_UNANCHORED_RATE`, `PROPOSER_FABRICATION`,
`PROPOSER_LOW_FALSIFIABILITY`) with per-proposer accountability. The integrity of
the verdicts is no stronger than the integrity of whoever proposed the claims,
and the report refuses to hide that.

## Non-goals (what this kernel does **not** do)

- It does not decide the truth of a claim; it decides what scrutiny a claim
  admits and applies it.
- It does not prove BCI claims true.
- It does not extract claims from a PDF for you; extraction is the proposer's
  job, and every proposed claim must pass the verbatim-anchor gate.
- It does not replace peer review; it makes one auditable, reproducible pass.
