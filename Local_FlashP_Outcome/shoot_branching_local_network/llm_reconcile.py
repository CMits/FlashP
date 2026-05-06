#!/usr/bin/env python3
"""LLM-driven Step 3 PERTURBATION reconciliation. Single Ollama call.

Lets qwen3 do the biological judgment:
  - ortholog mapping (rms3->D14, d3->MAX2, DAD1->D14, etc.)
  - composite redundancy (single smxl6 KO -> SMXL678 with modifier ~0.97)
  - rescue baselines (max2+GR24 -> baseline=mutant)
  - novel chemicals via mechanism inference
  - multi-gene perturbations (max2 max3 dKO -> both as separate entries)
"""
import argparse, json, time, urllib.request
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
DATA = ROOT/"data"; NET = ROOT/"network"
OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPT = """You are reconciling perturbation tests for the FLASH-P shoot-branching pipeline. You have:
- A 32-node mechanistic network for "shoot branching" in Arabidopsis thaliana.
- 175 perturbation tests extracted from the literature, each with a gene name and perturbation type.

Your job: for each test, decide whether it can be modeled in this network, and if so, how.

NETWORK NODES (id, type):
{nodes_list}

PERTURBATION TESTS:
{tests_list}

RECONCILIATION RULES (per FLASH-P PERTURBATION_AGENT.md):

1. ORTHOLOG MAPPING — many tests use orthologs from non-Arabidopsis species. Map them:
   - Pea: RMS3=D14, RMS4=MAX2, RMS1=MAX4, RMS5=MAX3, PsBRC1=BRC1
   - Rice: D3=MAX2, D14=D14, D10=MAX4, D17=MAX3, D27=D27, D53=SMXL678 family, FC1=BRC1
   - Petunia: DAD1=D14, DAD2=KAI2, PhCCD7=MAX3, PhCCD8=MAX4
   - Maize: TB1=BRC1
   If the ortholog maps to a node in the network, set in_network=true and use that node.

2. COMPOSITE REDUNDANCY — for paralog families:
   - Single-paralog KO (e.g. smxl6 alone) of a redundant family should use modifier 0.97 (mostly compensated by smxl7/smxl8). Only the triple smxl6/7/8 KO uses 0.0.
   - If only the composite SMXL678 node exists (not individual SMXL6/7/8), map all to SMXL678.

3. PERTURBATION TYPE → MODIFIER:
   - KO/knockout/null = gene_modifier 0.0 (or 0.97 if redundant single paralog of family)
   - KD/knockdown/silenced = 0.5
   - OE/overexpression = 2.0
   - WT (control) = 1.0 (do not include — only reference)

4. TREATMENTS — chemical applications use exogenous_supply, NOT gene_modifier:
   - GR24 = exogenous Strigolactone {1.0}
   - BAP/kinetin/zeatin = exogenous Cytokinin {1.0}
   - IAA/NAA = exogenous Auxin {1.0}
   - GA3/GA4 = exogenous GA {1.0}
   - Sucrose treatment = exogenous Sucrose {1.0}
   If no node matches, in_network=false.

5. RESCUE EXPERIMENTS — when a test combines a mutant background with a treatment:
   - comparison_baseline = "mutant" (compare to mutant alone)
   - Both gene_modifier (mutant) AND exogenous_supply (treatment) are set.

6. MULTI-GENE PERTURBATIONS — "max2 max3 double KO":
   - perturbations array contains BOTH genes with their respective modifier values.
   - network_gene = ["MAX2", "MAX3"].

7. NOT-IN-NETWORK — if the gene is not represented and not an ortholog of any network node, in_network=false. Examples: PHYB, IPA1, axr1 (if AXR1 absent from network).

Return ONE JSON object:

{{
  "reconciled": [
    {{
      "test_id": "T001",
      "in_network": true,
      "network_gene": ["BRC1"],
      "gene_modifiers": {{"BRC1": 0.0}},
      "exogenous_supply": {{}},
      "comparison_baseline": "WT",
      "reconciliation_type": "exact_match",
      "reconciliation_note": ""
    }},
    {{
      "test_id": "T020",
      "in_network": true,
      "network_gene": ["D14"],
      "gene_modifiers": {{"D14": 0.0}},
      "exogenous_supply": {{}},
      "comparison_baseline": "WT",
      "reconciliation_type": "ortholog",
      "reconciliation_note": "rms3 (pea ortholog of D14)"
    }},
    {{
      "test_id": "T088",
      "in_network": true,
      "network_gene": ["MAX2", "Strigolactone"],
      "gene_modifiers": {{"MAX2": 0.0}},
      "exogenous_supply": {{"Strigolactone": 1.0}},
      "comparison_baseline": "mutant",
      "reconciliation_type": "rescue",
      "reconciliation_note": "max2 mutant + GR24 rescue"
    }}
  ]
}}

Output ONLY the JSON object, no surrounding text or markdown."""


def call_ollama(model, prompt, num_ctx=131072, timeout=2400):
    body = json.dumps({"model": model, "prompt": prompt, "format": "json",
                       "stream": False, "options": {"temperature": 0.2, "num_ctx": num_ctx}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    print(f"calling Ollama (model={model}, num_ctx={num_ctx})...", flush=True)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    print(f"  returned in {time.time()-t0:.0f}s", flush=True)
    return resp.get("response", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="awaescher/qwen3-235b-2507-unsloth-q3-k-xl:latest")
    args = ap.parse_args()

    net = json.load((NET/"network.json").open())
    pds = json.load((DATA/"perturbation_dataset.json").open())
    phenotype_node = net["metadata"]["phenotype_node"]
    node_ids = {n["id"] for n in net["nodes"]}
    node_types = {n["id"]: n["type"] for n in net["nodes"]}

    nodes_list = "\n".join(f"  {n['id']:25s} {n['type']}" for n in sorted(net["nodes"], key=lambda x: x["id"]))
    tests_list = "\n".join(
        f"  {t['test_id']:6s} gene={t.get('gene','')!r:20s} ptype={t.get('perturbation_type','')!r:14s} expected={t.get('expected_direction','unchanged')}"
        for t in pds["perturbations"]
    )

    prompt = PROMPT.format(nodes_list=nodes_list, tests_list=tests_list)
    print(f"prompt: ~{len(prompt)//4} tokens, {len(pds['perturbations'])} tests")
    resp = call_ollama(args.model, prompt)
    plan = json.loads(resp)
    reconciled_lookup = {r["test_id"]: r for r in plan.get("reconciled", [])}

    # build full reconciled file (with evidence + perturbations array re-derived)
    out_perts = []
    n_in = 0
    for t in pds["perturbations"]:
        tid = t["test_id"]
        r = reconciled_lookup.get(tid)
        if r is None:
            r = {"in_network": False, "network_gene": [], "gene_modifiers": {},
                 "exogenous_supply": {}, "comparison_baseline": "WT",
                 "reconciliation_type": "missing", "reconciliation_note": "qwen3 didn't return entry"}
        # validate against actual node IDs — drop unknowns
        ng = [g for g in r.get("network_gene", []) if g in node_ids]
        gm = {k: v for k, v in r.get("gene_modifiers", {}).items() if k in node_ids}
        exo = {k: v for k, v in r.get("exogenous_supply", {}).items() if k in node_ids}
        in_net = bool(ng) and (bool(gm) or bool(exo))
        if in_net: n_in += 1

        perts = ([{"node": k, "modifier_type": "gene_modifier", "value": v} for k, v in gm.items()] +
                 [{"node": k, "modifier_type": "exogenous_supply", "value": v} for k, v in exo.items()])
        out_perts.append({
            "test_id": tid,
            "expected_direction": t.get("expected_direction", "unchanged"),
            "expected_magnitude": "moderate",
            "phenotype_node": phenotype_node,
            "comparison_baseline": r.get("comparison_baseline", "WT"),
            "condition": "both",
            "in_network": in_net,
            "network_gene": ng,
            "gene_modifiers": gm,
            "exogenous_supply": exo,
            "perturbations": perts,
            "notes": "",
            "reconciliation_type": r.get("reconciliation_type", "missing"),
            "reconciliation_note": r.get("reconciliation_note", ""),
            "evidence": [t["evidence"]] if isinstance(t.get("evidence"), dict) else (t.get("evidence") or []),
            "gene": t.get("gene", ""),
            "perturbation_type": t.get("perturbation_type", ""),
        })

    out = {"metadata": {"flash_p_version":"2.0","phenotype":"shoot_branching",
                        "phenotype_node": phenotype_node, "species":"Arabidopsis thaliana",
                        "created":"2026-05-03","iteration":1,
                        "total_tests": len(out_perts),
                        "tests_in_network": n_in,
                        "tests_not_in_network": len(out_perts) - n_in,
                        "reconciler": f"LLM-driven via {args.model}"},
           "direction_threshold": 0.05,
           "perturbations": out_perts}
    json.dump(out, (DATA/"reconciled_perturbation_dataset.json").open("w"), indent=2, ensure_ascii=False)

    # report
    types = Counter(r["reconciliation_type"] for r in out_perts)
    print(f"\nreconciled {len(out_perts)} tests")
    print(f"  in network:     {n_in}  ({100*n_in/len(out_perts):.1f}%)")
    print(f"  not in network: {len(out_perts) - n_in}")
    print(f"  by type: {dict(types)}")

if __name__ == "__main__":
    main()
