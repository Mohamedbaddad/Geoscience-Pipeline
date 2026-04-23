from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import logging

log = logging.getLogger(__name__)

def plot_rhob_nphi_crossplot(df: pd.DataFrame, well_name: str, save_path: str = None):
    if "RHOB" not in df.columns or "NPHI" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    color_col = df["GR"] if "GR" in df.columns else df.get("VSH", None)
    
    if color_col is not None:
        sc = ax.scatter(df["NPHI"], df["RHOB"], c=color_col, cmap="RdYlGn_r",
                        s=4, alpha=0.5, vmin=0, vmax=150 if "GR" in df.columns else 1)
        plt.colorbar(sc, ax=ax, label="GR (API)" if "GR" in df.columns else "VSH")
    else:
        ax.scatter(df["NPHI"], df["RHOB"], s=4, alpha=0.5, color='blue')

    minerals = {"Quartz": (0.0, 2.65), "Calcite": (0.0, 2.71),
                "Dolomite": (0.02, 2.87), "Anhydrite": (-0.01, 2.98)}
    for name, (nphi_pt, rhob_pt) in minerals.items():
        ax.plot(nphi_pt, rhob_pt, "k^", markersize=8)
        ax.annotate(name, (nphi_pt, rhob_pt), textcoords="offset points",
                    xytext=(5, 3), fontsize=8)
    ax.set_xlabel("NPHI (v/v)")
    ax.set_ylabel("RHOB (g/cc)")
    ax.set_xlim(-0.05, 0.60)
    ax.set_ylim(3.0, 1.8)   # inverted Y
    ax.set_title(f"Density–Neutron Crossplot — {well_name}")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    fig.text(0.01, 0.005, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             fontsize=6, color="gray")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_phit_rt_crossplot(df: pd.DataFrame, well_name: str, save_path: str = None):
    if "PHIT_D" not in df.columns or "RT" not in df.columns or "DEPTH" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    sc = ax.scatter(df["PHIT_D"], df["RT"], c=df["DEPTH"], cmap="viridis", s=4, alpha=0.5)
    plt.colorbar(sc, ax=ax, label="Depth")
    ax.set_yscale('log')
    ax.set_xlabel("PHIT (v/v)")
    ax.set_ylabel("RT (ohm.m)")
    ax.set_title(f"Pickett Plot — {well_name}")
    
    ax.axvspan(0.10, 0.45, ymin=0.5, ymax=1.0, color='green', alpha=0.1, label='Pay Zone')
    
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    fig.text(0.01, 0.005, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fontsize=6, color="gray")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_ai_synthetic(df: pd.DataFrame, well_name: str, save_path: str = None):
    if "AI" not in df.columns or "RC" not in df.columns or "DEPTH" not in df.columns:
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6, 10), sharey=True)
    depth = df["DEPTH"]
    
    ax1.plot(df["AI"], depth, color='blue')
    ax1.set_xlabel("Acoustic Impedance")
    ax1.set_ylabel("Depth")
    ax1.set_ylim(depth.max(), depth.min())
    ax1.grid(True)
    
    ax2.plot(df["RC"], depth, color='black')
    ax2.fill_betweenx(depth, 0, df["RC"], where=(df["RC"] > 0), color='black')
    ax2.set_xlabel("Reflection Coefficient")
    ax2.set_xlim(-0.5, 0.5)
    ax2.grid(True)
    
    fig.suptitle(f"Synthetic Seismogram Preview — {well_name}")
    fig.text(0.01, 0.005, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fontsize=6, color="gray")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
