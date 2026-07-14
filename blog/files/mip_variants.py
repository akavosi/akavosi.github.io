"""
mip_variants.py
================
Not part of the paper's codebase. This is a demo-only fork of
solve_sqep_mip() from sqep_mip.py, with two individual constraints
toggle-able, so the blog post can show *numerically* what breaks when
each one is removed:

  drop_upper_block=True   -> removes constraint (8), z_ij <= 1 - x_k
                              for every blocker k (the blocking upper
                              bound).
  drop_lower_force=True   -> removes constraint (9), the inequality that
                              forces z_ij up to 1 whenever i,j are both
                              alive, attacking, and unblocked (the
                              "you must admit this cost" lower bound).

Everything else (objective, (6)-(7), (10)-(16)) is identical to
solve_sqep_mip(). Only used to generate the three side-by-side numbers
in the "Inside the MIP" post; sqep_mip.py itself is untouched.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pulp

from sqep_model import BoardData


@dataclass
class VariantResult:
    status: str
    objective: Optional[float]
    activation_sequence: List[int]


def solve_variant(bd: BoardData, H: Optional[int] = None,
                   drop_upper_block: bool = False,
                   drop_lower_force: bool = False,
                   msg: bool = False) -> VariantResult:
    n = bd.n
    if H is None:
        H = max(n - 1, 1)
    a = bd.attack
    is_blocker = [[set(bd.blockers[i][j]) for j in range(n)] for i in range(n)]

    prob = pulp.LpProblem("SQEP_variant", pulp.LpMinimize)
    T0 = range(0, H + 1)
    T1 = range(1, H + 1)

    x = {(t, i): pulp.LpVariable(f"x_{t}_{i}", cat="Binary") for t in T0 for i in range(n)}
    y = {(t, i): pulp.LpVariable(f"y_{t}_{i}", cat="Binary") for t in T1 for i in range(n)}
    z = {(t, i, j): pulp.LpVariable(f"z_{t}_{i}_{j}", cat="Binary")
         for t in T1 for i in range(n) for j in range(n) if i < j}
    u = {(t, i, j): pulp.LpVariable(f"u_{t}_{i}_{j}", cat="Binary")
         for t in T1 for i in range(n) for j in range(n) if i != j}
    beta = {(t, i): pulp.LpVariable(f"beta_{t}_{i}", cat="Binary") for t in T1 for i in range(n)}
    v = {(t, i): pulp.LpVariable(f"v_{t}_{i}", cat="Binary") for t in T1 for i in range(n)}

    def zpair(t, i, j):
        lo, hi = (i, j) if i < j else (j, i)
        return z[(t, lo, hi)]

    prob += pulp.lpSum(z[(t, i, j)] for t in T1 for i in range(n) for j in range(n) if i < j)

    for i in range(n):
        prob += x[(0, i)] == 1

    for t in T1:
        prob += pulp.lpSum(y[(t, i)] for i in range(n)) == 1
        for i in range(n):
            prob += y[(t, i)] <= x[(t - 1, i)]

        for i in range(n):
            for j in range(n):
                if i >= j:
                    continue
                prob += z[(t, i, j)] <= (1 if a[i][j] else 0)
                prob += z[(t, i, j)] <= x[(t - 1, i)]
                prob += z[(t, i, j)] <= x[(t - 1, j)]
                if not drop_upper_block:
                    for k in is_blocker[i][j]:
                        prob += z[(t, i, j)] <= 1 - x[(t - 1, k)]
                if not drop_lower_force:
                    block_sum = pulp.lpSum(x[(t - 1, k)] for k in is_blocker[i][j])
                    prob += z[(t, i, j)] >= (x[(t - 1, i)] + x[(t - 1, j)]
                                             + (1 if a[i][j] else 0) - 2 - block_sum)

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                zt = zpair(t, i, j)
                prob += u[(t, i, j)] <= y[(t, i)]
                prob += u[(t, i, j)] <= zt
                prob += u[(t, i, j)] >= y[(t, i)] + zt - 1

        for j in range(n):
            prob += x[(t, j)] == x[(t - 1, j)] - pulp.lpSum(u[(t, i, j)] for i in range(n) if i != j)

        for i in range(n):
            for j in range(n):
                if j == i:
                    continue
                prob += beta[(t, i)] >= zpair(t, i, j)
            prob += beta[(t, i)] <= pulp.lpSum(zpair(t, i, j) for j in range(n) if j != i)

        for i in range(n):
            prob += v[(t, i)] <= y[(t, i)]
            prob += v[(t, i)] <= beta[(t, i)]
            prob += v[(t, i)] >= y[(t, i)] + beta[(t, i)] - 1

        for k in range(n):
            rhs = n * (1 - x[(t - 1, k)]) + n * pulp.lpSum(v[(t, i)] for i in range(n))
            prob += pulp.lpSum(zpair(t, k, j) for j in range(n) if j != k) <= rhs

    solver = pulp.PULP_CBC_CMD(msg=msg)
    prob.solve(solver)
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return VariantResult(status=status, objective=None, activation_sequence=[])

    seq = []
    for t in T1:
        for i in range(n):
            if round(y[(t, i)].value()) == 1:
                seq.append(i)
                break
    return VariantResult(status=status, objective=pulp.value(prob.objective), activation_sequence=seq)


if __name__ == "__main__":
    from sqep_model import build_board_data

    positions = [(0, 0), (0, 2), (0, 3), (3, 0)]
    bd = build_board_data(4, positions)

    correct = solve_variant(bd)
    no_upper = solve_variant(bd, drop_upper_block=True)
    no_lower = solve_variant(bd, drop_lower_force=True)

    print("Full model         (7)-(16):   objective =", correct.objective, " sequence =", correct.activation_sequence)
    print("Drop (8) only, keep (9):        objective =", no_upper.objective, " sequence =", no_upper.activation_sequence)
    print("Drop (9) only, keep (8):        objective =", no_lower.objective, " sequence =", no_lower.activation_sequence)
