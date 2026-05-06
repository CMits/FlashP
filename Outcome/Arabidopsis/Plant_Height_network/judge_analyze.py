"""
Judge analysis helper for Plant_Height network iteration 1.

Runs:
  - rejected-edge set difference (curated - network)
  - per-node coverage ratios (with composite-node alias expansion)
  - per-node inputs/outputs in the network
  - per-pathway inventory
Does NOT read perturbation or validation files.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
NET = json.load(open(ROOT / "network" / "network.json", encoding="utf-8"))
CUR = json.load(open(ROOT / "data" / "curated_edges.json", encoding="utf-8"))

# ------------------------------------------------------------------
# Composite expansion: map curated-node -> network-node
#   e.g. RGA, GAI, RGL1, RGL2 -> DELLA
# ------------------------------------------------------------------
ALIAS = {
    # DELLA composite
    "RGA": "DELLA", "GAI": "DELLA", "RGL1": "DELLA", "RGL2": "DELLA", "DELLA": "DELLA",
    # GID1 composite
    "GID1A": "GID1", "GID1B": "GID1", "GID1C": "GID1",
    # PIF composite
    "PIF4": "PIF4_5_7", "PIF5": "PIF4_5_7", "PIF7": "PIF4_5_7",
    # BZR/BES composite
    "BZR1": "BZR_BES", "BES1": "BZR_BES",
    # ARF composite
    "ARF6": "ARF6_7_8", "ARF7": "ARF6_7_8", "ARF8": "ARF6_7_8",
    # GA biosynthesis composites
    "GA20ox1": "GA20OX", "GA20ox2": "GA20OX", "GA20ox3": "GA20OX",
    "GA3ox1": "GA3OX", "GA3ox2": "GA3OX",
    "GA2ox1": "GA2OX", "GA2ox2": "GA2OX",
    # BR biosynthesis composite
    "DWF4": "BR_SYN", "DET2": "BR_SYN", "CPD": "BR_SYN", "CYP85A1": "BR_SYN",
    # Auxin biosynthesis composite
    "YUC8": "YUC_TAA", "TAA1": "YUC_TAA",
    # IPT composite
    "IPT3": "IPT", "IPT5": "IPT", "IPT7": "IPT",
    # Ethylene biosynthesis composite
    "ACS": "ACS_ACO", "ACO": "ACS_ACO",
    # Renamed nodes
    "phyB": "PHYB", "SnRK2": "SNRK2",
    # ---- Iteration-2 additions ----
    # Autonomous pathway composite
    "FCA": "AUT_SYN", "FPA": "AUT_SYN", "FLD": "AUT_SYN", "FVE": "AUT_SYN",
    "LD": "AUT_SYN", "FY": "AUT_SYN",
    # PRC2 composite
    "VRN2": "PRC2", "CLF": "PRC2", "SWN": "PRC2", "FIE": "PRC2",
    # AP2_TOE composite
    "AP2": "AP2_TOE", "TOE1": "AP2_TOE", "TOE2": "AP2_TOE",
    "SMZ": "AP2_TOE", "SNZ": "AP2_TOE", "TOE3": "AP2_TOE",
    # Evening Complex composite
    "ELF3": "EC", "ELF4": "EC", "LUX": "EC",
    # SL biosynthesis composite
    "D27": "SL_SYN", "MAX1": "SL_SYN", "MAX3": "SL_SYN", "MAX4": "SL_SYN",
    # Flowering integrators composite
    "SOC1": "FLOWER_INT", "LFY": "FLOWER_INT", "AP1": "FLOWER_INT",
    # MIR172B maps to miR172 (REGULATORY_RNA)
    "MIR172B": "miR172",
    # Iteration 3 additions
    "phyA": "PHYA",
    "COOLAIR": "lncCOOLAIR",
    # Hormones / envs already same
    "Gibberellin": "Gibberellin", "Brassinosteroid": "Brassinosteroid",
    "Auxin": "Auxin", "Cytokinin": "Cytokinin", "Ethylene": "Ethylene",
    "ABA": "ABA", "Strigolactone": "Strigolactone",
}

def alias(name):
    return ALIAS.get(name, name)  # else keep as-is

# ------------------------------------------------------------------
# Network side
# ------------------------------------------------------------------
net_nodes = {n["id"] for n in NET["nodes"]}
net_edges = NET["edges"]
net_out = defaultdict(list)
net_in = defaultdict(list)
for e in net_edges:
    net_out[e["source"]].append((e["target"], e["sign"]))
    net_in[e["target"]].append((e["source"], e["sign"]))

# ------------------------------------------------------------------
# Curated side, re-aliased into the network namespace
# ------------------------------------------------------------------
cur_edges = CUR["edges"]
# For counting coverage we alias curated endpoints so composites get credit.
# Intra-composite edges (e.g. RGA → GAI, both map to DELLA) get flagged but
# we still count them on the DELLA bucket.
cur_counts_total = defaultdict(int)      # curated total edges per ORIGINAL node
cur_counts_comp  = defaultdict(int)      # curated edges per ALIASED node (composite view)

# Per-(src,tgt) lookup
def canon(src, tgt):
    return (alias(src), alias(tgt))

in_net_pairs = {(e["source"], e["target"]) for e in net_edges}

covered_by_network = []
uncovered = []

for e in cur_edges:
    s, t = e["source"], e["target"]
    cs, ct = alias(s), alias(t)
    cur_counts_total[s] += 1
    cur_counts_total[t] += 1
    # composite view counts (may double-count self-collapsed edges)
    if cs != ct:  # skip intra-composite edges
        cur_counts_comp[cs] += 1
        cur_counts_comp[ct] += 1
    # is it represented in the network?
    if (cs, ct) in in_net_pairs:
        covered_by_network.append(e)
    else:
        uncovered.append(e)

# Network counts per node
net_counts = defaultdict(int)
for e in net_edges:
    net_counts[e["source"]] += 1
    net_counts[e["target"]] += 1

# ------------------------------------------------------------------
# Coverage ratio per node (composite-aware)
# ------------------------------------------------------------------
coverage_rows = []
for node in net_nodes:
    cur = cur_counts_comp.get(node, cur_counts_total.get(node, 0))
    net = net_counts.get(node, 0)
    ratio = (net / cur) if cur > 0 else None
    coverage_rows.append({"node": node, "curated": cur, "network": net, "ratio": ratio})

coverage_rows.sort(key=lambda r: (r["curated"] == 0, -(r["curated"] or 0)))

# ------------------------------------------------------------------
# Print summary (for the Judge to reason from)
# ------------------------------------------------------------------
print("=" * 72)
print("NETWORK SUMMARY")
print("=" * 72)
print(f"nodes={len(NET['nodes'])}  edges={len(net_edges)}")

print("\n" + "=" * 72)
print("COVERAGE RATIOS (composite-aware)")
print(f"{'node':25s} {'cur':>5s} {'net':>5s} {'ratio':>7s}")
print("=" * 72)
for row in coverage_rows:
    r = row["ratio"]
    rstr = f"{r:.2f}" if r is not None else "  - "
    print(f"{row['node']:25s} {row['curated']:5d} {row['network']:5d} {rstr:>7s}")

print("\n" + "=" * 72)
print("KEY PLAYER FLAGS (curated>=5, ratio<0.30)")
print("=" * 72)
for row in coverage_rows:
    if (row["curated"] >= 5
        and row["ratio"] is not None
        and row["ratio"] < 0.30):
        print(f"  FLAG: {row['node']:20s} curated={row['curated']} network={row['network']} ratio={row['ratio']:.2f}")

print("\n" + "=" * 72)
print("REJECTED CURATED EDGES (grouped by aliased endpoints)")
print("=" * 72)
print(f"Total curated edges: {len(cur_edges)}")
print(f"Covered (pair in network): {len(covered_by_network)}")
print(f"Uncovered: {len(uncovered)}")

# Which uncovered edges involve endpoints that ARE in the network?
relevant = [e for e in uncovered
            if alias(e["source"]) in net_nodes or alias(e["target"]) in net_nodes]
print(f"Uncovered but endpoints intersect network: {len(relevant)}")

# Breakdown by target (aliased) for uncovered
by_tgt = defaultdict(list)
for e in relevant:
    by_tgt[alias(e["target"])].append(e)

print("\nTop targets of rejected edges (aliased to network namespace):")
tgt_items = sorted(by_tgt.items(), key=lambda kv: -len(kv[1]))
for tgt, elist in tgt_items[:20]:
    if tgt in net_nodes:
        print(f"\n  TARGET in network: {tgt} ({len(elist)} rejected edges)")
        for e in elist:
            src = e["source"]
            print(f"      {e['edge_id']:6s}  {src} -> {e['target']} "
                  f"(sign={e['sign']}, alias: {alias(src)})")
    else:
        print(f"\n  TARGET NOT in network: {tgt} ({len(elist)} rejected edges) "
              f"[candidates for ignoring]")

# ------------------------------------------------------------------
# Dump per-node audit skeleton (inputs/outputs) for Judge writeup
# ------------------------------------------------------------------
print("\n" + "=" * 72)
print("PER-NODE INPUTS/OUTPUTS (network)")
print("=" * 72)
for n in NET["nodes"]:
    nid = n["id"]
    ins = net_in.get(nid, [])
    outs = net_out.get(nid, [])
    ins_str = ",".join(f"{s}{'+' if sg==1 else '-'}" for s, sg in ins) or "(source)"
    outs_str = ",".join(f"{t}{'+' if sg==1 else '-'}" for t, sg in outs) or "(leaf)"
    print(f"{nid:25s} IN  [{ins_str}]")
    print(f"{'':25s} OUT [{outs_str}]")

# Save as machine-readable
analysis = {
    "coverage_rows": coverage_rows,
    "key_player_flags": [r for r in coverage_rows
                         if r["curated"] >= 5 and r["ratio"] is not None
                         and r["ratio"] < 0.30],
    "rejected_edges_by_target": {
        tgt: [{"edge_id": e["edge_id"],
               "source": e["source"], "target": e["target"],
               "sign": e["sign"], "mechanism": e.get("mechanism", "")}
              for e in elist]
        for tgt, elist in by_tgt.items()
    },
    "n_covered": len(covered_by_network),
    "n_uncovered": len(uncovered),
    "n_relevant_uncovered": len(relevant),
}
with open(ROOT / "judge_analysis.json", "w", encoding="utf-8") as f:
    json.dump(analysis, f, indent=2)
print(f"\nAnalysis saved to judge_analysis.json")
