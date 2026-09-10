"""
Exact stochastic dynamic program over the age-vector state.

This is the ground truth. The state is the full inventory age profile
(n_1,...,n_m), not a scalar total, so the value function knows the
difference between five fresh units and five units that expire tonight.

Backward recursion over the reachable state graph:

    V_T(x)   = 0
    V_t(x)   = max_{0<=q<=Q}  E_D [ g(x,q,D) + V_{t+1}(f(x,q,D)) ]

with g the one-day profit and f the age-transition map. Demand has
three-point support per day, so the expectation is an exact finite sum,
not a sample average.

Issuing is oldest-first. That is not an imposed restriction: with a
non-negative wastage cost and age-independent holding cost, issuing the
oldest unit first weakly dominates every other issuing rule, so the
optimal policy uses it anyway. The scenario-tree MIP leaves issuing free
and independently rediscovers it.
"""

import json
import os
import sys
from functools import lru_cache

import instance as inst_mod


INST = inst_mod.build()
M = INST["shelf_life"]
T = INST["horizon"]
QMAX = INST["order_cap"]
R = INST["price"]
C = INST["purchase"]
K = INST["setup"]
H = INST["holding"]
P = INST["shortage"]
W = INST["wastage"]
SUPPORT = [[(int(v), float(p)) for v, p in day] for day in INST["demand_support"]]


def step(state, q, demand):
    """One day. Returns (profit, next_state, breakdown)."""
    stock = list(state)
    stock[0] += q                       # arrival becomes age-1 stock

    # issue oldest-first
    remaining = demand
    sold = 0
    for a in range(M - 1, -1, -1):
        take = min(stock[a], remaining)
        stock[a] -= take
        remaining -= take
        sold += take
        if remaining == 0:
            break

    lost = demand - sold
    waste = stock[M - 1]                # unsold age-m stock is scrapped
    stock[M - 1] = 0
    end_inv = sum(stock)

    profit = (R * sold - C * q - K * (1 if q > 0 else 0)
              - H * end_inv - P * lost - W * waste)
    nxt = tuple([0] + stock[: M - 1])   # everything ages one day
    return profit, nxt, (sold, lost, waste, end_inv)


@lru_cache(maxsize=None)
def value(t, state):
    """Optimal expected profit-to-go from day t (0-indexed) in `state`."""
    if t == T:
        return 0.0, 0
    best_val = -1e18
    best_q = 0
    on_hand = sum(state)
    qcap = min(QMAX, INST["inventory_cap"] - on_hand)
    for q in range(0, max(qcap, 0) + 1):
        exp_val = 0.0
        for d, prob in SUPPORT[t]:
            profit, nxt, _ = step(state, q, d)
            exp_val += prob * (profit + value(t + 1, nxt)[0])
        if exp_val > best_val + 1e-12:
            best_val = exp_val
            best_q = q
    return best_val, best_q


def policy_order(t, state):
    """The optimal order quantity, looked up from the solved value function."""
    return value(t, tuple(state))[1]


def main():
    x0 = tuple(INST["initial_stock"])
    opt, q0 = value(0, x0)

    # Reachable-state census, for reporting the true size of the solved DP.
    frontier = {(0, x0)}
    seen = set()
    per_day = [0] * (T + 1)
    while frontier:
        t, s = frontier.pop()
        if (t, s) in seen:
            continue
        seen.add((t, s))
        per_day[t] += 1
        if t == T:
            continue
        q = value(t, s)[1]
        for d, _ in SUPPORT[t]:
            _, nxt, _ = step(s, q, d)
            frontier.add((t + 1, nxt))

    out = {
        "method": "exact-stochastic-dp",
        "optimal_expected_profit": round(opt, 6),
        "first_order": q0,
        "states_evaluated": value.cache_info().currsize,
        "reachable_states_under_optimal_policy": per_day,
        "initial_state": list(x0),
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "..", "results", "exact_dp.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=2)

    print(f"exact DP optimal expected profit : {opt:.6f}")
    print(f"first-day order quantity         : {q0}")
    print(f"(t,state) pairs evaluated        : {value.cache_info().currsize}")
    print(f"reachable states per day         : {per_day}")


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
