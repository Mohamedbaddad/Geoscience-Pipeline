from __future__ import annotations
import lasio
import pandas as pd
import numpy as np
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def load_las(path: Path) -> tuple[pd.DataFrame, dict]:
    """
    Load a LAS file. Returns (dataframe, metadata_dict).
    Handles encoding errors, null value replacement, and version 1.2/2.0.
    """
    las = lasio.read(str(path), ignore_header_errors=True, read_policy="default")
    df = las.df().reset_index()           # depth becomes a column, not index
    
    df.rename(columns={"DEPT": "DEPTH", "DEPTH": "DEPTH"}, inplace=True)

    # Replace LAS null value sentinel (commonly -999.25) with NaN
    null_val = las.well.NULL.value if hasattr(las.well, "NULL") else -999.25
    df.replace(null_val, np.nan, inplace=True)

    metadata = {
        "well_name": las.well.WELL.value if hasattr(las.well, "WELL") else path.stem,
        "company":   las.well.COMP.value if hasattr(las.well, "COMP") else "UNKNOWN",
        "field":     las.well.FLD.value  if hasattr(las.well, "FLD")  else "UNKNOWN",
        "start_depth": las.well.STRT.value if hasattr(las.well, "STRT") else None,
        "stop_depth":  las.well.STOP.value if hasattr(las.well, "STOP") else None,
        "step":        las.well.STEP.value if hasattr(las.well, "STEP") else None,
        "depth_unit":  las.well.STRT.unit if hasattr(las.well, "STRT") else "M",
        "curves":      {c.mnemonic: c.descr for c in las.curves},
        "source_path": str(path),
    }
    return df, metadata
