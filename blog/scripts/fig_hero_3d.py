"""
3D hero: the age-time surface.

Two things are genuinely three-dimensional in this model: day, age, and
quantity. Drawing them as a bar field makes the diagonal structure of
perishable inventory visible in a way the 2D charts cannot -- a batch
enters at age one and walks diagonally away from the viewer, one age class
per day, until it either sells out or hits the accent-coloured back row.

Bars are the exact expected units under the optimal policy. Draw order is
set explicitly (back to front) rather than trusting depth sorting, which
mis-orders mixed-colour bar fields.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

import theme

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "assets", "perishable-inventory")

theme.use()

tr = json.load(open(os.path.join(RESULTS, "traces.json")))
M, T = tr["meta"]["shelf_life"], tr["meta"]["horizon"]

# Expected units held in each (day, age) cell, before scrapping, under the
# optimal policy: end-of-day stock plus what was scrapped in the age-M cell.
age = np.array(tr["policies"]["optimal"]["age_by_day"])          # (T, M)
waste = np.array(tr["policies"]["optimal"]["components"]["waste_units"])
cell = age.copy()
cell[:, M - 1] += waste

fig = plt.figure(figsize=(8.2, 5.0))
ax = fig.add_subplot(111, projection="3d")
ax.set_box_aspect((1.55, 1.0, 0.72), zoom=1.14)
ax.computed_zorder = False

dx = dy = 0.62
order = []
for t in range(T):
    for a in range(M):
        order.append((t, a))
# paint far bars first so near bars overlap them correctly
order.sort(key=lambda ta: (-(ta[0]), ta[1]))

for t, a in order:
    h = cell[t, a]
    if h < 1e-9:
        continue
    color = theme.AGE_COLORS[a]
    edge = "white"
    if a == M - 1 and waste[t] > 1e-9:
        color = theme.ACCENT
    ax.bar3d(t + 1 - dx / 2, a + 1 - dy / 2, 0, dx, dy, h,
             color=color, edgecolor=edge, linewidth=0.35,
             shade=True, zsort="max")

ax.set_xlabel("day", labelpad=8, color=theme.BODY, fontsize=9)
ax.set_ylabel("age", labelpad=6, color=theme.BODY, fontsize=9)
ax.set_zlabel("expected units", labelpad=2, color=theme.BODY, fontsize=9)
ax.set_xticks(range(1, T + 1))
ax.set_yticks(range(1, M + 1))
ax.set_xlim(0.4, T + 0.6)
ax.set_ylim(0.4, M + 0.6)
ax.view_init(elev=26, azim=-56)

ax.xaxis.pane.set_facecolor("white")
ax.yaxis.pane.set_facecolor("white")
ax.zaxis.pane.set_facecolor(theme.SOFT)
for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
    pane.set_edgecolor(theme.RULE)
    pane.set_alpha(1.0)
ax.grid(True)
ax.tick_params(colors=theme.MUTED, labelsize=8)

fig.text(0.02, 0.97, "The age-time surface under the optimal policy",
         fontsize=12.4, fontweight="600", color=theme.INK)
fig.text(0.02, 0.918,
         "Expected units in every (day, age) cell. Stock enters at age one "
         "and walks diagonally back;\nthe accent row is what never made it.",
         fontsize=8.6, color=theme.MUTED)

out = os.path.join(ASSETS, "age_surface_3d_hero.png")
fig.subplots_adjust(left=0.0, right=0.97, top=1.02, bottom=0.02)
fig.savefig(out, dpi=170, bbox_inches="tight", pad_inches=0.12)
print("wrote", os.path.normpath(out))
