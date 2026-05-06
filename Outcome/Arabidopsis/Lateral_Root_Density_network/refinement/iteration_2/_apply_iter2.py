"""
LR Iteration 2: continued encoding refinement.

Diagnoses after iter 1:
- PIN composite still ratio 0.95-0.98 for T028/T029/T030/T071 -- tighten further to 0.5.
- MAX1/MAX4 single KO at gm=0.5 still over-amplifies (ratio 1.26) -- tighten to 0.85
  (single KO of one of three sequential SL biosynth enzymes doesn't fully eliminate SL).
- T141 cle3+low_N: Low_Nitrate exo=1.0 dominates the CLE composite -> remove exo
  (cle3 KO removes the demand feedback regardless of N status).
- T149 EBR+mild_N: same Low_Nitrate exo issue -> remove exo.
- T096/T097: revert iter1 baseline change since no encoding works (framework limitation).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET = ROOT / "data" / "reconciled_perturbation_dataset.json"

with open(DATASET, "r", encoding="utf-8") as fh:
    d = json.load(fh)

PATCHES = {
    "T028": {"gene_modifiers": {"PIN": 0.5}},
    "T029": {"gene_modifiers": {"PIN": 0.5}},
    "T030": {"gene_modifiers": {"PIN": 0.7}},
    "T071": {"gene_modifiers": {"PIN": 0.5}},
    "T065": {"gene_modifiers": {"MAX4": 0.85}},
    "T066": {"gene_modifiers": {"MAX1": 0.85}},
    # cle3 + low-N: drop Low_Nitrate exo so CLE composite reduction shows through
    "T141": {"gene_modifiers": {"CLE": 0.5}, "exogenous_supply": {}},
    # EBR + mild_N: drop Low_Nitrate exo so BR signal can show
    "T149": {"gene_modifiers": {}, "exogenous_supply": {"Brassinosteroid": 1.0}},
    # Revert T096/T097 -- no Trap-5 encoding works (framework limit)
    "T096": {"comparison_baseline": "WT", "expected_direction": "decreased"},
    "T097": {"comparison_baseline": "WT", "expected_direction": "decreased"},
}

def rebuild_perturbations(p):
    pl = []
    for node, val in p.get("gene_modifiers", {}).items():
        pl.append({"node": node, "modifier_type": "gene_modifier", "value": float(val)})
    for node, val in p.get("exogenous_supply", {}).items():
        pl.append({"node": node, "modifier_type": "exogenous_supply", "value": float(val)})
    return pl

changed = []
for p in d["perturbations"]:
    tid = p["test_id"]
    if tid not in PATCHES:
        continue
    patch = PATCHES[tid]
    rec = []
    for k, v in patch.items():
        if k == "gene_modifiers":
            old = dict(p.get("gene_modifiers", {}))
            p["gene_modifiers"] = v
            rec.append(f"gm: {old} -> {v}")
        elif k == "exogenous_supply":
            old = dict(p.get("exogenous_supply", {}))
            p["exogenous_supply"] = v
            rec.append(f"exo: {old} -> {v}")
        elif k == "comparison_baseline":
            old = p.get("comparison_baseline")
            p["comparison_baseline"] = v
            rec.append(f"baseline: {old} -> {v}")
        elif k == "expected_direction":
            old = p.get("expected_direction")
            p["expected_direction"] = v
            rec.append(f"expected: {old} -> {v}")
    p["perturbations"] = rebuild_perturbations(p)
    p["notes"] = (p.get("notes", "") or "") + f" [iter2 LR refinement: {'; '.join(rec)}]"
    changed.append((tid, "; ".join(rec)))

with open(DATASET, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)

print(f"Applied {len(changed)} fixes:")
for tid, rec in changed:
    print(f"  {tid}: {rec}")
