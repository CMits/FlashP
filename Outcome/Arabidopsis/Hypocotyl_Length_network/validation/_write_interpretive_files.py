"""
Step 4 interpretive file generator for Hypocotyl_Length.
Produces: accuracy_metrics.json (with by_light_condition), failure_analysis.json,
method_comparison.json.
"""
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

# -----------------------------------------------------------------------------
# Light-condition bucketing
# -----------------------------------------------------------------------------
def bucket_light(cond):
    c = (cond or "").lower()
    if "uv-b" in c or "uv b" in c:
        return "uv-b"
    if "shade" in c or "low r:fr" in c or "high r:fr" in c:
        return "shade"
    # Temperature stress buckets before dark (e.g. "darkness 28C" -> warm)
    if re.search(r"(27|28|29|30)\s?c", c) or "warm" in c:
        return "warm"
    if "dark" in c or "skotomorph" in c:
        return "dark"
    if "frc" in c or "far-red" in c or "far red" in c:
        return "far-red"
    if "blue" in c:
        return "blue"
    if c.startswith("rc") or c == "rc" or "red light" in c:
        return "red"
    if "white" in c or "long day" in c or c == "ld" or "short days" in c:
        return "white"
    if "22c" in c:
        return "white"
    # Hormone/chemical/generic — lump as 'standard'
    return "standard"

# -----------------------------------------------------------------------------
# Per-method result extraction
# -----------------------------------------------------------------------------
def _method_summary(res, label, best_params_str=""):
    m = res["metrics"]
    # failures
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

# Find ODE best K,n and RWR best alpha
ode_params = ode.get("parameters", {})
rwr_params = rwr.get("parameters", {})
ode_best_str = f"K={ode_params.get('K')}, n={ode_params.get('n')}"
rwr_best_str = f"alpha={rwr_params.get('alpha')}"

alg_sum = _method_summary(alg, "Algebraic")
ode_sum = _method_summary(ode, "ODE", ode_best_str)
rwr_sum = _method_summary(rwr, "RWR", rwr_best_str)

# -----------------------------------------------------------------------------
# by_light_condition accuracy per method
# -----------------------------------------------------------------------------
def by_light(res):
    buckets = defaultdict(lambda: {"n": 0, "correct": 0})
    for r in res["detailed_results"]:
        tid = r["test_id"]
        cond = by_tid.get(tid, {}).get("condition", "")
        b = bucket_light(cond)
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

alg_bl = by_light(alg)
ode_bl = by_light(ode)
rwr_bl = by_light(rwr)

# -----------------------------------------------------------------------------
# Best-method selection (accuracy -> kappa -> MCC)
# -----------------------------------------------------------------------------
def rank(m):
    return (m["accuracy"], m["kappa"], m["mcc"])

methods = [alg_sum, ode_sum, rwr_sum]
best = max(methods, key=rank)
best_label = best["label"]

# -----------------------------------------------------------------------------
# accuracy_metrics.json
# -----------------------------------------------------------------------------
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
        "flash_p_version": "2.0",
        "phenotype": "Hypocotyl_Length",
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
    "by_light_condition": {
        "algebraic": alg_bl,
        "ode": ode_bl,
        "rwr": rwr_bl,
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
# failure_analysis.json
# -----------------------------------------------------------------------------
# Build failure categorisation.  Use predicted direction from the best method
# (Algebraic here) when available, else from whichever method failed.
CATEGORIES = {
    "T003": ("framework_limitation",
             "ACC treatment at warm temperature (28C): the ethylene-at-high-temperature uncoupling "
             "(thermo-induced EIN3 degradation / desensitisation) is not encoded. Network always "
             "propagates Ethylene->EIN3->inhibit hypocotyl, predicting 'decreased'; observed is 'unchanged'.",
             False,
             ""),
    "T004": ("epistasis_complexity",
             "afb5 + picloram: AFB5-preferential auxin (picloram) interaction. afb5 KO is encoded as "
             "a weak (gm=0.997) perturbation on the TIR1 composite, then Auxin supply dominates the "
             "prediction (increased). Expected is decreased because AFB5 is the preferential receptor "
             "for picloram specifically.",
             True,
             "Split AFB5 out of TIR1 composite, or add a picloram-specific dummy-edge so AFB5 KO "
             "strengthens auxin response block."),
    "T022": ("epistasis_complexity",
             "bin2-1 dominant gain-of-function in darkness: network encodes BIN2 gm=2.0 -> stronger "
             "BZR inhibition -> lower hypocotyl. Observed is increased. BIN2 has BR-signalling-"
             "independent effects on PIFs / other substrates (Li et al.) not captured as edges from "
             "BIN2 to PIF/AUXIN targets in this network.",
             True,
             "Add BIN2 -> PIF3/4/5 (inhibition of PIF degradation, net positive on PIF) and/or "
             "BIN2 -> ARF6 (negative) edges to reproduce non-BR BIN2 effects."),
    "T046": ("framework_limitation",
             "ein2 + ACC: ratio=1.0 (no change from WT). The Ethylene hormone node has no direct "
             "activation edge into EIN2 (EIN2 activators=[]); the ethylene axis therefore cannot "
             "propagate supply into downstream EIN3/hypocotyl differences, so KO of EIN2 does not "
             "measurably change the baseline in the algebraic model. This is a perception-gate "
             "wiring gap.",
             True,
             "Add edge Ethylene->EIN2 (+1) so the ethylene signalling cascade actually propagates "
             "supply into EIN3."),
    "T047": ("framework_limitation",
             "ein3 + ACC: same ethylene-axis wiring gap as T046. EIN3 changes alone do not propagate "
             "because the WT baseline already has EIN3 saturated or unaffected by Ethylene supply.",
             True,
             "Same fix as T046 (wire Ethylene->EIN2 so Ethylene supply has a downstream effect)."),
    "T049": ("composite_collapse",
             "ein3 eil1 double + ACC: EIL1 is collapsed into EIN3. Combined with the same ethylene-"
             "axis wiring gap, the double KO cannot propagate its effect.",
             True,
             "Fix ethylene-axis wiring (Ethylene->EIN2) and keep EIN3 as composite representative "
             "for EIN3/EIL1."),
    "T077": ("edge_case",
             "NAA exogenous auxin treatment: algebraic passes (+increased), but ODE gives ratio "
             "1.026 just under the 5%% direction threshold. Signal dilution through cascade at K=0.5 "
             "n=1 makes the prediction borderline unchanged.",
             True,
             "Minor: add direct Auxin->Hypocotyl_Length edge OR tune ODE towards higher n so "
             "cooperativity amplifies a small auxin increase."),
    "T099": ("framework_limitation",
             "PIF7 phospho-dead dominant form under shade: network ratio 1.035 -> classified as "
             "'unchanged' (threshold 5%%). The PIF7 gm=2.0 perturbation is diluted by the geometric-"
             "mean activator structure at the Hypocotyl_Length node (5 activators -> 1/5 exponent).",
             True,
             "Shorten the PIF7->Hypocotyl_Length path or add a direct PIF7->Hypocotyl_Length "
             "activator edge to avoid geometric-mean dilution."),
    "T104": ("framework_limitation",
             "Picloram at 30C: thermomorphogenic hypocotyl elongation at 30C is not directly "
             "modelled as a source node; auxin supply alone fails to cross threshold in the ODE "
             "method at K=0.5, n=1.",
             False,
             ""),
    "T112": ("framework_limitation",
             "tir1 + auxin treatment: classical Trap 5 (signalling-mutant rescue). Network adds "
             "Auxin exogenous=1.0 regardless of whether TIR1 is functional, so the prediction "
             "reverts to 'unchanged' rather than 'decreased'. Perception-gate motif on TIR1 not "
             "enforced.",
             False,
             "Framework limitation per §Trap 5. Can only be remedied by enforcing Perception Gate "
             "purity (remove Auxin bypass edges) and fully gating Auxin signalling through TIR1."),
    "T128": ("epistasis_complexity",
             "gid1a gid1b double KO: network encodes GID1 composite gm=0.5 -> DELLA accumulates -> "
             "shorter hypocotyl (decreased). Observed is increased in the specific double; this is "
             "a GID1-paralog-specific context that a single composite cannot resolve.",
             True,
             "Split GID1A/B/C into separate nodes to capture paralog-specific DELLA-preference."),
    "T129": ("composite_collapse",
             "gid1b gid1c double KO: algebraic passes (unchanged), but RWR predicts decreased "
             "because the composite GID1 gm=0.99 still carries diffusive signal in the random-walk "
             "method. Resolution loss due to composite collapse.",
             True,
             "Split GID1 paralogs or tune RWR signal threshold."),
    "T137": ("edge_case",
             "bas1 sob7 double KO in light: network predicts increased (matches broader BR-"
             "catabolism biology: more BR -> longer hypocotyl); test expected_direction 'decreased' "
             "may be incorrect in the encoded test (bas1 sob7 are BR-inactivating enzymes; KO "
             "produces elongated hypocotyls). Possible test-encoding edge case.",
             True,
             "Re-check source paper: if direction should be 'increased', fix expected_direction "
             "in T137; otherwise add an unmodelled secondary path."),
}

# Predicted-direction lookup: pick the algebraic predicted direction if that method failed,
# else ODE, else RWR.
pred_by_tid = {}
for method_res in (alg, ode, rwr):
    for r in method_res["detailed_results"]:
        tid = r["test_id"]
        if tid in CATEGORIES and tid not in pred_by_tid and not r["correct"]:
            pred_by_tid[tid] = r["predicted_direction"]

# Only include tests that still fail in at least one method after iter 4
current_failures = set(alg_sum["failures"]) | set(ode_sum["failures"]) | set(rwr_sum["failures"])
failures = []
for tid, (cat, explanation, fixable, fix) in CATEGORIES.items():
    if tid not in current_failures:
        continue
    pdata = by_tid.get(tid, {})
    evid = pdata.get("evidence", [{}])[0] if pdata.get("evidence") else {}
    failures.append({
        "test_id": tid,
        "gene": pdata.get("gene", ""),
        "perturbation_type": pdata.get("perturbation_type", ""),
        "expected_direction": pdata.get("expected_direction", "unchanged"),
        "predicted_direction": pred_by_tid.get(tid, "unchanged"),
        "category": cat,
        "explanation": explanation,
        "evidence": evid.get("doi", ""),
        "fixable": fixable,
        "fix_strategy": fix,
    })

# Sort by test_id numerical
failures.sort(key=lambda f: int(f["test_id"][1:]))

cat_counts = defaultdict(int)
for f in failures:
    cat_counts[f["category"]] += 1
fix_count = sum(1 for f in failures if f["fixable"])

failure_analysis = {
    "metadata": {
        "flash_p_version": "2.0",
        "phenotype": "Hypocotyl_Length",
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
          "Highest kappa (0.84, 'almost perfect' band); robust convergence given "
          "step-wise algebraic iteration; lowest failure count tied with RWR at 10; "
          "DARS 12.02 (exceptional).",
          "Convergence rate 91.4% (slightly below ODE/RWR 100%); bounded-inverse saturation "
          "produces ratio=1.0 on some ethylene-axis tests (T046/T047/T049), masking directional "
          "effects that would otherwise be directional."),
    entry(ode_sum,
          "100% convergence; smooth Hill-function kinetics capture saturation more gracefully.",
          "Lowest accuracy (89.7%) and lowest kappa (0.81); best sensitivity sweep lands at K=0.5, "
          "n=1 which is close to linear and loses cooperative amplification; borderline failures "
          "on T077 and T104 (ratios just under threshold)."),
    entry(rwr_sum,
          "Highest MCC (0.84) reflecting best-balanced per-class performance; 100% convergence; "
          "fully alpha-insensitive (91.4% across every alpha in {0.5..0.99}).",
          "Kappa (0.83) slightly below algebraic (0.84); alpha insensitivity also means sensitivity "
          "analysis is uninformative; composite-collapse resolution loss shows up on T129 "
          "(gid1b gid1c double)."),
]

recommendation = (
    "Proceed to Step 5 (Refinement). Best method achieved 91.4% accuracy with kappa 0.84 "
    "('almost perfect') and DARS 12.02 (exceptional, tier >=12+). The failure budget is "
    "10 tests (8.6%%), of which 9 are classified as fixable. Highest-leverage fix: wire "
    "Ethylene->EIN2 (+1) to recover the ethylene-signalling cascade (unlocks T046/T047/T049). "
    "Lower-leverage: split GID1 composite (T128/T129), split AFB5 out of TIR1 (T004), and add "
    "BIN2->PIF edges (T022). Trap-5 and warm-temperature tests (T003, T104, T112) should be "
    "accepted as framework limitations rather than chased."
)

method_comparison = {
    "metadata": {
        "flash_p_version": "2.0",
        "phenotype": "Hypocotyl_Length",
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
        "tie_break_rule_applied": (
            "Algebraic and RWR tied on accuracy 91.4%; Algebraic wins on kappa (0.8367 > 0.8285)."
            if alg_sum["accuracy"] == rwr_sum["accuracy"] else ""
        ),
        "recommendation": recommendation,
        "refinement_needed": True,
    },
    "comparison": comparison,
}

with open(VAL / "method_comparison.json", "w", encoding="utf-8") as fh:
    json.dump(method_comparison, fh, indent=2)

# ---- console summary ----
print("Wrote 3 interpretive files.")
print(f"Best method: {best_label} (acc={best['accuracy_pct']}%, kappa={best['kappa']}, MCC={best['mcc']})")
print(f"FRS_best={best['frs']} ({best['frs_band']}); DARS_best={best['dars']} ({best['dars_band']})")
print(f"Failures: {len(failures)} | fixable={fix_count} | unfixable={len(failures)-fix_count}")
print(f"By category: {dict(cat_counts)}")
print()
print("by_light_condition (algebraic):")
for b, v in sorted(alg_bl.items()):
    print(f"  {b:12s} n={v['n']:3d}  correct={v['correct']:3d}  acc={v['accuracy_pct']}%")
