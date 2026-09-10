"""
Produce the per-day traces every figure is drawn from.

For each policy, this walks the full 128-scenario tree and accumulates
probability-weighted expected quantities per day:

  - inventory by exact age at end of day  (the stacked-area flagship)
  - units wasted, lost, sold, ordered     (the cost-component chart)
  - the realised age histogram            (the filmstrip)

Everything is an exact expectation over the tree, not a sample average,
so the figures carry no Monte Carlo noise.
"""

import json
import os
import random

from exact_dp import step, value, M, T, INST
from baselines import make_ss, train_q, evaluate, X0, SUPPORT

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "results")


def trace(policy_fn):
    """Expected end-of-day age profile and cost components, per day."""
    age = [[0.0] * M for _ in range(T)]      # age[t][a] expected units of age a+1
    comp = {k: [0.0] * T for k in
            ("revenue", "purchase", "setup", "holding", "shortage", "wastage",
             "sold", "waste_units", "lost_units", "ordered", "onhand")}

    def walk(t, state, prob):
        if t == T:
            return
        q = policy_fn(t, state)
        comp["ordered"][t] += prob * q
        comp["purchase"][t] += prob * INST["purchase"] * q
        comp["setup"][t] += prob * INST["setup"] * (1 if q > 0 else 0)
        for d, p in SUPPORT[t]:
            pr = prob * p
            _, nxt, (sold, lost, waste, end_inv) = step(state, q, d)
            comp["revenue"][t] += pr * INST["price"] * sold
            comp["holding"][t] += pr * INST["holding"] * end_inv
            comp["shortage"][t] += pr * INST["shortage"] * lost
            comp["wastage"][t] += pr * INST["wastage"] * waste
            comp["sold"][t] += pr * sold
            comp["waste_units"][t] += pr * waste
            comp["lost_units"][t] += pr * lost
            comp["onhand"][t] += pr * end_inv
            # nxt is the *aged* profile; report the pre-ageing end-of-day one
            stock = list(state)
            stock[0] += q
            rem = d
            for a in range(M - 1, -1, -1):
                take = min(stock[a], rem)
                stock[a] -= take
                rem -= take
            stock[M - 1] = 0                 # scrapped
            for a in range(M):
                age[t][a] += pr * stock[a]
            walk(t + 1, nxt, pr)

    walk(0, X0, 1.0)
    return age, comp


def single_path(policy_fn, demand_path):
    """One deterministic walk, for the filmstrip. Returns per-day detail."""
    state = X0
    days = []
    for t in range(T):
        q = policy_fn(t, state)
        d = demand_path[t]
        stock = list(state)
        stock[0] += q
        rem, sales = d, [0] * M
        for a in range(M - 1, -1, -1):
            take = min(stock[a], rem)
            stock[a] -= take
            rem -= take
            sales[a] = take
        lost = d - sum(sales)
        waste = stock[M - 1]
        stock[M - 1] = 0
        days.append({"day": t + 1, "order": q, "demand": d,
                     "end_age": list(stock), "sales_by_age": sales,
                     "lost": lost, "waste": waste})
        _, state, _ = step(state, q, d)
    return days


def main():
    opt_pol = lambda t, s: value(t, tuple(s))[1]

    base = json.load(open(os.path.join(RESULTS, "baselines.json")))
    ss_pol = make_ss(base["ss"]["s"], base["ss"]["S"])

    best_seed = max(base["q_learning"]["runs"], key=lambda r: r["value"])["seed"]
    print(f"retraining RL on best seed {best_seed} ...")
    rl_pol, _ = train_q(best_seed)

    policies = {"optimal": opt_pol, "ss": ss_pol, "rl": rl_pol}
    out = {"policies": {}, "meta": {
        "shelf_life": M, "horizon": T,
        "ss_params": [base["ss"]["s"], base["ss"]["S"]],
        "rl_seed": best_seed,
        "exact_optimum": base["exact_optimum"],
    }}

    # A representative demand path for the filmstrip: the midweek peak
    # realises high, the weekend realises low. This is one of the 128
    # scenarios, probability 1/128, not an average.
    demand_path = [INST["demand_support"][t][1 if t <= 3 else 0][0]
                   for t in range(T)]
    out["meta"]["filmstrip_demand"] = demand_path

    for name, pol in policies.items():
        age, comp = trace(pol)
        v, stats = evaluate(pol)
        out["policies"][name] = {
            "value": round(v, 6),
            "age_by_day": [[round(x, 6) for x in row] for row in age],
            "components": {k: [round(x, 6) for x in v2] for k, v2 in comp.items()},
            "filmstrip": single_path(pol, demand_path),
            "expected_waste": round(stats["waste"], 4),
            "expected_lost": round(stats["lost"], 4),
        }
        print(f"  {name:8} value {v:9.4f}  waste {stats['waste']:.3f}  "
              f"lost {stats['lost']:.3f}")

    with open(os.path.join(RESULTS, "traces.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("wrote traces.json")


if __name__ == "__main__":
    main()
