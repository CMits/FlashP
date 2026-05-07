#!/usr/bin/env python3
"""Direct Ollama-API extractor: one paper at a time, JSON-mode, resumable.
Bypasses opencode entirely — no agent loop, no tool-call parsing, no session
state. Each paper is one HTTP call. Tolerates APSIM CPU pressure.

Usage:
    python3 extract_edges.py                  # process every remaining paper
    python3 extract_edges.py --model qwen2.5:72b   # try a different model
    python3 extract_edges.py --only Brewer    # only papers whose filename contains 'Brewer'
    python3 extract_edges.py --max 5          # process at most 5 (smoke test)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TEXT_DIR = ROOT.parent / "Shoot_Branching_papers" / "text"
OLLAMA_URL = "http://localhost:11434/api/generate"

PHENOTYPE = "shoot branching"
SPECIES = "Arabidopsis thaliana"

VALID_TYPES = {
    "GENE", "HORMONE", "METABOLITE", "ENVIRONMENT",
    "PROTEIN_COMPLEX", "REGULATORY_RNA", "PHENOTYPE", "PROCESS",
}
VALID_DIRECTIONS = {"increased", "decreased", "unchanged"}
VALID_PERT_TYPES = {"KO", "KD", "OE", "treatment"}
VALID_BASELINES = {"WT", "mutant"}

PROMPT = """You are a scientific literature curator extracting regulatory edges and perturbation experiments from a paper about shoot branching in Arabidopsis thaliana.

SOURCE PAPER (filename: {filename}):
=====
{paper_text}
=====

Extract from the paper above:
1. Paper metadata — DOI must be in the paper text (header / first page / references). Do NOT invent.
2. Regulatory edges — X regulates Y, with sign +1 (activates) or -1 (inhibits).
3. Perturbation experiments — mutants (KO/KD), overexpression (OE), or chemical treatments.

Return ONE JSON object with this EXACT shape (no surrounding text, no markdown):

{{
  "doi": "10.xxxx/...",
  "title": "Full paper title",
  "authors": ["Author A", "Author B"],
  "year": 2020,
  "journal": "Plant Cell",
  "edges": [
    {{
      "source": "BRC1",
      "target": "Shoot_Branching",
      "sign": -1,
      "source_type": "GENE",
      "target_type": "PHENOTYPE",
      "evidence_sentence": "EXACT verbatim quote from the paper text above",
      "claim": "BRC1 inhibits shoot branching"
    }}
  ],
  "perturbations": [
    {{
      "gene": "BRC1",
      "perturbation_type": "KO",
      "expected_direction": "increased",
      "comparison_baseline": "WT",
      "evidence_sentence": "exact quote"
    }}
  ]
}}

RULES:
- evidence_sentence MUST be an EXACT verbatim quote that appears in the paper text above.
- DOI must appear in the paper text. If absent, set "doi": null.
- Node naming: GENE = ALL_CAPS (BRC1, MAX2, D14); HORMONE / METABOLITE / ENVIRONMENT = Title_Case (Auxin, Sucrose, Decapitation, Light); PHENOTYPE = Title_Case (Shoot_Branching, Bud_Outgrowth, Tillering); PROTEIN_COMPLEX = CAPS (SMXL678, DELLA); REGULATORY_RNA = lowercase prefix (miR156).
- source_type / target_type: one of GENE, HORMONE, METABOLITE, ENVIRONMENT, PROTEIN_COMPLEX, REGULATORY_RNA, PHENOTYPE, PROCESS.
- sign MUST be integer 1 or -1 (NOT "positive"/"negative").
- perturbation_type: one of KO, KD, OE, treatment.
- expected_direction: one of "increased", "decreased", "unchanged" (referring to {phenotype}).
- comparison_baseline: one of "WT", "mutant".
- Aim for 3-10 edges and 1-5 perturbations per paper. Skip any claim you cannot quote verbatim.

Output ONLY the JSON object."""


def call_ollama(model: str, prompt: str, num_ctx: int = 32768, temperature: float = 0.3, timeout: int = 600) -> str:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
        },
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return resp.get("response", "")


def load_master() -> tuple[dict, dict, dict]:
    p = json.load((DATA / "candidate_papers.json").open())
    e = json.load((DATA / "curated_edges.json").open())
    pt = json.load((DATA / "perturbation_dataset.json").open())
    return p, e, pt


def save_master(p: dict, e: dict, pt: dict) -> None:
    # atomic-ish: write to .tmp then rename
    for fn, d in [("candidate_papers.json", p), ("curated_edges.json", e), ("perturbation_dataset.json", pt)]:
        tmp = DATA / (fn + ".tmp")
        json.dump(d, tmp.open("w"), indent=2, ensure_ascii=False)
        tmp.replace(DATA / fn)


def already_done_dois(p: dict) -> set:
    return {pp.get("doi") for pp in p.get("papers", []) if pp.get("doi")}


def already_done_filenames(p: dict) -> set:
    return {pp.get("source_file") for pp in p.get("papers", []) if pp.get("source_file")}


def next_id(items: list, prefix: str, key: str) -> int:
    n = 0
    for it in items:
        v = it.get(key, "")
        if isinstance(v, str) and v.startswith(prefix):
            try:
                n = max(n, int(v[len(prefix):]))
            except ValueError:
                pass
    return n + 1


def normalize_authors(a) -> list:
    if isinstance(a, str):
        # split on commas, " and ", " & "
        for sep in [" and ", " & ", ";"]:
            a = a.replace(sep, ",")
        return [s.strip() for s in a.split(",") if s.strip()]
    if isinstance(a, list):
        return [str(s).strip() for s in a if str(s).strip()]
    return []


def validate_extracted(extracted: dict) -> tuple[list, list, str]:
    """Drop edges/perturbations that don't validate. Return (clean_edges, clean_perts, warning_summary)."""
    warnings = []
    edges = []
    for ed in extracted.get("edges", []) or []:
        if not isinstance(ed, dict):
            continue
        sign = ed.get("sign")
        if sign in (1, -1, "1", "-1"):
            ed["sign"] = int(sign)
        else:
            warnings.append(f"bad sign {sign!r}")
            continue
        if ed.get("source_type") not in VALID_TYPES:
            ed["source_type"] = "GENE"
        if ed.get("target_type") not in VALID_TYPES:
            ed["target_type"] = "GENE"
        if not (ed.get("source") and ed.get("target") and (ed.get("evidence_sentence") or "").strip()):
            continue
        edges.append(ed)

    perts = []
    for t in extracted.get("perturbations", []) or []:
        if not isinstance(t, dict):
            continue
        if t.get("perturbation_type") not in VALID_PERT_TYPES:
            t["perturbation_type"] = "KO"
        if t.get("expected_direction") not in VALID_DIRECTIONS:
            t["expected_direction"] = "increased"
        if t.get("comparison_baseline") not in VALID_BASELINES:
            t["comparison_baseline"] = "WT"
        if not (t.get("gene") and (t.get("evidence_sentence") or "").strip()):
            continue
        perts.append(t)
    return edges, perts, "; ".join(warnings) if warnings else ""


def append_to_master(p: dict, e: dict, pt: dict, extracted: dict, filename: str) -> tuple[int, int]:
    edges, perts, _w = validate_extracted(extracted)

    # paper entry
    next_pid = next_id(p["papers"], "P", "paper_id")
    paper_entry = {
        "paper_id": f"P{next_pid:03d}",
        "doi": extracted.get("doi"),
        "title": extracted.get("title", ""),
        "authors": normalize_authors(extracted.get("authors")),
        "year": extracted.get("year"),
        "journal": extracted.get("journal", ""),
        "status": "read",
        "source_file": filename,
    }
    p["papers"].append(paper_entry)

    # build flat evidence template from paper metadata
    def flat_evidence(quote: str, claim: str = "") -> dict:
        return {
            "doi": paper_entry["doi"],
            "title": paper_entry["title"],
            "authors": paper_entry["authors"],
            "year": paper_entry["year"],
            "journal": paper_entry["journal"],
            "evidence_sentence": quote,
            "claim": claim,
            "verification": "full_text_read",
            "full_text_read": True,
        }

    # edges
    next_eid = next_id(e["edges"], "E", "edge_id")
    for ed in edges:
        e["edges"].append({
            "edge_id": f"E{next_eid:03d}",
            "source": ed["source"],
            "target": ed["target"],
            "sign": ed["sign"],
            "source_type": ed["source_type"],
            "target_type": ed["target_type"],
            "in_model": False,
            "evidence": flat_evidence(ed["evidence_sentence"], ed.get("claim", "")),
        })
        next_eid += 1

    # perturbations
    next_tid = next_id(pt["perturbations"], "T", "test_id")
    for t in perts:
        pt["perturbations"].append({
            "test_id": f"T{next_tid:03d}",
            "gene": t["gene"],
            "perturbation_type": t["perturbation_type"],
            "expected_direction": t["expected_direction"],
            "comparison_baseline": t["comparison_baseline"],
            "evidence": flat_evidence(t["evidence_sentence"]),
        })
        next_tid += 1

    return len(edges), len(perts)


def truncate_paper(text: str, max_chars: int = 180_000) -> str:
    """Cap paper size to keep prompt under ~50K tokens. Most papers fit."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated ...]\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--only", default=None, help="only process papers whose filename contains this substring")
    ap.add_argument("--max", type=int, default=None, help="max papers to process this run")
    ap.add_argument("--num-ctx", type=int, default=32768)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--sleep-on-fail", type=float, default=10.0)
    args = ap.parse_args()

    if not TEXT_DIR.exists():
        print(f"FATAL: {TEXT_DIR} not found", file=sys.stderr); sys.exit(2)

    txt_files = sorted(TEXT_DIR.glob("*.txt"))
    if not txt_files:
        print(f"FATAL: no .txt files in {TEXT_DIR}", file=sys.stderr); sys.exit(2)

    p, e, pt = load_master()
    done_files = already_done_filenames(p)
    done_dois = already_done_dois(p)

    queue = []
    for fp in txt_files:
        if fp.name in done_files:
            continue
        if args.only and args.only.lower() not in fp.name.lower():
            continue
        queue.append(fp)
    if args.max:
        queue = queue[:args.max]

    print(f"papers in text dir: {len(txt_files)}")
    print(f"already done (matched by source_file): {sum(1 for f in txt_files if f.name in done_files)}")
    print(f"already done (matched by DOI): {len(done_dois)} DOIs")
    print(f"queue this run: {len(queue)}")
    print(f"model: {args.model}, num_ctx: {args.num_ctx}\n")
    if not queue:
        print("Nothing to do.")
        return

    failed = []
    for i, fp in enumerate(queue, 1):
        t0 = time.time()
        paper_text = truncate_paper(fp.read_text(errors="replace"))
        prompt = PROMPT.format(filename=fp.name, paper_text=paper_text, phenotype=PHENOTYPE)

        last_err = None
        extracted = None
        for attempt in range(args.retries + 1):
            try:
                resp = call_ollama(args.model, prompt, num_ctx=args.num_ctx)
                extracted = json.loads(resp)
                break
            except json.JSONDecodeError as ex:
                last_err = f"JSON parse: {ex}"
            except urllib.error.URLError as ex:
                last_err = f"HTTP: {ex}"
            except Exception as ex:
                last_err = f"{type(ex).__name__}: {ex}"
            time.sleep(args.sleep_on_fail)

        dt = time.time() - t0
        if extracted is None:
            print(f"[{i:3d}/{len(queue)}] FAIL  {fp.name:55s} ({dt:5.0f}s) — {last_err}")
            failed.append((fp.name, last_err))
            continue

        # skip if doi already present (same paper extracted earlier under different filename)
        if extracted.get("doi") and extracted["doi"] in done_dois:
            print(f"[{i:3d}/{len(queue)}] dup   {fp.name:55s} ({dt:5.0f}s) — DOI already done")
            continue

        ne, np_ = append_to_master(p, e, pt, extracted, fp.name)
        if extracted.get("doi"):
            done_dois.add(extracted["doi"])
        save_master(p, e, pt)
        print(f"[{i:3d}/{len(queue)}] ok    {fp.name:55s} ({dt:5.0f}s) — {ne} edges, {np_} perts")

    print(f"\nrun complete. processed={len(queue)-len(failed)}, failed={len(failed)}")
    if failed:
        print("failed papers:")
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
