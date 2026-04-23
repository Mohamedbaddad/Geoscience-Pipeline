from __future__ import annotations
import pandas as pd
import numpy as np
import logging

log = logging.getLogger(__name__)

def compute_vsh_gr(gr: pd.Series, gr_clean: float = None, gr_shale: float = None) -> pd.Series:
    """Larionov (1969) corrected for Tertiary rocks."""
    if gr_clean is None: gr_clean = gr.quantile(0.05)
    if gr_shale is None: gr_shale = gr.quantile(0.95)
    if gr_shale == gr_clean:
        return pd.Series(0, index=gr.index, name="VSH")
    igr = (gr - gr_clean) / (gr_shale - gr_clean)
    igr = igr.clip(0, 1)
    vsh = 0.083 * (2 ** (3.7 * igr) - 1)
    return vsh.clip(0, 1).rename("VSH")

def compute_phit_density(rhob: pd.Series, rho_matrix: float = 2.65, rho_fluid: float = 1.0) -> pd.Series:
    phit = (rho_matrix - rhob) / (rho_matrix - rho_fluid)
    return phit.clip(0, 0.45).rename("PHIT_D")

def compute_nd_crossover(nphi: pd.Series, phit_d: pd.Series) -> pd.Series:
    return (nphi - phit_d).rename("ND_CROSSOVER")

def flag_reservoir(df: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    if all(c in df.columns for c in ["VSH", "PHIT_D", "RT"]):
        mask = (df["VSH"] < 0.35) & (df["PHIT_D"] > 0.08) & (df["RT"] > 10.0)
    return mask.rename("RESERVOIR_FLAG")

def compute_ai(rhob: pd.Series, dt: pd.Series) -> pd.Series:
    vp = 1e6 / (dt * 3.28084)
    ai = vp * rhob * 1000
    return ai.rename("AI")

def compute_reflection_coefficient(ai: pd.Series) -> pd.Series:
    ai_shifted = ai.shift(-1)
    denom = ai_shifted + ai
    rc = (ai_shifted - ai) / np.where(denom == 0, np.nan, denom)
    return rc.fillna(0).rename("RC")

def compute_derived_logs(df: pd.DataFrame) -> pd.DataFrame:
    df_derived = df.copy()
    if "GR" in df_derived.columns:
        df_derived["VSH"] = compute_vsh_gr(df_derived["GR"])
    if "RHOB" in df_derived.columns:
        df_derived["PHIT_D"] = compute_phit_density(df_derived["RHOB"])
    if "NPHI" in df_derived.columns and "PHIT_D" in df_derived.columns:
        df_derived["ND_CROSSOVER"] = compute_nd_crossover(df_derived["NPHI"], df_derived["PHIT_D"])
    
    df_derived["RESERVOIR_FLAG"] = flag_reservoir(df_derived)
    
    if "RHOB" in df_derived.columns and "DT" in df_derived.columns:
        df_derived["AI"] = compute_ai(df_derived["RHOB"], df_derived["DT"])
        df_derived["RC"] = compute_reflection_coefficient(df_derived["AI"])
        
    return df_derived
