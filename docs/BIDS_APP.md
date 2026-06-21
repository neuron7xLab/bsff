<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

<!--
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
-->

# BSFF BIDS-App contract

BSFF exposes its real-data falsification path through a
[BIDS-App](https://bids-apps.neuroimaging.io/)-style command. The CLI is wired by
the orchestrator to `bsff.bids.run_bids_case`; this document specifies the
intended interface and the reproducibility manifest so a run is verifiable from
hash-locked inputs.

## Command

```
bsff bids-app \
    --bids-dir   <path to a BIDS-EEG dataset> \
    --output-dir <path for the verdict + manifest> \
    --participant-label <subject id, e.g. 01> \
    [--task <task, e.g. rest>] \
    [--seed <int, default 123>] \
    [--policy <smoke|standard|strict, default standard>]
```

Following the BIDS-App convention, `--bids-dir` and `--output-dir` are the
primary positional contract and `--participant-label` selects the subject
(`sub-<label>`). `--task` is optional when the subject has exactly one task; it is
**required** when several are present (ingestion refuses an ambiguous layout
rather than guessing).

The command maps directly onto the library call:

```python
from bsff.bids import run_bids_case
out = run_bids_case(
    bids_dir, subject="01", task="rest", seed=123, policy="standard",
)
# out["verdict"]  -> machine-readable verdict (VerdictJSON.to_dict())
# out["manifest"] -> reproducibility manifest (below)
```

The verdict is produced by the **real** fail-closed engine
(`bsff.verdict_engine.evaluate_claim`), through the same leakage-first /
surrogate-test / stationarity-gate logic as every other BSFF entry point.

## Reproducibility manifest

`out["manifest"]` (schema `bsff.bids_manifest/v1`) carries the fields that make a
run independently reproducible:

| Field                       | Meaning                                               |
| --------------------------- | ----------------------------------------------------- |
| `command`                   | the exact `bsff bids-app ...` invocation              |
| `policy`, `seed`            | profile + RNG seed (determinism inputs)               |
| `inputs.data_file`          | resolved path to the raw `_eeg.tsv[.gz]`              |
| `inputs.data_sha256`        | **input hash** — sha256 of the raw data file          |
| `inputs.sampling_frequency` | sampling rate from the `_eeg.json` sidecar            |
| `inputs.channels`           | declared electrode channels                            |
| `software_versions`         | bsff + numpy/scipy/statsmodels (importlib.metadata)   |
| `claim`                     | the resolved, validated `ClaimSpec`                   |

When run inside the container (below), pair the manifest with the **image
digest** (`docker inspect --format '{{index .RepoDigests 0}}' <image>`) and the
**output hash** (sha256 of `verdict.json`) for a full input→image→output chain.

## Containerized reproduction

The shipped [`Dockerfile`](../Dockerfile) builds a pinned `python:3.12-slim`
image with the package installed as `.[dev,leakage]` and `bsff` as the
entrypoint. A run started from this image reproduces a verdict from hash-locked
inputs:

```
docker build -t bsff:local .
docker run --rm \
    -v "$PWD/examples/real_eeg_bids/bids:/data:ro" \
    -v "$PWD/out:/out" \
    bsff:local bids-app \
        --bids-dir /data --output-dir /out --participant-label 01 --task rest
```

Because the base tag is pinned and the dataset is mounted read-only, the same
image digest + same `--bids-dir` (same `data_sha256`) + same seed reproduce an
identical core verdict. The DataLad wrapper in
[`DATALAD_PROVENANCE.md`](DATALAD_PROVENANCE.md) records this chain end to end.
