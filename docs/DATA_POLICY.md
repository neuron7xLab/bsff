<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Data policy

## Raw data is NOT committed
The Bonn raw EEG (`.txt` segments) is **gitignored** and never shipped in the repo or
package (license + size). Only manifests, hashes, verdicts, logs, and code are committed.
Verified in CI: `git ls-files | grep bonn_data` must be empty (`bsff evidence verify`).

## Accepted source (Bonn)
- Dataset: Andrzejak et al. 2001 Bonn EEG. **DOI** `10.1103/PhysRevE.64.061907`.
- Canonical source: **UPF NTSA** `https://www.upf.edu/web/ntsa/downloads`
  (`epileptologie-bonn.de` offline since 2024).
- The endpoint is Cloudflare-gated; fetch the per-set zips once via a browser and stage as
  `examples/bonn_bright_line/bonn_data/{A,B,E}/*.txt` (100 segments each, 4096|4097 samples).

## Forbidden derivatives (must never substitute)
- UCI "Epileptic Seizure Recognition" **178-feature** variant.
- Kaggle re-uploads or any undocumented mirror without a hash manifest.

## Expected local layout
```text
examples/bonn_bright_line/bonn_data/
  A/*.txt   B/*.txt   E/*.txt        # 100 files each, single-column ASCII
```

## Verification
`bash examples/bonn_bright_line/download_bonn.sh examples/bonn_bright_line/bonn_data`
verifies counts + sample convention, or writes `FAIL_DOWNLOAD.json` and exits non-zero.
Per-file SHA256 + provenance: `artifacts/bonn_bright_line/DATASET_MANIFEST.json`.

## Reproducibility impact if the source disappears
The committed `DATASET_MANIFEST.json` pins every file's SHA256, so a future copy can be
hash-verified against the exact bytes used for the S2 bright-line. The verdict artifacts
remain valid evidence even if the upstream source moves.
