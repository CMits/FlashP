"""
REFINEMENT iteration 3 - encoding fix for etr1-1 dominant gain-of-function.

T107 gene=ETR1 was reconciled as knockout (gm=0.0), but the evidence sentence
('etr1 mutants are ethylene-insensitive with marginally increased elongation')
refers to the classic etr1-1 dominant GAIN-OF-FUNCTION mutant (Chang 1993
Science). The mutant protein cannot bind ethylene, so the receptor stays
constitutively active. Encoding as gain_of_function with gm=2.0 matches the
network's inverse-receptor logic (Ethylene -| ETR1 -> CTR1 -| EIN2 -| EIN3
-| Plant_Height). Constitutively-active ETR1 -> CTR1 high -> EIN2 low ->
EIN3 low -> growth up (matches expected 'increased').
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
RECON = ROOT / "data" / "reconciled_perturbation_dataset.json"

data = json.load(open(RECON, encoding="utf-8"))
for p in data["perturbations"]:
    if p["test_id"] == "T107":
        before = {"perturbation_type": p["perturbation_type"],
                   "gene_modifiers": dict(p["gene_modifiers"])}
        p["perturbation_type"] = "gain_of_function"
        p["gene_modifiers"] = {"ETR1": 2.0}
        p["perturbations"] = [{"node": "ETR1",
                                 "modifier_type": "gene_modifier",
                                 "value": 2.0}]
        p["notes"] += (" [iter-3 refinement: re-encoded as gain_of_function "
                        "to match etr1-1 dominant mutant biology "
                        "(Chang 1993). Constitutively-active receptor "
                        "phenocopies ethylene insensitivity.]")
        p["reconciliation_note"] = p["notes"]
        print("Updated T107:")
        print("  before:", before)
        print("  after:", {"perturbation_type": p["perturbation_type"],
                            "gene_modifiers": p["gene_modifiers"]})
        break

with open(RECON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Saved.")
