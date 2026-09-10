"""
Export the exact DP optimal policy as a scenario-tree warm start.

The deterministic-equivalent MIP and the DP solve the same problem. The DP
solves it in seconds; the MIP has to prove optimality over 1093 setup
binaries, which is far slower from a cold start. Handing the MIP the DP's
solution as an incumbent means branch-and-bound only has to close the dual
gap, not also find the answer.

This is a solver convenience, not a shortcut in the result. The MIP still
proves optimality on its own independent formulation; if the two models
disagreed, the warm start would be rejected as infeasible or improved on.

Node ordering matches the MIP builders exactly: breadth-first, root first,
children in demand-support order. Because the tree is enumerated by stage,
the 1093 decision nodes (stage < T) occupy the first 1093 indices.
"""

import json
import os

from exact_dp import step, value, T, INST


def main():
    x0 = tuple(INST["initial_stock"])
    dp_opt = value(0, x0)[0]

    support = [[(int(v), float(p)) for v, p in day] for day in INST["demand_support"]]

    orders = []          # index i -> DP order at decision node i
    level = [x0]         # states at the current stage, in node order
    for t in range(T):
        nxt = []
        for state in level:
            q = value(t, state)[1]
            orders.append(q)
            for d, _ in support[t]:
                _, ns, _ = step(state, q, d)
                nxt.append(ns)
        level = nxt

    out = {
        "orders_by_decision_node": orders,
        "n_decision_nodes": len(orders),
        "dp_optimal": round(dp_opt, 6),
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "..", "results", "dp_policy_tree.json")
    with open(dest, "w") as f:
        json.dump(out, f)
    print(f"exported {len(orders)} decision-node orders")
    print(f"DP optimum {out['dp_optimal']}")
    print(f"first-day order {orders[0]}, distinct order sizes used "
          f"{sorted(set(orders))}")


if __name__ == "__main__":
    main()
