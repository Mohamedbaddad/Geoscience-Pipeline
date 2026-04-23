from __future__ import annotations
import segyio
import numpy as np
import pandas as pd
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def inspect_segy(path: Path) -> dict:
    """Read only binary and text headers. No trace data loaded."""
    with segyio.open(str(path), ignore_geometry=True) as f:
        n_traces   = f.tracecount
        n_samples  = f.bin[segyio.BinField.Samples]
        sample_int = f.bin[segyio.BinField.Interval] / 1000.0   # µs → ms
        text_hdr   = segyio.tools.wrap(f.text[0])
        binary_hdr = dict(f.bin)
        keys = [k for k in dir(segyio.TraceField) if not k.startswith('_') and k != 'enums']
        trace_headers = [
            {k: f.header[i][getattr(segyio.TraceField, k)] for k in keys}
            for i in range(min(10, n_traces))
        ]
    return {
        "path": str(path),
        "n_traces": n_traces,
        "n_samples": n_samples,
        "sample_interval_ms": sample_int,
        "total_time_ms": n_samples * sample_int,
        "text_header": text_hdr,
        "binary_header": binary_hdr,
        "sample_trace_headers": trace_headers,
        "estimated_size_mb": (n_traces * n_samples * 4) / 1e6,
    }

def load_segy(path: Path, info: dict, memory_limit_mb: int = 2048) -> dict:
    decimation = max(1, int(np.ceil(info["estimated_size_mb"] / memory_limit_mb)))
    if decimation > 1:
        log.warning(f"Large SEGY file detected. Decimating by factor {decimation} for in-memory analysis.")
    with segyio.open(str(path), ignore_geometry=True) as f:
        trace_indices = list(range(0, f.tracecount, decimation))
        data = np.stack([f.trace[i] for i in trace_indices], axis=0)   # shape: (n_traces_loaded, n_samples)
        all_headers = [{
            "inline":    f.header[i][segyio.TraceField.INLINE_3D],
            "crossline": f.header[i][segyio.TraceField.CROSSLINE_3D],
            "cdpx":      f.header[i][segyio.TraceField.CDP_X],
            "cdpy":      f.header[i][segyio.TraceField.CDP_Y],
            "offset":    f.header[i][segyio.TraceField.offset],
            "shotpoint": f.header[i][segyio.TraceField.FieldRecord],
        } for i in range(f.tracecount)]
    time_axis = np.arange(info["n_samples"]) * info["sample_interval_ms"]
    
    # Check geometry
    is_2d = True
    inlines = set(h["inline"] for h in all_headers)
    if len(inlines) > 1 and max(inlines) > 0:
        is_2d = False
    
    info["geometry"] = "2D" if is_2d else "3D"
    log.info(f"Detected SEGY geometry: {info['geometry']}")
    
    # Amplitude Normalization (RMS)
    rms = np.sqrt(np.mean(data**2, axis=1, keepdims=True))
    data = data / (rms + 1e-10)
    
    return {
        "data":         data,
        "time_axis_ms": time_axis,
        "headers_df":   pd.DataFrame(all_headers),
        "decimation":   decimation,
        "info":         info,
    }
