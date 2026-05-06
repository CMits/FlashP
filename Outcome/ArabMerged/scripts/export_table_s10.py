"""
Generate Table_S10a/b/c (per-method pleiotropic results) and Table_S10
(cross-method pleiotropic summary) for the merged Arabidopsis network.

Inputs:
  validation/pleiotropic_{algebraic,ode,rwr}_results.json  (from validate_pleiotropic.py)
  validation/pleiotropic_summary.csv                        (from validate_pleiotropic.py)
  data/pleiotropic_perturbation_dataset.json                (for evidence DOIs)

Outputs:
  supplementary/Table_S10a_pleiotropic_algebraic.csv
  supplementary/Table_S10b_pleiotropic_ode.csv
  supplementary/Table_S10c_pleiotropic_rwr.csv
  supplementary/Table_S10_pleiotropic_summary.csv

Usage:
  py merged_arabidopsis_network/scripts/export_table_s10.py
"""
from __future__ import annotations
import csv, json, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
VAL  = BASE / "validation"
SUPP = BASE / "supplementary"

S10_COLS = [
    "test_id", "gene", "perturbation_type",
    "gene_modifier", "exogenous_node", "exogenous_value",
    "wt_value", "perturbed_value",
    "comparison_baseline", "comparison_baseline_value",
    "ratio", "log2_fold_change", "direction_threshold",
    "predicted_direction", "expected_direction", "correct",
    "phenotype_node",
    "complexity_score", "complexity_label",
    "path_length", "converged", "iterations",
    "evidence_doi",
]


def _doi_for_test(meta: dict, test_id: str) -> str:
    """test_id like PLEIO_001__Plant_Height -> base PLEIO_001 -> first DOI."""
    base = test_id.split("__", 1)[0] if "__" in test_id else test_id
    t = meta.get(base, {})
    ev = (t.get("evidence") or [{}])[0]
    return ev.get("doi", "")


def _build_pleio_meta(pleio_path: Path) -> dict:
    """Index tests by PLEIO_xxx base id."""
    d = json.loads(pleio_path.read_text(encoding="utf-8"))
    return {t["test_id"]: t for t in d.get("pleiotropic_tests", [])}


def _row(r: dict, meta: dict) -> dict:
    tid = r.get("test_id", "")
    row = {k: r.get(k, "") for k in S10_COLS}
    # Common normalizations
    row["test_id"] = tid
    # Fill in gene/perturbation_type if missing
    base = tid.split("__", 1)[0] if "__" in tid else tid
    m = meta.get(base, {})
    row["gene"] = r.get("gene") or m.get("gene", "")
    row["perturbation_type"] = r.get("perturbation_type") or m.get("perturbation_type", "")
    # Gene modifier (pleiotropic tests may have multi-gene mods; emit first)
    gm = m.get("gene_modifiers") or {}
    if not r.get("gene_modifier") and gm:
        row["gene_modifier"] = list(gm.values())[0]
    es = m.get("exogenous_supply") or {}
    if not r.get("exogenous_node") and es:
        row["exogenous_node"] = list(es.keys())[0]
        row["exogenous_value"] = list(es.values())[0]
    # Complexity
    n_gm = len([v for v in gm.values() if v != 1.0])
    n_exo = len(es)
    row["complexity_score"] = r.get("complexity_score") or max(n_gm + n_exo, 1)
    row["complexity_label"] = r.get("complexity_label") or (
        "easy" if row["complexity_score"] <= 1 else ("medium" if row["complexity_score"] == 2 else "hard")
    )
    # DOI
    row["evidence_doi"] = r.get("evidence_doi") or _doi_for_test(meta, tid)
    # correct as True/False
    row["correct"] = bool(r.get("correct", False))
    row["converged"] = bool(r.get("converged", False))
    return row


def write_s10(method_tag: str, method_json: Path, out_path: Path, meta: dict):
    d = json.loads(method_json.read_text(encoding="utf-8"))
    rows = [_row(r, meta) for r in d.get("detailed_results", [])]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=S10_COLS)
        w.writeheader()
        w.writerows(rows)
    correct = sum(1 for r in rows if r["correct"])
    total   = len(rows)
    print(f"  wrote {out_path.name:44s} {correct}/{total} correct ({100*correct/total if total else 0:.1f}%)")


def main():
    meta = _build_pleio_meta(BASE / "data" / "pleiotropic_perturbation_dataset.json")
    pairs = [
        ("algebraic", VAL / "pleiotropic_algebraic_results.json", SUPP / "Table_S10a_pleiotropic_algebraic.csv"),
        ("ode",       VAL / "pleiotropic_ode_results.json",       SUPP / "Table_S10b_pleiotropic_ode.csv"),
        ("rwr",       VAL / "pleiotropic_rwr_results.json",       SUPP / "Table_S10c_pleiotropic_rwr.csv"),
    ]
    for tag, jp, op in pairs:
        write_s10(tag, jp, op, meta)

    # Table_S10 is the combined summary — just copy from the validator-written pleiotropic_summary.csv
    src = VAL / "pleiotropic_summary.csv"
    dst = SUPP / "Table_S10_pleiotropic_summary.csv"
    shutil.copy(src, dst)
    print(f"  wrote {dst.name:44s} (copy of pleiotropic_summary.csv)")


if __name__ == "__main__":
    main()
