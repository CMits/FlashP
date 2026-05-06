"""
Build a master test-level CSV for the pleiotropic test suite on the merged
Arabidopsis network, mirroring the column layout of
`supplementary/master_test_level.csv` so the two files can be concatenated or
compared column-for-column.

Input:
  data/pleiotropic_perturbation_dataset.json      (15 pleiotropic tests)
  validation/pleiotropic_algebraic_results.json   (35 test x phenotype rows)
  validation/pleiotropic_ode_results.json
  validation/pleiotropic_rwr_results.json

Output:
  supplementary/master_test_level_pleio.csv       (35 * 3 = 105 rows)

Paper-scoped artifact. Re-run after any re-validation of the pleiotropic suite.

Usage:
    python merged_arabidopsis_network/scripts/export_master_pleio.py
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from pathlib import Path

NETWORK_LABEL = "Merged Arabidopsis"
DEFAULT_SPECIES = "Arabidopsis thaliana"

METHODS = [
    ("pleiotropic_algebraic_results.json", "Algebraic"),
    ("pleiotropic_ode_results.json", "ODE"),
    ("pleiotropic_rwr_results.json", "RWR"),
]

FIELDNAMES = [
    # Identity
    "network", "species", "method",
    "test_id", "gene", "perturbation_type",
    # Reconciliation / metadata
    "in_network", "network_gene", "reconciliation_type",
    "gene_modifiers", "n_gene_mods",
    "exogenous_supply", "n_exogenous",
    "comparison_baseline",
    "expected_magnitude", "notes",
    # Classification
    "modelled_as", "complexity_score", "complexity_label",
    # Biological expectation
    "expected_direction",
    # Simulation results
    "wt_value", "perturbed_value", "comparison_baseline_value",
    "ratio", "log2_fold_change",
    "direction_threshold",
    # Prediction
    "predicted_direction", "correct",
    # Convergence
    "converged", "iterations",
    # Graph topology
    "path_length", "path",
    "phenotype_node",
    # Evidence
    "evidence_doi",
]


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def classify_perturbation(n_gm: int, n_exo: int) -> str:
    if n_gm == 0 and n_exo == 0:
        return "control"
    if n_gm == 0:
        return "treatment_only"
    if n_gm == 1 and n_exo == 0:
        return "single_mutation"
    if n_gm == 1:
        return "mutation_plus_treatment"
    if n_gm == 2 and n_exo == 0:
        return "double_mutation"
    if n_gm == 2:
        return "double_mutation_plus_treatment"
    if n_exo == 0:
        return f"multi_mutation_{n_gm}"
    return f"multi_mutation_{n_gm}_plus_treatment"


def load_pleiotropic_metadata(path: Path) -> dict:
    """Index pleiotropic tests by their base test_id (e.g. 'PLEIO_001')."""
    d = load_json(path)
    mapping = {}
    for t in d.get("pleiotropic_tests", []):
        tid = t.get("test_id", "")
        gm = t.get("gene_modifiers") or {}
        exo = t.get("exogenous_supply") or {}
        mod_nodes = [n for n, m in gm.items() if m != 1.0]
        evidence = t.get("evidence") or []
        first_ev = evidence[0] if evidence else {}
        mapping[tid] = {
            "gene_modifiers": gm,
            "mod_nodes": mod_nodes,
            "n_gene_mods": len(mod_nodes),
            "exogenous_supply": exo,
            "n_exogenous": len(exo),
            "description": t.get("description", ""),
            "evidence_title": first_ev.get("title", ""),
            "evidence_claim": first_ev.get("claim", ""),
        }
    return mapping


def base_test_id(test_id: str) -> str:
    """'PLEIO_001__Plant_Height' -> 'PLEIO_001'."""
    return test_id.split("__", 1)[0] if "__" in test_id else test_id


def build_edges_and_nodes(algebraic_eq_path: Path):
    """Replicate flashp_validator's extract_edges_from_equations.

    Returns (adjacency_dict, set_of_nodes). Edges are (activator, node) and
    (inhibitor, node), matching how `measure_path_length` BFS walks the
    simulation graph.
    """
    eq = json.loads(algebraic_eq_path.read_text(encoding="utf-8"))
    adj: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for e in eq.get("equations", []):
        tgt = e["node"]
        nodes.add(tgt)
        for src in list(e.get("activators") or []) + list(e.get("inhibitors") or []):
            nodes.add(src)
            adj.setdefault(src, []).append(tgt)
    return adj, nodes


def bfs_path(adj: dict, starts: list[str], goal: str) -> tuple[int, list[str]]:
    """Shortest path from any `starts` node to `goal`. Returns (-1, []) if none."""
    best_len, best_path = -1, []
    for start in starts:
        if start == goal:
            return 0, [start]
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            node, path = queue.popleft()
            for nb in adj.get(node, []):
                if nb == goal:
                    found = path + [nb]
                    flen = len(found) - 1
                    if best_len == -1 or flen < best_len:
                        best_len, best_path = flen, found
                    break
                if nb not in visited:
                    visited.add(nb)
                    queue.append((nb, path + [nb]))
    return best_len, best_path


def row_for_result(
    r: dict,
    method: str,
    meta: dict,
    species: str,
    adj: dict | None = None,
    network_nodes: set | None = None,
) -> dict:
    tid = r.get("test_id", "")
    m = meta.get(base_test_id(tid), {})

    gm = m.get("gene_modifiers") or {}
    exo = m.get("exogenous_supply") or {}
    mod_nodes = m.get("mod_nodes") or []
    n_gm = m.get("n_gene_mods", 0)
    n_exo = m.get("n_exogenous", 0)

    # Fallback to per-result fields if metadata lookup failed
    if not m:
        gene = r.get("gene", "")
        gm_val = r.get("gene_modifier")
        if gene and gm_val is not None and gm_val != 1.0:
            gm = {gene: gm_val}
            mod_nodes = [gene]
            n_gm = 1
        exo_node = r.get("exogenous_node")
        if exo_node:
            exo = {exo_node: r.get("exogenous_value") or 1.0}
            n_exo = 1

    modelled_as = classify_perturbation(n_gm, n_exo)
    complexity_score = r.get("complexity_score", max(n_gm + n_exo, 1))
    complexity_label = r.get("complexity_label") or (
        "easy" if complexity_score <= 1 else ("medium" if complexity_score == 2 else "hard")
    )

    gm_str = "; ".join(f"{k}={v}" for k, v in gm.items()) if gm else ""
    exo_str = "; ".join(f"{k}={v}" for k, v in exo.items()) if exo else ""

    path_list = r.get("path") or []
    path_length = r.get("path_length")

    # The upstream validators sometimes emit path_length=None / path=[] even
    # when a directed path exists in the algebraic graph (observed: HY5, EIN2,
    # AHK perturbations across several phenotypes). Re-run the same BFS the
    # validator uses, sourced from algebraic_equations.json.
    if adj is not None and network_nodes is not None and (not path_list or path_length in (None, "")):
        starts = [n for n in mod_nodes if n in network_nodes]
        if not starts and r.get("gene") in network_nodes:
            starts = [r["gene"]]
        goal = r.get("phenotype_node", "")
        if starts and goal:
            plen, ppath = bfs_path(adj, starts, goal)
            path_length = plen
            path_list = ppath

    # Disconnected = no directed path from perturbed node to phenotype.
    # Leave path_length blank (rather than -1) and annotate the path column so
    # downstream plots can filter on blank path_length cleanly.
    if path_length in (None, "", -1):
        path_length = ""
        path_str = "not connected to phenotype"
    else:
        path_str = " > ".join(path_list) if path_list else ""

    return {
        "network": NETWORK_LABEL,
        "species": species,
        "method": method,
        "test_id": tid,
        "gene": r.get("gene", ""),
        "perturbation_type": r.get("perturbation_type", ""),
        "in_network": True,
        "network_gene": ",".join(mod_nodes) if mod_nodes else r.get("gene", ""),
        "reconciliation_type": "pleiotropic",
        "gene_modifiers": gm_str,
        "n_gene_mods": n_gm,
        "exogenous_supply": exo_str,
        "n_exogenous": n_exo,
        "comparison_baseline": r.get("comparison_baseline", "WT"),
        "expected_magnitude": "",
        "notes": m.get("description", ""),
        "modelled_as": modelled_as,
        "complexity_score": complexity_score,
        "complexity_label": complexity_label,
        "expected_direction": r.get("expected_direction", ""),
        "wt_value": r.get("wt_value", ""),
        "perturbed_value": r.get("perturbed_value", ""),
        "comparison_baseline_value": r.get("comparison_baseline_value", ""),
        "ratio": r.get("ratio", ""),
        "log2_fold_change": r.get("log2_fold_change", ""),
        "direction_threshold": r.get("direction_threshold", ""),
        "predicted_direction": r.get("predicted_direction", ""),
        "correct": 1 if r.get("correct") else 0,
        "converged": 1 if r.get("converged") else 0,
        "iterations": r.get("iterations", ""),
        "path_length": path_length,
        "path": path_str,
        "phenotype_node": r.get("phenotype_node", ""),
        "evidence_doi": r.get("evidence_doi", ""),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_dir",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent),
        help="merged_arabidopsis_network directory (default: parent of this script)",
    )
    parser.add_argument("--output", default=None,
                        help="Output CSV path (default: <base>/supplementary/master_test_level_pleio.csv)")
    args = parser.parse_args()

    base = Path(args.base_dir)
    out_path = Path(args.output) if args.output else base / "supplementary" / "master_test_level_pleio.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Species from merged network metadata, fall back to default
    net_meta_path = base / "network" / "network.json"
    species = DEFAULT_SPECIES
    if net_meta_path.exists():
        species = load_json(net_meta_path).get("metadata", {}).get("species", DEFAULT_SPECIES)

    meta = load_pleiotropic_metadata(base / "data" / "pleiotropic_perturbation_dataset.json")
    adj, network_nodes = build_edges_and_nodes(base / "network" / "algebraic_equations.json")

    rows = []
    for fname, method_label in METHODS:
        results = load_json(base / "validation" / fname)
        for r in results.get("detailed_results", []):
            rows.append(row_for_result(r, method_label, meta, species, adj, network_nodes))

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    correct = sum(r["correct"] for r in rows)
    print(f"Wrote {out_path}")
    print(f"  rows: {total}")
    print(f"  correct: {correct}/{total} ({round(correct / total * 100, 1)}%)" if total else "  (no rows)")

    from collections import defaultdict
    acc = defaultdict(lambda: {"c": 0, "t": 0})
    for r in rows:
        acc[r["method"]]["t"] += 1
        acc[r["method"]]["c"] += r["correct"]
    print("  per-method:")
    for m, g in sorted(acc.items()):
        a = round(g["c"] / g["t"] * 100, 1) if g["t"] else 0
        print(f"    {m:10s}: {g['c']:3d}/{g['t']:3d} = {a}%")


if __name__ == "__main__":
    main()
