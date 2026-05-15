"""
Build refinement_report.json from iteration snapshots.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFINE = ROOT / "refinement"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, indent=2, ensure_ascii=False)


def acc_pct(result):
    """Extract overall_accuracy as a percentage float."""
    return float(result["metrics"]["overall_accuracy"])


def failures(result):
    return [r["test_id"] for r in result["detailed_results"] if not r["correct"]]


# Build iteration history
iteration_records = []
fix_applied_entries = []

for n in [0, 1, 2, 3]:
    idir = REFINE / f"iteration_{n}"
    alg = load(idir / "algebraic_validation_results.json")
    ode_ = load(idir / "ode_validation_results.json")
    rwr = load(idir / "rwr_validation_results.json")

    rec = {
        "iteration": n,
        "description": "",
        "algebraic_accuracy": acc_pct(alg),
        "ode_accuracy": acc_pct(ode_),
        "rwr_accuracy": acc_pct(rwr),
        "failures": failures(rwr),  # use best-method (RWR) failures for headline list
        "fixes_applied": 0,
        "edges_added": 0,
        "edges_removed": 0,
    }

    if n == 0:
        rec["description"] = "Baseline before refinement."
    elif (idir / "fixes_applied.json").exists():
        fap = load(idir / "fixes_applied.json")
        fixes = fap["fixes"]
        rec["fixes_applied"] = len(fixes)
        rec["edges_added"] = sum(1 for f in fixes if f["action"] == "add_edge")
        rec["edges_removed"] = sum(1 for f in fixes if f["action"] == "remove_edge")

        # Short description
        descs = [f.get("description", "")[:80] for f in fixes[:3]]
        rec["description"] = f"iter {n}: " + "; ".join(descs)

        for f in fixes:
            fa = {
                "iteration": n,
                "action": {
                    "remove_edge": "edge_removal",
                    "add_edge": "edge_addition",
                    "sign_change": "sign_change",
                    "encoding_test": "perturbation_encoding",
                }.get(f["action"], f["action"]),
                "description": f.get("description", ""),
                "reason": f.get("reason", ""),
                "biological_justification": f.get("biological_justification", ""),
                "source": f.get("source", ""),
                "target": f.get("target", ""),
                "sign": f.get("sign"),
                "modifier_type": None,
                "value": None,
            }
            # Extract modifier_type / value from encoding updates
            if f["action"] == "encoding_test":
                ups = f.get("updates", {})
                gm = ups.get("gene_modifiers", {})
                if gm:
                    fa["modifier_type"] = "gene_modifier"
                    fa["value"] = list(gm.values())[0]
                else:
                    es = ups.get("exogenous_supply", {})
                    if es:
                        fa["modifier_type"] = "exogenous_supply"
                        fa["value"] = list(es.values())[0]
            fix_applied_entries.append(fa)

    iteration_records.append(rec)


# Pick best iteration = highest best-method (max of 3) accuracy
def best_method_acc(rec):
    return max(rec["algebraic_accuracy"], rec["ode_accuracy"], rec["rwr_accuracy"])


best_iter = max(range(4), key=lambda i: best_method_acc(iteration_records[i]))

# Final best model stats
net = load(REFINE / f"iteration_{best_iter}/network_snapshot.json")
best_rec = iteration_records[best_iter]
best_model = {
    "location": f"refinement/iteration_{best_iter}/",
    "algebraic_accuracy": best_rec["algebraic_accuracy"],
    "ode_accuracy": best_rec["ode_accuracy"],
    "rwr_accuracy": best_rec["rwr_accuracy"],
    "total_nodes": len(net["nodes"]),
    "total_edges": len(net["edges"]),
}

report = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lycopene_Titer",
        "species": "Escherichia coli",
        "created": "2026-04-21",
        "iterations_run": 3,
        "best_iteration": best_iter,
    },
    "iteration_history": iteration_records,
    "fixes_applied": fix_applied_entries,
    "best_model": best_model,
}

dump(REFINE / "refinement_report.json", report)
print(f"Wrote refinement_report.json, best_iteration={best_iter}")
print(f"Best model accuracies: alg={best_model['algebraic_accuracy']:.1f}%, "
      f"ode={best_model['ode_accuracy']:.1f}%, rwr={best_model['rwr_accuracy']:.1f}%")

# Also write fixes_applied.json for iteration 0 (empty) to pass schema validation
i0_fixes = {
    "iteration": 0,
    "date": "2026-04-21",
    "fixes": [],
    "results": {
        "algebraic_accuracy": iteration_records[0]["algebraic_accuracy"],
        "ode_accuracy": iteration_records[0]["ode_accuracy"],
        "rwr_accuracy": iteration_records[0]["rwr_accuracy"],
        "kept": True,
        "reason": "Baseline (no fixes applied)",
    },
}
dump(REFINE / "iteration_0" / "fixes_applied.json", i0_fixes)
print("Wrote iteration_0/fixes_applied.json (baseline placeholder)")

# Update iter 1-3 fixes_applied.json with results blocks
for n in [1, 2, 3]:
    idir = REFINE / f"iteration_{n}"
    fap = load(idir / "fixes_applied.json")
    rec = iteration_records[n]
    prev_best = max(best_method_acc(iteration_records[k]) for k in range(n))
    curr_best = best_method_acc(rec)
    gain = curr_best - prev_best
    fap["results"] = {
        "algebraic_accuracy": rec["algebraic_accuracy"],
        "ode_accuracy": rec["ode_accuracy"],
        "rwr_accuracy": rec["rwr_accuracy"],
        "kept": gain >= 0.5,
        "reason": f"Best-method gained +{gain:.1f}% (from {prev_best:.1f}% to {curr_best:.1f}%)",
    }
    # Rewrite fixes with the schema-compliant shape (same transformation as above)
    transformed = []
    for f in fap["fixes"]:
        fa = {
            "iteration": n,
            "action": {
                "remove_edge": "edge_removal",
                "add_edge": "edge_addition",
                "sign_change": "sign_change",
                "encoding_test": "perturbation_encoding",
            }.get(f["action"], f["action"]),
            "description": f.get("description", ""),
            "reason": f.get("reason", ""),
            "biological_justification": f.get("biological_justification", ""),
            "source": f.get("source", ""),
            "target": f.get("target", ""),
            "sign": f.get("sign"),
            "modifier_type": None,
            "value": None,
        }
        if f["action"] == "encoding_test":
            ups = f.get("updates", {})
            gm = ups.get("gene_modifiers", {})
            if gm:
                fa["modifier_type"] = "gene_modifier"
                fa["value"] = list(gm.values())[0]
            else:
                es = ups.get("exogenous_supply", {})
                if es:
                    fa["modifier_type"] = "exogenous_supply"
                    fa["value"] = list(es.values())[0]
        transformed.append(fa)
    fap["fixes"] = transformed
    dump(idir / "fixes_applied.json", fap)
    print(f"Updated iteration_{n}/fixes_applied.json")
