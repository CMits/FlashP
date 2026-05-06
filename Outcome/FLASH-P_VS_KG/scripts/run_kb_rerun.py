#!/usr/bin/env python3
"""
KB rerun orchestrator.

Assumes that validators have already been run (by run_validators_individual.py
and run_validators_merged.py). This script:

1. Runs Agent/shared/export_supplementary.py on every KB rerun network.
2. Runs scripts/build_table_s8b_per_phenotype.py on the merged KB network.
3. Builds results/comparison_summary.json + results/figure_data.csv pulling:
   - FLASH-P metrics from Arabidopsis/<Phenotype>_network/validation/ + merged_arabidopsis_network/validation/
   - KB metrics from Knowledge_Base_Comparison_rerun_2026-04-20/KB_Cleaned/<trait>_network/validation/
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "Agent" / "shared"
FLASHP = ROOT / "Arabidopsis"
MERGED_FP = ROOT / "merged_arabidopsis_network"
RERUN = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20"
KB = RERUN / "KB_Cleaned"
SCRIPTS = RERUN / "scripts"
RESULTS = RERUN / "results"

TRAITS = [
    ("shoot_branching",      "Shoot_Branching_network"),
    ("flowering_time",       "Flowering_Time_network"),
    ("hypocotyl_length",     "Hypocotyl_Length_network"),
    ("plant_height",         "Plant_Height_network"),
    ("lateral_root_density", "Lateral_Root_Density_network"),
    ("seed_size",            "Seed_Size_network"),
]

VAL_FILES = {
    "algebraic": "script_validation_results.json",
    "ode":       "ode_validation_results.json",
    "rwr":       "rwr_validation_results.json",
}


def run(cmd):
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    dt = time.time() - t0
    if r.returncode != 0:
        print(f"  ! {' '.join(map(str, cmd))} failed ({dt:.0f}s)")
        print(f"    stderr: {r.stderr[:300]}")
        return False
    print(f"  ok ({dt:.0f}s)")
    return True


def export_all_supplementary():
    print("\n--- Export supplementary for each KB network ---")
    script = SHARED / "export_supplementary.py"
    for trait, _ in TRAITS:
        ndir = KB / f"{trait}_network"
        if not ndir.exists():
            continue
        print(f"\nexport_supplementary {trait}")
        run([sys.executable, str(script), str(ndir)])

    print(f"\nexport_supplementary merged")
    run([sys.executable, str(script), str(KB / "merged_arabidopsis_network")])


def build_table_s8b():
    print("\n--- Build Table_S8b per-phenotype-in-merged ---")
    run([sys.executable, str(SCRIPTS / "build_table_s8b_per_phenotype.py"),
         str(KB / "merged_arabidopsis_network" / "supplementary")])


def copy_pleiotropic_to_supplementary():
    """After Agent/validate_pleiotropic.py runs, copy its validation/pleiotropic_*
    CSVs into supplementary/Table_S10* names (matching merged_arabidopsis_network layout).
    """
    import shutil
    print("\n--- Copy pleiotropic CSVs to Table_S10* ---")
    val = KB / "merged_arabidopsis_network" / "validation"
    supp = KB / "merged_arabidopsis_network" / "supplementary"
    supp.mkdir(parents=True, exist_ok=True)
    moves = [
        ("pleiotropic_summary.csv",        "Table_S10_pleiotropic_summary.csv"),
        ("pleiotropic_algebraic_results.csv", "Table_S10a_pleiotropic_algebraic.csv"),
        ("pleiotropic_ode_results.csv",       "Table_S10b_pleiotropic_ode.csv"),
        ("pleiotropic_rwr_results.csv",       "Table_S10c_pleiotropic_rwr.csv"),
    ]
    for src, dst in moves:
        s = val / src
        d = supp / dst
        if s.exists():
            shutil.copy2(s, d)
            print(f"  {s.name} -> {d.name}")
        else:
            print(f"  skip (missing) {s}")


def read_metrics(val_dir: Path, filename: str):
    p = val_dir / filename
    if not p.exists():
        return None
    try:
        d = json.load(open(p, "r", encoding="utf-8"))
    except Exception:
        return None
    m = d.get("metrics", {}) or {}
    s = d.get("summary", {}) or {}
    return {
        "accuracy": m.get("overall_accuracy", 0),
        "n_tested": s.get("tested", 0),
        "kappa":    m.get("cohens_kappa", 0),
        "mcc":      m.get("mcc", 0),
        "frs":      m.get("frs", 0),
        "dars":     m.get("dars", 0),
    }


def build_summary():
    print("\n--- Build comparison_summary.json + figure_data.csv ---")
    RESULTS.mkdir(parents=True, exist_ok=True)

    out = {"FLASH_P": {}, "KB_Cleaned": {}}

    # FLASH-P side
    for trait, fp_dir in TRAITS:
        td = {}
        for m, fn in VAL_FILES.items():
            td[m] = read_metrics(FLASHP / fp_dir / "validation", fn) or {}
        out["FLASH_P"][trait] = td
    td = {}
    for m, fn in VAL_FILES.items():
        td[m] = read_metrics(MERGED_FP / "validation", fn) or {}
    out["FLASH_P"]["merged"] = td

    # KB side
    for trait, _ in TRAITS:
        td = {}
        for m, fn in VAL_FILES.items():
            td[m] = read_metrics(KB / f"{trait}_network" / "validation", fn) or {}
        out["KB_Cleaned"][trait] = td
    td = {}
    for m, fn in VAL_FILES.items():
        td[m] = read_metrics(KB / "merged_arabidopsis_network" / "validation", fn) or {}
    out["KB_Cleaned"]["merged"] = td

    (RESULTS / "comparison_summary.json").write_text(
        json.dumps({"date": str(date.today()), "results": out}, indent=2),
        encoding="utf-8")

    # figure_data.csv (long)
    with open(RESULTS / "figure_data.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trait", "source", "method", "accuracy", "n_tested",
                    "kappa", "mcc", "frs", "dars"])
        for src in ("FLASH_P", "KB_Cleaned"):
            for trait_key in [t for t, _ in TRAITS] + ["merged"]:
                for m in ("algebraic", "ode", "rwr"):
                    d = out[src].get(trait_key, {}).get(m, {}) or {}
                    w.writerow([trait_key, src, m,
                                d.get("accuracy", 0),
                                d.get("n_tested", 0),
                                d.get("kappa", 0),
                                d.get("mcc", 0),
                                d.get("frs", 0),
                                d.get("dars", 0)])
    print(f"  wrote {RESULTS / 'comparison_summary.json'}")
    print(f"  wrote {RESULTS / 'figure_data.csv'}")

    # Pretty summary
    print(f"\n{'trait':<22} {'source':<11} {'alg':>7} {'ode':>7} {'rwr':>7}   n")
    print("-" * 70)
    for trait_key in [t for t, _ in TRAITS] + ["merged"]:
        for src in ("FLASH_P", "KB_Cleaned"):
            r = out[src].get(trait_key, {})
            a = r.get("algebraic", {}).get("accuracy", 0)
            o = r.get("ode", {}).get("accuracy", 0)
            w = r.get("rwr", {}).get("accuracy", 0)
            n = r.get("algebraic", {}).get("n_tested", 0)
            print(f"{trait_key:<22} {src:<11} {a:>6.1f}% {o:>6.1f}% {w:>6.1f}%   {n}")
        print()


def main():
    export_all_supplementary()
    copy_pleiotropic_to_supplementary()
    build_table_s8b()
    build_summary()


if __name__ == "__main__":
    main()
