"""
Filmstrip: one scenario, seven days, the shelf drawn as it actually is.

This is a single path through the tree (probability 1/128), not an average:
demand realises high through the midweek peak and low over the weekend.
Averages hide the thing worth seeing, which is a specific batch of stock
ageing across the panels and either selling or dying.

Each panel is the shelf at end of day, one column per age class, with the
units sold that day drawn as hollow outline above the surviving stock.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import theme

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "assets", "perishable-inventory")

theme.use()

tr = json.load(open(os.path.join(RESULTS, "traces.json")))
M = tr["meta"]["shelf_life"]
T = tr["meta"]["horizon"]
# The scenario is chosen by pick_scenario.py, which searches all 128 paths
# for the one that best shows the mechanism. Probability 1/128, like any other.
scen = json.load(open(os.path.join(RESULTS, "filmstrip_scenario.json")))
film = scen["days"]

fig, axes = plt.subplots(1, T, figsize=(12.4, 2.95), sharey=True)
ages = np.arange(1, M + 1)

for t, (ax, day) in enumerate(zip(axes, film)):
    end = np.array(day["end_age"], dtype=float)
    sold = np.array(day["sales_by_age"], dtype=float)

    ax.bar(ages, end, width=0.68, color=theme.AGE_COLORS, zorder=3,
           linewidth=0)
    ax.bar(ages, sold, bottom=end, width=0.68, facecolor="white",
           edgecolor=theme.FAINT, linewidth=0.7, zorder=3)

    if day["waste"] > 0:
        # Sits on top of whatever sold at age M, so the column still totals
        # the stock that was actually available in that age class.
        base = end[M - 1] + sold[M - 1]
        ax.bar([M], [day["waste"]], bottom=[base], width=0.68,
               color=theme.ACCENT, zorder=4, linewidth=0)
        ax.text(M, base + day["waste"] + 0.9, f"−{day['waste']}", ha="center",
                fontsize=8.6, color=theme.ACCENT, fontweight="700", zorder=5)

    ax.set_xticks(ages)
    ax.set_xticklabels(ages, fontsize=7.8)
    ax.set_xlim(0.4, M + 0.6)
    ax.set_xlabel("age", fontsize=8)
    theme.hairline(ax)

    head = f"day {day['day']}"
    ax.set_title(head, loc="left", fontsize=9.8, fontweight="600",
                 color=theme.INK, pad=16)
    ax.text(0.0, 1.03,
            f"order {day['order']}   demand {day['demand']}",
            transform=ax.transAxes, fontsize=7.9, color=theme.MUTED,
            va="bottom", ha="left")
    if day["lost"]:
        ax.text(0.99, 0.96, f"{day['lost']} unmet", transform=ax.transAxes,
                fontsize=7.9, color=theme.MUTED, ha="right", va="top",
                style="italic")

axes[0].set_ylabel("units")
axes[0].set_ylim(0, 26)

legend = [Patch(facecolor=theme.AGE_COLORS[2], label="stock carried into tomorrow"),
          Patch(facecolor="white", edgecolor=theme.FAINT, label="sold today"),
          Patch(facecolor=theme.ACCENT, label="scrapped at age five")]
fig.legend(handles=legend, loc="lower center", ncol=3,
           bbox_to_anchor=(0.5, -0.10), handlelength=1.5)

fig.text(0.005, 1.10, "One scenario, day by day: the shelf, by age",
         ha="left", fontsize=12.2, fontweight="600", color=theme.INK)
fig.text(0.005, 1.035,
         "One of the 128 demand paths, probability 1/128. A 22-unit order on "
         "day three meets a collapse to four units of demand — watch that "
         "batch march right across the age axis and die on day seven.",
         ha="left", fontsize=8.5, color=theme.MUTED)

out = os.path.join(ASSETS, "filmstrip.png")
fig.savefig(out)
print("wrote", os.path.normpath(out))
