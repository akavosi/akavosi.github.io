"""
Choose the filmstrip scenario, by search rather than by taste.

A filmstrip of a path where nothing expires is a filmstrip that fails to
show the one thing the post is about. This enumerates all 128 demand
paths, runs the optimal policy along each, and scores them for
storytelling value: a path that both scraps stock and misses demand,
where the scrapping is visible, and where the age profile actually moves.

The winner is still an ordinary scenario with probability 1/128 -- it is
selected, not constructed.
"""

import json
import os
from itertools import product

from exact_dp import step, value, M, T, INST

SUPPORT = [[(int(v), float(p)) for v, p in day] for day in INST["demand_support"]]
X0 = tuple(INST["initial_stock"])


def walk(path):
    state = X0
    days, waste_tot, lost_tot = [], 0, 0
    for t in range(T):
        q = value(t, state)[1]
        d = path[t]
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
        waste_tot += waste
        lost_tot += lost
        _, state, _ = step(state, q, d)
    return days, waste_tot, lost_tot


def main():
    value(0, X0)
    best = None
    for choice in product([0, 1], repeat=T):
        path = [SUPPORT[t][c][0] for t, c in enumerate(choice)]
        days, w, l = walk(path)
        if w == 0 or l == 0:
            continue
        # prefer: real spoilage, some unmet demand, and a shelf that is
        # not empty most of the week (so the age bands are actually visible)
        occupancy = sum(1 for d in days if sum(d["end_age"]) > 0)
        score = (min(w, 6), min(l, 4), occupancy)
        if best is None or score > best[0]:
            best = (score, path, days, w, l)

    score, path, days, w, l = best
    print(f"selected path {path}")
    print(f"  scrapped {w} units, missed {l} units, "
          f"non-empty shelf on {score[2]}/{T} days")
    for d in days:
        print("   ", d)

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "results", "filmstrip_scenario.json")
    with open(dest, "w") as f:
        json.dump({"demand_path": path, "days": days,
                   "total_waste": w, "total_lost": l,
                   "probability": 1 / (2 ** T)}, f, indent=2)


if __name__ == "__main__":
    main()
