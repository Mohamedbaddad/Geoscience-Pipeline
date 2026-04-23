from __future__ import annotations
import json
import xml.etree.ElementTree as ET
import pandas as pd
import configparser
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def xml_to_dict(element):
    d = {}
    for child in element:
        if len(child) > 0:
            d[child.tag] = xml_to_dict(child)
        else:
            d[child.tag] = child.text
    return d

def load_pet(path: Path) -> dict:
    result = {"path": str(path), "format": "unknown", "data": None, "count": 0}
    try:
        raw = path.read_bytes()
        
        # 1. Attempt JSON
        try:
            content = raw.decode('utf-8', errors='replace')
            data = json.loads(content)
            result["format"] = "json"
            result["data"] = data
            result["count"] = len(data) if isinstance(data, dict) else len(data)
            return result
        except Exception:
            pass
            
        # 2. Attempt XML
        try:
            root = ET.fromstring(raw)
            data = flatten_dict(xml_to_dict(root))
            result["format"] = "xml"
            result["data"] = data
            result["count"] = len(data)
            return result
        except Exception:
            pass
            
        # 3. Attempt CSV/TSV
        try:
            df = pd.read_csv(path, sep=None, engine='python')
            if df.shape[1] >= 2 and df.shape[0] >= 3:
                result["format"] = "csv"
                result["data"] = df
                result["count"] = df.shape[0]
                return result
        except Exception:
            pass
            
        # 4. Attempt INI
        try:
            config = configparser.ConfigParser()
            config.read(path)
            if config.sections():
                result["format"] = "ini"
                result["data"] = {s: dict(config.items(s)) for s in config.sections()}
                result["count"] = len(config.sections())
                return result
        except Exception:
            pass
            
        # 5. Fall through
        content = raw.decode('utf-8', errors='replace')
        result["format"] = "raw"
        result["data"] = {"pet_raw_text": content[:10000]}
        result["count"] = 1
        
    except Exception as e:
        log.error(f"Error loading PET file {path}: {e}")
        
    return result
