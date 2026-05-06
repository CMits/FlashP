"""
LR Iteration 1: encoding fix package.

13 fixes total, all encoding (no DOI required):
- Composite-paralog gm tightening for major LR effectors (LBD/PIN/AFB/MAX1/MAX4)
- Trap-5 baseline corrections for stabilised-IAA + auxin (T096, T097)
- Rescue baseline correction for arf/plt rescue tests (T100, T101, T102)
- CLE composite tighten for cle3 single (T141)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET = ROOT / "data" / "reconciled_perturbation_dataset.json"

with open(DATASET, "r", encoding="utf-8") as fh:
    d = json.load(fh)

# Per-test patch instructions:
PATCHES = {
    # Composite-paralog gm tightening
    "T015": {"gene_modifiers": {"LBD": 0.5}},
    "T019": {"gene_modifiers": {"LBD": 0.5}},
    "T020": {"gene_modifiers": {"LBD": 0.5}},
    "T027": {"gene_modifiers": {"PIN": 0.5}},
    "T028": {"gene_modifiers": {"PIN": 0.7}},
    "T030": {"gene_modifiers": {"PIN": 0.85}},
    "T044": {"gene_modifiers": {"TIR1": 0.7}},
    "T003": {"gene_modifiers": {"TIR1": 0.85}},
    "T065": {"gene_modifiers": {"MAX4": 0.5}},
    "T066": {"gene_modifiers": {"MAX1": 0.5}},
    "T071": {"gene_modifiers": {"PIN": 0.7}},
    # Trap-5 (combined IAA gof + auxin)
    "T096": {
        "comparison_baseline": "mutant",
        "expected_direction": "unchanged",
    },
    "T097": {
        "comparison_baseline": "mutant",
        "expected_direction": "unchanged",
    },
    # Rescue baseline correction (no exogenous_supply -> mutant baseline collapses ratio)
    "T100": {"comparison_baseline": "WT"},
    "T101": {"comparison_baseline": "WT"},
    "T102": {"comparison_baseline": "WT"},
    # CLE composite tighten for cle3
    "T141": {"gene_modifiers": {"CLE": 0.5, "Low_Nitrate": 1.0}},
}

# Need to also rebuild the per-test 'perturbations' array when gene_modifiers/exo change
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
            # Replace gene_modifiers entirely with the patch (keeps the exo as is)
            old = dict(p.get("gene_modifiers", {}))
            # Special handling: T141 has Low_Nitrate in gene_modifiers (not exo)
            # Keep Low_Nitrate in exo if patch only sets gene_modifiers
            if tid == "T141":
                # Move Low_Nitrate to exo
                p["gene_modifiers"] = {"CLE": 0.5}
                p["exogenous_supply"] = {"Low_Nitrate": 1.0}
                rec.append(f"gm: {old} -> {{CLE: 0.5}}, exo: {{Low_Nitrate: 1.0}}")
            else:
                p["gene_modifiers"] = v
                rec.append(f"gm: {old} -> {v}")
        elif k == "comparison_baseline":
            old = p.get("comparison_baseline")
            p["comparison_baseline"] = v
            rec.append(f"baseline: {old} -> {v}")
        elif k == "expected_direction":
            old = p.get("expected_direction")
            p["expected_direction"] = v
            rec.append(f"expected: {old} -> {v}")
    p["perturbations"] = rebuild_perturbations(p)
    p["notes"] = (p.get("notes", "") or "") + f" [iter1 LR refinement: {'; '.join(rec)}]"
    changed.append((tid, "; ".join(rec)))

with open(DATASET, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)

print(f"Applied {len(changed)} fixes:")
for tid, rec in changed:
    print(f"  {tid}: {rec}")
