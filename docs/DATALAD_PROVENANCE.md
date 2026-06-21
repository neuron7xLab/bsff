<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

<!--
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
-->

# DataLad provenance for BSFF runs

[DataLad](https://www.datalad.org/) records the inputs, command, and outputs of a
computation so a verdict can be re-derived and audited. This document shows how to
wrap a BSFF BIDS-App run in DataLad and how that maps onto BSFF's own
reproducibility manifest (see [`BIDS_APP.md`](BIDS_APP.md)).

DataLad is **optional** — BSFF's manifest already hashes inputs and records
software versions. DataLad adds dataset-level version pinning and a re-runnable
provenance record on top.

## Wrapping a run with `datalad run`

```bash
# 1. Create (or clone) a dataset for the outputs.
datalad create -c text2git bsff-runs
cd bsff-runs

# 2. Install the input BIDS dataset as a versioned subdataset (e.g. OpenNeuro).
datalad install -d . -s https://github.com/OpenNeuroDatasets/dsXXXXXX.git inputs/bids

# 3. Run BSFF with provenance capture. DataLad records the command, the exact
#    input file content, and the produced outputs.
datalad run \
    -m "BSFF falsification of sub-01 task-rest" \
    --input  "inputs/bids/sub-01/eeg/*" \
    --output "out/verdict.json" \
    --output "out/manifest.json" \
    "bsff bids-app --bids-dir inputs/bids --output-dir out \
        --participant-label 01 --task rest --seed 123 --policy standard"
```

`datalad rerun` then re-executes the recorded command against the pinned inputs
and fails loudly if the outputs differ — the dataset-level twin of BSFF's own
core-verdict reproducibility check.

## Containerized provenance with `datalad containers-run`

To pin the *software* as well as the data, register the BSFF image (built from the
shipped [`Dockerfile`](../Dockerfile)) and run through it:

```bash
datalad containers-add bsff --url dhub://bsff:local   # or a registry digest
datalad containers-run -n bsff \
    -m "BSFF (pinned image) falsification of sub-01 task-rest" \
    --input  "inputs/bids/sub-01/eeg/*" \
    --output "out/verdict.json" \
    --output "out/manifest.json" \
    "bids-app --bids-dir inputs/bids --output-dir out \
        --participant-label 01 --task rest"
```

This captures the **image digest** alongside the input/output content, giving the
full input → image → command → output chain.

## Mapping to the BSFF manifest

DataLad provenance and the BSFF `bsff.bids_manifest/v1` manifest overlap and
reinforce each other:

| BSFF manifest field         | DataLad equivalent                              |
| --------------------------- | ----------------------------------------------- |
| `inputs.data_sha256`        | content hash of the pinned input file           |
| `command`                   | the recorded `datalad run` command              |
| `software_versions`         | the registered container image digest           |
| `inputs.bids_dir` (+ subds) | the input subdataset version (commit id)        |
| output `verdict.json` hash  | the recorded output content hash                |

Keep both: BSFF's manifest is portable and dependency-free (it travels with the
verdict JSON), while DataLad provides repository-level versioning and a
push-button `rerun` audit.
