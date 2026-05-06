#!/usr/bin/env python3
"""
Collect the set of gene / exogenous-supply node names from FLASH-P tests that
did NOT exact/case-insensitively match any KB node, per trait. Writes one JSON
per trait under results/unmapped/<trait>.json with shape:

{
  "trait": "shoot_branching",
  "phenotype_node": "Shoot_Branching",
  "kb_nodes": [...],                # full sorted list of KB node IDs
  "unmapped_terms": [
    {"term": "CCD7", "test_ids": ["T010","T011"], "kind": "gene_modifier"},
    ...
  ]
}

Used as input to the per-trait reconciliation agents.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP = ROOT / "Arabidopsis"
MERGED_FP = ROOT / "merged_arabidopsis_network"
RERUN = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20"
KB = RERUN / "KB_Cleaned"
OUT = RERUN / "results" / "unmapped"

TRAITS = {
    "shoot_branching":      ("Shoot_Branching_network",      "Shoot_Branching"),
    "flowering_time":       ("Flowering_Time_network",       "Flowering_Time"),
    "hypocotyl_length":     ("Hypocotyl_Length_network",     "Hypocotyl_Length"),
    "plant_height":         ("Plant_Height_network",         "Plant_Height"),
    "lateral_root_density": ("Lateral_Root_Density_network", "Lateral_Root_Density"),
    "seed_size":            ("Seed_Size_network",            "Seed_Size"),
}


def load_json(p):
    return json.load(open(p, "r", encoding="utf-8"))


def collect(src_reconciled: Path, kb_dir: Path, phenotype_node: str,
            trait: str):
    kb = load_json(kb_dir / "network" / "network.json")
    kb_nodes = sorted({n["id"] for n in kb.get("nodes", [])})
    kb_exact = set(kb_nodes)
    kb_ci = {n.lower(): n for n in kb_exact}

    tests = load_json(src_reconciled).get("perturbations", [])
    buckets = {}  # term -> {"kind": str, "test_ids": [..]}
    for t in tests:
        for kind, d in (("gene_modifier", t.get("gene_modifiers") or {}),
                        ("exogenous_supply", t.get("exogenous_supply") or {})):
            for term in d.keys():
                if term in kb_exact:
                    continue
                if term.lower() in kb_ci:
                    continue
                rec = buckets.setdefault(term, {"kind": kind, "test_ids": []})
                rec["test_ids"].append(t.get("test_id", ""))
    unmapped = [
        {"term": k, "kind": v["kind"], "test_ids": sorted(set(v["test_ids"]))}
        for k, v in sorted(buckets.items())
    ]
    return {
        "trait": trait,
        "phenotype_node": phenotype_node,
        "n_kb_nodes": len(kb_nodes),
        "kb_nodes": kb_nodes,
        "n_tests_total": len(tests),
        "n_unmapped_terms": len(unmapped),
        "unmapped_terms": unmapped,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for trait, (fp_dir, ph) in TRAITS.items():
        src = FP / fp_dir / "data" / "reconciled_perturbation_dataset.json"
        kb_dir = KB / f"{trait}_network"
        d = collect(src, kb_dir, ph, trait)
        (OUT / f"{trait}.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
        print(f"{trait:<22}  kb_nodes={d['n_kb_nodes']:>5}  tests={d['n_tests_total']:>4}  unmapped_terms={d['n_unmapped_terms']:>4}")

    # merged
    src = MERGED_FP / "data" / "reconciled_perturbation_dataset.json"
    kb_dir = KB / "merged_arabidopsis_network"
    d = collect(src, kb_dir, "", "merged")
    (OUT / "merged.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"{'merged':<22}  kb_nodes={d['n_kb_nodes']:>5}  tests={d['n_tests_total']:>4}  unmapped_terms={d['n_unmapped_terms']:>4}")


if __name__ == "__main__":
    main()
