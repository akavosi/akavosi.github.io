"""
Shared visual language for the perishable-inventory figures.

Palette is taken directly from the site stylesheet so figures sit in the
page rather than on top of it.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import rcParams

INK        = "#18181a"
BODY       = "#3a3a36"
MUTED      = "#75756e"
FAINT      = "#a3a39a"
SOFT       = "#f6f6f4"
RULE       = "#e3e2dd"
RULE_STRONG = "#cac9c1"
ACCENT     = "#9c2b2b"      # waste / spoilage
NAVY       = "#2f3d63"      # the optimal policy
NAVY_LIGHT = "#4d5f96"
GOLD       = "#a9781f"      # the learned policy
GOLD_LIGHT = "#c9a24b"

# Age ramp: fresh stock is pale, near-expiry stock darkens toward the accent.
AGE_COLORS = ["#dfe3ee", "#b9c1d8", "#8e9bc0", "#c98f78", "#9c2b2b"]

POLICY = {
    "optimal": NAVY,
    "rl":      GOLD,
    "ss":      MUTED,
}
POLICY_LABEL = {
    "optimal": "Exact optimal policy",
    "rl":      "Learned policy",
    "ss":      "Best base-stock policy",
}


def use():
    rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": RULE_STRONG,
        "axes.labelcolor": BODY,
        "axes.titlecolor": INK,
        "axes.linewidth": 0.8,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": MUTED,
        "ytick.labelcolor": MUTED,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "figure.dpi": 160,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.22,
    })


def title(ax, text, sub=None):
    """Left-aligned title with an optional deck line above the axes.

    The deck is drawn in axes coordinates ABOVE the title, and the title pad
    is opened up to make room, so the two never sit on the same baseline.
    """
    ax.set_title(text, loc="left", fontsize=10.5, fontweight="600",
                 color=INK, pad=22 if sub else 6)
    if sub:
        ax.text(0.0, 1.055, sub, transform=ax.transAxes, fontsize=8.3,
                color=MUTED, va="bottom", ha="left")


def hairline(ax, y=0):
    ax.axhline(y, color=RULE_STRONG, lw=0.8, zorder=1)
