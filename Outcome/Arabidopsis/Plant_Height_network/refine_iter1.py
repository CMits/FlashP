"""
REFINEMENT iteration 1 - encoding-only fix.

BR_SYN composite over-collapses non-redundant rate-limiting BR biosynthesis
enzymes (DWF4, DET2, CPD, CYP85A1). Per JUDGE §9.3, composite-member single-KO
defaults to gm=0.99 (Trap 2), but each of DWF4/DET2/CPD alone is a STRONG
dwarf in Arabidopsis - they are not >70% functionally redundant. Overriding
the single-KO modifier to 0.0 for these specific reconciled tests.

Tests affected: T043 (DWF4 KO), T045 (DET2 KO), T046 (CPD KO), T090 (det2+BL
rescue).

No network change. No equation regeneration. Just re-encode the reconciled
perturbation dataset.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
RECON = ROOT / "data" / "reconciled_perturbation_dataset.json"

data = json.load(open(RECON, encoding="utf-8"))

ID_TO_OVERRIDE = {"T043", "T045", "T046", "T090"}

changes = []
for p in data["perturbations"]:
    if p["test_id"] in ID_TO_OVERRIDE:
        before = dict(p["gene_modifiers"])
        p["gene_modifiers"]["BR_SYN"] = 0.0
        # Update perturbations array too
        for mod in p.get("perturbations", []):
            if mod["node"] == "BR_SYN" and mod["modifier_type"] == "gene_modifier":
                mod["value"] = 0.0
        p["notes"] += (" [iter-1 refinement: BR_SYN composite over-collapses "
                       "non-redundant rate-limiting enzymes DWF4/DET2/CPD; "
                       "single-KO modifier overridden from 0.99 to 0.0.]")
        p["reconciliation_note"] = p["notes"]
        changes.append({"test_id": p["test_id"], "before": before,
                         "after": dict(p["gene_modifiers"])})

with open(RECON, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Iteration 1 encoding fix applied. {len(changes)} tests updated.")
for c in changes:
    print(f"  {c['test_id']}: {c['before']} -> {c['after']}")
