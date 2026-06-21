<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Release certificate — independent streams chained into one root

BSFF's verifiers are independent: the honesty gate, the self-falsification
controls, the null/threshold registries, the conformance check, the
demonstration. Each, alone, proves a *local* property.

`tools/certify_release.py` integrates them: every stream's verdict and its
evidence hash are folded into a hash chain, where each link carries the previous
root. The head hash therefore certifies the **whole ordered chain at once** — a
property no individual gate has:

- change any stream's evidence → its link hash changes → the **root changes**;
- reorder or drop a stream → the chain's `prev_hash` linkage **breaks**.

```bash
python tools/certify_release.py            # chain the streams -> root + CERTIFICATE.json
python tools/certify_release.py --verify    # recompute; CERTIFIED iff intact AND all streams green
```

## Emergent state

No single verifier can attest "the entire verification ran, in order, untampered".
The chained root can. It is the integration the parts could not reach alone:
one deterministic 64-hex root that stands for the conjunction of every stream in
sequence. Tamper-evidence is global, not per-gate.

## Scale

The chain extends like an append-only ledger: add a stream today, or a per-case
verdict later, and the root advances deterministically. Throughput grows by
appending links, not by rewriting the whole.

## Honest scope

The certificate is a **runtime proof**, not a committed claim — its root embeds
live values (e.g. the generated test count), so it is regenerated on demand and
in CI rather than frozen in the tree. It certifies the feasible streams; the
network/GPU-blocked case-001 work is `UNVERIFIABLE` inside `self_conformance`
(named, not faked), so a `CERTIFIED` root means *every feasible promise holds and
the chain is intact* — never that the blocked work is done.
