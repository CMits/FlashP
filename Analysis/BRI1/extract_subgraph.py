"""Extract a gene-centric subgraph from a merged FLASH-P network JSON.

BFS forward from the seed gene up to --forward-hops hops, stopping at PHENOTYPE
nodes so cascades terminate cleanly at the trait. Optionally include --backward-hops
of upstream regulators for context (e.g. Gibberellin -> DELLA).

Emits four Cytoscape-ready artefacts matching the bri1_subgraph_old format:
  {prefix}.sif                  source \t (activates|inhibits) \t target
  {prefix}.graphml              GraphML (keys: type/label/full_name; sign/interaction)
  {prefix}_node_attrs.txt       node_id \t node_type \t full_name \t is_phenotype \t is_source \t source_networks
  {prefix}_edge_attrs.txt       source \t target \t sign \t effect \t mechanism \t doi

Usage:
  python extract_subgraph.py --network <network.json> --gene DELLA --out <prefix>
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import xml.etree.ElementTree as ET


def load_network(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_adj(edges: list[dict]):
    fwd: dict[str, list[tuple[str, dict]]] = collections.defaultdict(list)
    bwd: dict[str, list[tuple[str, dict]]] = collections.defaultdict(list)
    for e in edges:
        fwd[e["source"]].append((e["target"], e))
        bwd[e["target"]].append((e["source"], e))
    return fwd, bwd


def bfs(start: str, adj, max_hops: int, stop_nodes: set[str] | None = None):
    """BFS up to max_hops; do not expand past stop_nodes (they are still included)."""
    visited = {start: 0}
    queue = collections.deque([(start, 0)])
    edges_kept: list[dict] = []
    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        if stop_nodes and node in stop_nodes and node != start:
            continue
        for neighbor, edge in adj.get(node, []):
            edges_kept.append(edge)
            if neighbor not in visited:
                visited[neighbor] = depth + 1
                queue.append((neighbor, depth + 1))
    return visited, edges_kept


def shortest_path_subgraph(start: str, targets: set[str], fwd, max_hops: int):
    """Return nodes/edges on any shortest path from start to each reachable target in targets.

    Uses BFS from start to compute layer distances, then backtracks layer-by-layer
    from each target collecting every edge that lies on a shortest path.
    """
    dist = {start: 0}
    parents: dict[str, list[tuple[str, dict]]] = collections.defaultdict(list)
    queue = collections.deque([start])
    while queue:
        node = queue.popleft()
        if dist[node] >= max_hops:
            continue
        for neighbor, edge in fwd.get(node, []):
            nd = dist[node] + 1
            if neighbor not in dist:
                dist[neighbor] = nd
                parents[neighbor].append((node, edge))
                queue.append(neighbor)
            elif dist[neighbor] == nd:
                parents[neighbor].append((node, edge))
    kept_nodes: set[str] = {start}
    kept_edges: list[dict] = []
    seen_edges: set[tuple] = set()
    stack = [t for t in targets if t in dist]
    while stack:
        node = stack.pop()
        if node in kept_nodes:
            continue
        kept_nodes.add(node)
        for parent, edge in parents.get(node, []):
            key = (edge["source"], edge["target"], edge.get("edge_id", ""))
            if key not in seen_edges:
                seen_edges.add(key)
                kept_edges.append(edge)
            if parent not in kept_nodes:
                stack.append(parent)
    return kept_nodes, kept_edges


def edge_relation(sign) -> str:
    try:
        return "activates" if int(sign) == 1 else "inhibits"
    except (TypeError, ValueError):
        return "activates"


def edge_sign_label(sign) -> str:
    try:
        return "positive" if int(sign) == 1 else "negative"
    except (TypeError, ValueError):
        return "positive"


def first_doi(edge: dict) -> str:
    ev = edge.get("evidence")
    if isinstance(ev, list) and ev:
        item = ev[0]
        if isinstance(item, dict) and item.get("doi"):
            return item["doi"]
    if edge.get("pmid"):
        return f"PMID:{edge['pmid']}"
    return ""


def write_sif(path: str, edges: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for e in edges:
            f.write(f"{e['source']}\t{edge_relation(e.get('sign'))}\t{e['target']}\n")


def write_node_attrs(path: str, node_ids: list[str], node_index: dict[str, dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("node_id\tnode_type\tfull_name\tis_phenotype\tis_source\tsource_networks\n")
        for nid in node_ids:
            n = node_index.get(nid, {"id": nid})
            full = (n.get("full_name") or nid).replace("\t", " ").replace("\n", " ")
            is_pheno = "TRUE" if n.get("type") == "PHENOTYPE" else "FALSE"
            is_source = "TRUE" if n.get("is_source") else "FALSE"
            src_nets = ";".join(n.get("source_networks") or [])
            f.write(f"{nid}\t{n.get('type','')}\t{full}\t{is_pheno}\t{is_source}\t{src_nets}\n")


def write_edge_attrs(path: str, edges: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("source\ttarget\tsign\teffect\tmechanism\tdoi\n")
        for e in edges:
            mech = (e.get("mechanism") or "").replace("\t", " ").replace("\n", " ")
            if len(mech) > 300:
                mech = mech[:297] + "..."
            f.write(
                f"{e['source']}\t{e['target']}\t{e.get('sign','')}\t"
                f"{e.get('effect','')}\t{mech}\t{first_doi(e)}\n"
            )


def write_graphml(path: str, node_ids: list[str], edges: list[dict], node_index: dict[str, dict]) -> None:
    NS = "http://graphml.graphdrawing.org/graphml"
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}graphml")
    root.set(
        "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
        f"{NS} http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd",
    )
    for key_id, kind, kind_for in [
        ("type", "string", "node"),
        ("label", "string", "node"),
        ("full_name", "string", "node"),
        ("sign", "string", "edge"),
        ("interaction", "string", "edge"),
    ]:
        k = ET.SubElement(root, f"{{{NS}}}key")
        k.set("id", key_id)
        k.set("for", kind_for)
        k.set("attr.name", key_id)
        k.set("attr.type", kind)
    graph = ET.SubElement(root, f"{{{NS}}}graph")
    graph.set("id", "G")
    graph.set("edgedefault", "directed")
    for nid in node_ids:
        n = node_index.get(nid, {"id": nid})
        node_el = ET.SubElement(graph, f"{{{NS}}}node")
        node_el.set("id", nid)
        ET.SubElement(node_el, f"{{{NS}}}data", {"key": "type"}).text = n.get("type", "")
        ET.SubElement(node_el, f"{{{NS}}}data", {"key": "label"}).text = nid
        ET.SubElement(node_el, f"{{{NS}}}data", {"key": "full_name"}).text = n.get("full_name") or nid
    for i, e in enumerate(edges, start=1):
        edge_el = ET.SubElement(graph, f"{{{NS}}}edge")
        edge_el.set("id", f"e{i}")
        edge_el.set("source", e["source"])
        edge_el.set("target", e["target"])
        ET.SubElement(edge_el, f"{{{NS}}}data", {"key": "sign"}).text = edge_sign_label(e.get("sign"))
        ET.SubElement(edge_el, f"{{{NS}}}data", {"key": "interaction"}).text = edge_relation(e.get("sign"))
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    with open(path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--network", required=True, help="path to merged network.json")
    ap.add_argument("--gene", required=True, help="seed gene/node id")
    ap.add_argument("--out", required=True, help="output prefix (no extension)")
    ap.add_argument("--forward-hops", type=int, default=3)
    ap.add_argument("--backward-hops", type=int, default=1)
    ap.add_argument(
        "--mode",
        choices=("bfs", "paths"),
        default="bfs",
        help="bfs = expand all edges within forward-hops; paths = keep only shortest-path-to-phenotype edges (cleaner figure).",
    )
    args = ap.parse_args()

    net = load_network(args.network)
    fwd, bwd = build_adj(net["edges"])
    node_index = {n["id"]: n for n in net["nodes"]}

    if args.gene not in node_index:
        print(f"ERROR: gene {args.gene!r} not found in {args.network}.", file=sys.stderr)
        hits = sorted(nid for nid in node_index if args.gene.lower() in nid.lower())
        if hits:
            print("Similar node ids:", ", ".join(hits[:10]), file=sys.stderr)
        return 1

    phenotype_nodes = {nid for nid, n in node_index.items() if n.get("type") == "PHENOTYPE"}

    if args.mode == "paths":
        fwd_nodes, fwd_edges = shortest_path_subgraph(args.gene, phenotype_nodes, fwd, args.forward_hops)
    else:
        fwd_visited, fwd_edges = bfs(args.gene, fwd, args.forward_hops, stop_nodes=phenotype_nodes)
        fwd_nodes = set(fwd_visited)
    bwd_visited, bwd_edges = bfs(args.gene, bwd, args.backward_hops, stop_nodes=None)

    kept_nodes = fwd_nodes | set(bwd_visited)

    seen: set[tuple] = set()
    ordered_edges: list[dict] = []
    for e in fwd_edges + bwd_edges:
        if e["source"] not in kept_nodes or e["target"] not in kept_nodes:
            continue
        key = (e["source"], e["target"], e.get("edge_id", ""))
        if key in seen:
            continue
        seen.add(key)
        ordered_edges.append(e)

    ordered_nodes = sorted(kept_nodes)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    write_sif(args.out + ".sif", ordered_edges)
    write_node_attrs(args.out + "_node_attrs.txt", ordered_nodes, node_index)
    write_edge_attrs(args.out + "_edge_attrs.txt", ordered_edges)
    write_graphml(args.out + ".graphml", ordered_nodes, ordered_edges, node_index)

    reachable_phenotypes = sorted(nid for nid in kept_nodes if nid in phenotype_nodes)
    print(
        f"[{args.gene}] wrote {len(ordered_nodes)} nodes, {len(ordered_edges)} edges "
        f"-> {args.out}.(sif|graphml|_node_attrs.txt|_edge_attrs.txt)"
    )
    print(f"  reachable phenotypes ({len(reachable_phenotypes)}): {', '.join(reachable_phenotypes) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
