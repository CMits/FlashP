"""
Step 4 summary builder for Ecoli_Lycopene_network.

Reads the three validator outputs + reconciled perturbation dataset, computes
E. coli lycopene-specific stratifications (perturbation class / chassis /
condition), categorises failures of the best method, and writes the three
interpretive summary files:

    validation/accuracy_metrics.json
    validation/failure_analysis.json
    validation/method_comparison.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation"
DATA = ROOT / "data"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


alg = load(VAL / "script_validation_results.json")
ode = load(VAL / "ode_validation_results.json")
rwr = load(VAL / "rwr_validation_results.json")
pert = load(DATA / "reconciled_perturbation_dataset.json")

pert_by_id = {p["test_id"]: p for p in pert["perturbations"]}


# ----------------------------------------------------------------------
# Classification helpers
# ----------------------------------------------------------------------

MEP_GENES = {"DXS", "DXR", "ISPD", "ISPE", "ISPF", "ISPG", "ISPH", "IDI"}
MVA_GENES = {"ATOB", "HMGS", "HMGR", "MVK", "PMK", "MVD", "MVA_CASSETTE",
             "IDI_MVA", "ERG13", "TERG8", "ERG12", "ERG19", "ACCT"}
CAROTENOID_GENES = {"CRTE", "CRTB", "CRTI", "CRTY", "CRTZ"}
CENTRAL_METAB_GENES = {"PGI", "ZWF", "PPC", "GLTA", "ACKA", "ACEE", "ACEF",
                       "PYKF", "PYKA", "PTSHICRR", "FBA", "GAPA", "PFKA"}
REGULATOR_GENES = {"RPOS", "RPOH", "SOXR", "SOXS", "ARCA", "ARCB", "FNR",
                   "CRP", "FADR", "IHF", "CYA"}
ISPB_GENES = {"ISPB"}

CHASSIS_PATTERNS = [
    ("BL21", r"\bBL21"),
    ("MG1655", r"MG1655"),
    ("W3110", r"W3110"),
    ("DH5alpha", r"DH5"),
    ("JM109", r"JM109"),
    ("XL1", r"XL1"),
    ("TOP10", r"TOP10"),
    ("HB101", r"HB101"),
]

CARBON_PATTERNS = [
    ("glucose", r"glucose|glc"),
    ("glycerol", r"glycerol"),
    ("xylose", r"xylose"),
    ("succinate", r"succinate"),
]

TEMPERATURE_PATTERNS = [
    ("30C", r"30\s*[\u00b0C]|30C"),
    ("37C", r"37\s*[\u00b0C]|37C"),
]

GROWTH_PATTERNS = [
    ("fed-batch", r"fed[-\s]?batch"),
    ("bioreactor", r"bioreactor|fermentor|fermenter"),
    ("shake-flask", r"shake[-\s]?flask|flask"),
]

OXYGEN_PATTERNS = [
    ("microaerobic", r"microaerobic|micro-aerobic"),
    ("anaerobic", r"\banaerobic"),
    ("aerobic", r"\baerobic"),
]


def classify_perturbation(p):
    """Return the perturbation class for an E. coli lycopene test."""
    genes_up = [g.upper() for g in (p.get("network_gene") or [])]
    gene_str = (p.get("gene") or "").upper()
    all_genes = set(genes_up) | {gene_str}
    pt = p.get("perturbation_type", "")
    notes = (p.get("notes") or "").lower()
    ev = " ".join(e.get("evidence_sentence", "") for e in p.get("evidence", [])).lower()
    text = notes + " " + ev

    # Engineering-input (inducer / temperature / carbon / oxygen)
    if any(tok in text for tok in ["iptg titration", "iptg concentr", "inducer dose"]):
        return "engineering_input"
    if "temperature" in gene_str.lower() or "temperature" in text and pt == "environmental":
        return "engineering_input"
    if pt == "environmental" or pt == "chemical_treatment":
        return "engineering_input"

    # Chassis comparison — perturbation IS the chassis
    if any(ch in gene_str.upper() for ch in ["BL21", "MG1655", "W3110", "DH5", "JM109"]):
        return "chassis_comparison"

    # IspB-KD (specific)
    if all_genes & ISPB_GENES:
        return "ispB_KD"

    # MVA cassette / MVA gene OE
    if all_genes & MVA_GENES:
        return "MVA_OE"
    if "mva cassette" in text or "mevalonate pathway" in text:
        return "MVA_OE"

    # Carotenoid cassette OE
    if all_genes & CAROTENOID_GENES:
        return "carotenoid_OE"

    # Central-metabolism deletion
    if all_genes & CENTRAL_METAB_GENES:
        return "central_metabolism_deletion"

    # Regulator deletion
    if all_genes & REGULATOR_GENES:
        return "regulator_deletion"

    # MEP-OE (everything left that hits a MEP gene)
    if all_genes & MEP_GENES:
        return "MEP_OE"

    return "other"


def extract_chassis(p):
    text = (p.get("notes") or "") + " " + " ".join(
        e.get("evidence_sentence", "") for e in p.get("evidence", [])
    )
    for name, pat in CHASSIS_PATTERNS:
        if re.search(pat, text, re.I):
            return name
    return "unspecified"


def extract_from_patterns(p, patterns):
    text = (p.get("notes") or "") + " " + " ".join(
        e.get("evidence_sentence", "") for e in p.get("evidence", [])
    )
    hits = []
    for name, pat in patterns:
        if re.search(pat, text, re.I):
            hits.append(name)
    if not hits:
        return "unspecified"
    return "|".join(hits)


# ----------------------------------------------------------------------
# Stratified accuracy for best method (ODE)
# ----------------------------------------------------------------------

def strat_acc(results, keyfn):
    buckets = defaultdict(lambda: [0, 0])
    for r in results:
        tid = r["test_id"]
        if tid not in pert_by_id:
            continue
        k = keyfn(pert_by_id[tid])
        buckets[k][1] += 1
        if r["correct"]:
            buckets[k][0] += 1
    out = {}
    for k, (c, t) in sorted(buckets.items()):
        out[k] = {"correct": c, "total": t, "accuracy": round(100 * c / t, 1) if t else 0.0}
    return out


ode_results = ode["detailed_results"]

by_class_ode = strat_acc(ode_results, classify_perturbation)
by_chassis_ode = strat_acc(ode_results, extract_chassis)
by_carbon_ode = strat_acc(ode_results, lambda p: extract_from_patterns(p, CARBON_PATTERNS))
by_temp_ode = strat_acc(ode_results, lambda p: extract_from_patterns(p, TEMPERATURE_PATTERNS))
by_growth_ode = strat_acc(ode_results, lambda p: extract_from_patterns(p, GROWTH_PATTERNS))
by_oxygen_ode = strat_acc(ode_results, lambda p: extract_from_patterns(p, OXYGEN_PATTERNS))


# Also per-class for algebraic + RWR
by_class_alg = strat_acc(alg["detailed_results"], classify_perturbation)
by_class_rwr = strat_acc(rwr["detailed_results"], classify_perturbation)

by_chassis_alg = strat_acc(alg["detailed_results"], extract_chassis)
by_chassis_rwr = strat_acc(rwr["detailed_results"], extract_chassis)


# Complex-strain accuracy: tests with >=3 gene modifiers OR perturbation type
# containing 'triple'/'quadruple'/'combined'
def is_complex(p):
    n = len(p.get("gene_modifiers") or {})
    pt = p.get("perturbation_type", "")
    return n >= 3 or pt in {"triple_knockout", "quadruple_knockout", "combined", "combined_transgenic"}


def complex_acc(results):
    c = t = 0
    for r in results:
        pid = r["test_id"]
        if pid not in pert_by_id:
            continue
        if is_complex(pert_by_id[pid]):
            t += 1
            if r["correct"]:
                c += 1
    return {"correct": c, "total": t,
            "accuracy": round(100 * c / t, 1) if t else 0.0}


complex_alg = complex_acc(alg["detailed_results"])
complex_ode = complex_acc(ode_results)
complex_rwr = complex_acc(rwr["detailed_results"])


# ----------------------------------------------------------------------
# accuracy_metrics.json
# ----------------------------------------------------------------------

def failures_list(results):
    return [r["test_id"] for r in results if not r["correct"]]


def method_acc(result_json, extra=None):
    m = result_json["metrics"]
    params = result_json.get("parameters", {})
    out = {
        "accuracy": round(m["overall_accuracy"] / 100.0, 4),
        "correct": m["correct"],
        "total_tested": m["total"],
        "kappa": round(m["cohens_kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "failures": failures_list(result_json["detailed_results"]),
    }
    # Convergence
    conv = sum(1 for r in result_json["detailed_results"] if r.get("converged", True))
    out["convergence_rate"] = round(conv / len(result_json["detailed_results"]), 4) \
        if result_json["detailed_results"] else 0.0
    if extra:
        out.update(extra)
    return out


summary_tests = {
    "total": pert["metadata"]["total_tests"],
    "tested": alg["summary"]["tested"],
    "skipped": alg["summary"]["skipped"],
}

accuracy = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lycopene_Titer",
        "species": "Escherichia coli",
        "created": "2026-04-21",
    },
    "tests": summary_tests,
    "algebraic": method_acc(alg),
    "ode": method_acc(ode, extra={"best_K": ode["parameters"]["K"],
                                  "best_n": ode["parameters"]["n"]}),
    "rwr": method_acc(rwr, extra={"best_alpha": rwr.get("best_alpha", 0.6)}),
}

with open(VAL / "accuracy_metrics.json", "w", encoding="utf-8") as f:
    json.dump(accuracy, f, indent=2, ensure_ascii=False)
print("Wrote accuracy_metrics.json")


# ----------------------------------------------------------------------
# failure_analysis.json — categorise ODE (best method) failures
# ----------------------------------------------------------------------

def categorise_failure(res, p):
    pt = p.get("perturbation_type", "")
    gene = p.get("gene", "")
    exp = res["expected_direction"]
    pred = res["predicted_direction"]
    ratio = res.get("ratio", 1.0)
    path_len = res.get("path_length")
    path = res.get("path") or []
    n_perts = len(p.get("gene_modifiers") or {})
    notes = (p.get("notes") or "").lower()

    # Complex multi-edit strain: likely epistasis
    if n_perts >= 3 or pt in {"triple_knockout", "quadruple_knockout"}:
        return (
            "epistasis_complexity",
            f"Multi-edit strain ({n_perts} simultaneous perturbations, "
            f"type={pt}). Model geometric-mean / Hill composition does not "
            f"capture combinatorial epistasis in this regime.",
            False,
            "",
        )

    # Combined treatment + genotype
    if pt in {"combined", "combined_transgenic", "rescue",
              "knockout_plus_treatment"}:
        # Could be framework rescue limitation
        return (
            "epistasis_complexity",
            f"Combined perturbation ({pt}) — multiple simultaneous inputs "
            f"(e.g. OE + chassis + medium). Framework does not decompose "
            f"the individual contributions.",
            True,
            "Check each component; consider adding chassis / medium source nodes.",
        )

    # Disconnected or no path → framework-limitation
    if path_len is None or path_len == 0 or not path:
        return (
            "framework_limitation",
            f"Gene {gene} has no directed path to phenotype in current network "
            f"(path_length={path_len}). Prediction defaults to unchanged or "
            f"reflects only local inhibition flip.",
            True,
            f"Add literature-backed edge(s) from {gene} onto the MEP/MVA/carotenoid "
            f"cascade, or mark {gene} as a literature_gap if no curated edge exists.",
        )

    # Sign inversion (expected increased, predicted decreased) on OE
    if exp == "increased" and pred == "decreased" and pt == "overexpression":
        if ratio < 0.2:
            return (
                "edge_case",
                f"Strong inversion: OE of {gene} predicts ratio={ratio:.3f} "
                f"(expected >1). Likely cascade sign error OR geometric-mean "
                f"dilution where the OE'd node is only one of many activators "
                f"on a downstream hub.",
                True,
                f"Trace cascade from {gene} → Lycopene_Titer; check each edge sign; "
                f"verify hub activator count doesn't dilute OE pulse.",
            )
        return (
            "edge_case",
            f"Mild inversion: OE of {gene} predicts decreased (ratio={ratio:.3f}). "
            f"Likely a single inverted edge sign along the cascade.",
            True,
            f"Audit edge signs on path from {gene} to Lycopene_Titer.",
        )

    # Expected decreased but predicted unchanged/increased
    if exp == "decreased" and pred in {"unchanged", "increased"}:
        return (
            "edge_case",
            f"Deletion / KD of {gene} should DECREASE lycopene but model "
            f"predicts {pred} (ratio={ratio:.3f}). Cascade from {gene} is "
            f"either missing, inverted, or {gene} only acts through a path "
            f"that is buffered by parallel supply (MEP || MVA).",
            True,
            f"Check whether {gene} has sufficient downstream weight and "
            f"whether parallel paths should be weakened in WT.",
        )

    # Expected unchanged but model predicts something
    if exp == "unchanged" and pred != "unchanged":
        return (
            "composite_collapse",
            f"Perturbation of {gene} (type={pt}) should leave lycopene "
            f"unchanged, but model predicts {pred} (ratio={ratio:.3f}). "
            f"Likely a composite node that over-weights a redundant member "
            f"or a spurious cascade edge.",
            True,
            f"Review composite membership and single-member modifier for {gene}; "
            f"consider modifier=0.99 for single-member perturbation of a "
            f"redundant family.",
        )

    # Fallback
    return (
        "edge_case",
        f"{gene} ({pt}): expected {exp}, predicted {pred} (ratio={ratio:.3f}). "
        f"Does not fit standard failure modes; requires manual investigation.",
        True,
        f"Trace cascade from {gene} to Lycopene_Titer and inspect each edge sign.",
    )


failures = []
for r in ode_results:
    if r["correct"]:
        continue
    tid = r["test_id"]
    p = pert_by_id.get(tid, {})
    cat, expl, fixable, strat = categorise_failure(r, p)
    doi = r.get("evidence_doi", "") or (
        p.get("evidence", [{}])[0].get("doi", "") if p.get("evidence") else ""
    )
    failures.append({
        "test_id": tid,
        "gene": r["gene"],
        "perturbation_type": r["perturbation_type"],
        "expected_direction": r["expected_direction"],
        "predicted_direction": r["predicted_direction"],
        "category": cat,
        "explanation": expl,
        "evidence": doi,
        "fixable": fixable,
        "fix_strategy": strat,
    })

by_cat = defaultdict(int)
for f in failures:
    by_cat[f["category"]] += 1

failure_analysis = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lycopene_Titer",
        "species": "Escherichia coli",
        "created": "2026-04-21",
    },
    "failures": failures,
    "summary": {
        "best_method": "ODE (Hill Functions)",
        "best_params": f"K={ode['parameters']['K']}, n={ode['parameters']['n']}",
        "total_failures": len(failures),
        "by_category": dict(by_cat),
        "fixable_count": sum(1 for f in failures if f["fixable"]),
        "unfixable_count": sum(1 for f in failures if not f["fixable"]),
        "notes": (
            "Failures categorised on ODE (best method, 66.3% accuracy). Many "
            "'increased expected, decreased predicted' failures on OE tests "
            "suggest cascade-sign or dilution problems downstream of DXS/IDI. "
            "A second common mode: chassis/medium/inducer tests where the "
            "source node is not wired — these read as unchanged or spurious "
            "movement."
        ),
    },
}

with open(VAL / "failure_analysis.json", "w", encoding="utf-8") as f:
    json.dump(failure_analysis, f, indent=2, ensure_ascii=False)
print("Wrote failure_analysis.json")


# ----------------------------------------------------------------------
# method_comparison.json
# ----------------------------------------------------------------------

def entry(result_json, strengths, weaknesses, best_params):
    m = result_json["metrics"]
    conv = sum(1 for r in result_json["detailed_results"] if r.get("converged", True)) \
        / len(result_json["detailed_results"])
    return {
        "method": result_json["method"],
        "accuracy": round(m["overall_accuracy"] / 100.0, 4),
        "kappa": round(m["cohens_kappa"], 4),
        "mcc": round(m["mcc"], 4),
        "convergence_rate": round(conv, 4),
        "best_params": best_params,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "failures": [r["test_id"] for r in result_json["detailed_results"] if not r["correct"]],
    }


def band(k):
    if k >= 0.81:
        return "almost-perfect"
    if k >= 0.61:
        return "substantial"
    if k >= 0.41:
        return "moderate"
    if k >= 0.21:
        return "fair"
    return "slight/poor"


methods = {
    "Algebraic": alg,
    "ODE": ode,
    "RWR": rwr,
}

# Pick best by accuracy, kappa, mcc
def score(j):
    m = j["metrics"]
    return (m["overall_accuracy"], m["cohens_kappa"], m["mcc"])


best_name = max(methods, key=lambda k: score(methods[k]))

comparison = [
    entry(
        alg,
        strengths="Runs fast; deterministic; good precision on 'increased' class.",
        weaknesses=(
            "Low convergence (41.9%) — many feedback configurations don't "
            "reach steady state. Kappa only 0.20 ('fair'). Many OE tests "
            "collapse to decreased due to geometric-mean dilution at hubs."
        ),
        best_params="epsilon=0.1, K=10.0, damping=0.7",
    ),
    entry(
        ode,
        strengths=(
            "Best overall — 66.3% acc, kappa 0.29 ('fair'), MCC 0.27. 100% "
            "convergence. Hill response with low n (=1) handles monotone "
            "activation without saturating."
        ),
        weaknesses=(
            "Still below 80% threshold. Many OE tests predict strong decrease "
            "(ratio < 0.02) — suggests a global sign issue on one or more "
            "dominant cascade nodes. Chassis / medium / inducer tests unwired."
        ),
        best_params=f"K={ode['parameters']['K']}, n={ode['parameters']['n']}",
    ),
    entry(
        rwr,
        strengths=(
            "100% convergence; no parameter-space pathology. Treats network as "
            "signed random walk so immune to cascade-length dilution."
        ),
        weaknesses=(
            "Lowest accuracy (51.2%) and kappa (0.19). Signed-RWR washes out "
            "any magnitude information — everything collapses to sign of net "
            "incoming influence, so tests depending on magnitude are lost."
        ),
        best_params=f"alpha={rwr.get('best_alpha', 0.6)}",
    ),
]

method_comparison = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Lycopene_Titer",
        "species": "Escherichia coli",
        "created": "2026-04-21",
    },
    "summary": {
        "best_method": ode["method"],
        "best_accuracy": round(ode["metrics"]["overall_accuracy"] / 100.0, 4),
        "best_kappa": round(ode["metrics"]["cohens_kappa"], 4),
        "best_kappa_band": band(ode["metrics"]["cohens_kappa"]),
        "best_mcc": round(ode["metrics"]["mcc"], 4),
        "best_convergence_rate": round(
            sum(1 for r in ode_results if r.get("converged", True)) / len(ode_results),
            4,
        ),
        "tests_tested": ode["summary"]["tested"],
        "tests_skipped": ode["summary"]["skipped"],
        "tests_total": pert["metadata"]["total_tests"],
        "recommendation": (
            "ACC 66.3% < 80% threshold → recommend Step 5 REFINEMENT, but this "
            "likely also needs a BUILDER-level structural review. 22/108 tests "
            "(20%) are skipped because their genes are not in the network "
            "(MVA cassette genes, chassis source nodes, IPTG dose node). "
            "Dominant failure modes: (a) OE tests predicting strong decrease "
            "on MEP genes — cascade sign / dilution issue; (b) chassis + "
            "medium tests flat — missing source wiring; (c) multi-edit MAGE "
            "strains — framework epistasis limit."
        ),
        "stratified_accuracy": {
            "by_perturbation_class": {
                "algebraic": by_class_alg,
                "ode": by_class_ode,
                "rwr": by_class_rwr,
            },
            "by_chassis_best_method": by_chassis_ode,
            "by_chassis_algebraic": by_chassis_alg,
            "by_chassis_rwr": by_chassis_rwr,
            "by_carbon_source_best_method": by_carbon_ode,
            "by_temperature_best_method": by_temp_ode,
            "by_growth_mode_best_method": by_growth_ode,
            "by_oxygen_best_method": by_oxygen_ode,
            "complex_strain_accuracy": {
                "algebraic": complex_alg,
                "ode": complex_ode,
                "rwr": complex_rwr,
            },
        },
    },
    "comparison": comparison,
}

with open(VAL / "method_comparison.json", "w", encoding="utf-8") as f:
    json.dump(method_comparison, f, indent=2, ensure_ascii=False)
print("Wrote method_comparison.json")


# ----------------------------------------------------------------------
# Console summary for the agent report
# ----------------------------------------------------------------------

print()
print("=" * 70)
print("STRATIFIED SUMMARY")
print("=" * 70)
print(f"Best method: {best_name} (ODE/Hill)")
print(f"  acc={ode['metrics']['overall_accuracy']:.1f}%  "
      f"kappa={ode['metrics']['cohens_kappa']:.3f} ({band(ode['metrics']['cohens_kappa'])})  "
      f"mcc={ode['metrics']['mcc']:.3f}")
print()
print("Per perturbation class (ODE):")
for k, v in by_class_ode.items():
    print(f"  {k:32s} {v['correct']:3d}/{v['total']:<3d}  {v['accuracy']:5.1f}%")
print()
print("Per chassis (ODE):")
for k, v in by_chassis_ode.items():
    print(f"  {k:32s} {v['correct']:3d}/{v['total']:<3d}  {v['accuracy']:5.1f}%")
print()
print("Complex-strain (>=3 edits) accuracy:")
for name, v in [("Algebraic", complex_alg), ("ODE", complex_ode), ("RWR", complex_rwr)]:
    print(f"  {name:12s} {v['correct']}/{v['total']}  {v['accuracy']}%")
print()
print("Failures by category (ODE):")
for k, v in by_cat.items():
    print(f"  {k:28s} {v}")
