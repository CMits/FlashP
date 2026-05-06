#!/usr/bin/env python3
"""
Build Table_S8b_per_phenotype_in_merged.csv from master_test_level.csv.

Groups per (method, phenotype_node) and computes accuracy + Cohen's kappa.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path


def cohens_kappa(rows):
    """rows = iterable of (expected, predicted). Returns (accuracy, kappa, n)."""
    from collections import Counter
    obs = [(e, p) for e, p in rows if e and p]
    n = len(obs)
    if n == 0:
        return 0.0, 0.0, 0
    correct = sum(1 for e, p in obs if e == p)
    acc = correct / n
    labels = sorted({e for e, _ in obs} | {p for _, p in obs})
    exp_c = Counter(e for e, _ in obs)
    pred_c = Counter(p for _, p in obs)
    pe = sum((exp_c[l] * pred_c[l]) / (n * n) for l in labels)
    if pe >= 1.0:
        return acc, 0.0, n
    kappa = (acc - pe) / (1 - pe)
    return acc, kappa, n


def main(merged_supp_dir: Path):
    master = merged_supp_dir / "master_test_level.csv"
    if not master.exists():
        print(f"missing {master}")
        sys.exit(1)

    buckets = defaultdict(list)  # (method, phenotype_node) -> [(exp, pred)]
    with open(master, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("in_network", "").lower() not in ("true", "1", "yes"):
                continue
            m = row.get("method", "")
            ph = row.get("phenotype_node", "")
            e = row.get("expected_direction", "")
            p = row.get("predicted_direction", "")
            if m and ph and e and p:
                buckets[(m, ph)].append((e, p))

    out = merged_supp_dir / "Table_S8b_per_phenotype_in_merged.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method", "phenotype_node", "n", "correct",
                    "accuracy_pct", "cohens_kappa"])
        for (method, ph), rows in sorted(buckets.items()):
            acc, kappa, n = cohens_kappa(rows)
            correct = sum(1 for e, p in rows if e == p)
            w.writerow([method, ph, n, correct, round(acc * 100, 1),
                        round(kappa, 4)])
    print(f"wrote {out}")


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).resolve().parents[1] / "KB_Cleaned" / "merged_arabidopsis_network" / "supplementary"
    main(d)
