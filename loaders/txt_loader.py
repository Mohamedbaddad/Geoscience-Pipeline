from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import re
import logging

log = logging.getLogger(__name__)

def classify_txt_content(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "unknown"
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        return "unknown"
    # Formation tops: lines like "FORMATION   TOP_DEPTH   BASE_DEPTH"
    top_keywords = {"top", "formation", "marker", "pick", "tvdss", "kb", "md"}
    if any(any(kw in l.lower() for kw in top_keywords) for l in lines[:10]):
        return "formation_tops"
    # LAS header dump: contains ~WELL or ~VERSION
    if any(l.startswith("~") for l in lines[:20]):
        return "log_header_dump"
    # Tabular: mostly lines with consistent delimiter counts
    delimiters = [",", "\t", "|", ";"]
    for d in delimiters:
        counts = [l.count(d) for l in lines[:20] if l]
        if counts and max(counts) > 1 and np.std(counts) < 1.0:
            return "tabular_data"
    return "free_text"

def parse_txt(path: Path) -> dict:
    content_type = classify_txt_content(path)
    result = {"type": content_type, "path": str(path)}
    
    try:
        if content_type == "formation_tops":
            try:
                df = pd.read_csv(path, sep=None, engine='python')
                df.columns = [str(c).lower().strip() for c in df.columns]
                col_map = {}
                for c in df.columns:
                    if "form" in c or "mark" in c or "name" in c:
                        col_map[c] = "formation"
                    elif "top" in c or "depth" in c and "base" not in c and "bot" not in c:
                        col_map[c] = "top_depth"
                    elif "base" in c or "bot" in c:
                        col_map[c] = "base_depth"
                df.rename(columns=col_map, inplace=True)
                cols_to_keep = [c for c in ["formation", "top_depth", "base_depth"] if c in df.columns]
                result["data"] = df[cols_to_keep] if cols_to_keep else df
            except Exception as e:
                log.warning(f"Failed to parse formation tops {path}: {e}")
                result["data"] = pd.DataFrame()
        elif content_type == "tabular_data":
            result["data"] = pd.read_csv(path, sep=None, engine='python')
        elif content_type == "log_header_dump":
            raw = path.read_text(encoding="utf-8", errors="replace")
            kv = {}
            for match in re.finditer(r"([A-Z_]+)\s*[:=]\s*(.+)", raw):
                kv[match.group(1)] = match.group(2).strip()
            result["data"] = kv
        else:
            result["data"] = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.error(f"Error parsing txt {path}: {e}")
        result["data"] = None
        
    return result
