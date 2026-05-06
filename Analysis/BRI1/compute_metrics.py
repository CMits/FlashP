"""Collect FLASH-P v2.0 vs KG-Cleaned comparison metrics for the
'Causal network inference outperforms knowledge-graph extraction' section.

Reads existing validation outputs + network JSONs and emits:
  della_subgraph_new/comparison_metrics.json   (structured, consumed by write_section_docx.py)
  della_subgraph_new/comparison_metrics.csv    (flat, for supplementary / sanity check)

No network rebuilds, no re-validation. Read-only aggregation.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PHENOTYPES = [
    "Flowering_Time",
    "Hypocotyl_Length",
    "Lateral_Root_Density",
    "Plant_Height",
    "Seed_Size",
    "Shoot_Branching",
]

FLASHP_INDIVIDUAL_DIR = "Arabidopsis"
KG_INDIVIDUAL_DIR = "Knowledge_Base_Comparison_rerun_2026-04-20/KB_Cleaned"
FLASHP_MERGED_DIR = "merged_arabidopsis_network"
KG_MERGED_DIR = f"{KG_INDIVIDUAL_DIR}/merged_arabidopsis_network"


def load_json(relpath: str) -> dict | None:
    path = os.path.join(ROOT, relpath)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def structural_stats(network_json: dict, phenotype_ids: set[str]) -> dict:
    nodes = network_json["nodes"]
    edges = network_json["edges"]
    n_nodes = len(nodes)
    n_edges = len(edges)
    direct_to_pheno = sum(1 for e in edges if e["target"] in phenotype_ids)
    return {
        "nodes": n_nodes,
        "edges": n_edges,
        "direct_to_phenotype_edges": direct_to_pheno,
        "direct_to_phenotype_pct": round(100 * direct_to_pheno / n_edges, 1) if n_edges else 0.0,
    }


def reachable_phenotypes(network_json: dict, seed: str, phenotype_ids: set[str], max_hops: int = 4) -> dict:
    """BFS from seed (stopping at phenotypes) to report which phenotypes are reachable and their shortest-path hop count."""
    fwd: dict[str, list[str]] = {}
    for e in network_json["edges"]:
        fwd.setdefault(e["source"], []).append(e["target"])
    if seed not in {n["id"] for n in network_json["nodes"]}:
        return {"reachable": [], "hops": {}, "reachable_count": 0}
    dist = {seed: 0}
    q = deque([seed])
    while q:
        u = q.popleft()
        if dist[u] >= max_hops:
            continue
        for v in fwd.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                if v not in phenotype_ids:
                    q.append(v)
    hops = {p: dist[p] for p in phenotype_ids if p in dist}
    return {
        "reachable": sorted(hops.keys()),
        "hops": hops,
        "reachable_count": len(hops),
    }


def _norm_pct(acc, correct, total):
    """Normalise accuracy to 0-100. Individual FLASH-P files are inconsistent:
    some store 0-1 fractions (Hypocotyl, LateralRoot, PlantHeight) and others store 0-100 (FloweringTime, SeedSize, ShootBranching).
    If correct/total is available and acc looks like a fraction, trust correct/total."""
    if acc is None:
        if correct is not None and total:
            return round(100 * correct / total, 1)
        return None
    if acc <= 1.5:  # treat as fraction
        return round(acc * 100, 1)
    return round(acc, 1)


def extract_accuracy_individual_flashp(phenotype_cap: str) -> dict:
    """FLASH-P individual accuracy_metrics.json — 5 phenotypes use top-level algebraic/ode/rwr, Shoot_Branching uses methods.*"""
    d = load_json(f"{FLASHP_INDIVIDUAL_DIR}/{phenotype_cap}_network/validation/accuracy_metrics.json")
    if d is None:
        return {}
    if "methods" in d:
        blocks = d["methods"]
    else:
        blocks = {k: d[k] for k in ("algebraic", "ode", "rwr") if k in d}
    out = {}
    for m, b in blocks.items():
        acc = b.get("accuracy") if "accuracy" in b else b.get("overall_accuracy")
        correct = b.get("correct")
        total = b.get("total") or b.get("total_tested")
        out[m] = {
            "accuracy": _norm_pct(acc, correct, total),
            "correct": correct,
            "total": total,
            "kappa": b.get("kappa") or b.get("cohens_kappa"),
        }
    return out


def extract_accuracy_from_validation_results(relpath: str) -> dict:
    d = load_json(relpath)
    if d is None:
        return {}
    metrics = d.get("metrics", {})
    summary = d.get("summary", {})
    return {
        "accuracy": metrics.get("overall_accuracy"),
        "correct": metrics.get("correct"),
        "total": metrics.get("total") or summary.get("tested"),
        "kappa": metrics.get("cohens_kappa"),
    }


def merged_accuracies(merged_dir: str) -> dict:
    methods = {
        "algebraic": f"{merged_dir}/validation/script_validation_results.json",
        "ode": f"{merged_dir}/validation/ode_validation_results.json",
        "rwr": f"{merged_dir}/validation/rwr_validation_results.json",
    }
    pleio = {
        "algebraic": f"{merged_dir}/validation/pleiotropic_algebraic_results.json",
        "ode": f"{merged_dir}/validation/pleiotropic_ode_results.json",
        "rwr": f"{merged_dir}/validation/pleiotropic_rwr_results.json",
    }
    return {
        "single_trait": {m: extract_accuracy_from_validation_results(p) for m, p in methods.items()},
        "pleiotropic": {m: extract_accuracy_from_validation_results(p) for m, p in pleio.items()},
    }


def kg_individual_accuracy(phenotype_lower: str) -> dict:
    paths = {
        "algebraic": f"{KG_INDIVIDUAL_DIR}/{phenotype_lower}_network/validation/script_validation_results.json",
        "ode": f"{KG_INDIVIDUAL_DIR}/{phenotype_lower}_network/validation/ode_validation_results.json",
        "rwr": f"{KG_INDIVIDUAL_DIR}/{phenotype_lower}_network/validation/rwr_validation_results.json",
    }
    return {m: extract_accuracy_from_validation_results(p) for m, p in paths.items()}


def best_method_accuracies(per_net: dict) -> list[float]:
    """Given {phenotype: {method: {accuracy: x}}}, return list of max-accuracy-per-phenotype (drops Nones)."""
    out = []
    for pheno, methods in per_net.items():
        vals = [m.get("accuracy") for m in methods.values() if m.get("accuracy") is not None]
        if vals:
            out.append(max(vals))
    return out


def main() -> int:
    flashp_merged = load_json(f"{FLASHP_MERGED_DIR}/network/network.json")
    kg_merged = load_json(f"{KG_MERGED_DIR}/network/network.json")
    if flashp_merged is None or kg_merged is None:
        print("ERROR: merged network JSON missing.", file=sys.stderr)
        return 1

    phenotype_ids = {p for p in PHENOTYPES}

    flashp_struct = structural_stats(flashp_merged, phenotype_ids)
    kg_struct = structural_stats(kg_merged, phenotype_ids)

    flashp_della = reachable_phenotypes(flashp_merged, "DELLA", phenotype_ids, max_hops=4)
    kg_della = reachable_phenotypes(kg_merged, "DELLA", phenotype_ids, max_hops=4)

    flashp_individual = {p: extract_accuracy_individual_flashp(p) for p in PHENOTYPES}
    kg_individual = {p: kg_individual_accuracy(p.lower()) for p in PHENOTYPES}

    flashp_individual_struct = {}
    kg_individual_struct = {}
    for p in PHENOTYPES:
        flashp_net = load_json(f"{FLASHP_INDIVIDUAL_DIR}/{p}_network/network/network.json")
        if flashp_net:
            flashp_individual_struct[p] = structural_stats(flashp_net, {p})
        kg_net = load_json(f"{KG_INDIVIDUAL_DIR}/{p.lower()}_network/network/network.json")
        if kg_net:
            kg_individual_struct[p] = structural_stats(kg_net, {p})

    flashp_merged_acc = merged_accuracies(FLASHP_MERGED_DIR)
    kg_merged_acc = merged_accuracies(KG_MERGED_DIR)

    flashp_best = best_method_accuracies(flashp_individual)
    kg_best = best_method_accuracies(kg_individual)

    flashp_direct_pcts = [s["direct_to_phenotype_pct"] for s in flashp_individual_struct.values()]
    kg_direct_pcts = [s["direct_to_phenotype_pct"] for s in kg_individual_struct.values()]

    out = {
        "generated": "2026-04-20",
        "flashp_merged": {
            "structure": flashp_struct,
            "della_reachability": flashp_della,
            "accuracy": flashp_merged_acc,
        },
        "kg_merged": {
            "structure": kg_struct,
            "della_reachability": kg_della,
            "accuracy": kg_merged_acc,
        },
        "flashp_individual": {
            "per_phenotype_accuracy": flashp_individual,
            "per_phenotype_structure": flashp_individual_struct,
            "best_method_accuracy_min": round(min(flashp_best), 1) if flashp_best else None,
            "best_method_accuracy_max": round(max(flashp_best), 1) if flashp_best else None,
            "direct_to_phenotype_pct_min": min(flashp_direct_pcts) if flashp_direct_pcts else None,
            "direct_to_phenotype_pct_max": max(flashp_direct_pcts) if flashp_direct_pcts else None,
            "direct_to_phenotype_pct_mean": round(sum(flashp_direct_pcts) / len(flashp_direct_pcts), 1) if flashp_direct_pcts else None,
        },
        "kg_individual": {
            "per_phenotype_accuracy": kg_individual,
            "per_phenotype_structure": kg_individual_struct,
            "best_method_accuracy_min": round(min(kg_best), 1) if kg_best else None,
            "best_method_accuracy_max": round(max(kg_best), 1) if kg_best else None,
            "direct_to_phenotype_pct_min": min(kg_direct_pcts) if kg_direct_pcts else None,
            "direct_to_phenotype_pct_max": max(kg_direct_pcts) if kg_direct_pcts else None,
            "direct_to_phenotype_pct_mean": round(sum(kg_direct_pcts) / len(kg_direct_pcts), 1) if kg_direct_pcts else None,
        },
    }

    json_path = os.path.join(OUT_DIR, "comparison_metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    csv_path = os.path.join(OUT_DIR, "comparison_metrics.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["network", "phenotype", "method", "accuracy", "correct", "total", "kappa", "nodes", "edges", "direct_to_pheno_pct"])
        for p, methods in flashp_individual.items():
            s = flashp_individual_struct.get(p, {})
            for m, r in methods.items():
                w.writerow(["FLASH-P", p, m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                            s.get("nodes"), s.get("edges"), s.get("direct_to_phenotype_pct")])
        for p, methods in kg_individual.items():
            s = kg_individual_struct.get(p, {})
            for m, r in methods.items():
                w.writerow(["KG-Cleaned", p, m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                            s.get("nodes"), s.get("edges"), s.get("direct_to_phenotype_pct")])
        for m, r in flashp_merged_acc["single_trait"].items():
            w.writerow(["FLASH-P", "merged_single_trait", m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                        flashp_struct["nodes"], flashp_struct["edges"], flashp_struct["direct_to_phenotype_pct"]])
        for m, r in flashp_merged_acc["pleiotropic"].items():
            w.writerow(["FLASH-P", "merged_pleiotropic", m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                        flashp_struct["nodes"], flashp_struct["edges"], flashp_struct["direct_to_phenotype_pct"]])
        for m, r in kg_merged_acc["single_trait"].items():
            w.writerow(["KG-Cleaned", "merged_single_trait", m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                        kg_struct["nodes"], kg_struct["edges"], kg_struct["direct_to_phenotype_pct"]])
        for m, r in kg_merged_acc["pleiotropic"].items():
            w.writerow(["KG-Cleaned", "merged_pleiotropic", m, r.get("accuracy"), r.get("correct"), r.get("total"), r.get("kappa"),
                        kg_struct["nodes"], kg_struct["edges"], kg_struct["direct_to_phenotype_pct"]])

    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")
    print()
    print(f"FLASH-P merged: {flashp_struct['nodes']} nodes / {flashp_struct['edges']} edges / {flashp_struct['direct_to_phenotype_pct']}% direct-to-phenotype")
    print(f"KG-Cleaned merged: {kg_struct['nodes']} nodes / {kg_struct['edges']} edges / {kg_struct['direct_to_phenotype_pct']}% direct-to-phenotype")
    print(f"FLASH-P individual best-method range: {out['flashp_individual']['best_method_accuracy_min']}–{out['flashp_individual']['best_method_accuracy_max']}%")
    print(f"KG-Cleaned individual best-method range: {out['kg_individual']['best_method_accuracy_min']}–{out['kg_individual']['best_method_accuracy_max']}%")
    print(f"FLASH-P individual direct-to-pheno %: {out['flashp_individual']['direct_to_phenotype_pct_min']}–{out['flashp_individual']['direct_to_phenotype_pct_max']}% (mean {out['flashp_individual']['direct_to_phenotype_pct_mean']}%)")
    print(f"KG-Cleaned individual direct-to-pheno %: {out['kg_individual']['direct_to_phenotype_pct_min']}–{out['kg_individual']['direct_to_phenotype_pct_max']}% (mean {out['kg_individual']['direct_to_phenotype_pct_mean']}%)")
    print(f"DELLA reachable phenotypes: FLASH-P={flashp_della['reachable_count']}/6, KG={kg_della['reachable_count']}/6")
    for m in ("algebraic", "ode", "rwr"):
        print(f"  merged single-trait {m}: FLASH-P={flashp_merged_acc['single_trait'][m]['accuracy']}% vs KG={kg_merged_acc['single_trait'][m]['accuracy']}%")
    for m in ("algebraic", "ode", "rwr"):
        print(f"  merged pleiotropic {m}: FLASH-P={flashp_merged_acc['pleiotropic'][m]['accuracy']}% vs KG={kg_merged_acc['pleiotropic'][m]['accuracy']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
