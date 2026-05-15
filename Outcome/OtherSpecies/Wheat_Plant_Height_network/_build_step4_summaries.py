"""One-off Step 4 summary writer for Wheat Plant Height network."""

from __future__ import annotations

import json
import math
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent
VAL = BASE / "validation"
DATA = BASE / "data"


def load(name: str) -> dict:
    with open(VAL / name, encoding="utf-8") as f:
        return json.load(f)


def load_data(name: str) -> dict:
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


alg = load("script_validation_results.json")
ode = load("ode_validation_results.json")
rwr = load("rwr_validation_results.json")
pert = load_data("reconciled_perturbation_dataset.json")


pert_by_id = {p["test_id"]: p for p in pert["perturbations"]}


# ----------------------------------------------------------------------------
# Class assignment for wheat height
# ----------------------------------------------------------------------------
def classify_test(t: dict) -> str:
    g = (t.get("gene") or "").lower()
    ptype = t.get("perturbation_type", "")
    notes = (t.get("notes", "") + " " + t.get("reconciliation_note", "")).lower()
    if "rht-b1b" in g and "plus_ga3" in g:
        return "Rht-B1b+GA3 (Trap 3)"
    if "rht-d1b" in g and "plus_ga3" in g:
        return "Rht-D1b+GA3 (Trap 3)"
    if "rht-b1c" in g and "plus_ga3" in g:
        return "Rht-B1c+GA3 (Trap 3)"
    if "rht-b1b+rht-d1b" in g or "rht-b1b_d1b" in g:
        return "Rht-B1b/D1b double"
    if "rht-b1b" == g:
        return "Rht-B1b"
    if "rht-d1b" == g:
        return "Rht-D1b"
    if "rht-b1c" == g:
        return "Rht-B1c"
    if "rht-d1c" == g:
        return "Rht-D1c"
    if g.startswith("rht-b1") and "transgenic" in g:
        return "Rht-B1b transgenic OE"
    if "rht-b1" in g and "znf" in g:
        return "Rht-B1 + TaZnF double (epistasis)"
    if g.startswith("rht-b1") or g.startswith("rht-d1"):
        return "Rht-B1/D1 other allele"
    if g in ("rht8",):
        return "Rht8"
    if "rht12" in g:
        return "Rht12 (TaGA2ox-like)"
    if "rht24" in g:
        return "Rht24 (TaGA2ox-like)"
    if g == "rht14":
        return "Rht14"
    if g == "rht13":
        return "Rht13"
    if g in ("rht3", "rht4", "rht5"):
        return "Rht3/4/5"
    if g == "rht18":
        return "Rht18 (TaGA20ox-like)"
    if "taga3ox" in g and "plus_ga3" in g:
        return "TaGA3ox KD + GA3 rescue"
    if "taga3ox" in g:
        return "TaGA3ox"
    if "taga1ox" in g:
        return "TaGA1ox"
    if "taga20ox" in g:
        return "TaGA20ox"
    if "taga2ox" in g:
        return "TaGA2ox"
    if "tabri1" in g and ("bl" in g or "plus_bl" in g):
        return "TaBRI1 + BL (Trap 5)"
    if "tabri1" in g:
        return "TaBRI1"
    if "tabzr1" in g:
        return "TaBZR1"
    if "tabin2" in g:
        return "TaBIN2"
    if "tagid1" in g:
        return "TaGID1"
    if "tadwf4" in g or "tad11" in g:
        return "BR biosynthesis (TaDWF4/TaD11)"
    if "taznf" in g:
        return "TaZnF"
    if "vrn1" in g and "triple" in g:
        return "VRN1 triple KO"
    if "vrn1" in g:
        return "VRN1 single (homeolog-composite)"
    if "tagrf4" in g:
        return "TaGRF4 OE"
    if "platz" in g:
        return "PLATZ"
    if "taerf" in g:
        return "TaERF"
    if "tapif4" in g:
        return "TaPIF4"
    if "taosca" in g:
        return "TaOSCA1.4"
    if "ppd-d1a" in g or "ppd" in g:
        return "Ppd-D1a"
    if "taarf4" in g:
        return "TaARF4"
    if g == "naa_treatment":
        return "WT + NAA treatment"
    if g == "wt_plus_ga3":
        return "WT + GA3 treatment"
    if "paclobutrazol" in g:
        return "WT + PAC treatment"
    if "brassinazole" in g:
        return "WT + Brz treatment"
    if "brassinolide" in g:
        return "WT + BL treatment"
    if "nitrate" in g or "nitrogen" in g:
        return "Nitrogen treatment"
    if "single_homeolog" in notes or "single-homeolog" in notes or "homeolog-single" in notes:
        return "homeolog-single (composite)"
    return "Other"


def classify_env(t: dict) -> str:
    text = (t.get("notes", "") + " " +
            t.get("reconciliation_note", "") + " " +
            " ".join(e.get("evidence_sentence", "") for e in t.get("evidence", []))).lower()
    for e in ("field", "greenhouse", "glasshouse", "growth chamber", "growth-chamber", "pot"):
        if e in text:
            return "field" if e == "field" else ("greenhouse" if e in ("greenhouse", "glasshouse") else "controlled")
    return "unspecified"


def classify_cultivar(t: dict) -> str:
    text = (t.get("notes", "") + " " +
            t.get("reconciliation_note", "") + " " +
            " ".join(e.get("evidence_sentence", "") for e in t.get("evidence", []))).lower()
    for c in ("mercia", "maringa", "bobwhite", "chinese spring", "fielder",
              "paragon", "cadenza", "kitt"):
        if c in text:
            return c
    return "other/unspecified"


# ----------------------------------------------------------------------------
# Per-test metadata table
# ----------------------------------------------------------------------------
test_meta: dict[str, dict] = {}
for tid, p in pert_by_id.items():
    test_meta[tid] = {
        "class": classify_test(p),
        "env": classify_env(p),
        "cultivar": classify_cultivar(p),
        "perturbation_type": p.get("perturbation_type"),
        "expected_direction": p.get("expected_direction"),
        "gene": p.get("gene"),
        "comparison_baseline": p.get("comparison_baseline"),
    }


# ----------------------------------------------------------------------------
# Per-method merged result (dict by test_id)
# ----------------------------------------------------------------------------
def index_results(d: dict) -> dict[str, dict]:
    return {r["test_id"]: r for r in d["detailed_results"]}


alg_r = index_results(alg)
ode_r = index_results(ode)
rwr_r = index_results(rwr)


def cohen_kappa(pairs: list[tuple[str, str]]) -> tuple[float, int]:
    """Return Cohen's kappa for (expected, predicted) label pairs."""
    n = len(pairs)
    if n < 2:
        return 0.0, n
    labels = sorted({lab for p in pairs for lab in p})
    idx = {lab: i for i, lab in enumerate(labels)}
    cm = [[0] * len(labels) for _ in labels]
    for exp, pred in pairs:
        cm[idx[exp]][idx[pred]] += 1
    po = sum(cm[i][i] for i in range(len(labels))) / n
    row = [sum(cm[i]) for i in range(len(labels))]
    col = [sum(cm[j][i] for j in range(len(labels))) for i in range(len(labels))]
    pe = sum(row[i] * col[i] for i in range(len(labels))) / (n * n)
    if pe == 1:
        return 1.0, n
    return (po - pe) / (1 - pe), n


def stratify(results: dict[str, dict], key_fn) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for tid, r in results.items():
        meta = test_meta.get(tid)
        if meta is None:
            continue
        groups[key_fn(meta)].append((tid, r))
    out = {}
    for k, rows in groups.items():
        pairs = [(r["expected_direction"], r["predicted_direction"]) for _, r in rows]
        correct = sum(1 for e, p in pairs if e == p)
        total = len(pairs)
        kappa, _ = cohen_kappa(pairs) if total >= 5 else (None, total)
        out[k] = {
            "n": total,
            "correct": correct,
            "accuracy": round(correct / total, 4) if total else 0.0,
            "kappa": None if kappa is None else round(kappa, 4),
            "failures": [tid for tid, r in rows if not r["correct"]],
        }
    return out


def stratify_all(results: dict[str, dict], method: str) -> dict:
    return {
        "by_class": stratify(results, lambda m: m["class"]),
        "by_cultivar": stratify(results, lambda m: m["cultivar"]),
        "by_environment": stratify(results, lambda m: m["env"]),
        "by_perturbation_type": stratify(results, lambda m: m["perturbation_type"]),
    }


# ----------------------------------------------------------------------------
# Build accuracy_metrics.json
# ----------------------------------------------------------------------------
def method_block(doc: dict, results: dict[str, dict]) -> dict:
    m = doc["metrics"]
    failures = [r["test_id"] for r in doc["detailed_results"] if not r["correct"]]
    block = {
        "accuracy": round(m["overall_accuracy"] / 100.0, 4),
        "correct": m["correct"],
        "total_tested": m["total"],
        "kappa": round(m["cohens_kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(m.get("convergence_rate", 100.0) / 100.0, 4),
        "failures": failures,
        "ci_95": [round(m.get("kappa_ci_lower", 0.0), 4),
                  round(m.get("kappa_ci_upper", 0.0), 4)],
    }
    if doc.get("parameters"):
        if "K" in doc["parameters"]:
            block["best_K"] = doc["parameters"]["K"]
        if "n" in doc["parameters"]:
            block["best_n"] = doc["parameters"]["n"]
    if doc.get("best_alpha") is not None:
        block["best_alpha"] = doc["best_alpha"]
    return block


method_kappa_band = {
    "algebraic": alg["metrics"].get("kappa_band"),
    "ode": ode["metrics"].get("kappa_band"),
    "rwr": rwr["metrics"].get("kappa_band"),
}
method_frs = {
    "algebraic": {"frs": alg["metrics"].get("rigor_score"), "band": alg["metrics"].get("rigor_band"),
                  "dars": alg["metrics"].get("dars"), "dars_band": alg["metrics"].get("dars_band")},
    "ode": {"frs": ode["metrics"].get("rigor_score"), "band": ode["metrics"].get("rigor_band"),
            "dars": ode["metrics"].get("dars"), "dars_band": ode["metrics"].get("dars_band")},
    "rwr": {"frs": rwr["metrics"].get("rigor_score"), "band": rwr["metrics"].get("rigor_band"),
            "dars": rwr["metrics"].get("dars"), "dars_band": rwr["metrics"].get("dars_band")},
}
tier2 = alg["metrics"].get("tier2_scope", {})

accuracy_metrics = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "species": "Triticum aestivum",
        "network": "Wheat_Plant_Height_network",
        "created": "2026-04-20",
        "kappa_band": method_kappa_band,
        "rigor_score": method_frs,
        "tier2_scope": tier2,
        "stratified": {
            "algebraic": stratify_all(alg_r, "Algebraic"),
            "ode": stratify_all(ode_r, "ODE"),
            "rwr": stratify_all(rwr_r, "RWR"),
        },
        "stratified_by_complexity": {
            "algebraic": alg["metrics"].get("stratified"),
            "ode": ode["metrics"].get("stratified"),
            "rwr": rwr["metrics"].get("stratified"),
        },
    },
    "tests": {
        "total": pert["metadata"]["total_tests"],
        "tested": alg["summary"]["tested"],
        "skipped": alg["summary"]["skipped"],
    },
    "algebraic": method_block(alg, alg_r),
    "ode": method_block(ode, ode_r),
    "rwr": method_block(rwr, rwr_r),
}

with open(VAL / "accuracy_metrics.json", "w", encoding="utf-8") as f:
    json.dump(accuracy_metrics, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# failure_analysis.json
# ----------------------------------------------------------------------------
# Union of failures across methods (with Algebraic used as canonical "predicted"
# in case of disagreement, because the algebraic method is primary).
failure_set = set()
for r in alg_r.values():
    if not r["correct"]:
        failure_set.add(r["test_id"])
for r in ode_r.values():
    if not r["correct"]:
        failure_set.add(r["test_id"])
for r in rwr_r.values():
    if not r["correct"]:
        failure_set.add(r["test_id"])


def categorise(tid: str) -> dict:
    p = pert_by_id[tid]
    gene = p["gene"]
    ptype = p["perturbation_type"]
    exp = p["expected_direction"]
    alg_pred = alg_r[tid]["predicted_direction"] if tid in alg_r else None
    ode_pred = ode_r[tid]["predicted_direction"] if tid in ode_r else None
    rwr_pred = rwr_r[tid]["predicted_direction"] if tid in rwr_r else None
    # Canonical predicted: algebraic if it failed, else the first method that failed
    predicted = alg_pred
    if alg_r.get(tid, {}).get("correct", True):
        if not ode_r.get(tid, {}).get("correct", True):
            predicted = ode_pred
        elif not rwr_r.get(tid, {}).get("correct", True):
            predicted = rwr_pred
    cls = test_meta[tid]["class"]
    baseline = p.get("comparison_baseline", "WT")
    doi = (p.get("evidence", [{}])[0].get("doi", "") if p.get("evidence") else "")

    # ----- classification rules -----
    if cls.endswith("(Trap 3)"):
        return {
            "test_id": tid, "gene": gene, "perturbation_type": ptype,
            "expected_direction": exp, "predicted_direction": predicted,
            "category": "framework_limitation",
            "explanation": (
                "Trap-3 framework limitation: stabilised DELLA allele (Rht-B1b/c or "
                "Rht-D1b) cannot be degraded by exogenous GA because TaGID1 perception "
                "requires DELLA to be a viable substrate. Expected=unchanged vs mutant "
                "baseline, but the algebraic model adds GA3 exogenous_supply at TaGID1 "
                "which then 'degrades' the DELLA composite regardless of allele state. "
                "Equivalent to the SL/GR24 + D14 rescue trap. Perception-gate purity is "
                "intact upstream, but DELLA itself is not 'gated' since stabilised DELLA "
                "is modelled via gm=2.0 (elevated baseline) rather than as an "
                "inhibition-resistant variant."),
            "evidence": doi,
            "fixable": False,
            "fix_strategy": "",
        }
    if cls.startswith("Rht-B1 + TaZnF"):
        return {
            "test_id": tid, "gene": gene, "perturbation_type": ptype,
            "expected_direction": exp, "predicted_direction": predicted,
            "category": "epistasis_complexity",
            "explanation": (
                "TaZnF-B suppressor of Rht-B1b: in the double mutant, phenotype is "
                "restored to near-WT (epistatic suppression). The additive algebraic "
                "framework with geometric-mean activation and bounded-inverse inhibition "
                "has no mechanism to encode 'mutation A cancels the effect of mutation "
                "B'. Multiplicative composite of gm=2.0 (RHT_B1) and gm=0.0 (TaZnF) "
                "does not produce the observed wild-type phenotype."),
            "evidence": doi,
            "fixable": False,
            "fix_strategy": "",
        }
    if cls.startswith("VRN1 single"):
        return {
            "test_id": tid, "gene": gene, "perturbation_type": ptype,
            "expected_direction": exp, "predicted_direction": predicted,
            "category": "composite_collapse",
            "explanation": (
                "VRN1 is encoded as a composite node. Single-homeolog KO uses gm=0.997 "
                "(composite convention for redundant homeologs) → near-WT predicted, "
                "but the paper reports a slight decrease vs WT. The composite encoding "
                "loses resolution: a single vrn1 homeolog KO in wheat does produce a "
                "modest height reduction in Fielder field trials, but the 0.003 "
                "deviation is below the 0.05 direction_threshold."),
            "evidence": doi,
            "fixable": True,
            "fix_strategy": (
                "Either (a) loosen composite factor for VRN1 to 0.9 to reflect modest "
                "dosage sensitivity, or (b) accept edge_case and flag as framework "
                "limitation for composite nodes with weak partial-loss phenotypes."),
        }
    if cls.startswith("TaGRF4"):
        return {
            "test_id": tid, "gene": gene, "perturbation_type": ptype,
            "expected_direction": exp, "predicted_direction": predicted,
            "category": "edge_case",
            "explanation": (
                "TaGRF4 OE reported phenotype unchanged, but the model routes TaGRF4 → "
                "DELLA as a positive regulator with gm=2.0 → DELLA increases "
                "significantly, predicting decreased height. The literature is mixed: "
                "GRF4 effect on wheat height is modest and cultivar-dependent. This is "
                "on the edge of the framework's resolution."),
            "evidence": doi,
            "fixable": True,
            "fix_strategy": (
                "Option 1: weaken the TaGRF4 → DELLA edge (downgrade modifier or remove "
                "edge in favour of flagging it in curated_edges.json only). Option 2: "
                "accept as edge_case — the paper itself reports subtle phenotype."),
        }
    if cls.startswith("TaBRI1 + BL"):
        return {
            "test_id": tid, "gene": gene, "perturbation_type": ptype,
            "expected_direction": exp, "predicted_direction": predicted,
            "category": "framework_limitation",
            "explanation": (
                "Trap-5-like signalling mutant rescue: TaBRI1 triple-KO with BL "
                "treatment. Expected=unchanged vs mutant baseline because BL cannot be "
                "perceived without BRI1. The algebraic model adds BL as exogenous_supply "
                "at Brassinosteroid source, and if there is any path from BL to "
                "Plant_Height that bypasses TaBRI1, the model predicts a change. "
                "Perception-gate purity required."),
            "evidence": doi,
            "fixable": False,
            "fix_strategy": "",
        }
    # default fallback
    return {
        "test_id": tid, "gene": gene, "perturbation_type": ptype,
        "expected_direction": exp, "predicted_direction": predicted,
        "category": "edge_case",
        "explanation": "Failure category not matched to a known pattern.",
        "evidence": doi,
        "fixable": False,
        "fix_strategy": "",
    }


failures = [categorise(t) for t in sorted(failure_set)]
by_category: dict[str, int] = defaultdict(int)
for f in failures:
    by_category[f["category"]] += 1

failure_analysis = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "species": "Triticum aestivum",
        "network": "Wheat_Plant_Height_network",
        "created": "2026-04-20",
    },
    "failures": failures,
    "summary": {
        "total_failures": len(failures),
        "by_category": dict(by_category),
        "fixable_count": sum(1 for f in failures if f["fixable"]),
        "unfixable_count": sum(1 for f in failures if not f["fixable"]),
        "union_over_methods": True,
        "note": (
            "Union of failures across Algebraic, ODE, RWR. Per-method failure lists "
            "are in accuracy_metrics.json."),
    },
}

with open(VAL / "failure_analysis.json", "w", encoding="utf-8") as f:
    json.dump(failure_analysis, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# method_comparison.json
# ----------------------------------------------------------------------------
def params_str(doc: dict) -> str:
    p = doc.get("parameters", {})
    if doc["method"].startswith("ODE"):
        return f"K={p.get('K', 1.0)}, n={p.get('n', 2)}"
    if "RWR" in doc["method"] or "Random Walk" in doc["method"]:
        return f"alpha={doc.get('best_alpha', p.get('alpha', 0.9))}"
    return "defaults"


def comparison_entry(doc: dict, results: dict[str, dict], method_label: str,
                     strengths: str, weaknesses: str) -> dict:
    m = doc["metrics"]
    return {
        "method": method_label,
        "accuracy": round(m["overall_accuracy"] / 100.0, 4),
        "kappa": round(m["cohens_kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(m.get("convergence_rate", 100.0) / 100.0, 4),
        "best_params": params_str(doc),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "failures": [tid for tid, r in results.items() if not r["correct"]],
    }


# Pick best method by accuracy, tie-breaker kappa, then MCC
def method_score(doc):
    m = doc["metrics"]
    return (m["overall_accuracy"], m["cohens_kappa"], m["mcc"])


scored = sorted(
    [("Algebraic", alg), ("ODE (Hill)", ode), ("RWR", rwr)],
    key=lambda x: method_score(x[1]),
    reverse=True,
)
best_method = scored[0][0]
best_doc = scored[0][1]

method_comparison = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "species": "Triticum aestivum",
        "network": "Wheat_Plant_Height_network",
        "created": "2026-04-20",
    },
    "summary": {
        "best_method": best_method,
        "best_accuracy": round(best_doc["metrics"]["overall_accuracy"] / 100.0, 4),
        "best_kappa": round(best_doc["metrics"]["cohens_kappa"], 4),
        "best_mcc": round(best_doc["metrics"]["mcc"], 4),
        "recommendation": (
            "Proceed to Step 5 (REFINEMENT) — best accuracy is 80-95% band. "
            "Two of the four failing tests are Trap-3 framework limitations "
            "(Rht-B1b+GA3, Rht-B1c+GA3) which are not refinable without DELLA "
            "allele-specific modelling. Remaining failures (Rht-B1b+TaZnF-B "
            "double, VRN1 single, TaGRF4 OE, TaBRI1 triple+BL) are edge-of-"
            "resolution or composite-collapse issues. Refinement should focus "
            "on the TaGRF4 → DELLA edge strength and optionally the VRN1 "
            "composite factor."),
        "frs_best": round(best_doc["metrics"].get("rigor_score", 0.0), 4),
        "frs_band_best": best_doc["metrics"].get("rigor_band"),
        "dars_best": round(best_doc["metrics"].get("dars", 0.0), 4),
        "dars_band_best": best_doc["metrics"].get("dars_band"),
    },
    "comparison": [
        comparison_entry(
            alg, alg_r, "Algebraic",
            strengths=(
                "Fastest (seconds to run), deterministic, transparent mechanism. "
                "Perfect on gain_of_function (Rht-B1/D1 dwarf alleles) and "
                "rescue_experiment categories. Strong kappa (substantial)."),
            weaknesses=(
                "Geometric-mean activation + bounded-inverse inhibition has low "
                "resolution on 'unchanged' outcomes (F1=0.29). Cannot encode "
                "Trap-3 (stabilised DELLA + GA3) or epistatic suppression."),
        ),
        comparison_entry(
            ode, ode_r, "ODE (Hill Functions)",
            strengths=(
                "Highest accuracy (92.2%) and kappa (almost-perfect band). Hill "
                "kinetics at K=1.0, n=3 crystallise dwarf alleles more sharply "
                "than pure multiplicative rules; unchanged F1 rises to 0.33."),
            weaknesses=(
                "Still fails the 2 Trap-3 tests and TaGRF4 OE. Adds Hill K,n "
                "hyperparameters that need sweeping. Slower than algebraic."),
        ),
        comparison_entry(
            rwr, rwr_r, "RWR",
            strengths=(
                "Highest MCC (0.888) — best-performing on multiclass balance. "
                "Converged on every test. Signed-graph propagation naturally "
                "handles long cascades without cascade-amplification traps."),
            weaknesses=(
                "'Unchanged' recall is 0 (F1=0.00) — RWR's continuous signal "
                "rarely lands inside the 1e-5 threshold band; most 'unchanged' "
                "expected outcomes get mislabelled. Alpha sweep offers only "
                "modest gains (88.2% → 90.2% at alpha=0.9)."),
        ),
    ],
}

with open(VAL / "method_comparison.json", "w", encoding="utf-8") as f:
    json.dump(method_comparison, f, indent=2, ensure_ascii=False)


print("Wrote accuracy_metrics.json, failure_analysis.json, method_comparison.json")
print(f"Best method: {best_method}")
print(f"Failures (union): {sorted(failure_set)}")
