from __future__ import annotations
import os
import sys
import logging
from pathlib import Path
import json
import numpy as np
import pandas as pd
from tqdm import tqdm

from config import DEPTH_UNIT, SEISMIC_UNIT, PROJECT_CRS
from loaders.las_loader import load_las
from loaders.segy_loader import inspect_segy, load_segy
from loaders.txt_loader import parse_txt
from loaders.pet_loader import load_pet
from processors.las_processor import normalize_curve_names, apply_qc
from processors.petrophysics import compute_derived_logs
from visualizers.log_plot import plot_multitrack_log
from visualizers.crossplot import plot_rhob_nphi_crossplot, plot_phit_rt_crossplot, plot_ai_synthetic
from visualizers.seismic_plot import plot_seismic_section

np.random.seed(42)

class FileScanner:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
    
    def scan(self) -> dict:
        manifest = {
            "las":  [],
            "segy": [],
            "txt":  [],
            "pet":  [],
            "skipped": []
        }
        
        counts = {"las": 0, "segy": 0, "txt": 0, "pet": 0, "skipped": 0}
        sizes = {"las": 0.0, "segy": 0.0, "txt": 0.0, "pet": 0.0, "skipped": 0.0}
        
        for path in self.directory.rglob("*"):
            if not path.is_file():
                continue
                
            ext = path.suffix.lower()
            size_mb = path.stat().st_size / (1024 * 1024)
            
            if ext == ".lock":
                manifest["skipped"].append(path)
                counts["skipped"] += 1
                sizes["skipped"] += size_mb
                logging.getLogger(__name__).info(f"Skipped .lock file: {path}")
            elif ext == ".env":
                try:
                    content = path.read_text()
                    if any(k in content for k in ["DEPTH_UNIT", "SEISMIC_UNIT", "PROJECT_CRS"]):
                        logging.getLogger(__name__).info(f"Parsed config from {path}")
                except Exception:
                    pass
                manifest["skipped"].append(path)
                counts["skipped"] += 1
                sizes["skipped"] += size_mb
            elif ext in [".las"]:
                manifest["las"].append(path)
                counts["las"] += 1
                sizes["las"] += size_mb
            elif ext in [".segy", ".sgy"]:
                manifest["segy"].append(path)
                counts["segy"] += 1
                sizes["segy"] += size_mb
            elif ext in [".txt"]:
                manifest["txt"].append(path)
                counts["txt"] += 1
                sizes["txt"] += size_mb
            elif ext in [".pet"]:
                manifest["pet"].append(path)
                counts["pet"] += 1
                sizes["pet"] += size_mb
            else:
                manifest["skipped"].append(path)
                counts["skipped"] += 1
                sizes["skipped"] += size_mb
                
        print("╔" + "═"*42 + "╗")
        print("║      GEOSCIENCE FILE MANIFEST SUMMARY    ║")
        print("╠" + "═"*11 + "╦" + "═"*10 + "╦" + "═"*19 + "╣")
        print(f"║ Type      ║ Count    ║ Total Size (MB)   ║")
        print("╠" + "═"*11 + "╬" + "═"*10 + "╬" + "═"*19 + "╣")
        for k in ["las", "segy", "txt", "pet"]:
            print(f"║ {k.upper():<9} ║ {counts[k]:<8} ║ {sizes[k]:<17.2f} ║")
        print(f"║ Skipped   ║ {counts['skipped']:<8} ║ —                 ║")
        print("╚" + "═"*11 + "╩" + "═"*10 + "╩" + "═"*19 + "╝")
        
        return manifest

def run_pipeline(input_directory: str):
    os.makedirs("reports", exist_ok=True)
    logging.basicConfig(filename="reports/pipeline_summary.txt", level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger(__name__)
    log.info(f"Pipeline started. Input directory: {input_directory}")

    scanner = FileScanner(input_directory)
    manifest = scanner.scan()
    
    os.makedirs("outputs/data", exist_ok=True)
    with open("outputs/data/pipeline_manifest.json", "w") as f:
        json.dump({k: [str(p) for p in v] for k, v in manifest.items()}, f, indent=2)

    wells = {}
    for las_path in tqdm(manifest["las"], desc="Loading LAS files"):
        try:
            df, meta = load_las(las_path)
            if len(df) > 1 and df["DEPTH"].iloc[0] > df["DEPTH"].iloc[-1]:
                df = df.iloc[::-1].reset_index(drop=True)
            df = normalize_curve_names(df)
            df, qc_flags = apply_qc(df)
            df = compute_derived_logs(df)
            well_name = meta["well_name"]
            if well_name in wells:
                # Merge if well already exists (e.g. Wireline + LWD)
                wells[well_name]["df"] = pd.merge(wells[well_name]["df"], df, on="DEPTH", how="outer").sort_values("DEPTH")
                wells[well_name]["qc_flags"] = pd.concat([wells[well_name]["qc_flags"], qc_flags], axis=1)
                wells[well_name]["meta"].update(meta)
            else:
                wells[well_name] = {"df": df, "meta": meta, "qc_flags": qc_flags}
            log.info(f"LAS loaded: {meta['well_name']} | Curves: {list(df.columns)} | Rows: {len(df)}")
        except Exception as e:
            log.error(f"Failed to load LAS {las_path}: {e}")

    segy_datasets = {}
    for segy_path in tqdm(manifest["segy"], desc="Loading SEGY files"):
        try:
            info = inspect_segy(segy_path)
            segy_data = load_segy(segy_path, info)
            segy_datasets[segy_path.stem] = segy_data
            log.info(f"SEGY loaded: {segy_path.name} | Traces: {info['n_traces']} | "
                     f"Samples: {info['n_samples']} | dt: {info['sample_interval_ms']} ms")
        except Exception as e:
            log.error(f"Failed to load SEGY {segy_path}: {e}")

    formation_tops_all = {}
    for txt_path in tqdm(manifest["txt"], desc="Parsing TXT files"):
        try:
            result = parse_txt(txt_path)
            if result["type"] == "formation_tops":
                well_key = txt_path.stem
                formation_tops_all[well_key] = result["data"]
            log.info(f"TXT parsed: {txt_path.name} | Type: {result['type']}")
        except Exception as e:
            log.error(f"Failed to parse TXT {txt_path}: {e}")

    for pet_path in tqdm(manifest["pet"], desc="Inspecting PET files"):
        try:
            pet_result = load_pet(pet_path)
            log.info(f"PET file {pet_path.name}: format={pet_result['format']}")
        except Exception as e:
            log.error(f"Failed to inspect PET {pet_path}: {e}")

    os.makedirs("outputs/figures", exist_ok=True)
    for well_name, well_data in tqdm(wells.items(), desc="Generating log plots"):
        tops = None
        for k, v in formation_tops_all.items():
            if k in well_name or well_name in k:
                tops = v
                break
                
        plot_multitrack_log(
            well_name=well_name,
            df=well_data["df"],
            formation_tops=tops,
            save_path=f"outputs/figures/{well_name}_multitrack.png"
        )
        plot_rhob_nphi_crossplot(
            df=well_data["df"],
            well_name=well_name,
            save_path=f"outputs/figures/{well_name}_rhob_nphi.png"
        )
        plot_phit_rt_crossplot(
            df=well_data["df"],
            well_name=well_name,
            save_path=f"outputs/figures/{well_name}_phit_rt.png"
        )
        plot_ai_synthetic(
            df=well_data["df"],
            well_name=well_name,
            save_path=f"outputs/figures/{well_name}_ai_synthetic.png"
        )

    for name, segy_data in tqdm(segy_datasets.items(), desc="Generating seismic plots"):
        plot_seismic_section(
            segy_data=segy_data,
            save_path=f"outputs/figures/{name}_section.png"
        )

    for well_name, well_data in wells.items():
        out_path = f"outputs/data/{well_name}_processed.csv"
        well_data["df"].to_csv(out_path, index=False)
        log.info(f"Exported processed well data → {out_path}")

    log.info("Pipeline completed successfully.")
    print("\n[DONE] Pipeline complete. See outputs/ for figures and data.")
    print(f"[DONE] Full log written to: reports/pipeline_summary.txt")


if __name__ == "__main__":
    import sys
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    run_pipeline(input_dir)
