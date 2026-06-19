// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
/**
 * @name Non-deterministic NumPy global RNG
 * @description Calls into numpy.random's legacy global-state API are not
 *              reproducible across processes; a falsification engine must seed
 *              every draw via numpy.random.default_rng(seed).
 * @kind problem
 * @problem.severity warning
 * @precision high
 * @id bsff/non-deterministic-numpy-rng
 * @tags reproducibility
 *       correctness
 *       bsff
 */

import python
import semmle.python.ApiGraphs

from API::CallNode call, string fn
where
  call = API::moduleImport("numpy").getMember("random").getMember(fn).getACall() and
  not fn in ["default_rng", "Generator", "SeedSequence", "BitGenerator", "PCG64", "Philox"]
select call,
  "Non-deterministic numpy.random." + fn + "() global-state call; route through default_rng(seed)."
