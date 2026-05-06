#!/usr/bin/env python3
"""
Extract the MAX2-KO propagation subgraph (13 nodes, 17 edges) from the current
Arabidopsis shoot branching network and emit Cytoscape-ready files:

    cytoscape/subgraph.graphml         (open directly in Cytoscape)
    cytoscape/subgraph.sif             (simple interaction format)
    cytoscape/node_attributes.tsv      (id, type, role, WT_value, KO_value, log2fc)
    cytoscape/edge_attributes.tsv      (source, interaction, target, sign, edge_id, label)
    data/subgraph_edges.csv            (mirror of edge attributes for the figure script)

The subgraph is the directed cone from MAX2 to Shoot_Branching that the figure
illustrates. Nodes / edges are picked from the current network.json — see plan
file for the rationale on which dropped/added vs the old 12-node module.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
NET_DIR = REPO / "Arabidopsis" / "Shoot_Branching_network" / "network"
NETWORK_JSON = NET_DIR / "network.json"

WT_KO_JSON = ROOT / "data" / "max2_ko_steady_state.json"
ALGEBRAIC_JSON = NET_DIR / "algebraic_equations.json"

OUT_GRAPHML = ROOT / "cytoscape" / "subgraph.graphml"
OUT_SIF = ROOT / "cytoscape" / "subgraph.sif"
OUT_NODE_TSV = ROOT / "cytoscape" / "node_attributes.tsv"
OUT_EDGE_TSV = ROOT / "cytoscape" / "edge_attributes.tsv"
OUT_EDGE_CSV = ROOT / "data" / "subgraph_edges.csv"

SUBGRAPH_NODES = [
    "Strigolactone",
    "D14",
    "MAX2",
    "SMXL678",
    "BES1",
    "SPL9",
    "BRC1",
    "HB21",
    "NCED3",
    "ABA",
    "PIN1",
    "PIN3",
    "Shoot_Branching",
]

NODE_ROLE = {
    "Strigolactone": "input_hormone",
    "D14": "receptor",
    "MAX2": "perturbed_gene",
    "SMXL678": "primary_target",
    "BES1": "primary_target",
    "SPL9": "secondary_target",
    "BRC1": "central_repressor",
    "HB21": "downstream_TF",
    "NCED3": "biosynthesis_enzyme",
    "ABA": "downstream_hormone",
    "PIN1": "downstream_transporter",
    "PIN3": "downstream_transporter",
    "Shoot_Branching": "phenotype",
}

# Style XML (FLASH-P) maps node `type` to fill / shape / size. Remap any types
# the style does not recognise onto its known categories.
TYPE_FOR_STYLE = {
    "PROTEIN_COMPLEX": "GENE",
}


def style_type(node_type: str) -> str:
    return TYPE_FOR_STYLE.get(node_type, node_type)


def sign_str(sign: int) -> str:
    return "positive" if sign == 1 else "negative"


def main() -> int:
    network = json.loads(NETWORK_JSON.read_text(encoding="utf-8"))
    nodes_full = {n["id"]: n for n in network["nodes"]}
    missing = [n for n in SUBGRAPH_NODES if n not in nodes_full]
    if missing:
        print(f"ERROR: nodes missing from network.json: {missing}", file=sys.stderr)
        return 1

    sub_set = set(SUBGRAPH_NODES)
    sub_edges = [
        e for e in network["edges"]
        if e["source"] in sub_set and e["target"] in sub_set
    ]
    print(f"Subgraph: {len(SUBGRAPH_NODES)} nodes, {len(sub_edges)} edges")

    state = json.loads(WT_KO_JSON.read_text(encoding="utf-8"))
    wt_vals = state["wt"]
    ko_vals = state["ko_run"]
    import math

    def log2fc(wt: float, ko: float) -> float:
        return math.log2(max(ko, 1e-6) / max(wt, 1e-6))

    OUT_NODE_TSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_NODE_TSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([
            "id", "label", "type", "raw_type", "role",
            "WT_value", "KO_value", "log2fc", "is_phenotype",
        ])
        for nid in SUBGRAPH_NODES:
            n = nodes_full[nid]
            wt = wt_vals.get(nid, 1.0)
            ko = ko_vals.get(nid, 1.0)
            raw_t = n.get("type", "")
            w.writerow([
                nid,
                nid,
                style_type(raw_t),
                raw_t,
                NODE_ROLE.get(nid, ""),
                f"{wt:.6f}",
                f"{ko:.6f}",
                f"{log2fc(wt, ko):.4f}",
                "true" if nid == "Shoot_Branching" else "false",
            ])

    with open(OUT_EDGE_TSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([
            "source", "interaction", "target", "sign", "sign_int", "edge_id", "label",
        ])
        for e in sub_edges:
            interaction = "activates" if e["sign"] == 1 else "inhibits"
            w.writerow([
                e["source"], interaction, e["target"],
                sign_str(e["sign"]), e["sign"],
                e.get("edge_id", ""), f"{e['source']} {interaction} {e['target']}",
            ])

    with open(OUT_EDGE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "sign", "sign_int", "edge_id"])
        for e in sub_edges:
            w.writerow([
                e["source"], e["target"], sign_str(e["sign"]),
                e["sign"], e.get("edge_id", ""),
            ])

    with open(OUT_SIF, "w", encoding="utf-8") as f:
        for e in sub_edges:
            interaction = "activates" if e["sign"] == 1 else "inhibits"
            f.write(f"{e['source']}\t{interaction}\t{e['target']}\n")

    register_namespace("", "http://graphml.graphdrawing.org/xmlns")
    g = Element(
        "graphml",
        attrib={"xmlns": "http://graphml.graphdrawing.org/xmlns"},
    )
    keys = [
        ("d_label", "node", "label", "string"),
        ("d_type", "node", "type", "string"),
        ("d_rawtype", "node", "raw_type", "string"),
        ("d_role", "node", "role", "string"),
        ("d_wt", "node", "WT_value", "double"),
        ("d_ko", "node", "KO_value", "double"),
        ("d_lfc", "node", "log2fc", "double"),
        ("d_phen", "node", "is_phenotype", "string"),
        ("d_sign", "edge", "sign", "string"),
        ("d_signi", "edge", "sign_int", "int"),
        ("d_int", "edge", "interaction", "string"),
        ("d_eid", "edge", "edge_id", "string"),
    ]
    for kid, kfor, kname, ktype in keys:
        SubElement(g, "key", attrib={
            "id": kid, "for": kfor, "attr.name": kname, "attr.type": ktype,
        })
    graph = SubElement(g, "graph", attrib={"id": "MAX2_KO_subgraph", "edgedefault": "directed"})
    for nid in SUBGRAPH_NODES:
        n_el = SubElement(graph, "node", attrib={"id": nid})
        wt = wt_vals.get(nid, 1.0)
        ko = ko_vals.get(nid, 1.0)
        raw_t = nodes_full[nid].get("type", "")
        for kid, val in [
            ("d_label", nid),
            ("d_type", style_type(raw_t)),
            ("d_rawtype", raw_t),
            ("d_role", NODE_ROLE.get(nid, "")),
            ("d_wt", f"{wt:.6f}"),
            ("d_ko", f"{ko:.6f}"),
            ("d_lfc", f"{log2fc(wt, ko):.4f}"),
            ("d_phen", "true" if nid == "Shoot_Branching" else "false"),
        ]:
            d_el = SubElement(n_el, "data", attrib={"key": kid})
            d_el.text = str(val)
    for i, e in enumerate(sub_edges):
        e_el = SubElement(graph, "edge", attrib={
            "id": f"e{i}", "source": e["source"], "target": e["target"],
        })
        interaction = "activates" if e["sign"] == 1 else "inhibits"
        for kid, val in [
            ("d_sign", sign_str(e["sign"])),
            ("d_signi", str(e["sign"])),
            ("d_int", interaction),
            ("d_eid", e.get("edge_id", "")),
        ]:
            d_el = SubElement(e_el, "data", attrib={"key": kid})
            d_el.text = val
    tree = ElementTree(g)
    tree.write(OUT_GRAPHML, encoding="utf-8", xml_declaration=True)

    print(f"Wrote {OUT_GRAPHML}")
    print(f"Wrote {OUT_SIF}")
    print(f"Wrote {OUT_NODE_TSV}")
    print(f"Wrote {OUT_EDGE_TSV}")
    print(f"Wrote {OUT_EDGE_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
