"""
Step 4 (VALIDATOR) post-analysis:
  - accuracy_metrics.json   (with by_light_condition stratification)
  - failure_analysis.json   (every failure categorized + fix strategy)
  - method_comparison.json  (list-of-dicts comparison; best method)

Run after the three validators have produced *_validation_results.json.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NETWORK_ROOT = ROOT.parent
RECON_FILE = NETWORK_ROOT / "data" / "reconciled_perturbation_dataset.json"
ALG_FILE = ROOT / "script_validation_results.json"
ODE_FILE = ROOT / "ode_validation_results.json"
RWR_FILE = ROOT / "rwr_validation_results.json"

CREATED = "2026-04-19"
PHENOTYPE = "Hypocotyl_Length"
SPECIES = "Arabidopsis thaliana"

# ----------------------------- Light-condition bucketing -------------------- #

def light_bucket(condition: str) -> str:
    c = (condition or "").lower()
    if "dark" in c or "acc dark" in c or "skotomorph" in c:
        return "dark"
    if "frc" in c or "far-red" in c:
        return "far_red"
    if "shade" in c or "low r:fr" in c:
        return "shade_lowRFR"
    if "uv-b" in c or "uvb" in c:
        return "UV_B"
    if "blue" in c:
        return "blue"
    if re.search(r"\brc\b", c) or "red light" in c or c == "rc/white light":
        return "red_continuous"
    if re.search(r"2[789]c|30c|warm", c):
        return "warm_temp"
    if "white" in c or "light" in c or " ld" in c or "ld" == c or "sd" in c or "22c" in c:
        return "white_light"
    return "any_other"


def per_light_condition(detailed_results, tid_to_bucket):
    by = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in detailed_results:
        b = tid_to_bucket.get(r["test_id"], "any_other")
        by[b]["total"] += 1
        if r["correct"]:
            by[b]["correct"] += 1
    out = {}
    for k, v in by.items():
        out[k] = {
            "correct": v["correct"],
            "total": v["total"],
            "accuracy_pct": round(100.0 * v["correct"] / v["total"], 1) if v["total"] else 0.0,
        }
    return dict(sorted(out.items()))


# ----------------------------- Failure categorisation ----------------------- #
# Categories: framework_limitation | composite_collapse | epistasis_complexity | edge_case

FAILURE_CATEGORIES = {
    "T003": {
        "category": "framework_limitation",
        "explanation": (
            "WT + ACC at 28C is expected unchanged because warm temperature "
            "(thermomorphogenesis) suppresses the ethylene triple response. The "
            "model cannot represent the warm-temperature gating of ethylene "
            "signalling, so it predicts decreased like the cool-temperature ACC test."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T004": {
        "category": "composite_collapse",
        "explanation": (
            "AFB5 single KO + picloram. AFB5 mapped to TIR1 composite via "
            "composite_member modifier 0.997, which produces no measurable change. "
            "Single AFB paralog phenotype is lost in the composite collapse."
        ),
        "fixable": False,
        "fix_strategy": "Could split AFB1/2/3/5 from TIR1, but adds 4 nodes for marginal coverage.",
    },
    "T009": {
        "category": "composite_collapse",
        "explanation": (
            "ARF7 single KO mapped to ARF6 family_member with modifier 0.997. ARF7 "
            "has hypocotyl-specific roles distinct from ARF6, but the single-paralog "
            "modifier washes out the effect."
        ),
        "fixable": False,
        "fix_strategy": "Add ARF7 as a separate node if curated_edges support its regulation; otherwise accept the limitation.",
    },
    "T010": {
        "category": "composite_collapse",
        "explanation": (
            "ARF8 single KO mapped to ARF6 family_member with modifier 0.997. Same "
            "rationale as ARF7."
        ),
        "fixable": False,
        "fix_strategy": "Add ARF8 as separate node, or accept composite limitation.",
    },
    "T022": {
        "category": "framework_limitation",
        "explanation": (
            "bin2-1 is a constitutively active kinase. In darkness, the dominant "
            "effect is reduced BR signalling -> reduced BES1/BZR1 activity. In the "
            "literature this paradoxically increases hypocotyl in dark (BR-deficient "
            "phenocopy of thin-stem dark-growth). The model has BIN2 -| BZR1 with "
            "BZR1 -> Hypocotyl(+); bin2-1 OE consistently predicts decreased. The "
            "context-dependent direction reversal between dark and light cannot be "
            "captured by sign-fixed edges."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T046": {
        "category": "framework_limitation",
        "explanation": (
            "ein2 KO + ACC in dark expects increased (insensitive). Model adds "
            "Ethylene exogenous=1.0 alongside EIN2 gm=0; with EIN2=0 the canonical "
            "ethylene cascade collapses and Hypocotyl returns to baseline. Compared "
            "to WT (no ACC) the prediction is correctly 'unchanged' biologically — "
            "the literature 'increased' label uses an implicit WT+ACC baseline. "
            "Trap 5 (signaling mutant + treatment baseline mismatch)."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T047": {
        "category": "framework_limitation",
        "explanation": (
            "ein3 KO + ACC. Same as T046 — receptor/TF KO removes the ethylene "
            "inhibition and the implicit baseline used by the literature differs "
            "from the WT-no-treatment baseline used by the validator."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T049": {
        "category": "framework_limitation",
        "explanation": (
            "ein3 eil1 double KO + ACC. EIL1 collapsed to EIN3 composite. Same "
            "Trap-5 baseline issue as T046/T047."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T087": {
        "category": "composite_collapse",
        "explanation": (
            "PIF1 (PIL5) is not a separate node. Mapped to PIF3 (closest "
            "skotomorphogenesis PIF) via family_member with modifier 0.997. PIF1's "
            "hypocotyl role under Rc is partially distinct from PIF3, so the "
            "single-paralog modifier washes out the effect."
        ),
        "fixable": True,
        "fix_strategy": "Add PIF1 as separate node if curated_edges support its hypocotyl-specific edges.",
    },
    "T099": {
        "category": "edge_case",
        "explanation": (
            "PIF7 phospho-dead mutant in shade. Encoded as PIF7 gm=2.0. Algebraic "
            "ratio = 1.035 (just below the 0.05 direction threshold) — geometric-mean "
            "dilution dampens the signal because PIF7 is one of several activators "
            "of Hypocotyl_Length. The directional change is correct in sign but too "
            "small to cross the threshold."
        ),
        "fixable": True,
        "fix_strategy": "Lower direction threshold for borderline tests, or add a direct PIF7 -> Hypocotyl edge if curated_edges allow.",
    },
    "T104": {
        "category": "edge_case",
        "explanation": (
            "Picloram (synthetic auxin) under warm temperature. Encoded as exogenous "
            "Auxin=1.0. ODE ratio = 1.026 (sub-threshold). The signal is present but "
            "geometric-mean dilution through the auxin cascade keeps the change "
            "below the 0.05 direction threshold under ODE Hill K=0.5, n=1."
        ),
        "fixable": True,
        "fix_strategy": "Sub-threshold magnitude. ODE-only failure (algebraic and RWR pass).",
    },
    "T077": {
        "category": "edge_case",
        "explanation": (
            "NAA exogenous Auxin treatment. ODE ratio = 1.026 (sub-threshold). Same "
            "sub-threshold dilution issue as T104; ODE-specific failure."
        ),
        "fixable": True,
        "fix_strategy": "Same as T104.",
    },
    "T106": {
        "category": "composite_collapse",
        "explanation": (
            "RGA single KO (1 of 5 DELLA paralogs) -> DELLA composite gm=0.997 -> "
            "no measurable change. RGA has the strongest single-paralog phenotype "
            "in the DELLA family but is collapsed into the composite."
        ),
        "fixable": True,
        "fix_strategy": "Could split RGA from DELLA composite (RGA dominates the family in hypocotyl); other DELLAs remain composite.",
    },
    "T112": {
        "category": "framework_limitation",
        "explanation": (
            "TIR1 KO + auxin treatment. Trap 5: removing the auxin receptor blocks "
            "perception, but the model still adds Auxin=1.0 to downstream nodes. "
            "Algebraic returns ratio=1.0 because TIR1 KO + Auxin=1.0 still reaches "
            "AUX_IAA equilibrium near baseline; RWR over-shoots positive."
        ),
        "fixable": False,
        "fix_strategy": "",
    },
    "T128": {
        "category": "composite_collapse",
        "explanation": (
            "gid1a gid1b double KO mapped to GID1 composite gm=0.5. Biology: gid1a "
            "and gid1b have asymmetric roles; the double can produce more elongation "
            "than expected from a uniform GID1 composite. Composite collapse loses "
            "the asymmetry."
        ),
        "fixable": False,
        "fix_strategy": "Splitting GID1 paralogs adds 3 nodes for gain on 3 tests (T127-T129).",
    },
    "T129": {
        "category": "composite_collapse",
        "explanation": (
            "gid1b gid1c double KO is expected unchanged because GID1A retains "
            "function. The composite collapse cannot distinguish which paralog "
            "remains functional, so it predicts a global GID1 reduction -> short "
            "hypocotyl."
        ),
        "fixable": False,
        "fix_strategy": "Same as T128.",
    },
    "T137": {
        "category": "epistasis_complexity",
        "explanation": (
            "bas1 sob7 double KO. Both BAS1 and SOB7 catabolise BR. Removing both "
            "should accumulate BR -> longer hypocotyl (the model's prediction). "
            "Literature reports paradoxical decreased hypocotyl, likely from BR "
            "overaccumulation feedback on BR biosynthesis or homeostasis. The model "
            "has no BR-overaccumulation feedback."
        ),
        "fixable": False,
        "fix_strategy": "Adding negative feedback BR -| DET2/DWF4 would model BR homeostasis but risks oscillation.",
    },
}


# ----------------------------- Build summary files -------------------------- #

def main():
    alg = json.loads(ALG_FILE.read_text(encoding="utf-8"))
    ode = json.loads(ODE_FILE.read_text(encoding="utf-8"))
    rwr = json.loads(RWR_FILE.read_text(encoding="utf-8"))
    recon = json.loads(RECON_FILE.read_text(encoding="utf-8"))

    tid_to_bucket = {p["test_id"]: light_bucket(p["condition"]) for p in recon["perturbations"]}
    tid_to_meta = {p["test_id"]: p for p in recon["perturbations"]}

    def method_pkg(d, extra_keys=None):
        m = d["metrics"]
        fails = [r["test_id"] for r in d["detailed_results"] if not r["correct"]]
        pkg = {
            "accuracy": round(m["overall_accuracy"] / 100.0, 4),
            "correct": m["correct"],
            "total_tested": m["total"],
            "kappa": round(m["cohens_kappa"], 4),
            "mcc": round(m["mcc"], 4),
            "convergence_rate": round(m["convergence_rate"] / 100.0, 4),
            "failures": fails,
            "ci_95": [round(m["kappa_ci_lower"], 4), round(m["kappa_ci_upper"], 4)],
        }
        if extra_keys:
            for k, v in extra_keys.items():
                pkg[k] = v
        return pkg

    # --- accuracy_metrics.json --- #
    accuracy = {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": PHENOTYPE,
            "species": SPECIES,
            "created": CREATED,
        },
        "tests": {
            "total": len(recon["perturbations"]),
            "tested": alg["metrics"]["total"],
            "skipped": len(recon["perturbations"]) - alg["metrics"]["total"],
        },
        "algebraic": method_pkg(alg),
        "ode": method_pkg(ode, {
            "best_K": ode["parameters"].get("K"),
            "best_n": ode["parameters"].get("n"),
        }),
        "rwr": method_pkg(rwr, {
            "best_alpha": rwr.get("best_alpha") or rwr["parameters"].get("alpha"),
        }),
        "by_light_condition": {
            "algebraic": per_light_condition(alg["detailed_results"], tid_to_bucket),
            "ode": per_light_condition(ode["detailed_results"], tid_to_bucket),
            "rwr": per_light_condition(rwr["detailed_results"], tid_to_bucket),
        },
        "rigor": {
            "algebraic": {
                "frs": alg["metrics"].get("rigor_score"),
                "frs_band": alg["metrics"].get("rigor_band"),
                "dars": alg["metrics"].get("dars"),
                "dars_band": alg["metrics"].get("dars_band"),
            },
            "ode": {
                "frs": ode["metrics"].get("rigor_score"),
                "frs_band": ode["metrics"].get("rigor_band"),
                "dars": ode["metrics"].get("dars"),
                "dars_band": ode["metrics"].get("dars_band"),
            },
            "rwr": {
                "frs": rwr["metrics"].get("rigor_score"),
                "frs_band": rwr["metrics"].get("rigor_band"),
                "dars": rwr["metrics"].get("dars"),
                "dars_band": rwr["metrics"].get("dars_band"),
            },
        },
    }
    (ROOT / "accuracy_metrics.json").write_text(
        json.dumps(accuracy, indent=2), encoding="utf-8"
    )
    print("Wrote accuracy_metrics.json")

    # --- failure_analysis.json --- #
    # Use the union of failures across the three methods so REFINEMENT sees
    # everything once. Per-method fail flag noted in explanation.
    union_failed_ids = sorted(
        set(accuracy["algebraic"]["failures"])
        | set(accuracy["ode"]["failures"])
        | set(accuracy["rwr"]["failures"])
    )

    fails = []
    by_cat = defaultdict(int)
    fixable_count = 0
    for tid in union_failed_ids:
        meta = tid_to_meta[tid]
        cat_entry = FAILURE_CATEGORIES.get(tid)
        if cat_entry is None:
            cat_entry = {
                "category": "edge_case",
                "explanation": "Uncategorised failure (no manual review).",
                "fixable": False,
                "fix_strategy": "",
            }
        # Use algebraic predicted direction by default; fall back to ODE/RWR
        pred = "unchanged"
        for d in (alg, ode, rwr):
            for r in d["detailed_results"]:
                if r["test_id"] == tid:
                    pred = r["predicted_direction"]
                    break
            if pred:
                break
        # Per-method fail breakdown
        per_method = {
            "algebraic": tid in accuracy["algebraic"]["failures"],
            "ode": tid in accuracy["ode"]["failures"],
            "rwr": tid in accuracy["rwr"]["failures"],
        }
        evidence_doi = ""
        if meta.get("evidence"):
            evidence_doi = meta["evidence"][0].get("doi", "")
        fails.append({
            "test_id": tid,
            "gene": meta["gene"],
            "perturbation_type": meta["perturbation_type"],
            "expected_direction": meta["expected_direction"],
            "predicted_direction": pred,
            "category": cat_entry["category"],
            "explanation": cat_entry["explanation"]
                + f" Failed on: {', '.join(k for k,v in per_method.items() if v)}.",
            "evidence": evidence_doi,
            "fixable": cat_entry["fixable"],
            "fix_strategy": cat_entry["fix_strategy"],
        })
        by_cat[cat_entry["category"]] += 1
        if cat_entry["fixable"]:
            fixable_count += 1

    failure_file = {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": PHENOTYPE,
            "species": SPECIES,
            "created": CREATED,
        },
        "failures": fails,
        "summary": {
            "total_failures": len(fails),
            "by_category": dict(by_cat),
            "fixable_count": fixable_count,
            "unfixable_count": len(fails) - fixable_count,
            "per_method_failure_counts": {
                "algebraic": len(accuracy["algebraic"]["failures"]),
                "ode": len(accuracy["ode"]["failures"]),
                "rwr": len(accuracy["rwr"]["failures"]),
            },
        },
    }
    (ROOT / "failure_analysis.json").write_text(
        json.dumps(failure_file, indent=2), encoding="utf-8"
    )
    print("Wrote failure_analysis.json")

    # --- method_comparison.json --- #
    comparison_entries = [
        {
            "method": "Algebraic",
            "accuracy": accuracy["algebraic"]["accuracy"],
            "kappa": accuracy["algebraic"]["kappa"],
            "mcc": accuracy["algebraic"]["mcc"],
            "convergence_rate": accuracy["algebraic"]["convergence_rate"],
            "best_params": "epsilon=0.1, K=10.0, damping=0.7",
            "strengths": (
                "Deterministic, fast, transparent. Captures gene-modifier and "
                "exogenous_supply mechanics directly. Strong on white-light and "
                "warm-temperature stratums."
            ),
            "weaknesses": (
                "Geometric-mean dilution causes sub-threshold ratios for "
                "single-paralog KOs (composite_member 0.997). Convergence rate 91.4% "
                "(some bistable feedback loops in BR/PIF arm)."
            ),
            "failures": accuracy["algebraic"]["failures"],
        },
        {
            "method": "ODE",
            "accuracy": accuracy["ode"]["accuracy"],
            "kappa": accuracy["ode"]["kappa"],
            "mcc": accuracy["ode"]["mcc"],
            "convergence_rate": accuracy["ode"]["convergence_rate"],
            "best_params": f"K={accuracy['ode']['best_K']}, n={accuracy['ode']['best_n']}",
            "strengths": (
                "100% convergence rate. Hill kinetics smooth out borderline "
                "predictions. Best at K=0.5, n=1 (low-cooperativity regime)."
            ),
            "weaknesses": (
                "Same composite_member sub-threshold problem as algebraic plus "
                "two extra exogenous-treatment misses (T077 NAA, T104 picloram) "
                "where Hill saturation flattens the auxin signal."
            ),
            "failures": accuracy["ode"]["failures"],
        },
        {
            "method": "RWR",
            "accuracy": accuracy["rwr"]["accuracy"],
            "kappa": accuracy["rwr"]["kappa"],
            "mcc": accuracy["rwr"]["mcc"],
            "convergence_rate": accuracy["rwr"]["convergence_rate"],
            "best_params": f"alpha={accuracy['rwr']['best_alpha']}",
            "strengths": (
                "Best overall at 91.4% / kappa=0.83 / MCC=0.84. Topology-based "
                "propagation is robust to composite-collapse weakening: RWR catches "
                "ARF7/8, PIF1, RGA single-paralog phenotypes that algebraic and ODE "
                "miss. Identical accuracy across alpha=0.5..0.95 (signal stable)."
            ),
            "weaknesses": (
                "Cannot model exogenous_supply as an additive term; signaling-mutant "
                "rescue tests (T046/T047/T049 EIN-KO+ACC, T112 TIR1+IAA) flip to "
                "decreased instead of unchanged because ligand input still propagates "
                "through alternative paths. Class-imbalance-weak (unchanged F1=0.0)."
            ),
            "failures": accuracy["rwr"]["failures"],
        },
    ]

    # Best method = highest accuracy, tiebreak kappa, then MCC.
    def sort_key(e):
        return (-e["accuracy"], -e["kappa"], -e["mcc"])
    best = min(comparison_entries, key=sort_key)

    # Recommendation per the prompt
    if best["accuracy"] >= 0.95:
        rec = "Refinement optional; ready for export."
    elif best["accuracy"] >= 0.80:
        rec = "Proceed to Step 5 (REFINEMENT) — focus on composite_collapse failures (T009/T010, T087, T106) and re-evaluate Trap-5 framework limitations."
    else:
        rec = "Network structural issue — re-invoke JUDGE before refinement."

    method_comp = {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": PHENOTYPE,
            "species": SPECIES,
            "created": CREATED,
        },
        "summary": {
            "best_method": best["method"],
            "best_accuracy": best["accuracy"],
            "best_kappa": best["kappa"],
            "best_mcc": best["mcc"],
            "best_params": best["best_params"],
            "recommendation": rec,
        },
        "comparison": comparison_entries,
    }
    (ROOT / "method_comparison.json").write_text(
        json.dumps(method_comp, indent=2), encoding="utf-8"
    )
    print("Wrote method_comparison.json")

    # ----------- Console roll-up ----------- #
    print()
    print("=== Headline ===")
    for e in comparison_entries:
        print(f"  {e['method']:<10} acc={e['accuracy']*100:5.1f}%  kappa={e['kappa']:.3f}  MCC={e['mcc']:.3f}")
    print(f"\nBest: {best['method']} ({best['accuracy']*100:.1f}%)")
    print(f"\nFailure counts: total union={len(fails)}, by_cat={dict(by_cat)}, fixable={fixable_count}")


if __name__ == "__main__":
    main()
