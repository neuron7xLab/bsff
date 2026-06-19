// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
/**
 * @name default_rng called without a seed
 * @description numpy.random.default_rng() with no seed draws from OS entropy and
 *              is not reproducible; every generator in a deterministic pipeline
 *              must be seeded.
 * @kind problem
 * @problem.severity warning
 * @precision high
 * @id bsff/default-rng-without-seed
 * @tags reproducibility
 *       correctness
 *       bsff
 */

import python
import semmle.python.ApiGraphs

from API::CallNode call
where
  call = API::moduleImport("numpy").getMember("random").getMember("default_rng").getACall() and
  not exists(call.getArg(0)) and
  not exists(call.getArgByName("seed"))
select call, "numpy.random.default_rng() called with no seed; output is non-reproducible."
