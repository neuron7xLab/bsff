<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Real-claims corpus — falsifiability triage on the public record

BSFF aimed at claims that are part of the public record, not a fabricated demo.

```bash
python examples/real_corpus/run_corpus.py            # render + ledger
# or, equivalently, the shipped CLI:
bsff adjudicate-batch --manifest examples/real_corpus/corpus.json --ledger out/ledger.jsonl
```

## The verdicts

| claim (verbatim, abbreviated) | tier | verdict |
|---|---|---|
| planets at birth **determine** character and life outcomes (astrology) | empirical | `PENDING_EVIDENCE` |
| a remedy with no molecule left still **produces a measurable effect** (homeopathy) | empirical | `PENDING_EVIDENCE` |
| the MMR vaccine **causes** autism (Lancet 1998, **retracted**) | empirical | `PENDING_EVIDENCE` |
| consciousness is a field **no instrument can ever detect** | non-falsifiable | **`QUARANTINED_NON_FALSIFIABLE`** |
| everyone **should** use crystals instead of medicine | normative | **`QUARANTINED_NORMATIVE`** |
| intelligent design **is defined as** ... | definitional | **`QUARANTINED_DEFINITIONAL`** |

## What this shows — and what it does not

The sharp result: claims that **forbid their own test** (the consciousness field),
that are **value judgements** (crystals), or that are **definitional dodges**
(intelligent design) are killed outright — no data required, because
unfalsifiability *is* the verdict. This is the Popperian signature of
pseudoscience, caught by form.

The honest boundary: the empirically phrased claims (astrology, homeopathy, the
retracted MMR paper) are **not** fake-killed. BSFF holds them at
`PENDING_EVIDENCE` and names what would settle them — their raw datasets.
Refuting them is a data exercise, and this repository does not invent data it
does not have. A claim being on a retracted paper is recorded as provenance, not
treated as a shortcut to a verdict.

Source texts here are curated, verbatim claim records with citation metadata in
`corpus.json`; the verbatim anchor proves the claim was not altered between the
corpus file and the verdict, not that it was fetched byte-for-byte from the
original publication. Every verdict is appended to a hash-chained ledger that
`bsff ledger-verify` confirms untampered, and rendered to `report.html` /
`report.md` for human reading.
