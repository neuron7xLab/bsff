// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
/**
 * @name Exception handler silently swallows errors
 * @description A pass-only except body hides failures. A fail-closed engine must
 *              surface or re-raise, not swallow — a silenced error is a verdict
 *              computed from corrupted state.
 * @kind problem
 * @problem.severity warning
 * @precision high
 * @id bsff/silent-exception-swallow
 * @tags reliability
 *       correctness
 *       bsff
 */

import python

from ExceptStmt ex
where
  exists(ex.getAStmt()) and
  forall(Stmt s | s = ex.getAStmt() | s instanceof Pass)
select ex, "Exception handler silently swallows errors (pass-only body); fail closed instead."
