from __future__ import annotations
import pandas as pd
import numpy as np
import logging

log = logging.getLogger(__name__)

from config import CURVE_ALIASES, CURVE_GROUPS

def normalize_curve_names(df: pd.DataFrame) -> pd.DataFrame:
    original_cols = df.columns.tolist()
    rename_map = {col: CURVE_ALIASES.get(col.upper(), col) for col in df.columns}
    df_renamed = df.rename(columns=rename_map)
    renamed_cols = [f"{o}->{n}" for o, n in zip(original_cols, df_renamed.columns) if o != n]
    if renamed_cols:
        log.info(f"Renamed curves: {renamed_cols}")
    return df_renamed

def classify_curves(df: pd.DataFrame) -> dict:
    groups = {}
    for group_name, curves in CURVE_GROUPS.items():
        present = [c for c in curves if c in df.columns]
        groups[group_name] = present
    return groups

def apply_qc(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    qc_flags = pd.DataFrame(index=df.index)
    df_clean = df.copy()
    
    # 1. Flag bad borehole intervals
    if "CALI" in df_clean.columns:
        bs = df_clean.get("BS", 8.5)
        if isinstance(bs, pd.Series):
            qc_flags["BAD_BOREHOLE"] = df_clean["CALI"] > 1.5 * bs
        else:
            qc_flags["BAD_BOREHOLE"] = df_clean["CALI"] > 1.5 * bs
            
    # 2. Spike detection
    for curve in ["GR", "RHOB", "NPHI"]:
        if curve in df_clean.columns:
            median = df_clean[curve].rolling(window=5, center=True).median()
            std = df_clean[curve].rolling(window=5, center=True).std()
            spike_mask = np.abs(df_clean[curve] - median) > 3 * std
            qc_flags[f"SPIKE_{curve}"] = spike_mask.fillna(False)
            
    # 3. Interpolation policy (only fill gaps <= 3 depth steps)
    for curve in df_clean.columns:
        if curve != "DEPTH" and pd.api.types.is_numeric_dtype(df_clean[curve]):
            isna = df_clean[curve].isna()
            gap_groups = (isna != isna.shift()).cumsum()
            gap_sizes = isna.groupby(gap_groups).sum()
            valid_gaps = gap_sizes[gap_sizes <= 3].index
            fill_mask = isna & gap_groups.isin(valid_gaps)
            
            if fill_mask.any():
                qc_flags[f"FILLED_{curve}"] = fill_mask
                df_clean.loc[fill_mask, curve] = df_clean[curve].interpolate(method="linear")
                
    # 4. Report completeness
    completeness = (df_clean.notna().sum() / len(df_clean) * 100).to_dict()
    log.info(f"Curve completeness: {completeness}")
    
    return df_clean, qc_flags
