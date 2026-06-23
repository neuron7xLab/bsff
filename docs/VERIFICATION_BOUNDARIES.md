<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Verification boundaries — where each gate could lie

A system that cannot lie must declare where it cannot see. Every gate has a domain
outside which a green result is not a truth claim. This ledger enumerates each
gate's **false-PASS boundary** (the dangerous direction: reporting PASS while the
underlying property is false), the bound that contains it, and its mitigation. The
declared constants here are **bound to the implementation** by
`tests/test_verification_boundaries.py`: a gate cannot silently become more
permissive than it declares.

| Gate | Could falsely PASS when… | Bound / mitigation |
|---|---|---|
| `network_guard` (offline) | code egresses via a path it does not patch (raw sockets opened in C extensions, `os`-level fds) | patches `connect`/`connect_ex`/`sendto`/`create_connection` for `AF_INET`/`AF_INET6`; loopback + `AF_UNIX` allowed. Python-level socket egress is covered; native-code sockets are out of scope and declared. |
| `mutation_kill_gate` | a mutant breaks **collection** (exit 2) rather than the **assertion** (exit 1), so "killed" would not mean the test caught the behaviour | a kill requires pytest exit code **1**; exit ∈ {2,3,4,5} aborts the gate as an invalid mutant. Baseline-green guard rejects a broken sandbox. |
| `compare_benchmark_baseline` (degradation) | a real wall-time regression below **2×**, or any regression in a **sub-500µs** micro-op | wall-time gated only ≥ `TIME_NOISE_FLOOR_S` at `TIME_THRESHOLD`; cross-machine micro-timing is noise-dominated. Peak **memory** (allocation-counted) is machine-independent and gated at `MEMORY_THRESHOLD`. |
| `statistical_power_profile` | a specificity regression that the **fixed seed battery** (N_null) does not happen to trigger | deterministic fixed-seed Monte-Carlo (N_null, N_positive); point estimate, not a confidence bound. Nightly may scale N. |
| `final_validation_verdict` | it reads **committed** evidence that is stale vs current code | mutation freshness cross-checks live mutant-ids; corpus completeness ≥ 14; baseline structurally validated; API imported, not file-checked. The live per-dimension grid jobs (which `13-final-verdict` `needs`) are the authoritative gates — the roll-up is bounded by that dependency. |
| `validate_lockfiles` | a lock pins+hashes a line whose hash is wrong, or omits a transitive dep | hash **correctness** and **completeness** are enforced downstream by `pip install --require-hashes` (fails loudly), not by this structural gate. |
| `validate_provenance` (SBOM hash) | committed SBOM bytes match their committed manifest **by construction** (tautological at commit time) | catches post-commit tampering; the structural `generate_sbom --check` independently validates the live closure. Keyless Sigstore signature is minted on push/release, not PR. |

## Falsification record (active break attempts)

A mutation score is only honest if the mutants were not hand-picked to be easy. A
falsification sweep applied five *new* subtle statistical/boundary mutants outside
the curated set. Four "survived" the first attempt — and that is the point: the
claim "the suite has teeth" only exists after surviving an attack.

| Mutant | Verdict | Resolution |
|---|---|---|
| rank-order ties `>=` → `>` | **real gap** | a flat signal would falsely "reject the null" and SURVIVE; closed by `test_degenerate_signal_not_falsely_rejected` + **MUT-009** (now 9/9) |
| drop `surrogate.status == "SKIP"` branch | equivalent | unreachable: a SKIP surrogate is always preceded by a fatal FAIL → REFUTED first (verified) |
| BF10 corroboration `<` → `<=` | equivalent | exact-equality boundary `BF10 == threshold` is measure-zero on a continuous Bayes factor |
| stationarity `p > alpha` → `>=` | equivalent | exact-equality boundary `p == alpha` is measure-zero on interpolated KPSS p-values |

Equivalent mutants are declared, not hidden: the mutation-kill claim is "every
*non-equivalent behavioural* mutant is killed", with the equivalences reasoned above.

## Principle

No gate is claimed to verify more than its domain. Where a property is not
mechanically decidable cross-environment (micro-timing, native-socket egress,
fixed-seed coverage), the boundary is named here and bound to the code, rather than
implied away by a green badge.
