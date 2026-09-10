"""
Third design sweep: two-point demand support.

The three-point tree (3^7 = 2187 scenarios, 3280 nodes, ~58k integer
variables) is a fine DP but an unreasonable MIP on a small machine: the
deterministic equivalent does not fit in memory well enough for
branch-and-bound to prove optimality.

Two-point support per day gives 2^7 = 128 scenarios and 255 nodes, which
is small enough for the deterministic-equivalent MIP to be solved to
proven optimality, while remaining a genuine multi-stage stochastic
program with non-anticipativity. The DP, the JuMP model and the OR-Tools
model then all solve the identical instance.

This sweep picks the fixed cost and demand spread so that the optimal
policy both spills stock and misses demand.
"""

from functools import lru_cache

M, T, CAP = 5, 7, 36
MEAN = [8, 10, 14, 12, 9, 6, 5]


def run(K, spread, qmax, short=6.0, waste_c=8.0, price=10.0, purchase=3.0,
        hold=0.5, x0=(0, 0, 4, 5, 0)):
    support = [((max(0, MEAN[t] - spread[t]), 0.5), (MEAN[t] + spread[t], 0.5))
               for t in range(T)]

    def step(state, q, d):
        s = list(state)
        s[0] += q
        rem, sold = d, 0
        for a in range(M - 1, -1, -1):
            take = min(s[a], rem)
            s[a] -= take
            rem -= take
            sold += take
        lost = d - sold
        w = s[M - 1]
        s[M - 1] = 0
        end = sum(s)
        prof = (price * sold - purchase * q - K * (1 if q > 0 else 0)
                - hold * end - short * lost - waste_c * w)
        return prof, tuple([0] + s[: M - 1]), lost, w

    @lru_cache(maxsize=None)
    def V(t, s):
        if t == T:
            return 0.0, 0
        best, bq = -1e18, 0
        cap = min(qmax, CAP - sum(s))
        for q in range(max(cap, 0) + 1):
            e = 0.0
            for d, p in support[t]:
                pr, nx, _, _ = step(s, q, d)
                e += p * (pr + V(t + 1, nx)[0])
            if e > best + 1e-12:
                best, bq = e, q
        return best, bq

    dist = {tuple(x0): 1.0}
    tw = tl = no = 0.0
    for t in range(T):
        nd = {}
        for s, pm in dist.items():
            q = V(t, s)[1]
            if q > 0:
                no += pm
            for d, p in support[t]:
                _, nx, lost, w = step(s, q, d)
                tw += pm * p * w
                tl += pm * p * lost
                nd[nx] = nd.get(nx, 0.0) + pm * p
        dist = nd
    return V(0, tuple(x0))[0], tw, tl, no


print(f"{'K':>5}{'qmax':>6}{'spread':>8} | {'profit':>9}{'E[waste]':>10}"
      f"{'E[short]':>10}{'E[orders]':>11}")
print("-" * 62)
for K in (30.0, 40.0, 50.0):
    for qmax in (18, 22):
        for name, spread in (("mid", [4, 5, 7, 6, 4, 3, 2]),
                             ("wide", [6, 8, 10, 9, 7, 4, 3])):
            p, w, l, no = run(K, spread, qmax)
            flag = "  <==" if w > 0.2 and l > 0.2 else ""
            print(f"{K:>5}{qmax:>6}{name:>8} | {p:>9.2f}{w:>10.3f}"
                  f"{l:>10.3f}{no:>11.2f}{flag}")
