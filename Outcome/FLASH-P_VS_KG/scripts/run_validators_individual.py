#!/usr/bin/env python3
"""Run algebraic + ODE(--sensitivity) + RWR(--sensitivity) on all 6 KB individual networks."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "Agent" / "shared"
KB = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20" / "KB_Cleaned"

TRAITS = [
    "shoot_branching", "flowering_time", "hypocotyl_length",
    "plant_height", "lateral_root_density", "seed_size",
]

VALIDATORS = [
    ("algebraic", SHARED / "flashp_validator.py", ["--csv", "--full-state"]),
    ("ode",       SHARED / "ode_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
    ("rwr",       SHARED / "rwr_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
]


def run_one(script: Path, network_dir: Path, args):
    cmd = [sys.executable, str(script), str(network_dir)] + args
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=7200)
        dt = time.time() - t0
        if r.returncode != 0:
            print(f"    FAILED ({dt:.0f}s): {r.stderr[:300]}")
            return False
        # extract final accuracy line from stdout if present
        last = [ln for ln in r.stdout.splitlines() if "Accuracy" in ln or "accuracy" in ln]
        last_s = last[-1] if last else ""
        print(f"    OK ({dt:.0f}s)  {last_s}")
        return True
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {time.time() - t0:.0f}s")
        return False


def main():
    overall_t0 = time.time()
    for trait in TRAITS:
        ndir = KB / f"{trait}_network"
        if not ndir.exists():
            print(f"SKIP {trait}: {ndir} missing")
            continue
        print(f"\n=== {trait} ===")
        for name, script, args in VALIDATORS:
            print(f"  [{name}] running...")
            run_one(script, ndir, args)
    print(f"\nTotal time: {time.time() - overall_t0:.0f}s")


if __name__ == "__main__":
    main()
