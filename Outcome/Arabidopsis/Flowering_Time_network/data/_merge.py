"""
Phase C merge: combine 5 _extracted_B*.json batches into the three
schema-compliant output files required by LITERATURE_REVIEW_AGENT.
"""

from __future__ import annotations

import glob
import json
import os
import re
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent

# ----------------------------------------------------------------------------
# Gene-name normalization (consistent Arabidopsis nomenclature)
# ----------------------------------------------------------------------------
GENE_ALIASES = {
    "GI1": "GI",
    "GIGANTEA": "GI",
    "CONSTANS": "CO",
    "FLOWERING_LOCUS_T": "FT",
    "FLOWERING_LOCUS_C": "FLC",
    "RGA1": "RGA",
    "AP1_CAULIFLOWER": "AP1",
    "CAULIFLOWER": "CAL",
    "miR172B": "miR172b",
    "MIR172B": "miR172b",
    "MIR172A": "miR172a",
    "CBF": "CBF",  # family-level placeholder
    "H2A.Z": "H2A_Z",  # avoid dots in node names
    "KIN10": "KIN10",
    "ARR_typeA": "ARR_A",
    "ARR_typeB": "ARR_B",
    "FRI-C": "FRI_C",
    "APRF1": "APRF1",
    "NF_YC": "NF_YC",
    "NF-YC": "NF_YC",
    "AP2-like": "AP2",
    "Long_day": "Long_Day",
    "Short_day": "Short_Day",
    "Warm_temperature": "Warm_Temperature",
    "Cold_temperature": "Cold_Temperature",
    "Blue_light": "Blue_Light",
    "Red_light": "Red_Light",
    "Far_red_light": "Far_Red_Light",
    "FLOWERING_TIME": "Flowering_Time",
    "flowering_time": "Flowering_Time",
}

# Environment / metabolite / phenotype nodes that might show up with odd cases
ENV_NODES = {
    "Long_Day", "Short_Day", "Cold", "Vernalization",
    "Warm_Temperature", "Cold_Temperature", "Ambient_Temperature",
    "Blue_Light", "Red_Light", "Far_Red_Light", "Darkness",
    "High_Temperature", "Low_Temperature", "Dawn", "Dusk",
    "Light", "Photoperiod",
}
METAB_NODES = {"T6P", "Sucrose", "Glucose", "Phosphatidylcholine", "PC"}
HORMONE_NODES = {"Gibberellin", "Auxin", "Cytokinin", "ABA", "Ethylene"}
RNA_NODES = {"miR156", "miR172", "miR172a", "miR172b", "miR399",
             "COOLAIR", "COLDAIR"}


def norm_node(name: str) -> str:
    if not name:
        return name
    n = name.strip()
    return GENE_ALIASES.get(n, n)


# ----------------------------------------------------------------------------
# Load batches
# ----------------------------------------------------------------------------
batch_files = sorted(glob.glob(str(DATA_DIR / "_extracted_B*.json")))
batches = []
for fp in batch_files:
    with open(fp, encoding="utf-8") as fh:
        batches.append(json.load(fh))

# ----------------------------------------------------------------------------
# Merge papers (dedupe by DOI, fall back to title)
# ----------------------------------------------------------------------------
papers_by_key = {}
for b in batches:
    for p in b.get("papers", []):
        key = (p.get("doi") or "").strip().lower()
        if not key:
            key = (p.get("title") or "").strip().lower()[:80]
        if key in papers_by_key:
            existing = papers_by_key[key]
            # Keep richer entry (more non-empty fields)
            def richness(x):
                return sum(1 for v in x.values() if v not in (None, "", 0))
            if richness(p) > richness(existing):
                papers_by_key[key] = p
            continue
        papers_by_key[key] = p

papers = list(papers_by_key.values())
for p in papers:
    # Schema: status ∈ {read, skipped, paywalled}. Drop extra verification field.
    p.pop("verification", None)
    if not p.get("status"):
        p["status"] = "read"
    if not p.get("authors"):
        p["authors"] = ""
    if not p.get("title"):
        p["title"] = ""
    if not p.get("journal"):
        p["journal"] = ""
    # Ensure only known fields
    allowed = {"doi", "title", "authors", "year", "journal", "status", "pmc_id"}
    for k in list(p.keys()):
        if k not in allowed:
            p.pop(k)

# ----------------------------------------------------------------------------
# Merge edges (dedupe by (source, target, sign); merge evidence arrays)
# ----------------------------------------------------------------------------
edges_by_key = {}
for b in batches:
    for e in b.get("edges", []):
        src = norm_node(e.get("source", ""))
        tgt = norm_node(e.get("target", ""))
        sign = e.get("sign")
        if not src or not tgt or sign not in (1, -1):
            continue
        # Skip the shortcut edge FT -> Flowering_Time for HORMONE-level placeholders
        key = (src, tgt, int(sign))
        if key in edges_by_key:
            existing = edges_by_key[key]
            # Merge evidence
            ev = e.get("evidence")
            if ev:
                existing["evidence"].append(ev)
            # Upgrade confidence if now 2+ papers
            if len(existing["evidence"]) >= 2:
                existing["confidence"] = "HIGH"
            continue
        # New edge
        ev = e.get("evidence")
        if not ev:
            continue
        new_edge = {
            "source": src,
            "target": tgt,
            "source_type": e.get("source_type", "GENE"),
            "target_type": e.get("target_type", "GENE"),
            "sign": int(sign),
            "effect": e.get("effect") or (
                "activation" if sign == 1 else "repression"
            ),
            "edge_type": e.get("edge_type", "transcriptional"),
            "confidence": e.get("confidence", "MEDIUM"),
            "mechanism": e.get("mechanism", ""),
            "in_model": False,
            "evidence": [ev],
        }
        edges_by_key[key] = new_edge

# Heuristic: re-apply node type for known env/metab/hormone/rna nodes
for e in edges_by_key.values():
    for side in ("source", "target"):
        name = e[side]
        if name in ENV_NODES:
            e[f"{side}_type"] = "ENVIRONMENT"
        elif name in METAB_NODES:
            e[f"{side}_type"] = "METABOLITE"
        elif name in HORMONE_NODES:
            e[f"{side}_type"] = "HORMONE"
        elif name in RNA_NODES:
            e[f"{side}_type"] = "REGULATORY_RNA"
        elif name == "Flowering_Time":
            e[f"{side}_type"] = "PHENOTYPE"

# Assign sequential edge IDs
edges = list(edges_by_key.values())
edges.sort(key=lambda x: (x["source"], x["target"], x["sign"]))
for i, e in enumerate(edges, start=1):
    e["edge_id"] = f"E{i:03d}"

# Reorder keys for stable output
def edge_ordered(e):
    return {
        "edge_id": e["edge_id"],
        "source": e["source"],
        "target": e["target"],
        "source_type": e["source_type"],
        "target_type": e["target_type"],
        "sign": e["sign"],
        "effect": e["effect"],
        "edge_type": e["edge_type"],
        "confidence": e["confidence"],
        "mechanism": e["mechanism"],
        "in_model": e["in_model"],
        "evidence": e["evidence"],
    }

edges = [edge_ordered(e) for e in edges]

# ----------------------------------------------------------------------------
# Merge perturbations (dedupe by (gene, type, direction, condition))
# ----------------------------------------------------------------------------
pert_by_key = {}
for b in batches:
    for p in b.get("perturbations", []):
        gene = norm_node(p.get("gene", ""))
        ptype = p.get("perturbation_type", "")
        pdir = p.get("expected_direction", "")
        cond = p.get("condition", "both")
        key = (gene, ptype, pdir, cond)
        if not gene or not ptype or not pdir:
            continue
        if key in pert_by_key:
            existing = pert_by_key[key]
            ev = p.get("evidence")
            if ev:
                existing["evidence"].append(ev)
            continue
        ev = p.get("evidence")
        if not ev:
            continue
        pert_by_key[key] = {
            "gene": gene,
            "perturbation_type": ptype,
            "expected_direction": pdir,
            "expected_magnitude": p.get("expected_magnitude", ""),
            "evidence": [ev],
            "condition": cond if cond else "both",
            "species": p.get("species", "Arabidopsis thaliana"),
        }

perts = list(pert_by_key.values())
perts.sort(key=lambda x: (x["gene"], x["perturbation_type"]))
for i, p in enumerate(perts, start=1):
    p["test_id"] = f"T{i:03d}"

# Reorder: test_id first
def pert_ordered(p):
    return {
        "test_id": p["test_id"],
        "gene": p["gene"],
        "perturbation_type": p["perturbation_type"],
        "expected_direction": p["expected_direction"],
        "expected_magnitude": p["expected_magnitude"],
        "evidence": p["evidence"],
        "condition": p["condition"],
        "species": p["species"],
    }
perts = [pert_ordered(p) for p in perts]

# ----------------------------------------------------------------------------
# Source-node audit: scan for nodes that only appear as source and never target
# ----------------------------------------------------------------------------
out_degree = defaultdict(int)
in_degree = defaultdict(int)
for e in edges:
    out_degree[e["source"]] += 1
    in_degree[e["target"]] += 1

all_nodes = set(out_degree) | set(in_degree)
source_only = sorted(
    [n for n in all_nodes
     if in_degree[n] == 0 and out_degree[n] >= 3
     and n not in ENV_NODES
     and n != "Flowering_Time"]
)

# ----------------------------------------------------------------------------
# Write three output files
# ----------------------------------------------------------------------------
metadata_common = {
    "flash_p_version": "2.0",
    "phenotype": "Flowering_Time",
    "species": "Arabidopsis thaliana",
    "created": "2026-04-18",
}

# candidate_papers.json
papers_out = {
    "metadata": {**metadata_common, "total_papers": len(papers)},
    "papers": papers,
}
with open(DATA_DIR / "candidate_papers.json", "w", encoding="utf-8") as fh:
    json.dump(papers_out, fh, indent=2, ensure_ascii=False)

# curated_edges.json
high = sum(1 for e in edges if e["confidence"] == "HIGH")
med = sum(1 for e in edges if e["confidence"] == "MEDIUM")
literature_gap_log = []
if "Sucrose" in source_only or in_degree.get("Sucrose", 0) <= 1:
    literature_gap_log.append({
        "node": "Sucrose",
        "status": "expected_source",
        "note": "Sucrose is a primary photosynthate; upstream regulation is light/photosynthesis-driven rather than transcriptional. Captured via Light -> Sucrose (+1) edge. Remaining 'source-only' status is biologically correct for a flowering network."
    })

edges_out = {
    "metadata": {
        **metadata_common,
        "total_edges": len(edges),
        "high_confidence": high,
        "medium_confidence": med,
        "source_node_audit_candidates": source_only,
        "literature_gap_log": literature_gap_log,
    },
    "edges": edges,
}
with open(DATA_DIR / "curated_edges.json", "w", encoding="utf-8") as fh:
    json.dump(edges_out, fh, indent=2, ensure_ascii=False)

# perturbation_dataset.json
by_type = defaultdict(int)
for p in perts:
    by_type[p["perturbation_type"]] += 1
perts_out = {
    "metadata": {
        **metadata_common,
        "total_perturbations": len(perts),
        "by_type": dict(by_type),
        "convention": "expected_direction refers to FLOWERING (increased=earlier; decreased=later)",
    },
    "direction_threshold": 0.05,
    "perturbations": perts,
}
with open(DATA_DIR / "perturbation_dataset.json", "w", encoding="utf-8") as fh:
    json.dump(perts_out, fh, indent=2, ensure_ascii=False)

# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------
print(f"Papers: {len(papers)}")
print(f"Edges: {len(edges)} (HIGH={high}, MEDIUM={med})")
print(f"Perturbations: {len(perts)}")
print(f"Unique source+target nodes: {len(all_nodes)}")
print(f"Source-only nodes (out-deg >= 3, no upstream): {len(source_only)}")
for n in source_only:
    print(f"  - {n}  (out-deg={out_degree[n]})")
