"""
Instance-design sweep.

An instance where the optimum wastes nothing and is never short is a bad
instance: the perishability constraint is not binding, and there is no
tradeoff to look at. This sweeps the cost ratios and demand volatility to
find a regime where the optimal policy genuinely has to spill some units
and miss some demand.
"""

import itertools
from functools import lru_cache

M = 5
T = 7
QMAX = 25
CAP = 40
PROBS = (0.25, 0.50, 0.25)


def solve(price, purchase, hold, short, waste_c, mean, spread, x0):
    support = []
    for t in range(T):
        mu, d = mean[t], spread[t]
        support.append(tuple((max(0, mu - d + i * d), p)
                             for i, p in zip(range(3), PROBS)))

    def step(state, q, demand):
        stock = list(state)
        stock[0] += q
        rem, sold = demand, 0
        for a in range(M - 1, -1, -1):
            take = min(stock[a], rem)
            stock[a] -= take
            rem -= take
            sold += take
        lost = demand - sold
        w = stock[M - 1]
        stock[M - 1] = 0
        end = sum(stock)
        prof = price * sold - purchase * q - hold * end - short * lost - waste_c * w
        return prof, tuple([0] + stock[: M - 1]), sold, lost, w

    @lru_cache(maxsize=None)
    def V(t, s):
        if t == T:
            return 0.0, 0
        best, bq = -1e18, 0
        cap = min(QMAX, CAP - sum(s))
        for q in range(max(cap, 0) + 1):
            e = 0.0
            for d, p in support[t]:
                pr, nx, _, _, _ = step(s, q, d)
                e += p * (pr + V(t + 1, nx)[0])
            if e > best + 1e-12:
                best, bq = e, q
        return best, bq

    # expected waste / shortage under the optimal policy
    dist = {tuple(x0): 1.0}
    tot_w = tot_l = 0.0
    for t in range(T):
        nd = {}
        for s, pm in dist.items():
            q = V(t, s)[1]
            for d, p in support[t]:
                _, nx, _, lost, w = step(s, q, d)
                tot_w += pm * p * w
                tot_l += pm * p * lost
                nd[nx] = nd.get(nx, 0.0) + pm * p
        dist = nd
    return V(0, tuple(x0))[0], tot_w, tot_l


BASE_MEAN = [8, 10, 14, 12, 9, 6, 5]

print(f"{'short':>6}{'waste':>7}{'price':>7}{'spread':>8} | "
      f"{'profit':>9}{'E[waste]':>10}{'E[short]':>10}")
print("-" * 62)

best_rows = []
for short, waste_c, price, sc in itertools.product(
        [2.0, 4.0, 6.0], [4.0, 8.0, 12.0], [10.0, 6.0], ["lo", "hi"]):
    spread = [3, 4, 6, 5, 4, 2, 2] if sc == "lo" else [5, 7, 9, 8, 6, 4, 3]
    mean = BASE_MEAN
    x0 = [0, 0, 4, 5, 0]
    p, w, l = solve(price, 3.0, 0.5, short, waste_c, mean, spread, x0)
    flag = "  <== tradeoff" if w > 0.15 and l > 0.15 else ""
    print(f"{short:>6}{waste_c:>7}{price:>7}{sc:>8} | "
          f"{p:>9.2f}{w:>10.3f}{l:>10.3f}{flag}")
    if w > 0.15 and l > 0.15:
        best_rows.append((short, waste_c, price, sc, p, w, l))

print()
print(f"{len(best_rows)} candidate regimes with both waste and shortage active")
