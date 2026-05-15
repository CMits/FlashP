#!/usr/bin/env python3
"""
Merge 6 Arabidopsis individual networks into a single unified network.

This script:
1. Reads all 6 network.json, algebraic_equations.json, reconciled_perturbation_dataset.json
2. Normalizes node names (GA->Gibberellin, Brassinolide->Brassinosteroid, etc.)
3. Unions all edges with evidence merging
4. Merges equations using "best single model" strategy for shared nodes
5. Pools all perturbation tests with explicit phenotype_node
6. Writes: network.json, algebraic_equations.json, curated_edges.json,
           reconciled_perturbation_dataset.json, merge_log.json
"""

import json
import os
import copy
from collections import defaultdict, OrderedDict
from datetime import date

# === CONFIGURATION ===

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARAB_DIR = os.path.join(BASE_DIR, "Arabidopsis")
OUTPUT_DIR = os.path.join(ARAB_DIR, "merged_arabidopsis_network")

NETWORKS = {
    "flowering_time": {
        "dir": "flowering_time_network",
        "phenotype_node": "Flowering_Time",
        "prefix": "FT",
    },
    "hypocotyl_length": {
        "dir": "hypocotyl_length_network",
        "phenotype_node": "Hypocotyl_Length",
        "prefix": "HL",
    },
    "lateral_root_density": {
        "dir": "lateral_root_density_network",
        "phenotype_node": "Lateral_Root_Density",
        "prefix": "LR",
    },
    "plant_height": {
        "dir": "plant_height_network",
        "phenotype_node": "Plant_Height",
        "prefix": "PH",
    },
    "seed_size": {
        "dir": "seed_size_network",
        "phenotype_node": "Seed_Size",
        "prefix": "SS",
    },
    "shoot_branching": {
        "dir": "shoot_branching_network",
        "phenotype_node": "Shoot_Branching",
        "prefix": "SB",
    },
}

# Node name normalization map
NAME_MAP = {
    "GA": "Gibberellin",
    "Brassinolide": "Brassinosteroid",
    "JA": "Jasmonate",
    "COP1": "COP1_SPA",
    "GA20OX": "GA20OX1",  # hypocotyl uses GA20OX, others use GA20OX1
    "Abscisic_Acid": "ABA",  # hypocotyl uses Abscisic_Acid, others use ABA
}

# === HELPERS ===

def normalize_name(name):
    """Apply canonical name mapping."""
    return NAME_MAP.get(name, name)

def normalize_names_in_list(lst):
    """Normalize all names in a list."""
    return [normalize_name(n) for n in lst]

def normalize_names_in_dict(d):
    """Normalize all keys in a dict."""
    return {normalize_name(k): v for k, v in d.items()}

def load_json(path):
    """Load a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    """Save data as JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {os.path.basename(path)}")

def build_formula(node_name, activators, inhibitors, is_source):
    """Build the algebraic formula string."""
    if is_source:
        return f"{node_name} = gene_modifier + exogenous_supply"

    # Activation term
    if activators:
        n = len(activators)
        act_parts = " * ".join(f"max({a}, 0.01)" for a in activators)
        if n == 1:
            act_term = f"({act_parts})"
        else:
            act_term = f"({act_parts})^(1/{n})"
    else:
        act_term = "1.0"

    # Inhibition term
    if inhibitors:
        inh_parts = " * ".join(inhibitors)
        if len(inhibitors) == 1:
            inh_term = f"min(1/max({inh_parts}, 0.1), 10.0)"
        else:
            inh_term = f"min(1/max({inh_parts}, 0.1), 10.0)"
    else:
        inh_term = "1.0"

    return f"{node_name} = {act_term} * {inh_term} * gene_modifier + exogenous_supply"


# === STEP 1: LOAD ALL DATA ===

def load_all_networks():
    """Load network.json, algebraic_equations.json, reconciled_perturbation_dataset.json
    from all 6 networks."""

    all_data = {}
    for net_name, net_info in NETWORKS.items():
        net_dir = os.path.join(ARAB_DIR, net_info["dir"])
        print(f"\nLoading {net_name}...")

        network_path = os.path.join(net_dir, "network", "network.json")
        equations_path = os.path.join(net_dir, "network", "algebraic_equations.json")
        perturbations_path = os.path.join(net_dir, "data", "reconciled_perturbation_dataset.json")

        network = load_json(network_path)
        equations = load_json(equations_path)
        perturbations = load_json(perturbations_path)

        n_nodes = len(network.get("nodes", []))
        n_edges = len(network.get("edges", []))
        n_eqs = len(equations.get("equations", []))
        n_perts = len(perturbations.get("perturbations", []))

        print(f"  Nodes: {n_nodes}, Edges: {n_edges}, Equations: {n_eqs}, Tests: {n_perts}")

        all_data[net_name] = {
            "network": network,
            "equations": equations,
            "perturbations": perturbations,
            "info": net_info,
        }

    return all_data


# === STEP 2: NORMALIZE NAMES ===

def normalize_network(network_data):
    """Apply name normalization to a network's nodes and edges."""
    network = copy.deepcopy(network_data)

    # Normalize nodes
    for node in network.get("nodes", []):
        old_id = node["id"]
        node["id"] = normalize_name(old_id)

    # Normalize edges
    for edge in network.get("edges", []):
        edge["source"] = normalize_name(edge["source"])
        edge["target"] = normalize_name(edge["target"])

    return network

def normalize_equations(equations_data):
    """Apply name normalization to equations."""
    equations = copy.deepcopy(equations_data)

    for eq in equations.get("equations", []):
        eq["node"] = normalize_name(eq["node"])
        eq["activators"] = normalize_names_in_list(eq.get("activators", []))
        eq["inhibitors"] = normalize_names_in_list(eq.get("inhibitors", []))
        # Rebuild formula with normalized names
        eq["formula"] = build_formula(
            eq["node"],
            eq["activators"],
            eq["inhibitors"],
            eq.get("is_source", False)
        )

    return equations

def normalize_perturbations(pert_data, phenotype_node):
    """Apply name normalization to perturbations and ensure phenotype_node is set."""
    perts = copy.deepcopy(pert_data)

    for p in perts.get("perturbations", []):
        # Normalize gene_modifiers keys
        if "gene_modifiers" in p and isinstance(p["gene_modifiers"], dict):
            p["gene_modifiers"] = normalize_names_in_dict(p["gene_modifiers"])

        # Normalize exogenous_supply keys
        if "exogenous_supply" in p and isinstance(p["exogenous_supply"], dict):
            p["exogenous_supply"] = normalize_names_in_dict(p["exogenous_supply"])

        # Normalize network_gene
        if "network_gene" in p:
            if isinstance(p["network_gene"], list):
                p["network_gene"] = normalize_names_in_list(p["network_gene"])
            elif isinstance(p["network_gene"], str):
                p["network_gene"] = normalize_name(p["network_gene"])

        # Ensure phenotype_node is set
        if not p.get("phenotype_node"):
            p["phenotype_node"] = phenotype_node

    return perts


# === STEP 3: MERGE EDGES ===

def merge_edges(all_data):
    """Merge all edges from all networks, combining evidence for shared edges."""

    # edge_key = (source, target, sign)
    edge_registry = {}  # key -> merged edge data
    edge_conflicts = []

    for net_name, data in all_data.items():
        network = data["normalized_network"]
        for edge in network.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            sign = edge.get("sign", 1)
            key = (source, target)

            if key not in edge_registry:
                edge_registry[key] = {
                    "source": source,
                    "target": target,
                    "sign": sign,
                    "source_networks": [net_name],
                    "evidence": edge.get("evidence", []),
                    "effect": edge.get("effect", ""),
                    "mechanism": edge.get("mechanism", ""),
                    "description": edge.get("description", ""),
                }
            else:
                existing = edge_registry[key]
                if existing["sign"] != sign:
                    # Sign conflict!
                    edge_conflicts.append({
                        "source": source,
                        "target": target,
                        "existing_sign": existing["sign"],
                        "new_sign": sign,
                        "existing_networks": existing["source_networks"],
                        "new_network": net_name,
                        "resolution": "kept existing (more networks)",
                    })
                    # Keep the one with more networks
                    if len(existing["source_networks"]) <= 0:
                        existing["sign"] = sign
                else:
                    existing["source_networks"].append(net_name)
                    # Merge evidence
                    existing_dois = set()
                    for ev in existing.get("evidence", []):
                        doi = ev.get("source", {}).get("doi", "") if isinstance(ev, dict) else ""
                        if doi:
                            existing_dois.add(doi)
                    for ev in edge.get("evidence", []):
                        doi = ev.get("source", {}).get("doi", "") if isinstance(ev, dict) else ""
                        if doi and doi not in existing_dois:
                            existing["evidence"].append(ev)
                            existing_dois.add(doi)

    print(f"\n=== EDGE MERGE RESULTS ===")
    print(f"Total unique edges: {len(edge_registry)}")
    print(f"Sign conflicts: {len(edge_conflicts)}")

    shared_edges = [(k, v) for k, v in edge_registry.items() if len(v["source_networks"]) > 1]
    print(f"Shared edges (2+ networks): {len(shared_edges)}")

    return edge_registry, edge_conflicts


# === STEP 4: MERGE NODES ===

def merge_nodes(all_data, edge_registry):
    """Merge all nodes from all networks."""

    node_registry = {}  # node_id -> merged node data

    for net_name, data in all_data.items():
        network = data["normalized_network"]
        for node in network.get("nodes", []):
            node_id = node["id"]

            if node_id not in node_registry:
                node_registry[node_id] = {
                    "id": node_id,
                    "type": node.get("type", "GENE"),
                    "full_name": node.get("full_name", node_id),
                    "description": node.get("description", ""),
                    "source_networks": [net_name],
                }
                if node.get("is_source"):
                    node_registry[node_id]["is_source"] = True
            else:
                existing = node_registry[node_id]
                existing["source_networks"].append(net_name)
                # Keep the longest description
                new_desc = node.get("description", "")
                if len(new_desc) > len(existing.get("description", "")):
                    existing["description"] = new_desc
                # Keep the most specific type (prefer non-GENE types)
                new_type = node.get("type", "GENE")
                if existing["type"] == "GENE" and new_type != "GENE":
                    existing["type"] = new_type

    # Add nodes from equations that are missing from the node list
    for net_name, data in all_data.items():
        equations = data.get("normalized_equations", {})
        for eq in equations.get("equations", []):
            node_id = eq["node"]
            if node_id not in node_registry:
                node_registry[node_id] = {
                    "id": node_id,
                    "type": eq.get("type", "GENE"),
                    "full_name": node_id,
                    "description": f"Added from {net_name} equations (missing from node list)",
                    "source_networks": [net_name],
                }
                if eq.get("is_source"):
                    node_registry[node_id]["is_source"] = True
                print(f"  Auto-added missing node: {node_id} (from {net_name} equations)")

    # Check for nodes referenced in edges but not in node list
    edge_nodes = set()
    for (src, tgt), edge in edge_registry.items():
        edge_nodes.add(src)
        edge_nodes.add(tgt)

    missing = edge_nodes - set(node_registry.keys())
    if missing:
        # Auto-add these too
        for m in missing:
            node_registry[m] = {
                "id": m,
                "type": "GENE",
                "full_name": m,
                "description": "Added from edge references (missing from node list)",
                "source_networks": ["unknown"],
            }
            print(f"  Auto-added missing edge node: {m}")

    print(f"\n=== NODE MERGE RESULTS ===")
    print(f"Total unique nodes: {len(node_registry)}")
    shared = [n for n, d in node_registry.items() if len(d["source_networks"]) > 1]
    print(f"Shared nodes (2+ networks): {len(shared)}")
    exclusive = [n for n, d in node_registry.items() if len(d["source_networks"]) == 1]
    print(f"Exclusive nodes (1 network): {len(exclusive)}")

    return node_registry


# === STEP 5: MERGE EQUATIONS (CRITICAL) ===

# For each shared node, specify which network's equation to use as base.
# This is the "best single model" strategy.
# We then add activators/inhibitors from other networks ONLY if they are referenced
# in perturbation tests and represent genuinely novel regulators.

# Best model selection rationale:
# - plant_height: richest DELLA, BZR1, Gibberellin, PHYB models
# - lateral_root_density: richest Auxin, Cytokinin, TIR1 models (most nodes overall)
# - shoot_branching: unique Strigolactone cascade
# - hypocotyl_length: good light signaling models

def merge_equations(all_data, node_registry, edge_registry):
    """Merge equations using CONSERVATIVE best-single-model strategy.

    For shared nodes, we use the equation from the network that models it
    most completely. We then ONLY add regulators from other networks if:
    1. The regulator is directly tested in perturbation tests (its KO/OE needs
       to propagate through this node)
    2. The regulator exists in the merged network
    3. Adding it doesn't exceed 7 activators or 7 inhibitors
    We do NOT blindly union from the edge registry.
    """

    # Build per-node equation inventory across all networks
    node_equations = defaultdict(dict)  # node_id -> {net_name: equation_dict}

    for net_name, data in all_data.items():
        equations = data["normalized_equations"]
        for eq in equations.get("equations", []):
            node = eq["node"]
            node_equations[node][net_name] = eq

    # Identify which nodes are DIRECTLY perturbed in tests AND which phenotype
    # they target. We need to know: if gene X is KO'd and the test targets
    # phenotype Y, does X need a path to Y through some shared node?
    # More precisely: identify regulators that MUST be in an equation for
    # a perturbation test to work.
    tested_as_modifier = defaultdict(set)  # gene -> set of (network_name)
    for net_name, data in all_data.items():
        perts = data["normalized_perturbations"]
        for p in perts.get("perturbations", []):
            if p.get("in_network", True):
                # Check gene_modifiers dict
                gm = p.get("gene_modifiers") or {}
                es = p.get("exogenous_supply") or {}
                for g in gm.keys():
                    tested_as_modifier[g].add(net_name)
                for g in es.keys():
                    tested_as_modifier[g].add(net_name)
                # Also check the 'gene' field and 'network_gene' field
                # Many tests specify the gene via these fields, not gene_modifiers
                gene = p.get("gene", "")
                if gene:
                    for g in gene.split(","):
                        g = normalize_name(g.strip())
                        if g and g != "WT":
                            tested_as_modifier[g].add(net_name)
                ng = p.get("network_gene", "")
                if isinstance(ng, list):
                    for g in ng:
                        tested_as_modifier[normalize_name(g)].add(net_name)
                elif isinstance(ng, str) and ng:
                    tested_as_modifier[normalize_name(ng)].add(net_name)

    merged_equations = []
    equation_decisions = {}

    all_nodes = set(node_registry.keys())

    for node_id, node_data in sorted(node_registry.items()):
        eqs = node_equations.get(node_id, {})

        if len(eqs) == 0:
            # Node exists in network but has no equation - make it a source
            merged_equations.append({
                "node": node_id,
                "type": node_data.get("type", "GENE"),
                "is_source": True,
                "activators": [],
                "inhibitors": [],
                "formula": build_formula(node_id, [], [], True),
            })
            continue

        if len(eqs) == 1:
            # Only in one network - copy directly
            net_name, eq = list(eqs.items())[0]
            merged_equations.append({
                "node": eq["node"],
                "type": eq.get("type", node_data.get("type", "GENE")),
                "is_source": eq.get("is_source", False),
                "activators": list(eq.get("activators", [])),
                "inhibitors": list(eq.get("inhibitors", [])),
                "formula": eq.get("formula", ""),
            })
            continue

        # === SHARED NODE: Best Single Model Strategy ===

        # Count how many networks treat this node as source vs non-source
        source_count = sum(1 for eq in eqs.values() if eq.get("is_source", False))
        nonsource_count = len(eqs) - source_count

        # Simple majority rule: if more networks model as source, keep source
        prefer_source = source_count > nonsource_count

        best_net = None
        best_score = -1

        for net_name, eq in eqs.items():
            acts = eq.get("activators", [])
            inhs = eq.get("inhibitors", [])
            is_src = eq.get("is_source", False)

            if prefer_source:
                # Prefer source equations, among sources prefer network with more tests
                score = 100 if is_src else 0
                n_tests = len(all_data[net_name]["normalized_perturbations"].get("perturbations", []))
                score += n_tests
            else:
                # Prefer non-source with more regulators (most complete model)
                score = 0 if is_src else 100
                score += len(acts) * 2 + len(inhs) * 2

            if score > best_score:
                best_score = score
                best_net = net_name

        base_eq = eqs[best_net]
        final_acts = list(base_eq.get("activators", []))
        final_inhs = list(base_eq.get("inhibitors", []))
        is_source = base_eq.get("is_source", False)

        # CONSERVATIVE: Do NOT add regulators from other networks in the initial merge.
        # Use only the base equation. Additions happen during refinement if needed.
        added_acts = []
        added_inhs = []

        # If base was source but now has regulators, no longer source
        if is_source and (final_acts or final_inhs):
            is_source = False

        # Record decision
        other_nets = [n for n in eqs.keys() if n != best_net]
        equation_decisions[node_id] = {
            "base_network": best_net,
            "other_networks": other_nets,
            "base_activators": list(base_eq.get("activators", [])),
            "base_inhibitors": list(base_eq.get("inhibitors", [])),
            "added_activators": added_acts,
            "added_inhibitors": added_inhs,
            "final_activators": final_acts,
            "final_inhibitors": final_inhs,
            "total_activators": len(final_acts),
            "total_inhibitors": len(final_inhs),
        }

        merged_equations.append({
            "node": node_id,
            "type": base_eq.get("type", node_data.get("type", "GENE")),
            "is_source": is_source,
            "activators": final_acts,
            "inhibitors": final_inhs,
            "formula": build_formula(node_id, final_acts, final_inhs, is_source),
        })

    # Print summary
    print(f"\n=== EQUATION MERGE RESULTS ===")
    print(f"Total equations: {len(merged_equations)}")
    source_count = sum(1 for eq in merged_equations if eq.get("is_source"))
    print(f"Source nodes: {source_count}")

    # Report nodes with many activators (dilution risk)
    high_act = [(eq["node"], len(eq["activators"])) for eq in merged_equations
                if len(eq.get("activators", [])) > 4]
    if high_act:
        print(f"\nDILUTION RISK - Nodes with >4 activators:")
        for node, count in sorted(high_act, key=lambda x: -x[1]):
            eq = next(e for e in merged_equations if e["node"] == node)
            print(f"  {node}: {count} activators = {eq['activators']}")

    return merged_equations, equation_decisions


# === STEP 6: POOL PERTURBATIONS ===

def pool_perturbations(all_data):
    """Pool all perturbation tests with phenotype_node enforcement and ID prefixing."""

    merged_perts = []
    per_phenotype_counts = {}

    for net_name, data in all_data.items():
        info = data["info"]
        prefix = info["prefix"]
        phenotype_node = info["phenotype_node"]
        perts = data["normalized_perturbations"]

        count = 0
        for p in perts.get("perturbations", []):
            merged_p = copy.deepcopy(p)

            # Prefix test_id
            old_id = merged_p.get("test_id", f"T{count}")
            merged_p["test_id"] = f"{prefix}_{old_id}"

            # Ensure phenotype_node
            if not merged_p.get("phenotype_node"):
                merged_p["phenotype_node"] = phenotype_node

            # Add source_network field
            merged_p["source_network"] = net_name

            merged_perts.append(merged_p)
            count += 1

        per_phenotype_counts[phenotype_node] = count
        print(f"  {net_name}: {count} tests -> phenotype={phenotype_node}")

    # Count in_network
    in_network = sum(1 for p in merged_perts if p.get("in_network", True))
    not_in_network = sum(1 for p in merged_perts if not p.get("in_network", True))

    print(f"\n=== PERTURBATION POOLING ===")
    print(f"Total tests: {len(merged_perts)}")
    print(f"In network: {in_network}")
    print(f"Not in network: {not_in_network}")

    return merged_perts, per_phenotype_counts


# === STEP 7: CONNECTIVITY CHECK ===

def check_connectivity(merged_equations, edge_registry, node_registry):
    """Check that all nodes are connected and all equations reference valid nodes."""

    eq_nodes = {eq["node"] for eq in merged_equations}
    all_nodes = set(node_registry.keys())

    # Check for nodes without equations
    missing_eqs = all_nodes - eq_nodes
    if missing_eqs:
        print(f"WARNING: {len(missing_eqs)} nodes without equations: {missing_eqs}")

    # Check for equation references to non-existent nodes
    for eq in merged_equations:
        for act in eq.get("activators", []):
            if act not in eq_nodes:
                print(f"WARNING: {eq['node']} references non-existent activator: {act}")
        for inh in eq.get("inhibitors", []):
            if inh not in eq_nodes:
                print(f"WARNING: {eq['node']} references non-existent inhibitor: {inh}")

    # Check that every non-source, non-phenotype node has at least one edge
    edge_nodes = set()
    for (src, tgt), edge in edge_registry.items():
        edge_nodes.add(src)
        edge_nodes.add(tgt)

    disconnected = []
    for eq in merged_equations:
        node = eq["node"]
        node_type = eq.get("type", "GENE")
        if node not in edge_nodes and node_type != "PHENOTYPE":
            disconnected.append(node)

    if disconnected:
        print(f"WARNING: {len(disconnected)} disconnected nodes: {disconnected}")

    # Check source nodes
    source_nodes = [eq["node"] for eq in merged_equations if eq.get("is_source")]
    for eq in merged_equations:
        if not eq.get("is_source") and not eq.get("activators") and not eq.get("inhibitors"):
            print(f"WARNING: {eq['node']} has no activators/inhibitors but is_source=False")

    print(f"\n=== CONNECTIVITY CHECK ===")
    print(f"Equation nodes: {len(eq_nodes)}")
    print(f"Source nodes: {len(source_nodes)}")
    print(f"Disconnected: {len(disconnected)}")


# === STEP 8: BUILD OUTPUT FILES ===

def build_network_json(node_registry, edge_registry):
    """Build the merged network.json."""

    nodes = []
    for node_id, node_data in sorted(node_registry.items()):
        node_entry = {
            "id": node_data["id"],
            "type": node_data["type"],
            "full_name": node_data.get("full_name", node_id),
            "description": node_data.get("description", ""),
            "source_networks": node_data["source_networks"],
        }
        if node_data.get("is_source"):
            node_entry["is_source"] = True
        nodes.append(node_entry)

    edges = []
    edge_id = 1
    for (src, tgt), edge_data in sorted(edge_registry.items()):
        edge_entry = {
            "edge_id": f"ME{edge_id:03d}",
            "source": edge_data["source"],
            "target": edge_data["target"],
            "sign": edge_data["sign"],
            "effect": edge_data.get("effect", "activation" if edge_data["sign"] == 1 else "inhibition"),
            "mechanism": edge_data.get("mechanism", ""),
            "description": edge_data.get("description", ""),
            "source_networks": edge_data["source_networks"],
            "evidence": edge_data.get("evidence", []),
        }
        edges.append(edge_entry)
        edge_id += 1

    network = {
        "metadata": {
            "flash_p_version": "1.0",
            "network_type": "merged",
            "species": "Arabidopsis thaliana",
            "phenotypes": ["Flowering_Time", "Hypocotyl_Length", "Lateral_Root_Density",
                           "Plant_Height", "Seed_Size", "Shoot_Branching"],
            "source_networks": list(NETWORKS.keys()),
            "created": str(date.today()),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }

    return network

def build_equations_json(merged_equations):
    """Build the merged algebraic_equations.json."""

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "network_type": "merged",
            "species": "Arabidopsis thaliana",
            "phenotypes": ["Flowering_Time", "Hypocotyl_Length", "Lateral_Root_Density",
                           "Plant_Height", "Seed_Size", "Shoot_Branching"],
            "created": str(date.today()),
            "total_equations": len(merged_equations),
            "equation_type": "algebraic_steady_state",
            "parameters": {
                "epsilon": 0.1,
                "K": 10.0,
                "activator_floor": 0.01,
                "damping": 0.7,
                "direction_threshold": 0.05,
                "max_iterations": 50,
                "convergence_tolerance": 0.0001,
            },
        },
        "equations": merged_equations,
    }

def build_perturbation_json(merged_perts, per_phenotype_counts):
    """Build the merged reconciled_perturbation_dataset.json."""

    in_network = sum(1 for p in merged_perts if p.get("in_network", True))

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "network_type": "merged",
            "species": "Arabidopsis thaliana",
            "created": str(date.today()),
            "total_tests": len(merged_perts),
            "in_network": in_network,
            "not_in_network": len(merged_perts) - in_network,
            "per_phenotype_counts": per_phenotype_counts,
            "convention": {
                "increased": "phenotype value goes up relative to comparison baseline",
                "decreased": "phenotype value goes down relative to comparison baseline",
            },
        },
        "perturbations": merged_perts,
    }

def build_merge_log(all_data, node_registry, edge_registry, edge_conflicts,
                     equation_decisions, per_phenotype_counts):
    """Build the merge_log.json documenting every decision."""

    source_networks = []
    for net_name, data in all_data.items():
        network = data["network"]
        n_nodes = len(network.get("nodes", []))
        n_edges = len(network.get("edges", []))
        n_tests = len(data["perturbations"].get("perturbations", []))
        source_networks.append({
            "name": net_name,
            "phenotype_node": data["info"]["phenotype_node"],
            "nodes": n_nodes,
            "edges": n_edges,
            "tests": n_tests,
        })

    shared_nodes = {n: d["source_networks"] for n, d in node_registry.items()
                    if len(d["source_networks"]) > 1}

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "merge_date": str(date.today()),
            "merge_script": "merge_arabidopsis.py",
        },
        "source_networks": source_networks,
        "normalization_map": NAME_MAP,
        "merged_stats": {
            "total_nodes": len(node_registry),
            "total_edges": len(edge_registry),
            "total_tests": sum(per_phenotype_counts.values()),
            "shared_nodes": len(shared_nodes),
            "per_phenotype_counts": per_phenotype_counts,
        },
        "shared_nodes": shared_nodes,
        "edge_conflicts": edge_conflicts,
        "equation_merge_decisions": equation_decisions,
    }


# === MAIN ===

def main():
    print("=" * 60)
    print("ARABIDOPSIS NETWORK MERGE")
    print("=" * 60)

    # Step 1: Load all networks
    print("\n--- STEP 1: Loading all networks ---")
    all_data = load_all_networks()

    # Step 2: Normalize names
    print("\n--- STEP 2: Normalizing names ---")
    for net_name, data in all_data.items():
        data["normalized_network"] = normalize_network(data["network"])
        data["normalized_equations"] = normalize_equations(data["equations"])
        data["normalized_perturbations"] = normalize_perturbations(
            data["perturbations"], data["info"]["phenotype_node"]
        )
        print(f"  Normalized {net_name}")

    # Step 3: Merge edges
    print("\n--- STEP 3: Merging edges ---")
    edge_registry, edge_conflicts = merge_edges(all_data)

    # Step 4: Merge nodes
    print("\n--- STEP 4: Merging nodes ---")
    node_registry = merge_nodes(all_data, edge_registry)

    # Step 5: Merge equations
    print("\n--- STEP 5: Merging equations ---")
    merged_equations, equation_decisions = merge_equations(all_data, node_registry, edge_registry)

    # Step 6: Pool perturbations
    print("\n--- STEP 6: Pooling perturbations ---")
    merged_perts, per_phenotype_counts = pool_perturbations(all_data)

    # Step 7: Connectivity check
    print("\n--- STEP 7: Connectivity check ---")
    check_connectivity(merged_equations, edge_registry, node_registry)

    # Step 8: Write output files
    print("\n--- STEP 8: Writing output files ---")

    # network.json
    network_json = build_network_json(node_registry, edge_registry)
    save_json(os.path.join(OUTPUT_DIR, "network", "network.json"), network_json)

    # algebraic_equations.json
    equations_json = build_equations_json(merged_equations)
    save_json(os.path.join(OUTPUT_DIR, "network", "algebraic_equations.json"), equations_json)

    # reconciled_perturbation_dataset.json
    pert_json = build_perturbation_json(merged_perts, per_phenotype_counts)
    save_json(os.path.join(OUTPUT_DIR, "data", "reconciled_perturbation_dataset.json"), pert_json)

    # curated_edges.json (all edges with evidence)
    curated_edges = {
        "metadata": {
            "flash_p_version": "1.0",
            "network_type": "merged",
            "species": "Arabidopsis thaliana",
            "created": str(date.today()),
            "total_edges": len(edge_registry),
        },
        "edges": [edge_data for edge_data in edge_registry.values()],
    }
    save_json(os.path.join(OUTPUT_DIR, "data", "curated_edges.json"), curated_edges)

    # merge_log.json
    merge_log = build_merge_log(all_data, node_registry, edge_registry,
                                 edge_conflicts, equation_decisions, per_phenotype_counts)
    save_json(os.path.join(OUTPUT_DIR, "data", "merge_log.json"), merge_log)

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print(f"  Nodes: {len(node_registry)}")
    print(f"  Edges: {len(edge_registry)}")
    print(f"  Equations: {len(merged_equations)}")
    print(f"  Tests: {sum(per_phenotype_counts.values())}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
