"""
Two policies that do not know the value function.

1. (s,S) base-stock. The standard perishable-inventory heuristic, and the
   thing practitioners actually run. It sees ONE number: total units on
   hand. If that total drops to or below s, order up to S. It is blind to
   age, which is precisely the point of the comparison -- five units that
   expire tonight look identical to five fresh ones.

   Both parameters are found by exhaustive grid search over the full
   0 <= s < S <= 36 grid, each candidate evaluated by exact enumeration of
   all 128 demand scenarios. So this is the BEST (s,S) policy on this
   instance, not a strawman with hand-picked numbers.

2. Tabular Q-learning over the age vector. Sees the whole age profile, so
   unlike (s,S) it *can* represent an age-aware rule. It learns from
   sampled episodes only -- no transition model, no value iteration.

Every policy is finally scored the same way: exact expected profit by
enumerating all 128 scenarios with their exact probabilities. No sampling
noise in any reported number.
"""

import json
import os
import random
from itertools import product

from exact_dp import step, value, M, T, INST

SUPPORT = [[(int(v), float(p)) for v, p in day] for day in INST["demand_support"]]
X0 = tuple(INST["initial_stock"])
QMAX = INST["order_cap"]
CAP = INST["inventory_cap"]


def evaluate(policy_fn):
    """Exact expected profit by full enumeration of the 128-scenario tree."""
    total = 0.0
    stats = {"waste": 0.0, "lost": 0.0, "sold": 0.0, "orders": 0.0}
    frontier = {(X0, 0.0): 1.0}          # (state, profit-so-far) -> prob
    dist = {X0: (1.0, 0.0)}

    def walk(t, state, prob, acc):
        nonlocal total
        if t == T:
            total += prob * acc
            return
        q = policy_fn(t, state)
        if q > 0:
            stats["orders"] += prob
        for d, p in SUPPORT[t]:
            profit, nxt, (sold, lost, waste, _) = step(state, q, d)
            stats["waste"] += prob * p * waste
            stats["lost"] += prob * p * lost
            stats["sold"] += prob * p * sold
            walk(t + 1, nxt, prob * p, acc + profit)

    walk(0, X0, 1.0, 0.0)
    return total, stats


# ----------------------------------------------------------------- (s,S)
def make_ss(s, S):
    def pol(t, state):
        on_hand = sum(state)
        if on_hand <= s:
            return min(S - on_hand, QMAX, CAP - on_hand)
        return 0
    return pol


def best_ss():
    best = (-1e18, None, None)
    for S in range(1, CAP + 1):
        for s in range(0, S):
            v, _ = evaluate(make_ss(s, S))
            if v > best[0]:
                best = (v, s, S)
    return best


# --------------------------------------------------- tabular Q-learning
def train_q(seed, episodes=200_000, alpha=0.10, gamma=1.0,
            eps_start=1.0, eps_end=0.02):
    rng = random.Random(seed)
    Q = {}

    def qrow(t, s):
        key = (t, s)
        if key not in Q:
            cap = min(QMAX, CAP - sum(s))
            Q[key] = [0.0] * (max(cap, 0) + 1)
        return Q[key]

    for ep in range(episodes):
        eps = eps_start + (eps_end - eps_start) * (ep / episodes)
        state, t = X0, 0
        while t < T:
            row = qrow(t, state)
            if rng.random() < eps:
                a = rng.randrange(len(row))
            else:
                a = max(range(len(row)), key=row.__getitem__)
            d, _ = SUPPORT[t][0] if rng.random() < 0.5 else SUPPORT[t][1]
            r, nxt, _ = step(state, a, d)
            future = 0.0 if t + 1 == T else max(qrow(t + 1, nxt))
            row[a] += alpha * (r + gamma * future - row[a])
            state, t = nxt, t + 1

    def pol(t, state):
        row = qrow(t, state)
        return max(range(len(row)), key=row.__getitem__)

    return pol, Q


def main():
    opt = value(0, X0)[0]

    print("grid-searching (s,S) over all 0 <= s < S <= 36 ...")
    ss_val, s_star, S_star = best_ss()
    ss_pol = make_ss(s_star, S_star)
    _, ss_stats = evaluate(ss_pol)
    print(f"  best (s,S) = ({s_star},{S_star})  expected profit {ss_val:.6f}")

    print("training tabular Q-learning, 5 seeds x 200k episodes ...")
    q_runs = []
    for seed in (1, 2, 3, 4, 5):
        pol, table = train_q(INST["seed"] + seed)
        v, st = evaluate(pol)
        q_runs.append({"seed": INST["seed"] + seed, "value": v,
                       "states": len(table), "stats": st})
        print(f"  seed {INST['seed']+seed}: {v:.6f}   "
              f"({100*(opt-v)/abs(opt):.2f}% below optimum)")

    best_q = max(q_runs, key=lambda r: r["value"])
    mean_q = sum(r["value"] for r in q_runs) / len(q_runs)

    out = {
        "exact_optimum": round(opt, 6),
        "ss": {"s": s_star, "S": S_star, "value": round(ss_val, 6),
               "expected_waste": round(ss_stats["waste"], 4),
               "expected_lost": round(ss_stats["lost"], 4),
               "expected_sold": round(ss_stats["sold"], 4),
               "expected_order_days": round(ss_stats["orders"], 4),
               "gap_pct": round(100 * (opt - ss_val) / abs(opt), 4)},
        "q_learning": {
            "runs": [{"seed": r["seed"], "value": round(r["value"], 6),
                      "states": r["states"],
                      "expected_waste": round(r["stats"]["waste"], 4),
                      "expected_lost": round(r["stats"]["lost"], 4),
                      "expected_order_days": round(r["stats"]["orders"], 4)}
                     for r in q_runs],
            "best_value": round(best_q["value"], 6),
            "mean_value": round(mean_q, 6),
            "best_gap_pct": round(100 * (opt - best_q["value"]) / abs(opt), 4),
            "mean_gap_pct": round(100 * (opt - mean_q) / abs(opt), 4),
        },
        "rl_vs_ss_pct": round(100 * (best_q["value"] - ss_val) / abs(ss_val), 4),
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "..", "results", "baselines.json"), "w") as f:
        json.dump(out, f, indent=2)

    print()
    print(f"exact optimum        {opt:10.4f}")
    print(f"best (s,S) ({s_star},{S_star})     {ss_val:10.4f}   "
          f"gap {out['ss']['gap_pct']:.2f}%")
    print(f"Q-learning best      {best_q['value']:10.4f}   "
          f"gap {out['q_learning']['best_gap_pct']:.2f}%")
    print(f"Q-learning mean      {mean_q:10.4f}   "
          f"gap {out['q_learning']['mean_gap_pct']:.2f}%")
    print(f"RL over (s,S)        {out['rl_vs_ss_pct']:+.2f}%")


if __name__ == "__main__":
    main()
