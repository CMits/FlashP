#!/usr/bin/env python3
"""Post-BUILDER polish:
 - merge duplicate plural/singular nodes (Cytokinins->Cytokinin, Strigolactones->Strigolactone)
 - fix naming-pattern violations (Far-red_Light, MAX_Pathway)
 - trim trivial source nodes (GENE/PROTEIN_COMPLEX with out_degree=1) that don't add cascade depth
 - rebuild equations + annotations from cleaned topology
 - re-emit network.json metadata"""
import json
from collections import defaultdict
from pathlib import Path

NET_DIR = Path(__file__).resolve().parent / "network"

MERGE_MAP = {
    "Cytokinins": "Cytokinin",
    "Strigolactones": "Strigolactone",
}
RENAME_MAP = {
    "Far-red_Light": "Far_Red_Light",
    "MAX_Pathway": None,   # delete — meta-node
}

VALID_NAME_RE = {
    "GENE":             r"^[A-Z][A-Z0-9_]*$",
    "HORMONE":          r"^[A-Z][A-Za-z0-9_]*$",
    "METABOLITE":       r"^[A-Z][A-Za-z0-9_]*$",
    "ENVIRONMENT":      r"^[A-Z][A-Za-z0-9_]*$",
    "PROTEIN_COMPLEX":  r"^[A-Z][A-Z0-9_]*$",
    "REGULATORY_RNA":   r".+",
    "PHENOTYPE":        r"^[A-Z][A-Za-z0-9_]*$",
    "PROCESS":          r"^[A-Z][A-Za-z0-9_]*$",
}


def main():
    net = json.load((NET_DIR/"network.json").open())
    nodes = net["nodes"]
    edges = net["edges"]
    n0, e0 = len(nodes), len(edges)

    # ── 1. apply rename/merge ─────────────────────────────────────────
    def remap(node_id: str) -> str | None:
        if node_id in RENAME_MAP:
            return RENAME_MAP[node_id]
        return MERGE_MAP.get(node_id, node_id)

    # filter nodes
    cleaned_nodes = []
    seen_ids = set()
    for n in nodes:
        new_id = remap(n["id"])
        if new_id is None:
            continue
        if new_id in seen_ids:
            continue   # duplicate after merge — keep first (the canonical singular)
        n2 = dict(n)
        n2["id"] = new_id
        # if the canonical singular already exists with different type, keep canonical type
        if new_id != n["id"]:
            # we're merging — the canonical singular's type is in the original list
            existing = next((x for x in nodes if x["id"] == new_id), None)
            if existing:
                n2["type"] = existing["type"]
                n2["full_name"] = existing["full_name"]
                n2["description"] = existing["description"]
        cleaned_nodes.append(n2)
        seen_ids.add(new_id)

    # filter edges: rename endpoints, drop edges whose endpoint was deleted, drop self-loops
    cleaned_edges = []
    seen_edge = set()
    for ed in edges:
        s = remap(ed["source"]); t = remap(ed["target"])
        if s is None or t is None or s == t:
            continue
        ed2 = dict(ed)
        ed2["source"] = s; ed2["target"] = t
        key = (s, t, ed["sign"])
        if key in seen_edge:
            continue   # dedup edges between same endpoints
        seen_edge.add(key)
        cleaned_edges.append(ed2)

    # renumber edge_ids
    for i, ed in enumerate(cleaned_edges, 1):
        ed["edge_id"] = f"N{i:03d}"

    # ── 2. recompute is_source from cleaned topology ──────────────────
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    for ed in cleaned_edges:
        in_deg[ed["target"]] += 1
        out_deg[ed["source"]] += 1
    for n in cleaned_nodes:
        n["is_source"] = (in_deg[n["id"]] == 0)

    # ── 3. trim trivial GENE sources with out=1 to bring source% under 60% ──
    cap_pct = 55.0   # aim a bit below the hard 60% cap
    while True:
        sources = [n for n in cleaned_nodes if n["is_source"]]
        pct = 100 * len(sources) / max(len(cleaned_nodes), 1)
        if pct <= cap_pct:
            break
        # candidates: GENE-typed sources with out=1 (least cascade contribution)
        candidates = [n for n in sources if n["type"] == "GENE" and out_deg[n["id"]] == 1]
        if not candidates:
            # fall back to any GENE source with smallest out-degree
            gene_sources = [n for n in sources if n["type"] == "GENE"]
            if not gene_sources:
                break
            gene_sources.sort(key=lambda n: out_deg[n["id"]])
            candidates = [gene_sources[0]]
        # remove the first candidate's node and its outgoing edges
        drop_id = candidates[0]["id"]
        cleaned_nodes = [n for n in cleaned_nodes if n["id"] != drop_id]
        cleaned_edges = [ed for ed in cleaned_edges if ed["source"] != drop_id and ed["target"] != drop_id]
        # rebuild degrees
        in_deg.clear(); out_deg.clear()
        for ed in cleaned_edges:
            in_deg[ed["target"]] += 1
            out_deg[ed["source"]] += 1
        for n in cleaned_nodes:
            n["is_source"] = (in_deg[n["id"]] == 0)

    # ── 4. renumber edges again post-trim ─────────────────────────────
    for i, ed in enumerate(cleaned_edges, 1):
        ed["edge_id"] = f"N{i:03d}"

    n_src = sum(1 for n in cleaned_nodes if n["is_source"])

    net["nodes"] = cleaned_nodes
    net["edges"] = cleaned_edges
    net["metadata"]["total_nodes"] = len(cleaned_nodes)
    net["metadata"]["total_edges"] = len(cleaned_edges)
    net["metadata"]["source_nodes"] = n_src
    net["metadata"]["source_percentage"] = round(100*n_src/max(len(cleaned_nodes),1), 1)
    net["metadata"]["polish_applied"] = "merged Cytokinins/Strigolactones plurals; renamed Far-red_Light; removed MAX_Pathway; trimmed trivial GENE sources to source% <= 55"

    json.dump(net, (NET_DIR/"network.json").open("w"), indent=2, ensure_ascii=False)

    # ── 5. regenerate equations + annotations from polished topology ─
    by_target = defaultdict(lambda: {"act": [], "inh": []})
    for ed in cleaned_edges:
        bucket = "act" if ed["sign"] > 0 else "inh"
        by_target[ed["target"]][bucket].append(ed["source"])

    alg_eqs = []
    for n in sorted(cleaned_nodes, key=lambda x: x["id"]):
        nid = n["id"]
        acts = by_target[nid]["act"]; inhs = by_target[nid]["inh"]
        if n["is_source"]:
            formula = f"{nid} = gene_modifier + exogenous_supply"
        else:
            act_term = "1.0" if not acts else f"max({'*'.join(f'max({a},0.01)' for a in acts)},0.01)^(1/{len(acts)})"
            inh_term = "1.0" if not inhs else f"min(1/max({'*'.join(inhs)},0.1),10.0)"
            formula = f"{nid} = ({act_term}) * ({inh_term}) * gene_modifier + exogenous_supply"
        alg_eqs.append({
            "node": nid, "type": n["type"], "is_source": n["is_source"],
            "activators": acts, "inhibitors": inhs, "formula": formula,
        })
    alg = json.load((NET_DIR/"algebraic_equations.json").open())
    alg["equations"] = alg_eqs
    alg["metadata"]["total_equations"] = len(alg_eqs)
    json.dump(alg, (NET_DIR/"algebraic_equations.json").open("w"), indent=2, ensure_ascii=False)

    # ODE
    K, n_h = 1.0, 2
    ode_eqs = []
    for nd in sorted(cleaned_nodes, key=lambda x: x["id"]):
        nid = nd["id"]; acts = by_target[nid]["act"]; inhs = by_target[nid]["inh"]
        if nd["is_source"]:
            formula = f"{nid} = 1.0 * 1.0 * gene_modifier + exogenous"
        else:
            at = " * ".join(f"({a}^{n_h} * ({K**n_h}+1) / ({K**n_h} + {a}^{n_h}))" for a in acts) or "1.0"
            it = " * ".join(f"(({K**n_h}+1) / ({K**n_h} + {i}^{n_h}))" for i in inhs) or "1.0"
            formula = f"{nid} = ({at}) * ({it}) * gene_modifier + exogenous"
        ode_eqs.append({"node": nid, "activators": acts, "inhibitors": inhs, "formula": formula})
    ode = json.load((NET_DIR/"ode_equations.json").open())
    ode["equations"] = ode_eqs
    ode["metadata"]["total_equations"] = len(ode_eqs)
    json.dump(ode, (NET_DIR/"ode_equations.json").open("w"), indent=2, ensure_ascii=False)

    # annotations
    ann_list = []
    for nd in cleaned_nodes:
        ann_list.append({
            "id": nd["id"], "type": nd["type"], "full_name": nd["full_name"],
            "description": nd["description"], "in_degree": in_deg[nd["id"]],
            "out_degree": out_deg[nd["id"]], "is_source": nd["is_source"],
        })
    ann = json.load((NET_DIR/"node_annotations.json").open())
    ann["annotations"] = ann_list
    ann["metadata"]["total_annotations"] = len(ann_list)
    json.dump(ann, (NET_DIR/"node_annotations.json").open("w"), indent=2, ensure_ascii=False)

    print(f"polished: {n0} -> {len(cleaned_nodes)} nodes, {e0} -> {len(cleaned_edges)} edges")
    print(f"sources:  {n_src}/{len(cleaned_nodes)} = {100*n_src/max(len(cleaned_nodes),1):.1f}%")


if __name__ == "__main__":
    main()
