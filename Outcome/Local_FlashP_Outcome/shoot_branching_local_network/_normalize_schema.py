#!/usr/bin/env python3
"""Wrap Gemma's bare-list output in the proper {metadata, items} envelope and
add missing fields (paper_id, source_type/target_type, gene/perturbation_type).
Re-runnable; idempotent."""
import json, sys, os, re

BASE = os.path.dirname(os.path.abspath(__file__)) + "/data"
META = {
    "flash_p_version": "2.0",
    "phenotype": "shoot branching",
    "species": "Arabidopsis thaliana",
    "created": "2026-05-02",
}

NODE_TYPE_GUESSES = {
    # genes (ALL_CAPS)
    "BRC1":"GENE","MAX1":"GENE","MAX2":"GENE","MAX3":"GENE","MAX4":"GENE",
    "D14":"GENE","D27":"GENE","D53":"GENE","D3":"GENE","D17":"GENE","D10":"GENE",
    "TB1":"GENE","TCP18":"GENE","HB21":"GENE","HB40":"GENE","HB53":"GENE",
    "ABI3":"GENE","ABI4":"GENE","ABI5":"GENE","ABF":"GENE","ABA":"HORMONE",
    "PIN1":"GENE","PIN3":"GENE","PIN4":"GENE","PIN7":"GENE",
    "TIR1":"GENE","AFB":"GENE","IAA":"HORMONE","ARF":"GENE","TPL":"GENE",
    "FT":"GENE","FUL":"GENE","SOC1":"GENE","FLC":"GENE",
    "AXR":"GENE","BES1":"GENE","BZR1":"GENE","DLF1":"GENE",
    "SMXL6":"GENE","SMXL7":"GENE","SMXL8":"GENE","SMXL678":"PROTEIN_COMPLEX",
    "SPL":"GENE","SPL9":"GENE","SPL15":"GENE","miR156":"REGULATORY_RNA",
    "RGA":"GENE","DELLA":"PROTEIN_COMPLEX","GID1":"GENE",
    "ABCG14":"GENE","CKX":"GENE","IPT":"GENE","LOG":"GENE",
    "LBO":"GENE","CCD7":"GENE","CCD8":"GENE","KAI2":"GENE",
    "MOC1":"GENE","WRKY":"GENE","WRKY40":"GENE",
    "TPS1":"GENE","T6P":"METABOLITE","HXK1":"GENE",
    "TIE1":"GENE","TIE2":"GENE","BRC2":"GENE","BA1":"GENE",
    # hormones (Title_Case)
    "Auxin":"HORMONE","Cytokinin":"HORMONE","Strigolactone":"HORMONE",
    "Gibberellin":"HORMONE","ABA":"HORMONE","BR":"HORMONE","Brassinosteroid":"HORMONE",
    "Ethylene":"HORMONE","JA":"HORMONE","SA":"HORMONE",
    # metabolites
    "Sucrose":"METABOLITE","Glucose":"METABOLITE","Sugar":"METABOLITE",
    "Carlactone":"METABOLITE","Carlactonoic_Acid":"METABOLITE",
    "T6P":"METABOLITE","Trehalose":"METABOLITE",
    # environment
    "Light":"ENVIRONMENT","Decapitation":"ENVIRONMENT","Nitrogen":"ENVIRONMENT",
    "Phosphate":"ENVIRONMENT","Temperature":"ENVIRONMENT","Photoperiod":"ENVIRONMENT",
    # phenotype
    "Shoot_Branching":"PHENOTYPE","Bud_Outgrowth":"PHENOTYPE","Tillering":"PHENOTYPE",
    "Branching":"PHENOTYPE","Axillary_Bud_Growth":"PHENOTYPE",
}

def guess_type(name: str) -> str:
    if not name: return "GENE"
    if name in NODE_TYPE_GUESSES: return NODE_TYPE_GUESSES[name]
    # heuristic
    if name.lower().startswith("mir") or name.startswith("mi"): return "REGULATORY_RNA"
    if "_branching" in name.lower() or "_outgrowth" in name.lower(): return "PHENOTYPE"
    if name == name.upper() and "_" not in name and len(name) <= 8: return "GENE"
    if name == name.title(): return "HORMONE"
    return "GENE"

def parse_perturbation(text: str):
    """split 'brc1 KO' or 'max2 mutant + GR24' etc. into (gene, type)."""
    if not text: return ("UNKNOWN", "KO")
    t = text.strip()
    m = re.match(r"([A-Za-z][A-Za-z0-9_]+)\s+(KO|KD|OE|knockout|knockdown|overexpression|mutant|treatment)", t, re.I)
    if m:
        gene = m.group(1).upper()
        ptype = m.group(2).upper()
        if ptype.startswith("KNOCKOUT") or ptype == "MUTANT": ptype = "KO"
        elif ptype.startswith("KNOCKDOWN"): ptype = "KD"
        elif ptype.startswith("OVEREXPR"): ptype = "OE"
        elif ptype.startswith("TREAT"): ptype = "treatment"
        return (gene, ptype)
    # fallback
    parts = t.split()
    return (parts[0].upper() if parts else "UNKNOWN", "KO")

def normalize_papers():
    path = f"{BASE}/candidate_papers.json"
    d = json.load(open(path))
    if isinstance(d, dict) and "papers" in d:
        papers = d["papers"]
    elif isinstance(d, list):
        papers = d
    else:
        return
    for i, pp in enumerate(papers, start=1):
        if "paper_id" not in pp:
            pp["paper_id"] = f"P{i:03d}"
    out = {"metadata": META, "papers": papers}
    json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"papers: wrapped {len(papers)} entries with metadata+paper_ids")

def normalize_edges():
    path = f"{BASE}/curated_edges.json"
    d = json.load(open(path))
    edges = d["edges"] if isinstance(d, dict) and "edges" in d else d
    for i, ed in enumerate(edges, start=1):
        ed.setdefault("edge_id", f"E{i:03d}")
        ed.setdefault("source_type", guess_type(ed.get("source", "")))
        ed.setdefault("target_type", guess_type(ed.get("target", "")))
        ed.setdefault("in_model", False)
    out = {"metadata": META, "edges": edges}
    json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"edges:  wrapped {len(edges)} entries with metadata+source_type/target_type")

def normalize_perturbations():
    path = f"{BASE}/perturbation_dataset.json"
    d = json.load(open(path))
    items = d["perturbations"] if isinstance(d, dict) and "perturbations" in d else d
    for i, t in enumerate(items, start=1):
        t.setdefault("test_id", f"T{i:03d}")
        if "gene" not in t or "perturbation_type" not in t:
            raw = t.get("perturbation") or t.get("description") or ""
            gene, ptype = parse_perturbation(raw)
            t.setdefault("gene", gene)
            t.setdefault("perturbation_type", ptype)
        t.setdefault("comparison_baseline", "WT")
    out = {"metadata": META, "perturbations": items}
    json.dump(out, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"perts:  wrapped {len(items)} entries with metadata+gene/perturbation_type")

if __name__ == "__main__":
    normalize_papers()
    normalize_edges()
    normalize_perturbations()
