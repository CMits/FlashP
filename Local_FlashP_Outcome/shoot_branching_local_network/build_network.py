#!/usr/bin/env python3
"""Step 2 — BUILDER: read curated_edges.json, ask Gemma which edges go into the
network model + how to type each node, then deterministically generate
network.json + algebraic_equations.json + ode_equations.json + node_annotations.json.

Strategy: Gemma's job is biological judgment (edge selection + node typing).
Equation generation is fixed math — done in Python, no LLM needed.

Run:
    python3 build_network.py
"""
from __future__ import annotations
import json, sys, time, urllib.request, re, argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NETWORK = ROOT / "network"
NETWORK.mkdir(exist_ok=True)
OLLAMA_URL = "http://localhost:11434/api/generate"

PHENOTYPE = "shoot_branching"
SPECIES = "Arabidopsis thaliana"

VALID_TYPES = {
    "GENE", "HORMONE", "METABOLITE", "ENVIRONMENT",
    "PROTEIN_COMPLEX", "REGULATORY_RNA", "PHENOTYPE", "PROCESS",
}

PROMPT = """You are a systems biologist building a mechanistic signaling network for the trait "shoot branching" in Arabidopsis thaliana.

Below are {n_edges} regulatory edges from the literature. Each line is:
  edge_id  source  -[sign]->  target   doi   |   short claim

EDGES:
{edge_list}

YOUR TASK:
Select a SUBSET of these edges (target ~70-90 edges, ~30-40 nodes) that forms a coherent multi-step CASCADE ending in a single PHENOTYPE node. The cascade must have DEPTH — most genes should reach the phenotype through 3-5 sequential edges, NOT a direct shortcut.

MANDATORY CANONICAL CASCADE (every one of these nodes MUST appear, in this exact topology):
   Strigolactone -> D14 -> SMXL678 (D14+MAX2 degrade SMXL678; encode as MAX2 -| SMXL678 and D14 -| SMXL678)
   SMXL678 -| BRC1
   Auxin -> MAX3, MAX4 (SL biosynthesis)
   MAX3, MAX4 -> Carlactone -> MAX1 -> Strigolactone (or direct: MAX1/3/4 -> Strigolactone)
   BRC1 -| Shoot_Branching
   Cytokinin -| BRC1 (CK promotes branching by inhibiting BRC1)
   Auxin -| Cytokinin (auxin inhibits CK biosynthesis/transport)
   Sucrose -| MAX2 or Sucrose -| BRC1 (carbon-driven branching)
   Decapitation -| Auxin (canonical apical-dominance experiment)

DIRECT-TO-PHENOTYPE EDGES — STRICT LIMIT:
   Allow direct "X -> Shoot_Branching" or "X -| Shoot_Branching" only for at most 5 hub nodes total. The default for other regulators must be to terminate at BRC1 (or another mid-cascade node), letting BRC1 carry the signal to the phenotype. Reject "RGA -| Shoot_Branching", "ABI5 -> Shoot_Branching", etc. — those should go through BRC1 (e.g., RGA -> BRC1).

CRITICAL RULES:
1. NO FLOATING NODES — every node in your selection must reach the phenotype via a directed path. If a node cannot reach the phenotype, drop it.
2. Pick ONE phenotype node ("Shoot_Branching"). All cascades must terminate there.
3. Source nodes (no upstream regulators) should be 30-50% of total nodes, hard cap 60%. ENVIRONMENT nodes (Decapitation, Light, Photoperiod), unregulated hormones, and constitutive regulators may be sources. Internal genes like MAX2, D14, SMXL678 must NOT be sources — they have upstream regulation in the canonical cascade above.
4. Include the canonical core: BRC1, MAX1, MAX2, MAX3, MAX4, D14, SMXL678, Auxin, Strigolactone, Cytokinin, Sucrose. Include peripheral regulators only if their full cascade closes (TB1/TCP18, BA1, HB21/HB40/HB53, FT, miR156/SPL, ABA/ABI5, GA/DELLA, PIN1, T6P, IPT/CKX).
5. Avoid duplicate edges (same source/target) — keep the highest-confidence one.
6. Use SINGULAR canonical names (HORMONE = Strigolactone NOT Strigolactones; Cytokinin NOT Cytokinins).

NODE TYPE RULES:
- GENE: ALL_CAPS short names (BRC1, MAX2, D14, ABI5)
- HORMONE: Title_Case (Auxin, Cytokinin, Strigolactone, Gibberellin, ABA)
- METABOLITE: Title_Case (Sucrose, T6P, Carlactone)
- ENVIRONMENT: Title_Case (Decapitation, Light, Nitrogen, Photoperiod)
- PROTEIN_COMPLEX: CAPS_underscore (SMXL678, DELLA)
- REGULATORY_RNA: lowercase prefix (miR156)
- PHENOTYPE: Title_Case (Shoot_Branching, Bud_Outgrowth)

Return ONE JSON object with this EXACT shape (no surrounding text, no markdown fences):

{{
  "phenotype_node": "Shoot_Branching",
  "biology_prose": "3-4 sentences describing the signaling story — which hormones drive branching, how SL/D14/MAX2/SMXL678/BRC1 cascade closes, what auxin/CK do, and how decapitation releases buds",
  "selected_edge_ids": ["E001", "E007", "E012", ...],
  "node_types": {{
    "BRC1": "GENE",
    "Auxin": "HORMONE",
    "Decapitation": "ENVIRONMENT",
    "Shoot_Branching": "PHENOTYPE"
  }}
}}

Output ONLY the JSON object."""


def compact_edges_for_prompt(edges: list) -> str:
    lines = []
    for ed in edges:
        ev = ed.get("evidence", {})
        doi = ev.get("doi", "?")
        claim = (ed.get("evidence", {}).get("claim", "") or "").strip()[:80]
        lines.append(
            f"  {ed['edge_id']}  {ed['source']:25s} -[{ed['sign']:+d}]-> {ed['target']:25s}  {doi:30s} | {claim}"
        )
    return "\n".join(lines)


def call_ollama(model: str, prompt: str, num_ctx: int = 65536, timeout: int = 1800) -> str:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": num_ctx},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    print(f"calling Ollama (model={model}, num_ctx={num_ctx}, timeout={timeout}s) ...", flush=True)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    print(f"  Ollama returned in {time.time()-t0:.1f}s", flush=True)
    return resp.get("response", "")


def build_network_json(curated, selected_ids, phenotype_node, node_types) -> dict:
    sel = {ed["edge_id"]: ed for ed in curated["edges"] if ed["edge_id"] in selected_ids}

    # Collect nodes from selected edges
    referenced = set()
    for ed in sel.values():
        referenced.add(ed["source"])
        referenced.add(ed["target"])

    # Figure out is_source from incoming edges in selection
    incoming = defaultdict(int)
    for ed in sel.values():
        incoming[ed["target"]] += 1

    # Prune floating nodes: must reach phenotype via directed path
    adj = defaultdict(list)
    for ed in sel.values():
        adj[ed["source"]].append(ed["target"])

    # BFS backwards from phenotype to find reachable nodes
    reverse_adj = defaultdict(list)
    for src, targets in adj.items():
        for tgt in targets:
            reverse_adj[tgt].append(src)
    reachable = {phenotype_node}
    frontier = [phenotype_node]
    while frontier:
        new = []
        for n in frontier:
            for predecessor in reverse_adj.get(n, []):
                if predecessor not in reachable:
                    reachable.add(predecessor)
                    new.append(predecessor)
        frontier = new

    # Filter edges to ones with both endpoints reachable
    final_edges = []
    next_nid = 1
    for eid in sorted(sel.keys()):
        ed = sel[eid]
        if ed["source"] in reachable and ed["target"] in reachable:
            evidence = ed.get("evidence", {})
            final_edges.append({
                "edge_id": f"N{next_nid:03d}",
                "source": ed["source"],
                "target": ed["target"],
                "sign": ed["sign"],
                "effect": "activation" if ed["sign"] > 0 else "inhibition",
                "mechanism": evidence.get("claim", "") or f"{ed['source']} regulates {ed['target']}",
                "evidence": [evidence] if evidence else [],
            })
            next_nid += 1

    # Build node list
    in_final = set()
    for ed in final_edges:
        in_final.add(ed["source"])
        in_final.add(ed["target"])

    incoming_final = defaultdict(int)
    for ed in final_edges:
        incoming_final[ed["target"]] += 1

    nodes = []
    for nid in sorted(in_final):
        ntype = node_types.get(nid, "GENE")
        if ntype not in VALID_TYPES:
            ntype = "GENE"
        if nid == phenotype_node:
            ntype = "PHENOTYPE"
        nodes.append({
            "id": nid,
            "type": ntype,
            "full_name": nid.replace("_", " "),
            "description": f"{ntype.lower().replace('_',' ')} {nid}",
            "is_source": incoming_final[nid] == 0,
        })

    n_source = sum(1 for n in nodes if n["is_source"])
    src_pct = round(100 * n_source / max(len(nodes), 1), 1)

    return {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": PHENOTYPE,
            "phenotype_node": phenotype_node,
            "species": SPECIES,
            "created": "2026-05-03",
            "iteration": 1,
            "curated_edges_source": f"{len(curated['edges'])}-edge repository",
            "total_nodes": len(nodes),
            "total_edges": len(final_edges),
            "source_nodes": n_source,
            "source_percentage": src_pct,
            "builder_model": "gemma4:31b (local)",
        },
        "nodes": nodes,
        "edges": final_edges,
    }


def build_algebraic_eqs(net: dict) -> dict:
    eqs = []
    by_target = defaultdict(lambda: {"act": [], "inh": []})
    for ed in net["edges"]:
        bucket = "act" if ed["sign"] > 0 else "inh"
        by_target[ed["target"]][bucket].append(ed["source"])

    for n in sorted(net["nodes"], key=lambda x: x["id"]):
        nid = n["id"]
        is_src = n["is_source"]
        acts = by_target[nid]["act"]
        inhs = by_target[nid]["inh"]
        if is_src:
            formula = f"{nid} = gene_modifier + exogenous_supply"
        else:
            act_term = "1.0" if not acts else (
                f"max({'*'.join(f'max({a},0.01)' for a in acts)},0.01)^(1/{len(acts)})"
            )
            inh_term = "1.0" if not inhs else (
                f"min(1/max({'*'.join(inhs)},0.1),10.0)"
            )
            formula = f"{nid} = ({act_term}) * ({inh_term}) * gene_modifier + exogenous_supply"
        eqs.append({
            "node": nid,
            "type": n["type"],
            "is_source": is_src,
            "activators": acts,
            "inhibitors": inhs,
            "formula": formula,
        })
    return {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": PHENOTYPE,
            "phenotype_node": net["metadata"]["phenotype_node"],
            "species": SPECIES,
            "created": "2026-05-03",
            "iteration": 1,
            "total_equations": len(eqs),
        },
        "parameters": {
            "epsilon": 0.1, "K": 10.0, "activator_floor": 0.01, "damping": 0.7,
            "direction_threshold": 0.05, "max_iterations": 50, "convergence_tolerance": 0.0001,
        },
        "equations": eqs,
    }


def build_ode_eqs(net: dict) -> dict:
    eqs = []
    by_target = defaultdict(lambda: {"act": [], "inh": []})
    for ed in net["edges"]:
        bucket = "act" if ed["sign"] > 0 else "inh"
        by_target[ed["target"]][bucket].append(ed["source"])

    K, n = 1.0, 2
    for node in sorted(net["nodes"], key=lambda x: x["id"]):
        nid = node["id"]
        acts = by_target[nid]["act"]
        inhs = by_target[nid]["inh"]
        if node["is_source"]:
            formula = f"{nid} = 1.0 * 1.0 * gene_modifier + exogenous"
        else:
            act_terms = " * ".join(
                f"({a}^{n} * ({K**n}+1) / ({K**n} + {a}^{n}))" for a in acts
            ) or "1.0"
            inh_terms = " * ".join(
                f"(({K**n}+1) / ({K**n} + {i}^{n}))" for i in inhs
            ) or "1.0"
            formula = f"{nid} = ({act_terms}) * ({inh_terms}) * gene_modifier + exogenous"
        eqs.append({
            "node": nid,
            "activators": acts,
            "inhibitors": inhs,
            "formula": formula,
        })
    return {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": PHENOTYPE,
            "phenotype_node": net["metadata"]["phenotype_node"],
            "species": SPECIES,
            "created": "2026-05-03",
            "iteration": 1,
            "total_equations": len(eqs),
            "default_parameters": {"K": K, "n": n},
        },
        "equations": eqs,
    }


def build_node_annotations(net: dict) -> dict:
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    for ed in net["edges"]:
        out_deg[ed["source"]] += 1
        in_deg[ed["target"]] += 1
    annotations = []
    for n in net["nodes"]:
        annotations.append({
            "id": n["id"],
            "type": n["type"],
            "full_name": n["full_name"],
            "description": n["description"],
            "in_degree": in_deg[n["id"]],
            "out_degree": out_deg[n["id"]],
            "is_source": n["is_source"],
        })
    return {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": PHENOTYPE,
            "species": SPECIES,
            "created": "2026-05-03",
            "iteration": 1,
            "total_annotations": len(annotations),
        },
        "annotations": annotations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--num-ctx", type=int, default=131072)
    args = ap.parse_args()

    curated = json.load((DATA / "curated_edges.json").open())
    print(f"input: {len(curated['edges'])} curated edges from {DATA/'curated_edges.json'}")

    edge_list_str = compact_edges_for_prompt(curated["edges"])
    prompt = PROMPT.format(n_edges=len(curated["edges"]), edge_list=edge_list_str)
    print(f"prompt size: ~{len(prompt)//4} tokens (rough)")

    resp = call_ollama(args.model, prompt, num_ctx=args.num_ctx)
    selection = json.loads(resp)
    print(f"\nGemma selected {len(selection['selected_edge_ids'])} edges, phenotype_node={selection['phenotype_node']!r}, typed {len(selection['node_types'])} nodes")
    if selection.get("biology_prose"):
        print(f"\nbiology prose:\n  {selection['biology_prose'][:500]}\n")

    net = build_network_json(
        curated, set(selection["selected_edge_ids"]),
        selection["phenotype_node"], selection["node_types"]
    )
    alg = build_algebraic_eqs(net)
    ode = build_ode_eqs(net)
    ann = build_node_annotations(net)

    # Save Gemma's raw output for traceability
    (NETWORK / "_builder_gemma_selection.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False))

    json.dump(net, (NETWORK / "network.json").open("w"), indent=2, ensure_ascii=False)
    json.dump(alg, (NETWORK / "algebraic_equations.json").open("w"), indent=2, ensure_ascii=False)
    json.dump(ode, (NETWORK / "ode_equations.json").open("w"), indent=2, ensure_ascii=False)
    json.dump(ann, (NETWORK / "node_annotations.json").open("w"), indent=2, ensure_ascii=False)

    print(f"\nwrote:")
    print(f"  network/network.json              {len(net['nodes'])} nodes, {len(net['edges'])} edges, source%={net['metadata']['source_percentage']}")
    print(f"  network/algebraic_equations.json  {len(alg['equations'])} equations")
    print(f"  network/ode_equations.json        {len(ode['equations'])} equations")
    print(f"  network/node_annotations.json     {len(ann['annotations'])} annotations")


if __name__ == "__main__":
    main()
