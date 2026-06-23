# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Benchmark suite is opt-in: it runs only under `pytest benchmarks`.

Kept out of the default test run (it is timing/throughput measurement, not a
correctness gate) and out of the offline-guard suite. The degradation workflow
invokes it explicitly with --benchmark-json.
"""

from __future__ import annotations
