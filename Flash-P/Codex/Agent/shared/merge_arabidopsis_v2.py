#!/usr/bin/env python3
"""
Merge 6 Arabidopsis individual networks into a unified multi-phenotype network.
v1.0-schema compliant. Adapted from merge_arabidopsis.py (v1.0 reference).

Steps:
 1. Load all 6 (network.json, algebraic_equations.json,
    reconciled_perturbation_dataset.json)
 2. Normalize node names via NAME_MAP
 3. Union edges (DOI merge, sign-conflict logging)
 4. Union nodes
 5. Best-single-model equation merge (conservative)
 6. Pool perturbations with prefixed test_ids and phenotype_node
 7. Copy 15 pleiotropic tests from v1 archive, flatten evidence, remap nodes
 8. Write v2-schema merged outputs
"""

import json
import os
import copy
from collections import defaultdict
from datetime import date

# === CONFIGURATION ===
THIS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS)
ARAB_DIR = os.path.join(REPO_ROOT, "Arabidopsis")
OUTPUT_DIR = os.path.join(REPO_ROOT, "merged_arabidopsis_network")
V1_ARCHIVE = os.path.join(REPO_ROOT, "merged_arabidopsis_network_v1_archive")

NETWORKS = {
    "flowering_time":        {"dir": "Flowering_Time_network",        "phenotype_node": "Flowering_Time",        "prefix": "FT"},
    "hypocotyl_length":      {"dir": "Hypocotyl_Length_network",      "phenotype_node": "Hypocotyl_Length",      "prefix": "HL"},
    "lateral_root_density":  {"dir": "Lateral_Root_Density_network",  "phenotype_node": "Lateral_Root_Density",  "prefix": "LR"},
    "plant_height":          {"dir": "Plant_Height_network",          "phenotype_node": "Plant_Height",          "prefix": "PH"},
    "seed_size":             {"dir": "Seed_Size_network",             "phenotype_node": "Seed_Size",             "prefix": "SS"},
    "shoot_branching":       {"dir": "Shoot_Branching_network",       "phenotype_node": "Shoot_Branching",       "prefix": "SB"},
}

NAME_MAP = {
    "GA":              "Gibberellin",
    "GA1":             "Gibberellin",  # GA1 biosynthesis gene → GA hormone (GA1 KO = GA deficiency)
    "Brassinolide":    "Brassinosteroid",
    "JA":              "Jasmonate",
    "COP1":            "COP1_SPA",
    "GA20OX":          "GA20OX1",
    "Abscisic_Acid":   "ABA",
}

# Non-composite-specific aliases (individual genes named slightly differently
# across networks).
COMPOSITE_TO_REPRESENTATIVE = {
    "BR":       "Brassinosteroid",  # Hypocotyl uses 'BR' as alias for the hormone
}

# Biosynthesis-pathway composites are deliberately PRESERVED. PH uses
# AUT_SYN/SL_SYN/BR_SYN/YUC_TAA/ACS_ACO as composite biosynthesis nodes;
# other networks use their individual components (FCA, DWF4, MAX1, YUC4,
# ACS, ...). Both representations coexist in the merged graph because
# collapsing composites to a single representative breaks test-specific
# semantics (e.g. PH_T005 gene=TOE1 should NOT be rerouted through FCA).
# Cross-network propagation at these hubs is handled downstream by the
# graph topology — RWR is robust to this; algebraic dilution at shared
# hubs is expected per CLAUDE.md TRAP 2.

# When a perturbation test targets a composite but the gene field names a
# specific component that's actually in the merged graph, remap the
# modifier to that component so the test's semantics match its intent.
COMPOSITE_COMPONENT_HINTS = {
    "AUT_SYN": ["FCA","FPA","FLD","FVE","LD","LDL1","FLK"],
    "SL_SYN":  ["MAX1","CCD7","CCD8","D27","LBO"],
    "BR_SYN":  ["DWF4","DET2","CPD","BR6OX"],
    "YUC_TAA": ["YUC4","YUC8","YUC10","YUC11","TAA1","TAR1","TAR2"],
    "ACS_ACO": ["ACS","ACO"],
}

CREATED_DATE = str(date.today())


# === HELPERS ===
def normalize_name(name):
    # First pass: standard aliases (GA→Gibberellin etc)
    name = NAME_MAP.get(name, name)
    # Second pass: composite → representative (collapse AUT_SYN→FCA etc)
    name = COMPOSITE_TO_REPRESENTATIVE.get(name, name)
    return name

def normalize_list(lst):
    return [normalize_name(n) for n in lst]

def normalize_dict_keys(d):
    return {normalize_name(k): v for k, v in d.items()}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {os.path.relpath(path, REPO_ROOT)}")

def build_formula(node_name, activators, inhibitors, is_source):
    if is_source:
        return f"{node_name} = gene_modifier + exogenous_supply"
    if activators:
        n = len(activators)
        parts = " * ".join(f"max({a}, 0.01)" for a in activators)
        act_term = f"({parts})" if n == 1 else f"({parts})^(1/{n})"
    else:
        act_term = "1.0"
    if inhibitors:
        inh_parts = " * ".join(inhibitors)
        inh_term = f"min(1/max({inh_parts}, 0.1), 10.0)"
    else:
        inh_term = "1.0"
    return f"{node_name} = {act_term} * {inh_term} * gene_modifier + exogenous_supply"


# === STEP 1: LOAD ===
def load_all_networks():
    all_data = {}
    for net_name, info in NETWORKS.items():
        d = os.path.join(ARAB_DIR, info["dir"])
        print(f"Loading {net_name}...")
        net  = load_json(os.path.join(d, "network", "network.json"))
        eqs  = load_json(os.path.join(d, "network", "algebraic_equations.json"))
        pert = load_json(os.path.join(d, "data", "reconciled_perturbation_dataset.json"))
        print(f"  nodes={len(net.get('nodes',[]))} edges={len(net.get('edges',[]))} "
              f"eqs={len(eqs.get('equations',[]))} tests={len(pert.get('perturbations',[]))}")
        all_data[net_name] = {"network": net, "equations": eqs, "perturbations": pert, "info": info}
    return all_data


# === STEP 2: NORMALIZE ===
def normalize_network(net):
    n = copy.deepcopy(net)
    for node in n.get("nodes", []):
        node["id"] = normalize_name(node["id"])
    for edge in n.get("edges", []):
        edge["source"] = normalize_name(edge["source"])
        edge["target"] = normalize_name(edge["target"])
    return n

def normalize_equations(eqs):
    e = copy.deepcopy(eqs)
    for eq in e.get("equations", []):
        eq["node"] = normalize_name(eq["node"])
        eq["activators"] = normalize_list(eq.get("activators", []))
        eq["inhibitors"] = normalize_list(eq.get("inhibitors", []))
        eq["formula"] = build_formula(eq["node"], eq["activators"], eq["inhibitors"], eq.get("is_source", False))
    return e

def normalize_perturbations(perts, phenotype_node):
    p = copy.deepcopy(perts)
    for t in p.get("perturbations", []):
        # Before normalizing, check if this test's gene_modifiers point at a
        # composite AND the gene field names a specific component — in that
        # case, remap the modifier to the component so propagation works
        # through the component's cascade.
        gm = t.get("gene_modifiers") or {}
        composite_keys = [k for k in list(gm.keys()) if k in COMPOSITE_COMPONENT_HINTS]
        if composite_keys and t.get("gene"):
            gene_names = [g.strip() for g in str(t["gene"]).split(",")]
            for ck in composite_keys:
                candidates = COMPOSITE_COMPONENT_HINTS[ck]
                # Exact gene match wins
                hit = next((g for g in gene_names if g in candidates), None)
                if hit:
                    gm[hit] = gm.pop(ck)
                    # Also remap in sub-perturbations list
                    for sp in t.get("perturbations", []) or []:
                        if sp.get("node") == ck:
                            sp["node"] = hit
            t["gene_modifiers"] = gm

        if isinstance(t.get("gene_modifiers"), dict):
            t["gene_modifiers"] = normalize_dict_keys(t["gene_modifiers"])
        if isinstance(t.get("exogenous_supply"), dict):
            t["exogenous_supply"] = normalize_dict_keys(t["exogenous_supply"])
        ng = t.get("network_gene")
        if isinstance(ng, list):
            t["network_gene"] = normalize_list(ng)
        elif isinstance(ng, str):
            t["network_gene"] = [normalize_name(ng)] if ng else []
        for sp in t.get("perturbations", []) or []:
            if "node" in sp:
                sp["node"] = normalize_name(sp["node"])
        if not t.get("phenotype_node"):
            t["phenotype_node"] = phenotype_node
        else:
            t["phenotype_node"] = normalize_name(t["phenotype_node"])
    return p


# === STEP 3: MERGE EDGES ===
def merge_edges(all_data):
    reg, conflicts = {}, []
    for net_name, d in all_data.items():
        for edge in d["normalized_network"].get("edges", []):
            key = (edge["source"], edge["target"])
            sign = edge.get("sign", 1)
            if key not in reg:
                reg[key] = {
                    "source": edge["source"],
                    "target": edge["target"],
                    "sign": sign,
                    "source_networks": [net_name],
                    "evidence": list(edge.get("evidence") or []),
                    "effect": edge.get("effect", ""),
                    "mechanism": edge.get("mechanism", ""),
                }
            else:
                ex = reg[key]
                if ex["sign"] != sign:
                    conflicts.append({
                        "source": edge["source"], "target": edge["target"],
                        "existing_sign": ex["sign"], "new_sign": sign,
                        "existing_networks": list(ex["source_networks"]),
                        "new_network": net_name,
                        "resolution": "kept existing (more networks)",
                    })
                else:
                    ex["source_networks"].append(net_name)
                    ex_dois = {e.get("doi","") for e in ex["evidence"] if isinstance(e, dict)}
                    for ev in (edge.get("evidence") or []):
                        if isinstance(ev, dict):
                            doi = ev.get("doi", "")
                            if doi and doi not in ex_dois:
                                ex["evidence"].append(ev)
                                ex_dois.add(doi)
    print(f"edges merged: {len(reg)}, conflicts: {len(conflicts)}")
    return reg, conflicts


# === STEP 4: MERGE NODES ===
def merge_nodes(all_data, edge_reg):
    reg = {}
    for net_name, d in all_data.items():
        for node in d["normalized_network"].get("nodes", []):
            nid = node["id"]
            if nid not in reg:
                reg[nid] = {
                    "id": nid,
                    "type": node.get("type", "GENE"),
                    "full_name": node.get("full_name", nid),
                    "description": node.get("description", ""),
                    "source_networks": [net_name],
                    "is_source": node.get("is_source", False),
                }
            else:
                ex = reg[nid]
                ex["source_networks"].append(net_name)
                new_desc = node.get("description", "")
                if len(new_desc) > len(ex.get("description", "")):
                    ex["description"] = new_desc
                new_type = node.get("type", "GENE")
                if ex["type"] == "GENE" and new_type != "GENE":
                    ex["type"] = new_type
    # Backfill: nodes referenced in equations/edges but missing from node list
    for net_name, d in all_data.items():
        for eq in d["normalized_equations"].get("equations", []):
            nid = eq["node"]
            if nid not in reg:
                reg[nid] = {
                    "id": nid, "type": eq.get("type", "GENE"),
                    "full_name": nid, "description": f"Backfilled from {net_name} equations",
                    "source_networks": [net_name],
                    "is_source": eq.get("is_source", False),
                }
    edge_nodes = set()
    for (s, t) in edge_reg:
        edge_nodes.add(s); edge_nodes.add(t)
    for m in edge_nodes - set(reg):
        reg[m] = {"id": m, "type": "GENE", "full_name": m,
                  "description": "Backfilled from edge references",
                  "source_networks": ["unknown"], "is_source": False}
    print(f"nodes merged: {len(reg)}")
    return reg


# === STEP 5: DERIVE EQUATIONS FROM EDGES (single source of truth) ===
# The merged edge graph is canonical. For every node, activators are the
# set of sources of sign=+1 edges into the node, and inhibitors are the
# set of sources of sign=-1 edges. This enforces the rule that equations
# must come from the network (CLAUDE.md Evidence & formulas). Algebraic
# dilution at shared hormone/TF hubs with many regulators is expected and
# documented in CLAUDE.md TRAPs 1–2; RWR remains the robust method.
def merge_equations(all_data, node_reg, edge_reg):
    per_node_order = defaultdict(lambda: {"acts": [], "inhs": []})
    per_node_type  = {}
    for net_name, d in all_data.items():
        for eq in d["normalized_equations"].get("equations", []):
            n = eq["node"]
            for a in eq.get("activators", []):
                if a not in per_node_order[n]["acts"]:
                    per_node_order[n]["acts"].append(a)
            for i in eq.get("inhibitors", []):
                if i not in per_node_order[n]["inhs"]:
                    per_node_order[n]["inhs"].append(i)
            per_node_type.setdefault(n, eq.get("type", "GENE"))

    edge_act = defaultdict(set); edge_inh = defaultdict(set)
    for (s, t), ed in edge_reg.items():
        (edge_act if ed["sign"] == 1 else edge_inh)[t].add(s)

    merged, decisions = [], {}
    for nid, ndata in sorted(node_reg.items()):
        node_type = per_node_type.get(nid, ndata.get("type", "GENE"))
        acts_set = edge_act.get(nid, set())
        inhs_set = edge_inh.get(nid, set())

        ordered_acts = [a for a in per_node_order[nid]["acts"] if a in acts_set]
        ordered_inhs = [i for i in per_node_order[nid]["inhs"] if i in inhs_set]
        for a in sorted(acts_set - set(ordered_acts)):
            ordered_acts.append(a)
        for i in sorted(inhs_set - set(ordered_inhs)):
            ordered_inhs.append(i)

        is_source = not ordered_acts and not ordered_inhs
        decisions[nid] = {
            "strategy": "edge-derived",
            "total_activators": len(ordered_acts),
            "total_inhibitors": len(ordered_inhs),
            "final_activators": ordered_acts,
            "final_inhibitors": ordered_inhs,
        }
        merged.append({
            "node": nid, "type": node_type,
            "is_source": is_source,
            "activators": ordered_acts,
            "inhibitors": ordered_inhs,
            "formula": build_formula(nid, ordered_acts, ordered_inhs, is_source),
        })
    print(f"equations derived from edges: {len(merged)}")
    return merged, decisions


# === STEP 6: POOL PERTURBATIONS ===
def pool_perturbations(all_data):
    pool, per_ph = [], {}
    for net_name, d in all_data.items():
        info = d["info"]
        cnt = 0
        for p in d["normalized_perturbations"].get("perturbations", []):
            mp = copy.deepcopy(p)
            old = mp.get("test_id", f"T{cnt:03d}")
            mp["test_id"] = f"{info['prefix']}_{old}"
            if not mp.get("phenotype_node"):
                mp["phenotype_node"] = info["phenotype_node"]
            mp["source_network"] = net_name
            pool.append(mp); cnt += 1
        per_ph[info["phenotype_node"]] = cnt
        print(f"  {net_name}: {cnt} tests")
    return pool, per_ph


# === STEP 7: COPY + REMAP PLEIOTROPIC TESTS ===
def copy_pleiotropic(node_reg):
    src = os.path.join(V1_ARCHIVE, "data", "pleiotropic_perturbation_dataset.json")
    v1 = load_json(src)
    tests_out, remap_log = [], []
    present = set(node_reg.keys())

    for t in v1.get("pleiotropic_tests", []):
        gene = normalize_name(t.get("gene", ""))
        gm = normalize_dict_keys(t.get("gene_modifiers") or {})
        es = normalize_dict_keys(t.get("exogenous_supply") or {})
        outs = []
        for o in t.get("expected_outcomes", []):
            pn = normalize_name(o["phenotype_node"])
            outs.append({"phenotype_node": pn, "expected_direction": o["expected_direction"]})
        # Flatten evidence: v1 nested {claim, evidence_sentence, source:{doi,...}}
        # v2 flat: {doi, title, authors, year, journal, evidence_sentence, claim}
        flat_ev = []
        for e in t.get("evidence", []):
            if "source" in e and isinstance(e["source"], dict):
                s = e["source"]
                flat_ev.append({
                    "doi": s.get("doi", ""),
                    "title": s.get("title", ""),
                    "authors": s.get("authors", s.get("author", "")),
                    "year": s.get("year"),
                    "journal": s.get("journal", ""),
                    "evidence_sentence": e.get("evidence_sentence", ""),
                    "claim": e.get("claim", ""),
                })
            else:
                flat_ev.append({
                    "doi": e.get("doi", ""),
                    "title": e.get("title", ""),
                    "authors": e.get("authors", ""),
                    "year": e.get("year"),
                    "journal": e.get("journal", ""),
                    "evidence_sentence": e.get("evidence_sentence", ""),
                    "claim": e.get("claim", ""),
                })

        # Verify referenced nodes exist in the new merged network
        missing = [n for n in gm.keys() if n not in present] + \
                  [n for n in es.keys() if n not in present] + \
                  [o["phenotype_node"] for o in outs if o["phenotype_node"] not in present]
        if missing:
            remap_log.append({"test_id": t["test_id"], "gene": gene, "missing": missing})

        tests_out.append({
            "test_id": t["test_id"],
            "gene": gene,
            "perturbation_type": t.get("perturbation_type", "knockout"),
            "description": t.get("description", ""),
            "gene_modifiers": gm,
            "exogenous_supply": es,
            "expected_outcomes": outs,
            "evidence": flat_ev,
            "source_network": t.get("source_network", ""),
        })

    total_pairs = sum(len(t["expected_outcomes"]) for t in tests_out)
    out = {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "network_type": "merged_pleiotropic",
            "description": "Pleiotropic perturbations: each test asserts outcomes across 2+ phenotype nodes.",
            "total_pleiotropic_tests": len(tests_out),
            "total_outcome_pairs": total_pairs,
        },
        "pleiotropic_tests": tests_out,
    }
    print(f"pleiotropic: {len(tests_out)} tests, {total_pairs} outcome pairs, "
          f"{len(remap_log)} w/ missing nodes")
    if remap_log:
        print("  Missing-node log (first 5):", remap_log[:5])
    return out, remap_log


# === STEP 8: BUILD OUTPUT FILES ===
def build_network_json(node_reg, edge_reg):
    nodes = []
    for nid, nd in sorted(node_reg.items()):
        e = {"id": nd["id"], "type": nd["type"], "full_name": nd.get("full_name", nid),
             "description": nd.get("description", "")}
        if nd.get("is_source"):
            e["is_source"] = True
        # keep for provenance (pydantic extra=ignore on validation)
        e["source_networks"] = nd["source_networks"]
        nodes.append(e)

    edges, eid = [], 1
    for (s, t), ed in sorted(edge_reg.items()):
        sign = ed["sign"]
        edges.append({
            "edge_id": f"ME{eid:03d}",
            "source": ed["source"], "target": ed["target"], "sign": sign,
            "effect": ed.get("effect") or ("activation" if sign == 1 else "inhibition"),
            "mechanism": ed.get("mechanism", ""),
            "evidence": ed.get("evidence", []),
            "source_networks": ed["source_networks"],
        })
        eid += 1

    n_source_nodes = sum(1 for n in nodes if n.get("is_source"))
    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "network_type": "merged",
            "phenotype_nodes": [v["phenotype_node"] for v in NETWORKS.values()],
            "source_networks": list(NETWORKS.keys()),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "source_nodes": n_source_nodes,
            "source_percentage": round(n_source_nodes * 100.0 / max(len(nodes),1), 1),
        },
        "nodes": nodes,
        "edges": edges,
    }

def build_equations_json(merged_equations):
    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "total_equations": len(merged_equations),
        },
        "parameters": {
            "epsilon": 0.1, "K": 10.0, "activator_floor": 0.01, "damping": 0.7,
            "direction_threshold": 0.05, "max_iterations": 200, "convergence_tolerance": 0.0001,
        },
        "equations": merged_equations,
    }

def build_perturbation_json(pool, per_ph):
    in_network = sum(1 for p in pool if p.get("in_network", True))
    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "total_tests": len(pool),
            "in_network": in_network,
            "not_in_network": len(pool) - in_network,
            "phenotype_node": "",
            "per_phenotype_counts": per_ph,
            "convention": "increased/decreased/unchanged relative to comparison_baseline",
        },
        "direction_threshold": 0.05,
        "perturbations": pool,
    }

def build_merge_log(all_data, node_reg, edge_reg, edge_conflicts, decisions, per_ph):
    source_networks = []
    for net_name, d in all_data.items():
        source_networks.append({
            "name": net_name,
            "phenotype_node": d["info"]["phenotype_node"],
            "nodes": len(d["network"].get("nodes", [])),
            "edges": len(d["network"].get("edges", [])),
            "tests": len(d["perturbations"].get("perturbations", [])),
        })
    shared = {n: d["source_networks"] for n, d in node_reg.items() if len(d["source_networks"]) > 1}
    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "merge_script": "Agent/merge_arabidopsis_v2.py",
        },
        "source_networks": source_networks,
        "normalization_map": NAME_MAP,
        "merged_stats": {
            "total_nodes": len(node_reg),
            "total_edges": len(edge_reg),
            "total_tests": sum(per_ph.values()),
            "shared_nodes": len(shared),
            "per_phenotype_counts": per_ph,
        },
        "shared_nodes": shared,
        "edge_conflicts": edge_conflicts,
        "equation_merge_decisions": decisions,
    }

def build_curated_edges(edge_reg, node_reg):
    node_type_of = {nid: nd.get("type", "GENE") for nid, nd in node_reg.items()}
    edges_out = []
    eid = 1
    for (s, t), ed in sorted(edge_reg.items()):
        sign = ed["sign"]
        effect = ed.get("effect") or ("activation" if sign == 1 else "inhibition")
        if effect not in ("activation", "inhibition", "repression"):
            effect = "activation" if sign == 1 else "inhibition"
        evidence = ed.get("evidence") or []
        if not evidence:  # min_length=1 required
            evidence = [{"doi": "", "claim": "merged-from-network-without-explicit-evidence"}]
        edges_out.append({
            "edge_id": f"ME{eid:03d}",
            "source": ed["source"],
            "target": ed["target"],
            "source_type": node_type_of.get(ed["source"], "GENE"),
            "target_type": node_type_of.get(ed["target"], "GENE"),
            "sign": sign,
            "effect": effect,
            "edge_type": "",
            "confidence": "MEDIUM",
            "mechanism": ed.get("mechanism", ""),
            "in_model": True,
            "evidence": evidence,
            "source_networks": ed["source_networks"],
        })
        eid += 1
    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": CREATED_DATE,
            "total_edges": len(edges_out),
        },
        "edges": edges_out,
    }


# === MAIN ===
def main():
    print("=" * 60)
    print("MERGE ARABIDOPSIS NETWORKS -> merged_arabidopsis_network/")
    print(f"Source: {ARAB_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    print("\n[1/8] Loading")
    all_data = load_all_networks()

    print("\n[2/8] Normalizing")
    for _, d in all_data.items():
        d["normalized_network"] = normalize_network(d["network"])
        d["normalized_equations"] = normalize_equations(d["equations"])
        d["normalized_perturbations"] = normalize_perturbations(d["perturbations"], d["info"]["phenotype_node"])

    print("\n[3/8] Merging edges")
    edge_reg, edge_conflicts = merge_edges(all_data)

    # Literature-backed additions — edges that v1's merge refinement had
    # with DOIs but that aren't in any current individual network. Only
    # include edges whose source gene is actually perturbed in >=1 test.
    extra_path = os.path.join(THIS, "merged_arabidopsis_extra_edges.json")
    if os.path.exists(extra_path):
        with open(extra_path, "r", encoding="utf-8") as f:
            ex = json.load(f)
        added = 0
        for e in ex.get("extra_edges", []):
            key = (e["source"], e["target"])
            sign = e.get("sign", 1)
            if key not in edge_reg:
                edge_reg[key] = {
                    "source": e["source"],
                    "target": e["target"],
                    "sign": sign,
                    "source_networks": e.get("source_networks", ["v1_merge_refinement"]),
                    "evidence": e.get("evidence", []),
                    "effect": e.get("effect", "activation" if sign == 1 else "inhibition"),
                    "mechanism": e.get("mechanism", ""),
                }
                added += 1
        print(f"  added {added} literature-backed edges from {os.path.basename(extra_path)}")

    print("\n[4/8] Merging nodes")
    node_reg = merge_nodes(all_data, edge_reg)

    print("\n[5/8] Deriving equations from edges")
    merged_eqs, decisions = merge_equations(all_data, node_reg, edge_reg)

    print("\n[6/8] Pooling perturbations")
    pool, per_ph = pool_perturbations(all_data)

    print("\n[7/8] Copying pleiotropic tests from v1 archive")
    pleio, remap_log = copy_pleiotropic(node_reg)

    print("\n[8/8] Writing outputs")
    save_json(os.path.join(OUTPUT_DIR, "network", "network.json"),                          build_network_json(node_reg, edge_reg))
    save_json(os.path.join(OUTPUT_DIR, "network", "algebraic_equations.json"),              build_equations_json(merged_eqs))
    save_json(os.path.join(OUTPUT_DIR, "data", "reconciled_perturbation_dataset.json"),     build_perturbation_json(pool, per_ph))
    save_json(os.path.join(OUTPUT_DIR, "data", "curated_edges.json"),                       build_curated_edges(edge_reg, node_reg))
    save_json(os.path.join(OUTPUT_DIR, "data", "pleiotropic_perturbation_dataset.json"),    pleio)
    save_json(os.path.join(OUTPUT_DIR, "data", "merge_log.json"),                           build_merge_log(all_data, node_reg, edge_reg, edge_conflicts, decisions, per_ph))
    save_json(os.path.join(OUTPUT_DIR, "data", "pleiotropic_node_remap_log.json"),          {"missing_node_tests": remap_log})

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print(f"  nodes={len(node_reg)}  edges={len(edge_reg)}  "
          f"eqs={len(merged_eqs)}  tests={sum(per_ph.values())}  pleio={len(pleio['pleiotropic_tests'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
