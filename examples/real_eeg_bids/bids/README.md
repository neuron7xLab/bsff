# BSFF synthetic EEG-shaped BIDS fixture

**This is NOT real recorded EEG.** Every channel is a deterministic
Henon-map trace (a known nonlinear generator), packaged in a minimal
BIDS-EEG layout so the BSFF ingestion path and its four expected-verdict
demonstrations run offline with zero setup. Do not interpret any verdict
on this fixture as a finding about real neural data.

## Layout

```
bids/
  dataset_description.json
  sub-01/eeg/
    sub-01_task-rest_eeg.tsv      # channels x time, raw
    sub-01_task-rest_eeg.json     # sidecar (SamplingFrequency)
    sub-01_task-rest_channels.tsv # channel names/types/units
```

## Pointing at a real dataset

The same loader works on any minimal BIDS-EEG tree. To validate on real
data, download a public dataset (e.g. an OpenNeuro `ds-XXXXXX` EEG
dataset), convert one run's channels-by-time matrix to the `_eeg.tsv`
shape above with its `_eeg.json` (`SamplingFrequency`) and
`_channels.tsv`, then run:

```python
from bsff.bids import run_bids_case
out = run_bids_case('/path/to/ds-XXXXXX', subject='01', task='rest')
```

Record the dataset DOI, version, and checksum in your manifest. BSFF
refuses any file that carries a hidden label column or looks like a
precomputed feature table (see ../../docs/INVALID_USE.md).
