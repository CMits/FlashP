#!/usr/bin/env python3
"""
FLASH-P v1.0 → v1.0 Migration Script

Normalises all JSON files in existing networks to v1.0 schema format.
Creates backups before modifying.

Usage:
    python migrate_v1_to_v2.py <network_dir>           # Migrate one network
    python migrate_v1_to_v2.py --all <base_dir>        # Migrate all networks
    python migrate_v1_to_v2.py --dry-run <network_dir> # Show changes without writing
"""

import json
import shutil
import sys
from pathlib import Path


def backup_file(path):
    """Create .v1_backup before modifying."""
    backup = path.with_suffix(path.suffix + ".v1_backup")
    if not backup.exists():
        shutil.copy2(path, backup)
        return True
    return False


def fix_reconciled_perturbation(data, dry_run=False):
    """Normalise reconciled_perturbation_dataset.json to v1.0."""
    changes = []

    # Fix metadata field names
    meta = data.get("metadata", {})
    for old_key, new_key in [
        ("in_network_tests", "in_network"),
        ("not_in_network_tests", "not_in_network"),
        ("reconciled_in_network", "in_network"),
        ("reconciled_not_in_network", "not_in_network"),
    ]:
        if old_key in meta and new_key not in meta:
            meta[new_key] = meta.pop(old_key)
            changes.append(f"metadata: renamed {old_key} -> {new_key}")

    # Ensure metadata has required fields
    if "total_tests" not in meta:
        meta["total_tests"] = len(data.get("perturbations", []))
        changes.append("metadata: added total_tests")
    if "in_network" not in meta:
        perts = data.get("perturbations", [])
        meta["in_network"] = sum(1 for p in perts if p.get("in_network", True))
        meta["not_in_network"] = len(perts) - meta["in_network"]
        changes.append("metadata: added in_network/not_in_network counts")

    # Fix version
    meta["flash_p_version"] = "1.0"

    # Renumber test_ids to sequential format
    perts = data.get("perturbations", [])
    for i, p in enumerate(perts):
        old_id = p.get("test_id", "")
        new_id = f"T{i+1:03d}"
        # Only renumber if not already sequential
        if old_id and not old_id.startswith("T") or (old_id.startswith("T") and not old_id[1:].isdigit()):
            p["_original_test_id"] = old_id
            p["test_id"] = new_id
            changes.append(f"test_id: {old_id} -> {new_id}")

    for p in perts:
        # Fix network_gene: always a list
        ng = p.get("network_gene")
        if ng is None:
            p["network_gene"] = []
            changes.append(f"{p['test_id']}: network_gene None -> []")
        elif isinstance(ng, str):
            p["network_gene"] = [ng]
            changes.append(f"{p['test_id']}: network_gene str -> list")

        # Fix gene_modifiers: always a dict
        gm_dict = p.get("gene_modifiers")
        gm_scalar = p.get("gene_modifier")
        if gm_dict is None and gm_scalar is not None:
            # Scalar format -> dict format
            net_genes = p.get("network_gene", [])
            if isinstance(net_genes, str):
                net_genes = [net_genes]
            if net_genes and gm_scalar != 1.0:
                # For single-gene, use first network_gene
                p["gene_modifiers"] = {net_genes[0]: gm_scalar}
            else:
                p["gene_modifiers"] = {}
            changes.append(f"{p['test_id']}: gene_modifier scalar -> gene_modifiers dict")
        elif gm_dict is None:
            p["gene_modifiers"] = {}
            changes.append(f"{p['test_id']}: gene_modifiers None -> {{}}")

        # Remove scalar gene_modifier field (v1.0 artifact)
        if "gene_modifier" in p:
            del p["gene_modifier"]

        # Fix exogenous_supply: always flat dict, never None, never nested
        exo = p.get("exogenous_supply")
        if exo is None:
            p["exogenous_supply"] = {}
            changes.append(f"{p['test_id']}: exogenous_supply None -> {{}}")
        elif isinstance(exo, dict) and "node" in exo:
            # Nested format {node: X, value: Y} -> flat {X: Y}
            node = exo["node"]
            val = exo.get("value", exo.get("amount", 1.0))
            p["exogenous_supply"] = {node: val}
            changes.append(f"{p['test_id']}: exogenous_supply nested -> flat")

        # Ensure phenotype_node exists
        if "phenotype_node" not in p or not p["phenotype_node"]:
            # Try to get from metadata
            pheno = meta.get("phenotype_node", meta.get("phenotype", ""))
            if pheno:
                # Convert to Title_Case
                p["phenotype_node"] = pheno.replace(" ", "_").title().replace("_", "_")
                changes.append(f"{p['test_id']}: added phenotype_node={p['phenotype_node']}")

        # Ensure perturbations list exists
        if "perturbations" not in p:
            mods = []
            gm = p.get("gene_modifiers", {})
            for node, val in gm.items():
                mods.append({"node": node, "modifier_type": "gene_modifier", "value": val})
            es = p.get("exogenous_supply", {})
            for node, val in es.items():
                mods.append({"node": node, "modifier_type": "exogenous_supply", "value": val})
            p["perturbations"] = mods
            if mods:
                changes.append(f"{p['test_id']}: generated perturbations list")

        # Fix evidence: flatten nested source objects
        for ev in p.get("evidence", []):
            if "source" in ev and isinstance(ev["source"], dict):
                src = ev.pop("source")
                for k, v in src.items():
                    if k not in ev:
                        ev[k] = v
                changes.append(f"{p['test_id']}: flattened evidence source")

        # Ensure comparison_baseline
        if "comparison_baseline" not in p:
            p["comparison_baseline"] = "WT"

        # Ensure condition
        if "condition" not in p:
            p["condition"] = "both"

        # Remove v1.0 artifact fields
        for old_field in ["adjusted_modifier", "gene_modifier_applied",
                          "compare_to", "phenotype_measured", "coverage_pct"]:
            if old_field in p:
                del p[old_field]

    return data, changes


def fix_network_json(data):
    """Normalise network.json to v1.0."""
    changes = []
    meta = data.get("metadata", {})
    meta["flash_p_version"] = "1.0"

    # Ensure total_nodes and total_edges
    if "total_nodes" not in meta:
        meta["total_nodes"] = len(data.get("nodes", []))
        changes.append("metadata: added total_nodes")
    if "total_edges" not in meta:
        meta["total_edges"] = len(data.get("edges", []))
        changes.append("metadata: added total_edges")

    # Fix source_percent -> source_percentage
    if "source_percent" in meta:
        meta["source_percentage"] = meta.pop("source_percent")
        changes.append("metadata: source_percent -> source_percentage")

    # Ensure edges have sign as int
    for e in data.get("edges", []):
        if "sign" not in e:
            effect = e.get("effect", "activation")
            e["sign"] = -1 if "inhib" in effect.lower() or "repress" in effect.lower() else 1
            changes.append(f"edge {e.get('source')}->{e.get('target')}: added sign={e['sign']}")

        # Flatten evidence in edges
        for ev in e.get("evidence", []):
            if "source" in ev and isinstance(ev["source"], dict):
                src = ev.pop("source")
                for k, v in src.items():
                    if k not in ev:
                        ev[k] = v
                changes.append(f"edge evidence: flattened source")

    return data, changes


def fix_curated_edges(data):
    """Normalise curated_edges.json to v1.0."""
    changes = []
    meta = data.get("metadata", {})
    meta["flash_p_version"] = "1.0"

    for e in data.get("edges", []):
        # Flatten evidence
        for ev in e.get("evidence", []):
            if "source" in ev and isinstance(ev["source"], dict):
                src = ev.pop("source")
                for k, v in src.items():
                    if k not in ev:
                        ev[k] = v
                changes.append(f"edge {e.get('edge_id', '')}: flattened evidence")

    return data, changes


def fix_algebraic_equations(data):
    """Normalise algebraic_equations.json to v1.0."""
    changes = []
    meta = data.get("metadata", {})
    meta["flash_p_version"] = "1.0"

    # Ensure parameters block exists at top level
    if "parameters" not in data:
        # Try to extract from metadata or use defaults
        data["parameters"] = {
            "epsilon": 0.1, "K": 10.0, "activator_floor": 0.01,
            "damping": 0.7, "direction_threshold": 0.05,
            "max_iterations": 100, "convergence_tolerance": 0.0001,
        }
        changes.append("added default parameters block")

    if "total_equations" not in meta:
        meta["total_equations"] = len(data.get("equations", []))
        changes.append("metadata: added total_equations")

    return data, changes


def fix_node_annotations(data):
    """Normalise node_annotations.json to v1.0."""
    changes = []
    meta = data.get("metadata", {})
    meta["flash_p_version"] = "1.0"

    if "total_nodes" not in meta:
        meta["total_nodes"] = len(data.get("annotations", []))
        changes.append("metadata: added total_nodes")

    return data, changes


FILE_FIXERS = {
    "reconciled_perturbation_dataset.json": fix_reconciled_perturbation,
    "network.json": fix_network_json,
    "curated_edges.json": fix_curated_edges,
    "algebraic_equations.json": fix_algebraic_equations,
    "node_annotations.json": fix_node_annotations,
}


def migrate_network(net_dir, dry_run=False):
    """Migrate all JSON files in a network directory."""
    print(f"\n{'='*60}")
    print(f"Migrating: {net_dir.name}")
    print(f"{'='*60}")

    total_changes = 0

    for subdir in ["data", "network"]:
        d = net_dir / subdir
        if not d.exists():
            continue
        for json_file in sorted(d.glob("*.json")):
            if json_file.name not in FILE_FIXERS:
                continue

            fixer = FILE_FIXERS[json_file.name]
            data = json.loads(json_file.read_text(encoding="utf-8"))

            if json_file.name == "reconciled_perturbation_dataset.json":
                data, changes = fixer(data, dry_run=dry_run)
            else:
                data, changes = fixer(data)

            if changes:
                total_changes += len(changes)
                print(f"\n  {subdir}/{json_file.name}: {len(changes)} changes")
                for c in changes[:10]:
                    print(f"    - {c}")
                if len(changes) > 10:
                    print(f"    ... and {len(changes) - 10} more")

                if not dry_run:
                    backup_file(json_file)
                    json_file.write_text(
                        json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
            else:
                print(f"  {subdir}/{json_file.name}: OK (no changes needed)")

    return total_changes


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Migrate FLASH-P v1.0 -> v1.0")
    parser.add_argument("path", nargs="?")
    parser.add_argument("--all", help="Migrate all networks under base dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing")
    args = parser.parse_args()

    if args.all:
        base = Path(args.all)
        net_dirs = sorted(p.parent for p in base.rglob("network/network.json"))
        total = 0
        for nd in net_dirs:
            total += migrate_network(nd, dry_run=args.dry_run)
        print(f"\n{'='*60}")
        print(f"Total changes across {len(net_dirs)} networks: {total}")
        if args.dry_run:
            print("(DRY RUN — no files modified)")
    elif args.path:
        net_dir = Path(args.path)
        changes = migrate_network(net_dir, dry_run=args.dry_run)
        print(f"\nTotal changes: {changes}")
        if args.dry_run:
            print("(DRY RUN — no files modified)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
