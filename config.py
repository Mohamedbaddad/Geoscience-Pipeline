from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
REPORTS_DIR = BASE_DIR / "reports"

# Unit flags
DEPTH_UNIT = "M"
SEISMIC_UNIT = "ms"
PROJECT_CRS = "EPSG:4326"

# Curve aliases
CURVE_ALIASES = {
    # Gamma Ray
    "GAMMA": "GR", "GR_DL": "GR", "GR_EDTC": "GR", "SGR": "GR", "GRAFM": "GR", "GR1BFM": "GR", "GR2AFM": "GR",
    # Bulk Density
    "DEN": "RHOB", "ZDEN": "RHOB", "RHOZ": "RHOB", "DPHI": "RHOB", "BDCM": "RHOB", "BDCFM": "RHOB",
    # Neutron Porosity
    "NEU": "NPHI", "TNPH": "NPHI", "CNCF": "NPHI", "NEUT": "NPHI", "NPLM": "NPHI", "NPLFM": "NPHI",
    # Resistivity
    "RESD": "RT", "ILD": "RT", "AT90": "RT", "M2RX": "RT", "LLD": "RT", "RPTHM": "RT", "RACLM": "RT",
    "RESM": "RILM", "ILM": "RILM",
    "RESS": "RILD", "SFL": "RILD",
    # Sonic
    "DTC": "DT", "DTCO": "DT", "AC": "DT", "DTPM": "DT", "DTP4M": "DT",
    # Caliper
    "CAL": "CALI", "C1": "CALI", "CALFM": "CALI",
    # SP
    "SPONTANEOUS_POTENTIAL": "SP",
    # Photoelectric
    "PEF": "PE", "PEFZ": "PE", "DPEM": "PE",
}

CURVE_GROUPS = {
    "lithology":    ["GR", "SP", "PE", "CALI"],
    "porosity":     ["NPHI", "RHOB", "DT", "DPHI"],
    "resistivity":  ["RT", "RILM", "RILD", "MSFL"],
    "auxiliary":    ["CALI", "BS", "DRHO", "DCAL"],
}
