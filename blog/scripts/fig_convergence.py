"""
Convergence figure, two panels.

Left  - where the money goes. Expected cost components per policy, as a
        signed breakdown from gross revenue down to net profit. This is
        the chart that explains *why* base-stock loses: its bar is short
        not because it spoils stock but because it never had the stock to
        sell.
Right - the gap to the proven optimum, per policy, with the five learning
        seeds shown individually so the spread is visible rather than
        hidden behind a mean.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt

import theme

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "assets", "perishable-inventory")

theme.use()

tr = json.load(open(os.path.join(RESULTS, "traces.json")))
base = json.load(open(os.path.join(RESULTS, "baselines.json")))
OPT = base["exact_optimum"]

fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.2, 4.5),
                             gridspec_kw={"width_ratios": [1.35, 1.0],
                                          "wspace": 0.28})

# ------------------------------------------------------ left: cost anatomy
order = ["optimal", "rl", "ss"]
labels = [theme.POLICY_LABEL[k] for k in order]
comps = ["revenue", "purchase", "setup", "holding", "shortage", "wastage"]
comp_label = {"revenue": "gross revenue", "purchase": "acquisition",
              "setup": "fixed ordering", "holding": "holding",
              "shortage": "shortage penalty", "wastage": "spoilage"}
comp_color = {"revenue": theme.NAVY_LIGHT, "purchase": "#b9c1d8",
              "setup": "#8e9bc0", "holding": theme.FAINT,
              "shortage": theme.MUTED, "wastage": theme.ACCENT}

x = np.arange(len(order))
width = 0.60

# A decomposition column per policy: total height is gross revenue, and the
# stack reads downward as each cost eats into it, bottoming out at net profit.
# Every segment is an exact expectation, so the segments sum to revenue exactly.
stack_order = ["net", "wastage", "shortage", "holding", "setup", "purchase"]
seg_label = {"net": "net expected profit", "purchase": "acquisition",
             "setup": "fixed ordering", "holding": "holding",
             "shortage": "shortage penalty", "wastage": "spoilage"}
seg_color = {"net": theme.NAVY, "purchase": "#c8cee0", "setup": "#9aa6c6",
             "holding": "#dcdbd4", "shortage": theme.MUTED,
             "wastage": theme.ACCENT}

vals = {c: np.array([sum(tr["policies"][k]["components"][c]) for k in order])
        for c in stack_order[1:]}
vals["net"] = np.array([tr["policies"][k]["value"] for k in order])
revenue = np.array([sum(tr["policies"][k]["components"]["revenue"]) for k in order])

bottom = np.zeros(len(order))
for c in stack_order:
    ax.bar(x, vals[c], width, bottom=bottom, color=seg_color[c],
           label=seg_label[c], zorder=3, edgecolor="white", linewidth=0.7)
    bottom += vals[c]

for i, k in enumerate(order):
    ax.text(i, vals["net"][i] / 2, f"{vals['net'][i]:.1f}", ha="center",
            va="center", fontsize=10.5, fontweight="700", color="white",
            zorder=6)
    ax.text(i, revenue[i] + 12, f"revenue {revenue[i]:.0f}", ha="center",
            fontsize=8.3, color=theme.MUTED, zorder=6)

theme.hairline(ax)
ax.set_xticks(x)
ax.set_xticklabels(["exact\noptimal", "learned", "best\nbase-stock"],
                   color=theme.BODY)
ax.set_ylabel("expected currency over the horizon")
ax.set_ylim(0, 700)
ax.set_xlim(-0.62, len(order) - 0.38)
handles, lab = ax.get_legend_handles_labels()
ax.legend(handles[::-1], lab[::-1], ncol=3, loc="upper center",
          bbox_to_anchor=(0.5, -0.14), columnspacing=1.4, handlelength=1.4)
theme.title(ax, "Where the money goes",
            "Gross revenue, eaten downward by each cost.")

# ------------------------------------------------------ right: gap to optimum
runs = sorted(base["q_learning"]["runs"], key=lambda r: -r["value"])
ss_val = base["ss"]["value"]

ypos = np.arange(len(runs) + 1)[::-1]
bx.barh(ypos[0], 0.0, color=theme.NAVY)     # optimum reference at zero

for i, r in enumerate(runs):
    gap = 100 * (OPT - r["value"]) / OPT
    bx.barh(ypos[i + 1] + 0.0, gap, height=0.52, color=theme.GOLD_LIGHT,
            zorder=3)
    bx.text(gap + 0.4, ypos[i + 1], f"{gap:.2f}%", va="center",
            fontsize=8.4, color=theme.MUTED)

ss_gap = 100 * (OPT - ss_val) / OPT
bx.barh(-1, ss_gap, height=0.52, color=theme.MUTED, zorder=3)
bx.text(ss_gap + 0.4, -1, f"{ss_gap:.2f}%", va="center", fontsize=8.4,
        color=theme.MUTED)

bx.axvline(0, color=theme.NAVY, lw=1.6, zorder=4)
bx.text(0.35, ypos[0], "exact optimum  257.87", va="center", fontsize=8.6,
        color=theme.NAVY, fontweight="600")

bx.set_yticks(list(ypos[1:]) + [-1])
bx.set_yticklabels([f"seed {r['seed']}" for r in runs] +
                   [f"best (s,S) = ({base['ss']['s']},{base['ss']['S']})"],
                   fontsize=8.4)
bx.set_ylim(-1.8, len(runs) + 0.6)
bx.set_xlim(0, ss_gap * 1.22)
bx.set_xlabel("shortfall below the proven optimum (%)")
bx.spines["left"].set_visible(False)
bx.tick_params(axis="y", length=0)
theme.title(bx, "Every run against a provable answer",
            "Five seeds, scored by exact enumeration.")

out = os.path.join(ASSETS, "convergence_chart.png")
fig.savefig(out)
print("wrote", os.path.normpath(out))
