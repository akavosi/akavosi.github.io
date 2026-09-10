"""
Age-tracked perishable inventory instance.

Single source of truth for the model data. Every implementation
(exact DP, scenario-tree MIP, RL agent, base-stock search) reads the
JSON emitted by this module, so no two solvers can silently disagree
about the instance they are solving.

Model
-----
Shelf life m = 5 days, horizon T = 7 days, zero lead time.
Inventory is tracked by exact age a = 1..m (a = 1 is arrived-today).

Within-day sequence:
    1. order q_t arrives and becomes age-1 stock
    2. demand D_t is realised
    3. sales are issued from stock (FIFO is optimal, never imposed)
    4. unmet demand is lost
    5. any unsold age-m stock is scrapped as wastage
    6. holding cost is charged on end-of-day inventory
    7. surviving stock ages by one day

Profit per day:
    r*sales - c*order - K*[order>0] - h*end_inventory - p*lost_sales - w*wastage

The fixed cost K is what makes perishability bind. Without it the optimal
policy orders near just-in-time every day and nothing ever reaches age m;
with it, replenishment becomes lumpy, stock is built ahead of the midweek
peak, and units that miss the peak can genuinely expire.
"""

import json
import os

SHELF_LIFE = 5          # m: an item survives m days, scrapped at end of day m
HORIZON = 7             # T: planning horizon in days
ORDER_CAP = 22          # Q_max: maximum units orderable per day
INVENTORY_CAP = 36      # state-space cap for exact DP (verified non-binding)

PRICE = 10.0            # r: revenue per unit sold
PURCHASE = 3.0          # c: acquisition cost per unit ordered
SETUP = 40.0            # K: fixed cost charged on any day an order is placed
HOLDING = 0.5           # h: per unit per day of end-of-day inventory
SHORTAGE = 6.0          # p: goodwill penalty per unit of unmet demand
WASTAGE = 8.0           # w: disposal cost per unit scrapped at age m

# Non-stationary demand: a weekly pattern peaking midweek, collapsing at the
# weekend. Two-point support per day, low/high with probability 1/2 each.
# Two points rather than three keeps the deterministic-equivalent scenario
# tree at 2^7 = 128 scenarios / 255 nodes, small enough that the MIP can be
# proved optimal rather than merely solved well.
DEMAND_MEAN = [8, 10, 14, 12, 9, 6, 5]
DEMAND_SPREAD = [6, 8, 10, 9, 7, 4, 3]
DEMAND_PROBS = [0.5, 0.5]

# Initial stock: 4 units at age 3 and 5 units at age 4. Deliberately aged,
# so the very first decision already trades ordering against wastage.
INITIAL_STOCK = [0, 0, 4, 5, 0]     # index a-1 -> units of age a

SEED = 20260910


def demand_support():
    """Per-day list of (demand, probability) pairs."""
    out = []
    for t in range(HORIZON):
        mu, d = DEMAND_MEAN[t], DEMAND_SPREAD[t]
        vals = [max(0, mu - d), mu + d]
        out.append(list(zip(vals, DEMAND_PROBS)))
    return out


def build():
    return {
        "name": "perishable-age-tracked-m5-T7",
        "seed": SEED,
        "shelf_life": SHELF_LIFE,
        "horizon": HORIZON,
        "order_cap": ORDER_CAP,
        "inventory_cap": INVENTORY_CAP,
        "price": PRICE,
        "purchase": PURCHASE,
        "setup": SETUP,
        "holding": HOLDING,
        "shortage": SHORTAGE,
        "wastage": WASTAGE,
        "initial_stock": INITIAL_STOCK,
        "demand_mean": DEMAND_MEAN,
        "demand_spread": DEMAND_SPREAD,
        "demand_probs": DEMAND_PROBS,
        # Flat low/high arrays: identical information to demand_support, in a
        # shape that a minimal reader can consume without nested parsing.
        "demand_low": [d[0][0] for d in demand_support()],
        "demand_high": [d[1][0] for d in demand_support()],
        "demand_support": [[list(pair) for pair in day] for day in demand_support()],
    }


def path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "..", "results", "instance.json")


def load():
    with open(path()) as f:
        return json.load(f)


if __name__ == "__main__":
    inst = build()
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with open(path(), "w") as f:
        json.dump(inst, f, indent=2)
    n_scen = 2 ** HORIZON
    n_nodes = 2 ** (HORIZON + 1) - 1
    print(f"instance written: {os.path.normpath(path())}")
    print(f"  shelf life {SHELF_LIFE}d, horizon {HORIZON}d, order cap {ORDER_CAP}")
    print(f"  scenario tree: {n_scen} scenarios, {n_nodes} nodes")
    for t, day in enumerate(demand_support()):
        print(f"  day {t+1}: support {[v for v, _ in day]}")
