"""
Iteration 4: apply 5 Trap-5 / combined-KO-plus-treatment encoding fixes.

Rationale: All 5 perturbations with both gene_modifiers AND exogenous_supply were
encoded with comparison_baseline="WT" but the validator auto-switches to
mutant-baseline for combined perturbations, producing ratio=1.0 "dead signal"
outputs. Per §Trap 5 and §Comparison Rules, these tests must be encoded
against the mutant baseline. Expected directions are also updated:

  T004 afb5 + picloram:  picloram still elongates via remaining TIR1/AFB family,
    so vs the afb5-alone mutant baseline the phenotype is "increased"
    (reduced-sensitivity, not null). DOI: 10.7554/eLife.19048 (Prigge 2020).
  T046 ein2 + ACC:  ein2 is a signaling mutant; ACC cannot be transduced,
    so expected "unchanged" vs ein2 alone (Trap 5).
  T047 ein3 + ACC:  EIN3 signaling mutant; same Trap 5 logic.
  T049 ein3 eil1 + ACC:  same Trap 5 logic.
  T112 tir1 + auxin:  TIR1 signaling mutant; auxin cannot signal through
    the missing receptor. Expected "unchanged" vs tir1 alone.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # .../Hypocotyl_Length_network
DATASET = ROOT / "data" / "reconciled_perturbation_dataset.json"

with open(DATASET, "r", encoding="utf-8") as fh:
    d = json.load(fh)

FIXES = {
    "T004": {"comparison_baseline": "mutant", "expected_direction": "increased"},
    "T046": {"comparison_baseline": "mutant", "expected_direction": "unchanged"},
    "T047": {"comparison_baseline": "mutant", "expected_direction": "unchanged"},
    "T049": {"comparison_baseline": "mutant", "expected_direction": "unchanged"},
    "T112": {"comparison_baseline": "mutant", "expected_direction": "unchanged"},
}

changed = []
for p in d["perturbations"]:
    tid = p["test_id"]
    if tid in FIXES:
        patch = FIXES[tid]
        old_base = p.get("comparison_baseline")
        old_exp = p.get("expected_direction")
        p["comparison_baseline"] = patch["comparison_baseline"]
        p["expected_direction"] = patch["expected_direction"]
        # Extend notes
        note_addition = (
            f" [iter4 Trap5 fix] baseline {old_base}->{patch['comparison_baseline']}, "
            f"expected {old_exp}->{patch['expected_direction']}."
        )
        p["notes"] = (p.get("notes", "") or "") + note_addition
        changed.append((tid, old_base, old_exp, patch["comparison_baseline"], patch["expected_direction"]))

with open(DATASET, "w", encoding="utf-8") as fh:
    json.dump(d, fh, indent=2)

for tid, ob, oe, nb, ne in changed:
    print(f"  {tid}: baseline {ob}->{nb}, expected {oe}->{ne}")
print(f"Applied {len(changed)} encoding fixes to {DATASET.name}")
