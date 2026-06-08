"""
compact.py — normalize FLASH-P **Light** files to their slim on-disk form.

Reads any pipeline file (Light short-key, fat long-key, or TOON), runs it through the slim
Pydantic model (drops fat fields, abbreviates keys via aliases) and rewrites it slim — TOON for
the flat-eligible files (curated_edges, perturbation_dataset), JSON otherwise. Run this after an
agent writes a file to GUARANTEE the on-disk file is slim, regardless of what the agent emitted
(stray `evidence` arrays, long keys, etc. are normalized away).

Usage:
    python compact.py <file> [<file> ...]
    python compact.py --network <network_dir>     # compact all known files in a network dir
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import light_io  # noqa: E402

PIPELINE_FILES = [
    "data/curated_edges.json",
    "data/perturbation_dataset.json",
    "data/reconciled_perturbation_dataset.json",
    "network/network.json",
    "network/algebraic_equations.json",
    "network/ode_equations.json",
    "network/node_annotations.json",
]


def compact_file(path: str):
    """Load (expand) then re-dump slim. Returns the format written, or None if unknown kind."""
    kind = light_io.kind_of(path)
    if kind == "unknown":
        return None
    data = light_io.load(path)
    before = os.path.getsize(path)
    fmt = light_io.dump_slim(path, data, kind)
    after = os.path.getsize(path)
    return fmt, before, after


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "--network":
        nd = argv[1]
        targets = [os.path.join(nd, f) for f in PIPELINE_FILES
                   if os.path.exists(os.path.join(nd, f))]
    else:
        targets = argv
    for p in targets:
        try:
            res = compact_file(p)
            if res is None:
                print(f"  skip  {p} (unknown kind)")
            else:
                fmt, b, a = res
                print(f"  ok    {p} -> {fmt}  ({b} -> {a} bytes)")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {p}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
