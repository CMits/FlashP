"""Step 4 interpretive file generator for Lateral_Root_Density."""
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "validation"
DATA = ROOT / "data" / "reconciled_perturbation_dataset.json"

with open(DATA, "r", encoding="utf-8") as fh:
    recon = json.load(fh)
by_tid = {p["test_id"]: p for p in recon["perturbations"]}

def _load(fname):
    with open(VAL / fname, "r", encoding="utf-8") as fh:
        return json.load(fh)

alg = _load("script_validation_results.json")
ode = _load("ode_validation_results.json")
rwr = _load("rwr_validation_results.json")

def bucket_condition(cond):
    """LR-specific: nutrient/condition stratification."""
    c = (cond or "").lower()
    if "low_nitrate_systemic" in c or "low_nitrate" in c:
        return "low_nitrate"
    if "high_nitrate" in c:
        return "high_nitrate"
    if "mild_n" in c or "mild_n_def" in c:
        return "mild_N_deficient"
    if "acc" in c:
        return "acc_treatment"
    return "standard"

def _method_summary(res, label, best_params_str=""):
    m = res["metrics"]
    failures = sorted(r["test_id"] for r in res["detailed_results"] if not r["correct"])
    return {
        "label": label,
        "accuracy_pct": m["overall_accuracy"],
        "accuracy": m["overall_accuracy"] / 100.0,
        "correct": m["correct"],
        "total_tested": m["total"],
        "kappa": m["cohens_kappa"],
        "kappa_band": m["kappa_band"],
        "kappa_ci_95": [m["kappa_ci_lower"], m["kappa_ci_upper"]],
        "mcc": m["mcc"],
        "convergence_rate": m["convergence_rate"] / 100.0,
        "frs": m["rigor_score"],
        "frs_band": m["rigor_band"],
        "dars": m["dars"],
        "dars_band": m["dars_band"],
        "tier2_scope": m["tier2_scope"],
        "stratified": m["stratified"],
        "failures": failures,
        "best_params": best_params_str,
    }

ode_params = ode.get("parameters", {})
rwr_params = rwr.get("parameters", {})
ode_best_str = f"K={ode_params.get('K')}, n={ode_params.get('n')}"
rwr_best_str = f"alpha={rwr_params.get('alpha')}"

alg_sum = _method_summary(alg, "Algebraic")
ode_sum = _method_summary(ode, "ODE", ode_best_str)
rwr_sum = _method_summary(rwr, "RWR", rwr_best_str)

def by_condition(res):
    buckets = defaultdict(lambda: {"n": 0, "correct": 0})
    for r in res["detailed_results"]:
        tid = r["test_id"]
        cond = by_tid.get(tid, {}).get("condition", "")
        b = bucket_condition(cond)
        buckets[b]["n"] += 1
        if r["correct"]:
            buckets[b]["correct"] += 1
    out = {}
    for b, v in buckets.items():
        out[b] = {
            "n": v["n"],
            "correct": v["correct"],
            "accuracy_pct": round(100.0 * v["correct"] / v["n"], 1) if v["n"] else None,
        }
    return out

alg_bc = by_condition(alg)
ode_bc = by_condition(ode)
rwr_bc = by_condition(rwr)

def rank(m):
    return (m["accuracy"], m["kappa"], m["mcc"])

methods = [alg_sum, ode_sum, rwr_sum]
best = max(methods, key=rank)
best_label = best["label"]

def to_methodaccuracy(m):
    d = {
        "accuracy": round(m["accuracy"], 4),
        "correct": m["correct"],
        "total_tested": m["total_tested"],
        "kappa": round(m["kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(m["convergence_rate"], 4),
        "failures": m["failures"],
        "ci_95": [round(m["kappa_ci_95"][0], 4), round(m["kappa_ci_95"][1], 4)],
    }
    if "K=" in m["best_params"]:
        d["best_K"] = ode_params.get("K")
        d["best_n"] = ode_params.get("n")
    if "alpha=" in m["best_params"]:
        d["best_alpha"] = rwr_params.get("alpha")
    return d

accuracy_metrics = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lateral_Root_Density",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
        "best_method": best_label,
        "best_accuracy_pct": best["accuracy_pct"],
        "frs_best": best["frs"],
        "frs_best_band": best["frs_band"],
        "dars_best": best["dars"],
        "dars_best_band": best["dars_band"],
    },
    "tests": {
        "total": len(recon["perturbations"]),
        "tested": alg_sum["total_tested"],
        "skipped": len(recon["perturbations"]) - alg_sum["total_tested"],
    },
    "algebraic": to_methodaccuracy(alg_sum),
    "ode": to_methodaccuracy(ode_sum),
    "rwr": to_methodaccuracy(rwr_sum),
    "by_condition": {
        "algebraic": alg_bc,
        "ode": ode_bc,
        "rwr": rwr_bc,
    },
    "stratified": {
        "algebraic": alg_sum["stratified"],
        "ode": ode_sum["stratified"],
        "rwr": rwr_sum["stratified"],
    },
    "tier2_scope": alg_sum["tier2_scope"],
}

with open(VAL / "accuracy_metrics.json", "w", encoding="utf-8") as fh:
    json.dump(accuracy_metrics, fh, indent=2)

# -----------------------------------------------------------------------------
# failure_analysis.json -- categorise current failures
# -----------------------------------------------------------------------------
CATEGORIES = {
    # Composite-member single-paralog ratio≈1.0 (no propagation)
    "T002": ("composite_collapse",
             "afb1 KO: AFB1 mapped to TIR1 composite gm=0.997. No propagation (ratio=0.996). AFB1 is biologically anti-correlated with other AFBs (Prigge 2020): single afb1 has slight LR-INCREASE while others decrease. The composite collapse cannot represent this.",
             False, ""),
    "T003": ("composite_collapse",
             "afb2 KO: TIR1 composite single-paralog gm=0.997 too weak. afb2 is part of the dominant LR receptor trio; single KO is phenotypic.",
             True, "Tighten gm (e.g., 0.7) for AFB2 single KO."),
    "T015": ("composite_collapse",
             "lbd16 KO: LBD composite gm=0.997 too weak. LBD16 is the master LR-initiator TF (Okushima 2007); single KO is strongly phenotypic.",
             True, "Tighten LBD composite gm to 0.5 for LBD16/18/29 single KOs."),
    "T019": ("composite_collapse",
             "lbd18 KO: same as T015. LBD18 with LBD16/29 form the LR-initiation triad.",
             True, "Tighten LBD composite gm to 0.5."),
    "T020": ("composite_collapse",
             "lbd29 KO: same as T015/T019.",
             True, "Tighten LBD composite gm to 0.5."),
    "T027": ("composite_collapse",
             "pin2 KO: PIN composite gm=0.997 too weak. pin2 alone is strongly defective in LR/gravitropism.",
             True, "Tighten PIN composite gm to 0.5 for pin2."),
    "T028": ("composite_collapse",
             "pin3 KO: PIN composite gm=0.997 too weak. pin3 alone has measurable LR effect.",
             True, "Tighten PIN composite gm to 0.7 for pin3."),
    "T029": ("composite_collapse",
             "pin3 pin7 double: gm=0.9 too weak; double is more defective than either alone.",
             True, "Tighten PIN composite gm to 0.5 for double."),
    "T030": ("composite_collapse",
             "pin8 KO: gm=0.997 too weak. PIN8 is one of multiple PINs but contributes to LR auxin transport.",
             True, "Tighten gm to 0.85 for pin8."),
    "T044": ("composite_collapse",
             "afb3 KO: TIR1 composite gm=0.997 too weak. AFB3 is the strongest single contributor to root auxin perception (Parry 2009).",
             True, "Tighten gm to 0.7 for afb3."),
    "T056": ("epistasis_complexity",
             "pyl8 KO: expected=decreased predicted=increased ratio=3.16. PYL8 has a non-canonical positive role on LR via ARF7/19 sensitisation (Zhao 2014). Network only models ABA→ABI4_5⊣LR (ABA-inhibitory arm), missing the PYL8→ARF7/19 sensitisation arm.",
             True, "Add edge PYL8 -> ARF7 (+1) per Zhao 2014 (DOI: 10.1038/nature13593)."),
    "T065": ("composite_collapse",
             "max4 KO single: expected=unchanged predicted=increased ratio=4.64. MAX4 is one of three SL-biosynthesis enzymes; current network treats them as INDEPENDENT activators (geomean), so single KO collapses Strigolactone signal. In biology, single max4 has redundant compensation.",
             True, "Encode max4/max1 single KO as gm=0.5 (not 0.0) to preserve partial SL biosynthesis."),
    "T066": ("composite_collapse",
             "max1 KO single: same pattern as T065.",
             True, "Same fix as T065."),
    "T069": ("epistasis_complexity",
             "phyB KO: expected=decreased predicted=increased ratio=1.73. Network's PHYB→HY5→ARF19(+) chain produces the wrong direction for LR. In biology, phyB negatively regulates LR via shoot-to-root HY5 mobile signal (Chen 2016). Direction needs structural fix.",
             False, "Requires structural change (re-route PHYB→LR cascade or add HY5⊣LR direct inhibition); deferred."),
    "T070": ("epistasis_complexity",
             "phyA KO: mapped to PHYB family. Same direction issue as T069.",
             False, "Same as T069."),
    "T071": ("composite_collapse",
             "pin3 single replicate: same as T028.",
             True, "Same fix as T028."),
    "T082": ("epistasis_complexity",
             "10 mM KNO3 high-N: expected=decreased predicted=increased ratio=4.05. Network has Low_Nitrate→CLE+→CLV1+→inhibit LR (correct for low-N feedback). Setting Low_Nitrate=0 removes inhibition, predicting MORE LR. But high-N also inhibits LR via OTHER feedbacks not modelled.",
             False, "Requires adding a high-N inhibition arm (e.g., glutamate/CEPs). Deferred — biological complexity beyond network scope."),
    "T086": ("epistasis_complexity",
             "Far-Red environmental: same direction issue as T069 (PHYB-cascade LR direction wrong).",
             False, "Same as T069."),
    "T096": ("framework_limitation",
             "iaa28-1 + NAA: stabilised IAA28 cannot be degraded by auxin. Per §Trap 5, expected should be unchanged vs mutant baseline. Currently baseline=WT, expected=decreased.",
             True, "Recode T096 baseline WT->mutant, expected decreased->unchanged."),
    "T097": ("framework_limitation",
             "slr-1 (IAA14 stabilised) + NAA: same Trap-5 pattern as T096.",
             True, "Same fix as T096."),
    "T100": ("edge_case",
             "arf7 arf19 + ARF7-GR + Dex rescue: encoded baseline=mutant but no exogenous supply, so mutant_baseline equals perturbed -> ratio=1.0. Should be baseline=WT for this rescue (Dex induces ARF7-GR transgene, comparing to WT not mutant).",
             True, "Switch baseline from mutant to WT for T100/T101/T102."),
    "T101": ("edge_case",
             "arf7 arf19 + LBD16 OE rescue: same baseline issue as T100.",
             True, "Same as T100."),
    "T102": ("edge_case",
             "plt3 plt5 plt7 + PLT1 OE rescue: same baseline issue as T100.",
             True, "Same as T100."),
    "T115": ("edge_case",
             "T101A NRT1.1 phospho-mimic: borderline ratio (0.964). Mechanism encoding (CHL1 gm=2.0) marginal.",
             False, "Borderline; framework limitation."),
    "T116": ("edge_case",
             "T101D NRT1.1 phospho-dead: borderline ratio (1.037). Same as T115.",
             False, "Borderline; framework limitation."),
    "T122": ("framework_limitation",
             "max2 + GR24 (Trap 5): RWR fails because signed-graph propagation cannot enforce perception-gate (algebraic/ODE pass).",
             False, "RWR-specific framework limit."),
    "T123": ("framework_limitation",
             "d14 + GR24 (Trap 5): same as T122.",
             False, "RWR-specific framework limit."),
    "T141": ("epistasis_complexity",
             "cle3 + low-N: encoded Low_Nitrate exo=1.0 dominates -> CLE up -> CLV1 up -> less LR. Single cle3 KO (gm=0.997 in CLE composite) doesn't rescue. Expected=increased per Araya 2014.",
             True, "Tighten CLE composite gm to 0.7 for cle3 single, OR reduce Low_Nitrate exogenous strength."),
    "T149": ("epistasis_complexity",
             "EBR + mild low-N: Low_Nitrate exo=1.0 forces CLE up, dominates BR effect. Predicted=decreased; expected=increased.",
             False, "Low_Nitrate node semantics make combined treatments hard to model. Deferred."),
    "T155": ("edge_case",
             "abi5 + high-N: ODE-only failure. Edge case.",
             False, "ODE borderline."),
    "T156": ("edge_case",
             "Low_Nitrate environmental systemic: ODE borderline.",
             False, "ODE borderline."),
    "T142": ("edge_case",
             "clv1 + low-N: RWR-only failure.",
             False, "RWR signal threshold."),
}

current_failures = set(alg_sum["failures"]) | set(ode_sum["failures"]) | set(rwr_sum["failures"])
failures = []
for tid in sorted(current_failures, key=lambda t: int(t[1:])):
    if tid not in CATEGORIES:
        # Default categorisation
        cat, explanation, fixable, fix = "edge_case", "No detailed diagnosis provided.", False, ""
    else:
        cat, explanation, fixable, fix = CATEGORIES[tid]
    pdata = by_tid.get(tid, {})
    evid = pdata.get("evidence", [{}])[0] if pdata.get("evidence") else {}
    # Predicted direction: pull from whichever method failed
    predicted = "unchanged"
    for method_res in (alg, ode, rwr):
        for r in method_res["detailed_results"]:
            if r["test_id"] == tid and not r["correct"]:
                predicted = r["predicted_direction"]
                break
    failures.append({
        "test_id": tid,
        "gene": pdata.get("gene", ""),
        "perturbation_type": pdata.get("perturbation_type", ""),
        "expected_direction": pdata.get("expected_direction", "unchanged"),
        "predicted_direction": predicted,
        "category": cat,
        "explanation": explanation,
        "evidence": evid.get("doi", ""),
        "fixable": fixable,
        "fix_strategy": fix,
    })

cat_counts = defaultdict(int)
for f in failures:
    cat_counts[f["category"]] += 1
fix_count = sum(1 for f in failures if f["fixable"])

failure_analysis = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lateral_Root_Density",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
    },
    "failures": failures,
    "summary": {
        "total_failures": len(failures),
        "by_category": dict(cat_counts),
        "fixable_count": fix_count,
        "unfixable_count": len(failures) - fix_count,
        "per_method_failure_counts": {
            "algebraic": len(alg_sum["failures"]),
            "ode": len(ode_sum["failures"]),
            "rwr": len(rwr_sum["failures"]),
        },
    },
}

with open(VAL / "failure_analysis.json", "w", encoding="utf-8") as fh:
    json.dump(failure_analysis, fh, indent=2)

# -----------------------------------------------------------------------------
# method_comparison.json
# -----------------------------------------------------------------------------
def entry(m, strengths, weaknesses):
    return {
        "method": m["label"],
        "accuracy": round(m["accuracy"], 4),
        "kappa": round(m["kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(m["convergence_rate"], 4),
        "best_params": m["best_params"],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "failures": m["failures"],
    }

comparison = [
    entry(alg_sum,
          "Captures mass-action steady-state directly; transparent ratios for diagnosis.",
          "Composite-member single-paralog encoding (gm=0.997) is too conservative for major LR TFs (LBD/PIN/AFB), producing ratio≈1.0 'no propagation' on 8 single-KO tests. Rescue tests with mutant baseline + no exogenous_supply collapse to ratio=1.0."),
    entry(ode_sum,
          "Hill kinetics provides smoother propagation; converges 100%; recovers some borderline cases.",
          "Composite-collapse failures persist; high-N (T082) inversion present; T155/T156 ODE borderlines on phospho-variant encoding."),
    entry(rwr_sum,
          "Signed-graph propagation handles cascade amplification more gracefully; highest baseline accuracy (85.7%); 100% convergence and alpha-insensitive.",
          "Cannot enforce perception-gate motif (T122/T123 fail under Trap-5 encoding); same direction inversions on PHYB and PYL8 paths."),
]

recommendation = (
    "Proceed to Step 5 (Refinement). Best method (RWR) at 85.7% sits in the 80-95%% band. "
    "13 failures are flagged fixable via encoding tweaks (composite-paralog gm tuning + Trap-5 baseline corrections + rescue baseline). "
    "Defer structural fixes for PHYB/PYL8 direction inversions and high-N inhibition arm to a future iteration."
)

method_comparison = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lateral_Root_Density",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
    },
    "summary": {
        "best_method": best_label,
        "best_accuracy": round(best["accuracy"], 4),
        "best_accuracy_pct": best["accuracy_pct"],
        "best_kappa": round(best["kappa"], 4),
        "best_mcc": round(best["mcc"], 4),
        "best_frs": round(best["frs"], 4),
        "best_dars": round(best["dars"], 4),
        "tie_break_rule_applied": "",
        "recommendation": recommendation,
        "refinement_needed": True,
    },
    "comparison": comparison,
}

with open(VAL / "method_comparison.json", "w", encoding="utf-8") as fh:
    json.dump(method_comparison, fh, indent=2)

print("Wrote 3 interpretive files.")
print(f"Best method: {best_label} (acc={best['accuracy_pct']}%, kappa={best['kappa']:.4f}, MCC={best['mcc']:.4f})")
print(f"FRS_best={best['frs']:.2f} ({best['frs_band']}); DARS_best={best['dars']:.2f} ({best['dars_band']})")
print(f"Failures: {len(failures)} | fixable={fix_count} | unfixable={len(failures)-fix_count}")
print(f"By category: {dict(cat_counts)}")
print()
print("by_condition (best method):")
best_bc = {"Algebraic": alg_bc, "ODE": ode_bc, "RWR": rwr_bc}[best_label]
for b, v in sorted(best_bc.items()):
    print(f"  {b:25s} n={v['n']:3d}  correct={v['correct']:3d}  acc={v['accuracy_pct']}%")
