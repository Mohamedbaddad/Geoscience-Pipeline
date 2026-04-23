from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from datetime import datetime
import logging

log = logging.getLogger(__name__)

def plot_multitrack_log(well_name: str, df: pd.DataFrame,
                        formation_tops: pd.DataFrame = None,
                        depth_col: str = "DEPTH",
                        save_path: str = None):

    if depth_col not in df.columns:
        return

    depth = df[depth_col]
    present = df.columns.tolist()

    # Define track configuration
    tracks = []
    if "GR" in present:   tracks.append(("GR/SP",         ["GR"],              False))
    if "CALI" in present: tracks.append(("Caliper",        ["CALI"],            False))
    if "RT" in present:   tracks.append(("Resistivity",    ["RT","RILM","RILD"],True))
    if "RHOB" in present: tracks.append(("Density/Neutron",["RHOB","NPHI"],     False))
    if "DT" in present:   tracks.append(("Sonic",          ["DT"],              False))
    if "VSH" in present:  tracks.append(("Computed Petro", ["VSH","PHIT_D"],    False))
    if "RESERVOIR_FLAG" in present: tracks.append(("Reservoir", ["RESERVOIR_FLAG"], False))

    n_tracks = len(tracks)
    if n_tracks == 0:
        log.warning(f"No plottable curves for well {well_name}. Skipping.")
        return

    fig_height = max(14, len(depth) / 50)
    fig_height = min(fig_height, 30)   # cap at 30 inches for manageability
    fig, axes = plt.subplots(1, n_tracks, figsize=(n_tracks * 2.2, fig_height),
                             sharey=True)
    if n_tracks == 1:
        axes = [axes]

    fig.suptitle(f"Well Log Composite — {well_name}", fontsize=13, fontweight="bold", y=1.01)

    COLORS = {
        "GR": "#2ca02c", "SP": "#8c564b",
        "CALI": "#e377c2", "BS": "black",
        "RT": "black", "RILM": "steelblue", "RILD": "darkorange",
        "RHOB": "red", "NPHI": "blue",
        "DT": "purple",
        "VSH": "saddlebrown", "PHIT_D": "teal",
        "RESERVOIR_FLAG": "#2ecc71",
    }

    for ax, (track_name, curves, log_scale) in zip(axes, tracks):
        ax.set_ylim(depth.max(), depth.min())   # invert depth axis
        ax.set_xlabel(track_name, fontsize=8, labelpad=2)
        ax.xaxis.set_label_position("top")
        ax.xaxis.tick_top()
        ax.tick_params(axis="y", labelsize=7)
        ax.tick_params(axis="x", labelsize=6)
        ax.grid(True, which="major", linestyle="--", linewidth=0.4, alpha=0.5)
        ax.grid(True, which="minor", linestyle=":",  linewidth=0.2, alpha=0.3)
        ax.minorticks_on()

        if log_scale:
            ax.set_xscale("log")

        if "RESERVOIR_FLAG" in df.columns:
            in_zone = False
            zone_top = None
            for d, flag in zip(depth, df["RESERVOIR_FLAG"]):
                if flag and not in_zone:
                    zone_top = d; in_zone = True
                elif not flag and in_zone:
                    ax.axhspan(zone_top, d, facecolor="#2ecc71", alpha=0.10, zorder=0)
                    in_zone = False
            if in_zone and len(depth) > 0:
                ax.axhspan(zone_top, depth.iloc[-1], facecolor="#2ecc71", alpha=0.10, zorder=0)

        for curve in curves:
            if curve not in df.columns:
                continue
            color = COLORS.get(curve, "gray")
            vals = df[curve]

            if curve == "RESERVOIR_FLAG":
                ax.fill_betweenx(depth, 0, vals.astype(float),
                                 color="#2ecc71", alpha=0.8, step="mid")
                ax.set_xlim(0, 1.1)
                continue

            if curve == "NPHI":
                ax.plot(vals, depth, color=color, linewidth=0.8, label=curve)
                ax.set_xlim(0.45, -0.15)   # reversed
            elif curve == "GR":
                ax.plot(vals, depth, color=color, linewidth=0.8, label=curve)
                ax.set_xlim(0, 150)
                if "VSH" in df.columns:
                    vsh_cut = 0.35
                    gr_cut = df["GR"].quantile(0.05) + vsh_cut * (df["GR"].quantile(0.95) - df["GR"].quantile(0.05))
                    ax.fill_betweenx(depth, 0, vals, where=(vals < gr_cut),
                                     color="gold", alpha=0.35, label="Sand")
                    ax.fill_betweenx(depth, 0, vals, where=(vals >= gr_cut),
                                     color="gray", alpha=0.25, label="Shale")
            elif curve == "RHOB":
                ax.plot(vals, depth, color=color, linewidth=0.8, label=curve)
                ax.set_xlim(1.65, 2.65)
                if "NPHI" in df.columns and "PHIT_D" in df.columns:
                    ax.fill_betweenx(depth, df["NPHI"], df["PHIT_D"],
                                     where=(df["NPHI"] > df["PHIT_D"]),
                                     color="blue", alpha=0.20, label="Wet")
                    ax.fill_betweenx(depth, df["NPHI"], df["PHIT_D"],
                                     where=(df["PHIT_D"] > df["NPHI"]),
                                     color="red", alpha=0.20, label="Gas Effect")
            else:
                ax.plot(vals, depth, color=color, linewidth=0.8, label=curve)

        ax.legend(loc="lower right", fontsize=5, framealpha=0.6)

        if formation_tops is not None and not formation_tops.empty:
            for _, top_row in formation_tops.iterrows():
                td = top_row.get("top_depth", None)
                fname = top_row.get("formation", "")
                if td is not None and depth.min() <= td <= depth.max():
                    ax.axhline(y=td, color="darkred", linewidth=0.8,
                               linestyle="--", zorder=5)
                    if ax == axes[0]:
                        ax.text(ax.get_xlim()[1], td, f" {fname}",
                                fontsize=6, color="darkred", va="center",
                                ha="left", clip_on=False)

    axes[0].set_ylabel(f"Depth ({depth_col})", fontsize=9)

    fig.text(0.01, 0.005, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             fontsize=6, color="gray", ha="left")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        log.info(f"[SAVED] Multi-track log plot → {save_path}")
    plt.close(fig)
