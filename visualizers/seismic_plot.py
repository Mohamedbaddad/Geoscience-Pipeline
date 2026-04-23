from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def plot_seismic_section(segy_data: dict, save_path: str = None,
                         clip_percentile: float = 98.0,
                         colormap: str = "Greys"):
    data   = segy_data["data"]
    t_axis = segy_data["time_axis_ms"]
    info   = segy_data["info"]

    clip = np.percentile(np.abs(data), clip_percentile)
    fig, ax = plt.subplots(figsize=(14, 8))

    im = ax.imshow(
        data.T,
        aspect="auto",
        cmap=colormap,
        vmin=-clip, vmax=clip,
        extent=[0, data.shape[0], t_axis[-1], t_axis[0]],
        interpolation="bilinear",
    )
    ax.set_xlabel("Trace Number" + (f" (decimated ×{info.get('decimation', 1)})"
                                    if info.get("decimation", 1) > 1 else ""), fontsize=10)
    ax.set_ylabel("Two-Way Time (ms)", fontsize=10)
    ax.set_title(f"Seismic Section — {Path(info['path']).name}", fontsize=12)
    plt.colorbar(im, ax=ax, label="Amplitude", fraction=0.02, pad=0.01)
    ax.grid(False)
    fig.text(0.01, 0.005, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             fontsize=6, color="gray")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        log.info(f"[SAVED] Seismic section → {save_path}")
    plt.close(fig)
