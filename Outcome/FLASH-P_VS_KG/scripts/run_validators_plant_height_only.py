#!/usr/bin/env python3
"""Re-run validators on plant_height KB only, after the second-pass aliases."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "Agent" / "shared"
NET = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20" / "KB_Cleaned" / "plant_height_network"

VALIDATORS = [
    ("algebraic", SHARED / "flashp_validator.py", ["--csv", "--full-state"]),
    ("ode",       SHARED / "ode_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
    ("rwr",       SHARED / "rwr_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
]


def main():
    for name, script, args in VALIDATORS:
        print(f"[{name}] running...", flush=True)
        t0 = time.time()
        cmd = [sys.executable, str(script), str(NET)] + args
        r = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace",
                           timeout=7200)
        print(f"[{name}] done in {time.time()-t0:.0f}s, rc={r.returncode}", flush=True)


if __name__ == "__main__":
    main()
