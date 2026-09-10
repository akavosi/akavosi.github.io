"""
Cross-check every number the post claims.

Three independent solvers must agree on the optimal expected profit:
  1. backward stochastic DP over the age-vector state
  2. deterministic-equivalent scenario-tree MIP, modelling layer A
  3. the same formulation rebuilt independently, solver B

They are written separately, use different algorithms, and are compared to
six decimal places. This script fails loudly if any of them drift.
"""

import json
import os
import sys

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")


def load(name):
    with open(os.path.join(RESULTS, name)) as f:
        return json.load(f)


def main():
    dp = load("exact_dp.json")
    mj = load("mip_julia.json")
    mc = load("mip_cpp.json")
    base = load("baselines.json")
    tr = load("traces.json")

    ok = True

    def check(label, a, b, tol=1e-6):
        nonlocal ok
        good = abs(a - b) <= tol
        ok &= good
        print(f"  [{'ok' if good else 'FAIL'}] {label}: {a} vs {b}")

    print("optimal expected profit, three independent methods")
    check("DP vs scenario-tree MIP (A)",
          dp["optimal_expected_profit"], mj["optimal_expected_profit"])
    check("DP vs scenario-tree MIP (B)",
          dp["optimal_expected_profit"], mc["optimal_expected_profit"])
    check("DP vs traces", dp["optimal_expected_profit"],
          tr["policies"]["optimal"]["value"])

    print("\nfirst-day order agrees")
    check("DP vs A", dp["first_order"], mj["first_order"])
    check("DP vs B", dp["first_order"], mc["first_order"])

    print("\nservice outcomes agree between the two MIPs")
    check("expected units wasted", mj["expected_units_wasted"],
          mc["expected_units_wasted"], tol=1e-3)
    check("expected units short", mj["expected_units_lost"],
          mc["expected_units_lost"], tol=1e-3)
    check("expected order days", mj["expected_order_days"],
          mc["expected_order_days"], tol=1e-3)

    print("\nMIP waste/shortage match the independently traced optimal policy")
    check("waste", mj["expected_units_wasted"],
          tr["policies"]["optimal"]["expected_waste"], tol=1e-3)
    check("shortage", mj["expected_units_lost"],
          tr["policies"]["optimal"]["expected_lost"], tol=1e-3)

    # Both MIPs leave issuing completely free, so their feasible set strictly
    # contains every oldest-first plan. Therefore MIP >= DP always. Observing
    # MIP == DP means no free-issuing plan beats oldest-first, which is a
    # proof of FIFO optimality on this instance rather than an assumption.
    print("\noldest-first issuing: proved, not assumed")
    for tag, m in (("A", mj), ("B", mc)):
        slack = m["optimal_expected_profit"] - dp["optimal_expected_profit"]
        print(f"  [{'ok' if abs(slack) <= 1e-6 else 'FAIL'}] model {tag} lets "
              f"the solver issue any age it likes and still gains "
              f"{slack:+.6f} over forced oldest-first")
        ok &= abs(slack) <= 1e-6
    for tag, m in (("A", mj), ("B", mc)):
        print(f"  [info] model {tag}: "
              f"{m['fifo_violations_under_free_issuing']} nodes sit on an "
              f"alternate optimum (a tie, not an improvement)")

    print("\npolicy ranking")
    opt = dp["optimal_expected_profit"]
    ss = base["ss"]["value"]
    rl = base["q_learning"]["best_value"]
    print(f"  exact optimum      {opt:9.4f}")
    print(f"  learned policy     {rl:9.4f}   "
          f"{100*(opt-rl)/opt:5.2f}% below optimum")
    print(f"  best (s,S)         {ss:9.4f}   "
          f"{100*(opt-ss)/opt:5.2f}% below optimum")
    print(f"  learned over (s,S) {100*(rl-ss)/ss:+.2f}%")
    ok &= rl > ss
    ok &= opt >= rl - 1e-9

    print()
    if ok:
        print("ALL CHECKS PASSED")
        return 0
    print("CHECKS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
