#!/usr/bin/env python3
"""
Build accuracy_metrics.json, failure_analysis.json, method_comparison.json
for the Sorghum_Flowering_Time_network, with photoperiod + class stratification.

Reads:
  validation/script_validation_results.json   (Algebraic)
  validation/ode_validation_results.json       (ODE)
  validation/rwr_validation_results.json       (RWR)
  data/reconciled_perturbation_dataset.json
  validation/ode_sensitivity_results.json
  validation/rwr_sensitivity_results.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

NET = Path(__file__).parent
VAL = NET / "validation"
DATA = NET / "data"


def load(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- load all ----------
alg = load(VAL / "script_validation_results.json")
ode = load(VAL / "ode_validation_results.json")
rwr = load(VAL / "rwr_validation_results.json")
perts = load(DATA / "reconciled_perturbation_dataset.json")["perturbations"]
ode_sens = load(VAL / "ode_sensitivity_results.json")
rwr_sens = load(VAL / "rwr_sensitivity_results.json")

pert_by_id = {p["test_id"]: p for p in perts}


# ---------- classification helpers ----------
def photoperiod_bucket(p) -> str:
    """Map a perturbation to photoperiod stratum."""
    cond = (p.get("condition") or "").strip()
    notes = (p.get("notes") or "").lower()
    if "night_break" in cond.lower() or "night-break" in notes:
        return "night_break"
    if cond == "LD_vs_SD":
        return "photoperiod_shift"
    if cond == "continuous_dark":
        return "continuous_dark"
    if cond == "far_red_supplementation":
        return "far_red"
    if cond == "LD" or "long day" in notes or "14h" in notes:
        return "LD"
    if cond == "SD" or "short day" in notes or "10h" in notes or "11h" in notes:
        return "SD"
    if cond == "normal":
        return "normal"
    if cond == "both":
        return "both"
    return "unspecified"


def class_bucket(p) -> str:
    """Sorghum-flowering-specific perturbation class."""
    gene_raw = (p.get("gene") or "").strip()
    ptype = (p.get("perturbation_type") or "").lower()
    genes = [g.strip() for g in gene_raw.split(",") if g.strip()]
    norm = [g.upper().replace("SB", "") if g.upper().startswith("SB") else g.upper() for g in genes]
    # note: SbPhyB -> PHYB, SbPRR37 -> PRR37, SbGhd7 -> GHD7, SbFT1 -> FT1, etc.
    # But MA2_SMYD doesn't have Sb prefix.
    norm = []
    for g in genes:
        gU = g.upper()
        if gU.startswith("SB") and len(gU) > 2:
            norm.append(gU[2:])
        else:
            norm.append(gU)

    is_double = len(genes) >= 2

    # SbFT family
    ft_set = {"FT1", "FT8", "FT10", "FT12"}
    is_ft_only = all(n in ft_set for n in norm)

    if is_ft_only and norm:
        if ptype in ("overexpression", "gain_of_function"):
            return "SbFT_OE"
        if ptype in ("knockout_crispr", "loss_of_function", "knockout", "triple_knockout", "knockdown"):
            return "SbFT_CRISPR"

    # Ma double mutants (two Ma-locus genes: PHYB, PRR37, GHD7, PHYC plus MA2_SMYD)
    ma_genes = {"PHYB", "PRR37", "GHD7", "PHYC", "MA2_SMYD"}
    if is_double and all(n in ma_genes for n in norm):
        return "Ma_double_mutant"

    if "PHOTOPERIOD" in norm or gene_raw.upper() == "PHOTOPERIOD":
        return "photoperiod_shift_only"

    if ptype in ("treatment", "inhibitor_pbz") or "gibberellin" in gene_raw.lower() or "ga" == gene_raw.lower() or "pbz" in gene_raw.lower():
        return "GA"

    if gene_raw.upper() == "WT" and ptype == "environmental":
        return "WT_environmental"

    if gene_raw.upper() == "WT" and ptype == "control":
        return "WT_control"

    if not is_double and norm:
        n0 = norm[0]
        if n0 == "PRR37":
            if ptype in ("loss_of_function", "knockout", "knockdown"):
                return "PRR37_LOF"
            if ptype in ("overexpression", "gain_of_function"):
                return "PRR37_OE"
        if n0 == "PHYB":
            return "PhyB_LOF" if ptype in ("loss_of_function", "knockout", "knockdown", "heterozygous") else "PhyB_OE"
        if n0 == "PHYC":
            return "PhyC_LOF"
        if n0 == "GHD7":
            if ptype in ("loss_of_function", "knockout", "knockdown"):
                return "Ghd7_LOF"
            if ptype in ("overexpression", "gain_of_function"):
                return "Ghd7_OE"
        if n0 in ("ELF3", "GI", "CCA1", "LHY", "TOC1", "FKF1", "ELF4", "LUX"):
            return "clock"
        if n0 == "CO":
            return "CO_like"
        if n0 in ("EHD1",):
            return "Ehd1"
        if n0 == "ID1":
            return "ID1"
        if n0 == "MA2_SMYD":
            return "MA2_SMYD"
        if n0 in ("SBP19", "SBP4", "MIR156H", "MIR172A", "AP1", "AP2", "SOC1", "LFY", "FD1", "GF14"):
            return "downstream_misc"

    return "other"


# ---------- accuracy metrics per method ----------
def method_summary(method_json, pert_by_id):
    """Return per-method accuracy metrics + stratifications."""
    m = method_json["metrics"]
    dr = method_json["detailed_results"]
    failures = [r["test_id"] for r in dr if not r["correct"]]

    # FRS/DARS already in metrics
    summary = {
        "accuracy": round(m["overall_accuracy"] / 100.0, 4),
        "correct": m["correct"],
        "total_tested": m["total"],
        "kappa": round(m["cohens_kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(m.get("convergence_rate", 1.0), 4),
        "failures": failures,
        "ci_95": [round(m.get("kappa_ci_lower", 0.0), 4), round(m.get("kappa_ci_upper", 0.0), 4)],
        "frs": round(m.get("rigor_score", 0.0), 4),
        "frs_band": m.get("rigor_band", ""),
        "dars": round(m.get("dars", 0.0), 4),
        "dars_band": m.get("dars_band", ""),
        "kappa_band": m.get("kappa_band", ""),
    }

    # Per-class F1 already in per_class
    per_class = m.get("per_class", {})

    # by_photoperiod
    by_pp = {}
    for r in dr:
        tid = r["test_id"]
        p = pert_by_id.get(tid)
        if not p:
            continue
        b = photoperiod_bucket(p)
        by_pp.setdefault(b, {"n": 0, "correct": 0})
        by_pp[b]["n"] += 1
        if r["correct"]:
            by_pp[b]["correct"] += 1
    for b, d in by_pp.items():
        d["accuracy"] = round(d["correct"] / d["n"], 4) if d["n"] else 0.0

    # by_class
    by_cls = {}
    for r in dr:
        tid = r["test_id"]
        p = pert_by_id.get(tid)
        if not p:
            continue
        b = class_bucket(p)
        by_cls.setdefault(b, {"n": 0, "correct": 0})
        by_cls[b]["n"] += 1
        if r["correct"]:
            by_cls[b]["correct"] += 1
    for b, d in by_cls.items():
        d["accuracy"] = round(d["correct"] / d["n"], 4) if d["n"] else 0.0

    summary["per_class"] = per_class
    summary["by_photoperiod"] = by_pp
    summary["by_class"] = by_cls
    # Tier2 scope
    summary["tier2_scope"] = m.get("tier2_scope", {})
    summary["stratified"] = m.get("stratified", {})
    return summary


alg_s = method_summary(alg, pert_by_id)
ode_s = method_summary(ode, pert_by_id)
rwr_s = method_summary(rwr, pert_by_id)

# Best-params tags
ode_s["best_K"] = ode.get("parameters", {}).get("K")
ode_s["best_n"] = ode.get("parameters", {}).get("n")
rwr_s["best_alpha"] = rwr.get("best_alpha") or rwr.get("parameters", {}).get("alpha")

# ---------- write accuracy_metrics.json ----------
accuracy_metrics = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Flowering_Time",
        "species": "Sorghum bicolor",
        "created": str(date.today()),
    },
    "tests": {
        "total": len(perts),
        "tested": alg["summary"]["tested"],
        "skipped": alg["summary"]["skipped"],
    },
    "algebraic": alg_s,
    "ode": ode_s,
    "rwr": rwr_s,
}

with open(VAL / "accuracy_metrics.json", "w", encoding="utf-8") as f:
    json.dump(accuracy_metrics, f, indent=2)
print(f"Wrote: {VAL / 'accuracy_metrics.json'}")


# ---------- failure_analysis.json ----------
# Categorize each failure from the BEST method (highest accuracy), but
# provide a unified failure list drawing failures that appeared in >=2
# of the 3 methods (consensus failures), plus mention method coverage.

def det_by_id(method_json):
    return {r["test_id"]: r for r in method_json["detailed_results"]}


alg_d = det_by_id(alg)
ode_d = det_by_id(ode)
rwr_d = det_by_id(rwr)

all_fail_ids = sorted(set(alg_s["failures"]) | set(ode_s["failures"]) | set(rwr_s["failures"]),
                      key=lambda x: int(x.lstrip("T")))


def failure_category(p, r_alg, r_ode, r_rwr):
    """Assign category for a single failing test.

    Heuristics:
      - perturbation_type in (rescue, heterozygous, epistasis, treatment)
        AND combines signaling KO + hormone/exogenous -> framework_limitation
      - gene is composite (comma-separated or FT-family) -> composite_collapse
      - multi-gene (double/triple) mutants -> epistasis_complexity
      - high-ratio runaway (ratio > 100 or < 0.01) -> edge_case (signal
        explosion / dilution through cascade)
      - otherwise edge_case
    """
    ptype = (p.get("perturbation_type") or "").lower()
    gene_raw = p.get("gene", "")
    is_multi = "," in gene_raw
    exo = p.get("exogenous_supply") or {}
    gm = p.get("gene_modifiers") or {}
    signaling_nodes = {"PHYB", "PHYC", "D14", "MAX2", "TIR1", "GID1"}
    # Rescue / signaling+treatment
    has_mutant_plus_treatment = (
        ptype == "rescue"
        or (ptype == "treatment" and any(v == 0.0 for v in gm.values()))
        or (any(v == 0.0 for v in gm.values()) and len(exo) > 0 and ptype not in ("loss_of_function", "knockout", "knockdown", "triple_knockout", "double_mutant", "knockout_crispr", "environmental"))
    )
    if has_mutant_plus_treatment:
        return "framework_limitation", (
            "Mutant + exogenous/treatment rescue. Framework adds exogenous "
            "supply regardless of whether the signaling receptor is functional, "
            "so the predicted rescue cannot be blocked by the KO."
        )

    # Composite collapse: SbFT CRISPR singles (FT1 vs FT8 vs FT10 redundancy),
    # or any single member of a paralog family being modified while other
    # members remain WT.
    ft_family = {"SBFT1", "SBFT8", "SBFT10", "SBFT12", "FT1", "FT8", "FT10", "FT12"}
    g_up = gene_raw.upper().replace(",", " ").split()
    if any(g in ft_family for g in g_up) and not is_multi and "triple" not in ptype:
        return "composite_collapse", (
            "Single SbFT paralog perturbed while other paralogs remain at WT. "
            "In the model FT1/FT8/FT10 all feed the same downstream integrator, "
            "so single-paralog perturbation is diluted by the geometric mean / "
            "sum across paralogs, producing small effects that fall below the "
            "direction threshold."
        )

    # Double/triple/epistasis
    if ptype in ("double_mutant", "triple_knockout", "epistasis") or is_multi:
        return "epistasis_complexity", (
            "Multi-gene interaction with compounding / opposing effects. "
            "Coherent feed-forward arms (PRR37 vs Ghd7 vs PhyB) combine in "
            "non-additive ways; geometric-mean activation under-weights the "
            "summed repression release."
        )

    # Signal runaway or collapse via cascade
    r = r_alg or r_ode or r_rwr
    if r:
        ratio = r.get("ratio") or 1.0
        if ratio is not None and (ratio > 50 or (0 < ratio < 0.02)):
            return "edge_case", (
                f"Cascade amplification / collapse (ratio={ratio:.3g}). "
                "Bounded-inverse inhibition on Flowering_Time plus long FT-arm "
                "cascade pushes the ratio to the K=10 ceiling or to the epsilon "
                "floor — predicted direction is correct in sign but wildly "
                "over-magnified, and small sign errors upstream flip the final "
                "direction."
            )

    # Unchanged-predicted-as-directional or vice versa via threshold edge
    pred = r.get("predicted_direction") if r else None
    exp = r.get("expected_direction") if r else None
    if pred == "unchanged" and exp in ("increased", "decreased"):
        return "edge_case", (
            "Predicted unchanged vs expected directional: upstream signal "
            "never propagates to the phenotype node — likely a broken or "
            "missing edge in the relevant cascade arm."
        )
    if pred in ("increased", "decreased") and exp == "unchanged":
        return "edge_case", (
            "Predicted directional vs expected unchanged: spurious propagation "
            "from the perturbed node to Flowering_Time — likely an extra edge "
            "or wrong-sign edge that introduces sensitivity where biology "
            "shows none."
        )

    # Default
    return "edge_case", (
        "Direction mismatch in a standard single-gene perturbation. Likely "
        "wrong-sign or missing intermediate edge in the PHYB/PRR37/Ghd7 → "
        "Ehd1 → SbFT → Flowering_Time cascade."
    )


failure_entries = []
by_cat = {"framework_limitation": 0, "composite_collapse": 0, "epistasis_complexity": 0, "edge_case": 0}
fixable_count = 0

for tid in all_fail_ids:
    p = pert_by_id.get(tid)
    if not p:
        continue
    r_alg = alg_d.get(tid)
    r_ode = ode_d.get(tid)
    r_rwr = rwr_d.get(tid)
    r_best = r_rwr or r_ode or r_alg  # use best-method's prediction for the direction fields

    cat, expl = failure_category(p, r_alg, r_ode, r_rwr)

    # Framework limitations are not fixable by refinement (usually)
    fixable = cat != "framework_limitation"
    if fixable:
        fixable_count += 1

    fix_strategy = ""
    if cat == "composite_collapse":
        fix_strategy = (
            "Collapse SbFT paralogs into a single FT_paralog_family node, or "
            "encode per-paralog contribution weights on the FT→Flowering_Time "
            "edges so single-paralog perturbations register."
        )
    elif cat == "epistasis_complexity":
        fix_strategy = (
            "Wire PRR37 and Ghd7 arms as independent coherent feed-forwards on "
            "Ehd1/SbFT so that double mutants additively stack releases."
        )
    elif cat == "edge_case":
        ratio = (r_best or {}).get("ratio") or 1.0
        if ratio is not None and ratio > 50:
            fix_strategy = (
                "Trim bounded-inverse cascade: remove one redundant PHYB/PRR37 "
                "→ FT direct-inhibition edge so Flowering_Time ratio stays "
                "within biological range."
            )
        elif ratio is not None and 0 < ratio < 0.02:
            fix_strategy = (
                "Add basal activator or soften inhibition on Flowering_Time "
                "to prevent collapse to zero; verify FT12/AP2 activator arm."
            )
        else:
            fix_strategy = (
                "Add missing direct edge or correct sign in PHYB/PRR37/Ghd7 → "
                "Ehd1 → SbFT → Flowering_Time cascade based on literature."
            )
    # framework_limitation: fix_strategy stays empty

    evidence = ""
    ev_list = p.get("evidence") or []
    if ev_list:
        evidence = ev_list[0].get("doi", "")

    pred = (r_best or {}).get("predicted_direction") or "unchanged"
    exp = (r_best or {}).get("expected_direction") or p.get("expected_direction") or "unchanged"

    failure_entries.append({
        "test_id": tid,
        "gene": p.get("gene", ""),
        "perturbation_type": p.get("perturbation_type", ""),
        "expected_direction": exp,
        "predicted_direction": pred,
        "category": cat,
        "explanation": expl + f" [algebraic={'correct' if r_alg and r_alg['correct'] else 'fail'}, ode={'correct' if r_ode and r_ode['correct'] else 'fail'}, rwr={'correct' if r_rwr and r_rwr['correct'] else 'fail'}]",
        "evidence": evidence,
        "fixable": fixable,
        "fix_strategy": fix_strategy,
    })
    by_cat[cat] += 1

failure_analysis = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Flowering_Time",
        "species": "Sorghum bicolor",
        "created": str(date.today()),
    },
    "failures": failure_entries,
    "summary": {
        "total_failures": len(failure_entries),
        "by_category": by_cat,
        "fixable_count": fixable_count,
        "unfixable_count": len(failure_entries) - fixable_count,
        "note": (
            "Failures are the UNION across all three methods (Algebraic, ODE, "
            "RWR). Per-method pass/fail is shown in the explanation field. "
            "Fixable=false for framework_limitation; REFINEMENT should focus on "
            "composite_collapse and edge_case items first."
        ),
    },
}

with open(VAL / "failure_analysis.json", "w", encoding="utf-8") as f:
    json.dump(failure_analysis, f, indent=2)
print(f"Wrote: {VAL / 'failure_analysis.json'}")


# ---------- method_comparison.json ----------
def entry(name, m_json, best_params_str, strengths, weaknesses, summary_s):
    return {
        "method": name,
        "accuracy": summary_s["accuracy"],
        "kappa": summary_s["kappa"],
        "mcc": summary_s["mcc"],
        "convergence_rate": summary_s["convergence_rate"],
        "best_params": best_params_str,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "failures": summary_s["failures"],
    }


comparison = [
    entry(
        "Algebraic",
        alg,
        "epsilon=0.1, K=10.0, damping=0.7",
        "Deterministic closed-form; fastest; direction reflects literature signs.",
        (
            "Bounded-inverse inhibition produces ratios in the hundreds when "
            "multiple inhibitors go to zero (PhyB KO, Ghd7 KO), amplifying "
            "true direction but flipping sign via cascade side-arms."
        ),
        alg_s,
    ),
    entry(
        "ODE (Hill Functions)",
        ode,
        f"K={ode_s.get('best_K')}, n={ode_s.get('best_n')}, dt=0.1, max_time=50",
        "Smooth Hill dynamics; captures threshold behaviour; all tests converged.",
        (
            "Low K=0.1 best, but still over-amplifies LOF cascades (ratios to "
            "1e12) — same structural imbalance as Algebraic. Unchanged class "
            "F1 very low (0.24)."
        ),
        ode_s,
    ),
    entry(
        "Random Walk with Restart",
        rwr,
        f"alpha={rwr_s.get('best_alpha')}",
        (
            "Best overall accuracy and MCC; propagation from perturbed node "
            "naturally dampens cascade explosion; highest recall on increased "
            "class."
        ),
        (
            "Kappa only 0.39 (fair) — class imbalance on decreased dominates; "
            "SbFT paralog single-CRISPR tests still fail because all three "
            "paralogs share the same downstream edge."
        ),
        rwr_s,
    ),
]

# pick best by accuracy -> kappa -> mcc
def rank_key(e):
    return (e["accuracy"], e["kappa"], e["mcc"])


best = max(comparison, key=rank_key)
best_name = best["method"]

if best["accuracy"] >= 0.95:
    rec = "Best method already at excellent accuracy; refinement optional. Proceed to export."
elif best["accuracy"] >= 0.80:
    rec = "Proceed to Step 5 (REFINEMENT). Focus on fixable failures."
else:
    rec = (
        "Best method accuracy < 80% — fundamental network structural issue. "
        "Re-invoke the JUDGE loop or have BUILDER revisit the PHYB/PRR37/Ghd7 "
        "→ Ehd1 → SbFT → Flowering_Time cascade before running REFINEMENT."
    )

method_comparison = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Flowering_Time",
        "species": "Sorghum bicolor",
        "created": str(date.today()),
    },
    "summary": {
        "best_method": best_name,
        "best_accuracy": best["accuracy"],
        "best_kappa": best["kappa"],
        "best_mcc": best["mcc"],
        "best_frs": (alg_s if best_name == "Algebraic" else ode_s if best_name.startswith("ODE") else rwr_s)["frs"],
        "best_dars": (alg_s if best_name == "Algebraic" else ode_s if best_name.startswith("ODE") else rwr_s)["dars"],
        "recommendation": rec,
        "next_step": "Step 5 (REFINEMENT)" if best["accuracy"] < 0.95 else "Step 6 (EXPORT)",
    },
    "comparison": comparison,
}

with open(VAL / "method_comparison.json", "w", encoding="utf-8") as f:
    json.dump(method_comparison, f, indent=2)
print(f"Wrote: {VAL / 'method_comparison.json'}")

# ---------- stdout summary ----------
print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
for name, s in [("Algebraic", alg_s), ("ODE", ode_s), ("RWR", rwr_s)]:
    print(f"{name:10s} acc={s['accuracy']:.3f} kappa={s['kappa']:.3f} ({s['kappa_band']}) "
          f"MCC={s['mcc']:.3f}  FRS={s['frs']:.2f} ({s['frs_band']})  "
          f"DARS={s['dars']:.2f} ({s['dars_band']})")
print(f"Best method: {best_name}")
print(f"Recommendation: {rec}")

print()
print("By photoperiod (best method = {}):".format(best_name))
bm = alg_s if best_name == "Algebraic" else ode_s if best_name.startswith("ODE") else rwr_s
for k, v in sorted(bm["by_photoperiod"].items()):
    print(f"  {k:25s} n={v['n']:3d}  correct={v['correct']:3d}  acc={v['accuracy']:.3f}")

print()
print("By class (best method = {}):".format(best_name))
for k, v in sorted(bm["by_class"].items(), key=lambda kv: -kv[1]["n"]):
    print(f"  {k:25s} n={v['n']:3d}  correct={v['correct']:3d}  acc={v['accuracy']:.3f}")

print()
print("Failure category counts (union across methods):")
for k, v in failure_analysis["summary"]["by_category"].items():
    print(f"  {k:25s} {v}")
print(f"  total={failure_analysis['summary']['total_failures']} fixable={fixable_count}")
