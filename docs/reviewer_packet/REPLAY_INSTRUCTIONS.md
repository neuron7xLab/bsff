# OpenAI-2026 Validation Grid — Replay Instructions

> **Disclaimer.** The "OpenAI-2026 Validation Grid" is an **internal
> OpenAI-grade research-validation target**, **NOT** an OpenAI certification.
> BSFF is **not affiliated with, certified by, or endorsed by OpenAI.** These
> steps reproduce **machine-derived PASS/FAIL evidence** locally; they confer no
> external certification.

Exact, copy-pasteable steps to reproduce the verdict from a clean checkout.

---

## 1. Clean checkout + hermetic install

```bash
git clone <repo-url> bsff
cd bsff

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip

# Hash-pinned, hermetic dependency closure (must match dependency_lock_hashes).
python -m pip install --require-hashes -r requirements/ci.lock

# Install the project itself without re-resolving dependencies.
python -m pip install --no-deps -e .
```

> `--require-hashes` fails closed: if any wheel's sha256 does not match
> `requirements/ci.lock`, installation aborts. This is gate `01-lock-integrity`.

---

## 2. Run the full grid

```bash
make openai-2026
```

This chains the Makefile targets `lock`, `verify-offline`, `build-proof`, and
`verify`, ending on `tools/final_validation_verdict.py`, which writes the
canonical verdict:

```
artifacts/final/openai_2026_validation_verdict.json
```

To run only the verdict derivation (after the gates have produced their
artifacts):

```bash
python tools/final_validation_verdict.py \
  --output artifacts/final/openai_2026_validation_verdict.json
```

The verdict is written deterministically (`json.dumps(..., sort_keys=True)`), so
two runs over identical inputs produce byte-identical output. The process exits
`0` on PASS and `1` on FAIL.

---

## 3. Verify artifact digests by hand

The verdict embeds `artifact_digests` (sha256 of every evidence artifact) and
`dependency_lock_hashes` (sha256 of every lockfile). Recompute and compare:

```bash
# Lockfile hashes (compare each against dependency_lock_hashes in the verdict).
sha256sum requirements/*.lock

# Evidence artifact hashes (compare against artifact_digests in the verdict).
sha256sum \
  artifacts/adversarial/mutation_kill_report.json \
  artifacts/adversarial/corpus_matrix.json \
  artifacts/statistics/power_profile.json \
  artifacts/benchmarks/baseline.json \
  artifacts/redteam/redteam_matrix.json \
  artifacts/replay/replayability_report.json \
  artifacts/hermetic/offline_evidence.json
```

Cross-check programmatically:

```bash
python - <<'PY'
import hashlib, json, pathlib
v = json.loads(pathlib.Path("artifacts/final/openai_2026_validation_verdict.json").read_text())
paths = {
    "mutation_kill_report": "artifacts/adversarial/mutation_kill_report.json",
    "corpus_matrix":        "artifacts/adversarial/corpus_matrix.json",
    "power_profile":        "artifacts/statistics/power_profile.json",
    "benchmark_baseline":   "artifacts/benchmarks/baseline.json",
    "redteam_matrix":       "artifacts/redteam/redteam_matrix.json",
    "replayability_report": "artifacts/replay/replayability_report.json",
    "offline_evidence":     "artifacts/hermetic/offline_evidence.json",
}
for name, p in paths.items():
    got = hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    exp = v["artifact_digests"].get(name)
    print(f"{name:24s} {'OK' if got == exp else 'MISMATCH'}  {got}")
PY
```

Any mismatch means the evidence was altered after the verdict was computed —
gate `18-artifact-digest-binding` would force FAIL. Compare your local verdict
JSON against the CI-uploaded `openai-2026-final-verdict` artifact; they should be
identical at the same `head_sha`.

---

## 4. How the 14-replayability gate works

The replayability gate (`gate 14`) re-runs the **deterministic subset** across
**≥3 RNG seeds** and records the result in
`artifacts/replay/replayability_report.json`. The verdict derivation
(`tools/final_validation_verdict.py`, `_replayability()`) requires all of:

- `len(seeds) >= 3` — at least three distinct seed sets were exercised;
- `verdict_class_stable == true` — the PASS/FAIL class is identical across every
  seed set (no seed-dependent flips);
- `artifact_hashes_match == true` — the deterministic artifacts hash identically
  across seeds;
- the report's own `verdict == "PASS"`.

If any of these is false, `replayable` is `false`, the gate FAILs, and the final
verdict is FAIL. The exercised seeds are surfaced in the verdict's
`seed_manifest.seeds`. To reproduce manually, run the deterministic gates under
each seed (e.g. the fuzz targets use `--seed 2026`; vary it across ≥3 values)
and confirm the verdict class and deterministic-artifact hashes do not change.
