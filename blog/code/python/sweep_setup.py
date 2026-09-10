"""
Second design sweep: introduce a fixed ordering cost.

Diagnosis from sweep_instance.py: with a 5-day shelf life and smooth
daily demand, the optimal policy simply orders close to just-in-time and
nothing ever ages out. Perishability is not binding, so there is no
tradeoff worth drawing.

A fixed cost K per replenishment changes the structure: ordering becomes
lumpy, stock is deliberately built ahead of the midweek peak, and units
that miss the peak can genuinely reach age 5 and be scrapped. It also
makes (s,S) a meaningful baseline rather than an arbitrary one, and turns
the scenario-tree model into a true fixed-charge MIP with setup binaries.
"""

from functools import lru_cache

M, T, QMAX, CAP = 5, 7, 20, 36
PROBS = (0.25, 0.50, 0.25)
MEAN = [8, 10, 14, 12, 9, 6, 5]


def run(K, short, waste_c, spread, price=10.0, purchase=3.0, hold=0.5,
        x0=(0, 0, 4, 5, 0)):
    support = [tuple((max(0, MEAN[t] - spread[t] + i * spread[t]), p)
                     for i, p in zip(range(3), PROBS)) for t in range(T)]

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
        cap = min(QMAX, CAP - sum(s))
        for q in range(max(cap, 0) + 1):
            e = 0.0
            for d, p in support[t]:
                pr, nx, _, _ = step(s, q, d)
                e += p * (pr + V(t + 1, nx)[0])
            if e > best + 1e-12:
                best, bq = e, q
        return best, bq

    dist = {tuple(x0): 1.0}
    tw = tl = norders = 0.0
    for t in range(T):
        nd = {}
        for s, pm in dist.items():
            q = V(t, s)[1]
            if q > 0:
                norders += pm
            for d, p in support[t]:
                _, nx, lost, w = step(s, q, d)
                tw += pm * p * w
                tl += pm * p * lost
                nd[nx] = nd.get(nx, 0.0) + pm * p
        dist = nd
    return V(0, tuple(x0))[0], tw, tl, norders


SPREAD_HI = [5, 7, 9, 8, 6, 4, 3]

print(f"{'K':>5}{'short':>7}{'waste':>7} | {'profit':>9}{'E[waste]':>10}"
      f"{'E[short]':>10}{'E[orders]':>11}")
print("-" * 60)
hits = []
for K in (20.0, 40.0, 60.0):
    for short, waste_c in ((6.0, 8.0), (10.0, 12.0)):
        p, w, l, no = run(K, short, waste_c, SPREAD_HI)
        flag = "  <==" if w > 0.2 and l > 0.2 else ""
        print(f"{K:>5}{short:>7}{waste_c:>7} | {p:>9.2f}{w:>10.3f}"
              f"{l:>10.3f}{no:>11.2f}{flag}")
        if w > 0.2 and l > 0.2:
            hits.append((K, short, waste_c, p, w, l, no))
print(f"\n{len(hits)} regimes with both waste and shortage active")
