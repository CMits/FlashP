"""
Apply a refinement iteration to the Ecoli_Lycopene_network.

Workflow per iteration:
  1. Read current network/equations/perturbations from the live files
     (network/, data/).
  2. Apply a list of structural + encoding fixes (encoded as a Python dict
     per fix).
  3. Regenerate the formula field for every node whose in-edges changed.
  4. Write the modified network + equations + perturbation dataset back to
     the live files.
  5. Also snapshot the modified files to refinement/iteration_N/.

The validator scripts are invoked separately; this only applies fixes.

Supported fix actions:
  - 'remove_edge':       {edge_id}
  - 'sign_change':       {edge_id, new_sign}
  - 'add_edge':          {edge_id, source, target, sign, effect, mechanism, evidence: [...]}
  - 'encoding_test':     {test_id, updates: {field: value, ...}}
                         Special: if 'network_gene' in updates, auto-sets
                         in_network=True and rebuilds gene_modifiers /
                         perturbations array per rules.

Usage:
    python apply_iteration.py <iter_N> <fix_package.json>

Or call apply_iteration(iter_num, fixes, root) from another script.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
NET_DIR = ROOT / "network"
DATA_DIR = ROOT / "data"
REFINE_DIR = ROOT / "refinement"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def rebuild_formula(node_dict, in_edges):
    """Given the equation entry for a node + all edges targeting it, rebuild
    the formula string using the FLASH-P default algebraic rules.
    Source nodes (is_source=true) use: Node = gene_modifier + exogenous_supply.
    """
    nid = node_dict["node"]
    if node_dict.get("is_source"):
        node_dict["activators"] = []
        node_dict["inhibitors"] = []
        node_dict["formula"] = f"{nid} = gene_modifier + exogenous_supply"
        return

    activators = [e["source"] for e in in_edges if e.get("sign", 1) == 1]
    inhibitors = [e["source"] for e in in_edges if e.get("sign", 1) == -1]
    node_dict["activators"] = activators
    node_dict["inhibitors"] = inhibitors

    # Activation term
    if activators:
        act_parts = [f"max({a}, 0.01)" for a in activators]
        n = len(activators)
        act_str = f"({' * '.join(act_parts)})^(1/{n})"
    else:
        act_str = "0.01"  # activator floor when no activators

    # Inhibition term
    if inhibitors:
        inh_product = " * ".join(inhibitors)
        inh_str = f"min(1/max({inh_product}, 0.1), 10.0)"
    else:
        inh_str = "1.0"

    formula = f"{nid} = {act_str} * {inh_str} * gene_modifier + exogenous_supply"
    node_dict["formula"] = formula


def apply_fixes(iter_num: int, fixes: List[Dict[str, Any]]):
    net = load(NET_DIR / "network.json")
    eqs = load(NET_DIR / "algebraic_equations.json")
    pert = load(DATA_DIR / "reconciled_perturbation_dataset.json")

    eq_by_node = {e["node"]: e for e in eqs["equations"]}
    affected_nodes = set()

    for fix in fixes:
        action = fix["action"]

        if action == "remove_edge":
            eid = fix["edge_id"]
            before = len(net["edges"])
            removed = [e for e in net["edges"] if e["edge_id"] == eid]
            net["edges"] = [e for e in net["edges"] if e["edge_id"] != eid]
            if len(net["edges"]) == before:
                raise RuntimeError(f"Edge {eid} not found")
            for e in removed:
                affected_nodes.add(e["target"])

        elif action == "sign_change":
            eid = fix["edge_id"]
            new_sign = fix["new_sign"]
            for e in net["edges"]:
                if e["edge_id"] == eid:
                    e["sign"] = new_sign
                    e["effect"] = "activation" if new_sign == 1 else "inhibition"
                    affected_nodes.add(e["target"])
                    break
            else:
                raise RuntimeError(f"Edge {eid} not found")

        elif action == "add_edge":
            e = {
                "edge_id": fix["edge_id"],
                "source": fix["source"],
                "target": fix["target"],
                "sign": fix["sign"],
                "effect": fix.get("effect",
                                  "activation" if fix["sign"] == 1 else "inhibition"),
                "mechanism": fix.get("mechanism", ""),
                "evidence": fix.get("evidence", []),
            }
            net["edges"].append(e)
            affected_nodes.add(fix["target"])

        elif action == "encoding_test":
            tid = fix["test_id"]
            updates = fix["updates"]
            for p in pert["perturbations"]:
                if p["test_id"] == tid:
                    for k, v in updates.items():
                        p[k] = v
                    # If encoding now includes network_gene list, auto-set in_network
                    if "network_gene" in updates and updates["network_gene"]:
                        p["in_network"] = True
                    break
            else:
                raise RuntimeError(f"Perturbation {tid} not found")

        else:
            raise ValueError(f"Unknown action: {action}")

    # Rebuild formulas for every affected node
    for node_id in affected_nodes:
        if node_id not in eq_by_node:
            continue
        in_edges = [e for e in net["edges"] if e["target"] == node_id]
        rebuild_formula(eq_by_node[node_id], in_edges)

    # Update network metadata
    net["metadata"]["total_edges"] = len(net["edges"])
    net["metadata"]["total_nodes"] = len(net["nodes"])
    net["metadata"]["refinement_iteration"] = iter_num

    # Write back to live files
    dump(NET_DIR / "network.json", net)
    dump(NET_DIR / "algebraic_equations.json", eqs)
    dump(DATA_DIR / "reconciled_perturbation_dataset.json", pert)

    # Snapshot to iteration directory
    iter_dir = REFINE_DIR / f"iteration_{iter_num}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    dump(iter_dir / "network_snapshot.json", net)
    dump(iter_dir / "equations_snapshot.json", eqs)
    dump(iter_dir / "perturbations_snapshot.json", pert)

    # Save the fixes applied
    fixes_file = {
        "iteration": iter_num,
        "date": "2026-04-21",
        "fixes": [dict(f, iteration=iter_num) for f in fixes],
    }
    dump(iter_dir / "fixes_applied.json", fixes_file)

    print(f"Iteration {iter_num}: applied {len(fixes)} fixes, "
          f"affected {len(affected_nodes)} node formulas.")
    print(f"Snapshot: {iter_dir}")
    return iter_dir


def revert_to_snapshot(iter_num: int):
    """Restore live network/equations/perturbations from an iteration
    snapshot (used for revert decisions)."""
    iter_dir = REFINE_DIR / f"iteration_{iter_num}"
    shutil.copy(iter_dir / "network_snapshot.json", NET_DIR / "network.json")
    shutil.copy(iter_dir / "equations_snapshot.json", NET_DIR / "algebraic_equations.json")
    shutil.copy(iter_dir / "perturbations_snapshot.json",
                DATA_DIR / "reconciled_perturbation_dataset.json")
    print(f"Reverted live files to iteration_{iter_num} snapshot.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python apply_iteration.py <iter_N> <fix_package.json>")
        sys.exit(1)
    iter_n = int(sys.argv[1])
    pkg = load(Path(sys.argv[2]))
    apply_fixes(iter_n, pkg["fixes"])
