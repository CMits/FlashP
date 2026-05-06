#!/usr/bin/env python3
"""Run algebraic + ODE(--sensitivity) + RWR(--sensitivity) on KB merged network."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "Agent" / "shared"
NET = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20" / "KB_Cleaned" / "merged_arabidopsis_network"

VALIDATORS = [
    ("algebraic", SHARED / "flashp_validator.py", ["--csv", "--full-state"]),
    ("ode",       SHARED / "ode_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
    ("rwr",       SHARED / "rwr_validator.py",   ["--sensitivity", "--csv", "--full-state"]),
]


def main():
    for name, script, args in VALIDATORS:
        print(f"\n[{name}] running...", flush=True)
        t0 = time.time()
        cmd = [sys.executable, str(script), str(NET)] + args
        r = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace",
                           timeout=72000)
        dt = time.time() - t0
        print(f"[{name}] done in {dt:.0f}s, rc={r.returncode}", flush=True)


if __name__ == "__main__":
    main()
