"""Merge LITERATURE REVIEW JUDGE additions into Step 1 outputs.

APPEND-ONLY: never delete, never renumber existing IDs.
- New papers: status='added_by_judge', discovered_by='literature_judge'.
- New edges: get next sequential edge_id starting at max(Step 1 IDs)+1.
- New tests: get next sequential test_id starting at max(Step 1 IDs)+1.
- Edge dedup: (source, target, sign) — append evidence to existing.
- Perturbation dedup: (gene, perturbation_type, condition) — skip if exact match.
- Paper dedup: by DOI — append additional evidence is not relevant for papers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent
TODAY = "2026-04-19"


def normalize_perturbation_type(value: str) -> str:
    if not value:
        return "knockout"
    norm = value.strip().lower().replace(" ", "_").replace("-", "_")
    mapping = {
        "ko": "knockout",
        "loss_of_function": "knockout",
        "kd": "knockdown",
        "oe": "overexpression",
        "double_mutant": "double_knockout",
        "triple_mutant": "triple_knockout",
        "quadruple_mutant": "quadruple_knockout",
        "quintuple_mutant": "quintuple_knockout",
        "exogenous_treatment": "exogenous_treatment",
        "chemical_treatment": "chemical_treatment",
        "treatment": "treatment",
        "rescue": "rescue",
    }
    return mapping.get(norm, norm)


def normalize_direction(value: str) -> str:
    norm = (value or "unchanged").strip().lower()
    if norm.startswith("incre") or norm in ("longer", "elongated"):
        return "increased"
    if norm.startswith("decre") or norm in ("shorter", "shortened", "short"):
        return "decreased"
    return "unchanged"


# ---------------------------------------------------------------------------
# Load existing files
# ---------------------------------------------------------------------------

with (DATA_DIR / "candidate_papers.json").open(encoding="utf-8") as f:
    papers_data = json.load(f)
with (DATA_DIR / "curated_edges.json").open(encoding="utf-8") as f:
    edges_data = json.load(f)
with (DATA_DIR / "perturbation_dataset.json").open(encoding="utf-8") as f:
    perts_data = json.load(f)
with (DATA_DIR / "_judge_additions.json").open(encoding="utf-8") as f:
    judge_data = json.load(f)

print(f"Step 1 baseline: {len(papers_data['papers'])} papers, {len(edges_data['edges'])} edges, {len(perts_data['perturbations'])} tests", file=sys.stderr)

# Find max existing IDs
max_edge_id = max(int(e["edge_id"][1:]) for e in edges_data["edges"])
max_test_id = max(int(p["test_id"][1:]) for p in perts_data["perturbations"])
print(f"Step 1 max IDs: edge=E{max_edge_id:03d}, test=T{max_test_id:03d}", file=sys.stderr)

# Build dedup indices
existing_dois = {p["doi"]: p for p in papers_data["papers"]}
existing_edges = {(e["source"], e["target"], int(e["sign"])): e for e in edges_data["edges"]}
existing_perts = {(p["gene"], p["perturbation_type"], p.get("condition", "both")): p for p in perts_data["perturbations"]}


# Index judge papers by DOI for evidence lookup
judge_paper_meta = {p["doi"]: p for p in judge_data["papers"]}

# ---------------------------------------------------------------------------
# Process new papers (append, mark as added_by_judge)
# ---------------------------------------------------------------------------
papers_added = 0
for p in judge_data["papers"]:
    doi = p["doi"]
    if doi in existing_dois:
        # Already in Step 1 candidate_papers, just bump status to read with provenance tag
        existing = existing_dois[doi]
        if existing.get("status") == "candidate":
            existing["status"] = "read"
            existing["pmc_id"] = p.get("pmc_id") or existing.get("pmc_id")
        continue
    new_paper = {
        "doi": doi,
        "title": p["title"],
        "authors": p.get("authors", ""),
        "year": p.get("year"),
        "journal": p.get("journal", ""),
        "status": "added_by_judge",
        "pmc_id": p.get("pmc_id"),
    }
    papers_data["papers"].append(new_paper)
    existing_dois[doi] = new_paper
    papers_added += 1


# ---------------------------------------------------------------------------
# Process new edges (append with sequential IDs starting at max_edge_id+1)
# ---------------------------------------------------------------------------
next_edge_num = max_edge_id + 1
edges_added = 0
edges_evidence_appended = 0
for e in judge_data["edges"]:
    key = (e["source"].strip(), e["target"].strip(), int(e["sign"]))
    meta = judge_paper_meta.get(e.get("evidence_doi"), {})
    evidence_entry = {
        "doi": e.get("evidence_doi", ""),
        "title": meta.get("title", ""),
        "authors": meta.get("authors", ""),
        "year": meta.get("year"),
        "journal": meta.get("journal", ""),
        "evidence_sentence": e.get("evidence_sentence", ""),
        "claim": e.get("mechanism", ""),
        "verification": "full_text_read",
        "full_text_read": True,
    }
    if key in existing_edges:
        existing = existing_edges[key]
        ex_keys = {(ev["doi"], ev["evidence_sentence"]) for ev in existing["evidence"]}
        ev_key = (evidence_entry["doi"], evidence_entry["evidence_sentence"])
        if ev_key not in ex_keys:
            existing["evidence"].append(evidence_entry)
            edges_evidence_appended += 1
            if len(existing["evidence"]) >= 2:
                existing["confidence"] = "HIGH"
    else:
        new_edge = {
            "edge_id": f"E{next_edge_num:03d}",
            "source": e["source"].strip(),
            "target": e["target"].strip(),
            "source_type": e.get("source_type", "GENE"),
            "target_type": e.get("target_type", "GENE"),
            "sign": int(e["sign"]),
            "effect": e.get("effect", "activation").lower(),
            "edge_type": e.get("edge_type", ""),
            "confidence": e.get("confidence", "MEDIUM"),
            "mechanism": e.get("mechanism", ""),
            "in_model": False,
            "evidence": [evidence_entry],
            "discovery_source": "literature_judge",
            "gap_addressed": e.get("gap_addressed", ""),
        }
        edges_data["edges"].append(new_edge)
        existing_edges[key] = new_edge
        next_edge_num += 1
        edges_added += 1


# ---------------------------------------------------------------------------
# Process new perturbations
# ---------------------------------------------------------------------------
next_test_num = max_test_id + 1
tests_added = 0
for p in judge_data["perturbations"]:
    pert_type = normalize_perturbation_type(p["perturbation_type"])
    cond = p.get("condition", "both")
    key = (p["gene"].strip(), pert_type, cond)
    if key in existing_perts:
        continue  # skip duplicate
    meta = judge_paper_meta.get(p.get("evidence_doi"), {})
    evidence_entry = {
        "doi": p.get("evidence_doi", ""),
        "title": meta.get("title", ""),
        "authors": meta.get("authors", ""),
        "year": meta.get("year"),
        "journal": meta.get("journal", ""),
        "evidence_sentence": p.get("evidence_sentence", ""),
        "claim": "",
        "verification": "full_text_read",
        "full_text_read": True,
    }
    new_pert = {
        "test_id": f"T{next_test_num:03d}",
        "gene": p["gene"].strip(),
        "perturbation_type": pert_type,
        "expected_direction": normalize_direction(p.get("expected_direction", "unchanged")),
        "expected_magnitude": p.get("expected_magnitude", ""),
        "evidence": [evidence_entry],
        "condition": cond,
        "species": "Arabidopsis thaliana",
        "discovery_source": "literature_judge",
        "gap_addressed": p.get("gap_addressed", ""),
    }
    perts_data["perturbations"].append(new_pert)
    existing_perts[key] = new_pert
    next_test_num += 1
    tests_added += 1


# ---------------------------------------------------------------------------
# Update metadata totals
# ---------------------------------------------------------------------------
papers_data["metadata"]["total_papers"] = len(papers_data["papers"])
papers_data["metadata"]["created"] = TODAY
papers_data["metadata"]["literature_judge_added"] = papers_added

edges_data["metadata"]["total_edges"] = len(edges_data["edges"])
edges_data["metadata"]["high_confidence"] = sum(1 for e in edges_data["edges"] if e.get("confidence") == "HIGH")
edges_data["metadata"]["medium_confidence"] = sum(1 for e in edges_data["edges"] if e.get("confidence") == "MEDIUM")
edges_data["metadata"]["created"] = TODAY
edges_data["metadata"]["literature_judge_added"] = edges_added
edges_data["metadata"]["literature_judge_evidence_appended"] = edges_evidence_appended

from collections import Counter
type_counts = Counter(p["perturbation_type"] for p in perts_data["perturbations"])
perts_data["metadata"]["total_perturbations"] = len(perts_data["perturbations"])
perts_data["metadata"]["by_type"] = dict(type_counts)
perts_data["metadata"]["created"] = TODAY
perts_data["metadata"]["literature_judge_added"] = tests_added


# ---------------------------------------------------------------------------
# Write back
# ---------------------------------------------------------------------------
with (DATA_DIR / "candidate_papers.json").open("w", encoding="utf-8") as f:
    json.dump(papers_data, f, indent=2, ensure_ascii=False)
with (DATA_DIR / "curated_edges.json").open("w", encoding="utf-8") as f:
    json.dump(edges_data, f, indent=2, ensure_ascii=False)
with (DATA_DIR / "perturbation_dataset.json").open("w", encoding="utf-8") as f:
    json.dump(perts_data, f, indent=2, ensure_ascii=False)

print(f"\n=== MERGE SUMMARY ===")
print(f"Papers added: {papers_added}")
print(f"Edges added: {edges_added}")
print(f"Edges with evidence appended (existing edge): {edges_evidence_appended}")
print(f"Perturbations added: {tests_added}")
print(f"\n=== FINAL TOTALS ===")
print(f"Papers: {len(papers_data['papers'])}")
print(f"Edges: {len(edges_data['edges'])} (HIGH={edges_data['metadata']['high_confidence']}, MEDIUM={edges_data['metadata']['medium_confidence']})")
print(f"Perturbations: {len(perts_data['perturbations'])}")
