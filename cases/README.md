# BSFF Cases

A **case** is BSFF aimed at a famous, externally-recognizable claim — not synthetic
self-validation. Each case is a self-contained, reproducible attack: a falsifiable
reduction of the claim, a pre-registered split/control battery, and a machine-readable,
hash-bound verdict (`SURVIVED | REFUTED | UNSUPPORTED`).

Every case ships:

| file | role |
|---|---|
| `CLAIM.md` | the target claim + its falsifiable reduction + pre-registered criterion |
| `METHOD.md` | the probes and controls, each with an expected outcome |
| `RESULTS.md` | the metrics table for the committed reference run |
| `REPORT.md` | the human-readable narrative + honest scope |
| `VERDICT.json` | machine-readable verdict + statistics + `artifact_sha256` |
| `MANIFEST.json` | environment, command, data provenance |
| `run_case.py` | the executable harness (offline ground-truth + real-data modes) |

The discipline: a case never emits `TRUE`; controls can only demote a verdict toward
`UNSUPPORTED`; and the harness is shown to be two-sided on labelled ground truth before
it is aimed at real data.

## Index

| case | target | verdict |
|---|---|---|
| [001 — PhysioNet EEGNet generalization](001_physionet_eegnet/) | Does within/global-validation motor-imagery accuracy reflect *generalizable* decoding? | **REFUTED** |

## Running a case

```bash
# Offline, deterministic ground-truth demonstration (CI-checked):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source synthetic --config headline --out /tmp/case001

# Real data (user runtime; needs network + optional extras):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source physionet --subjects 1-9 --out artifacts/case001_real
```
