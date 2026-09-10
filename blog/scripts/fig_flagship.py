"""
Flagship: inventory by exact age, three policies side by side.

Top row  - stacked area of expected end-of-day inventory split by age class,
           palest for fresh stock, darkening toward the accent for stock that
           expires tonight.
Bottom row - the two failure modes on their own scale, because they are ~1
           unit against a ~20 unit pile and would be invisible if drawn
           against the same axis.

The argument of the post is the difference between panel two and panel
three: the base-stock policy holds a *smaller* pile and still runs out far
more often, because it cannot see which part of the pile is about to die.
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
os.makedirs(ASSETS, exist_ok=True)

theme.use()

tr = json.load(open(os.path.join(RESULTS, "traces.json")))
M = tr["meta"]["shelf_life"]
T = tr["meta"]["horizon"]
days = np.arange(1, T + 1)
order = ["optimal", "rl", "ss"]

fig = plt.figure(figsize=(11.6, 5.0))
gs = fig.add_gridspec(2, 3, height_ratios=[3.0, 1.0], hspace=0.34, wspace=0.13)

top_axes, bot_axes = [], []
for j, key in enumerate(order):
    top_axes.append(fig.add_subplot(gs[0, j], sharey=top_axes[0] if j else None))
    bot_axes.append(fig.add_subplot(gs[1, j], sharey=bot_axes[0] if j else None))

for j, key in enumerate(order):
    ax, bx = top_axes[j], bot_axes[j]
    pol = tr["policies"][key]
    age = np.array(pol["age_by_day"])
    waste = np.array(pol["components"]["waste_units"])
    lost = np.array(pol["components"]["lost_units"])

    # Ages 1..M-1 only. End-of-day age-M stock is structurally zero: it has
    # already been scrapped by the time inventory is counted, and it is shown
    # in the strip below rather than as an always-empty band up here.
    ax.stackplot(days, age[:, : M - 1].T, colors=theme.AGE_COLORS[: M - 1],
                 edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_xlim(0.5, T + 0.5)
    ax.set_xticks(days)
    ax.tick_params(labelbottom=False)
    ax.set_title(theme.POLICY_LABEL[key], loc="left", fontsize=10.5,
                 fontweight="600", color=theme.POLICY[key], pad=16)
    ax.text(0.0, 1.015,
            f"expected profit {pol['value']:.1f}      "
            f"spoiled {pol['expected_waste']:.2f}      "
            f"short {pol['expected_lost']:.2f}",
            transform=ax.transAxes, fontsize=8.2, color=theme.MUTED,
            va="bottom", ha="left")

    w = 0.36
    bx.bar(days - w / 2, waste, width=w, color=theme.ACCENT, linewidth=0,
           zorder=3)
    bx.bar(days + w / 2, lost, width=w, color="white",
           edgecolor=theme.MUTED, hatch="////", linewidth=0.55, zorder=3)
    theme.hairline(bx)
    bx.set_xlim(0.5, T + 0.5)
    bx.set_xticks(days)
    bx.set_xlabel("day")
    if j:
        bx.tick_params(labelleft=False)

top_axes[0].set_ylabel("expected units on hand, by age")
top_axes[0].set_ylim(0, 24)
for ax in top_axes[1:]:
    ax.tick_params(labelleft=False)
bot_axes[0].set_ylabel("units lost")
bot_axes[0].set_ylim(0, 2.6)

legend_age = [Patch(facecolor=theme.AGE_COLORS[a], edgecolor="white",
                    label=f"age {a+1}" + (" — expires tomorrow" if a == M - 2 else ""))
              for a in range(M - 1)]
legend_bad = [Patch(facecolor=theme.ACCENT, label="scrapped at age five"),
              Patch(facecolor="white", edgecolor=theme.MUTED, hatch="////",
                    label="demand missed")]

fig.legend(handles=legend_age + legend_bad, loc="lower center", ncol=6,
           bbox_to_anchor=(0.5, -0.055), columnspacing=1.5,
           handlelength=1.5, handleheight=0.9)

fig.text(0.005, 1.045,
         "Inventory by exact age, five-day shelf life, seven-day horizon",
         ha="left", fontsize=12.5, fontweight="600", color=theme.INK)
fig.text(0.005, 1.005,
         "Exact expectations over all 128 demand scenarios — no sampling. "
         "The lower strip shows the two ways a day can go wrong, on its own scale.",
         ha="left", fontsize=8.6, color=theme.MUTED)

out = os.path.join(ASSETS, "age_stack_flagship.png")
fig.savefig(out)
print("wrote", os.path.normpath(out))
