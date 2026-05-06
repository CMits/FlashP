#!/usr/bin/env python3
"""
Run the 3 validators (algebraic / ODE / RWR) on pleiotropic perturbation tests.

Each pleiotropic test expands into N reconciled-style tests (one per expected
outcome). We write them to a shadow network directory so the production
validators can be used unchanged. Then we copy the outputs back to the main
validation/ folder with a `pleiotropic_` prefix and remove the shadow dir.

Usage:
    python Agent/validate_pleiotropic.py <merged_network_dir>
"""

import json, os, sys, shutil, subprocess, csv
from datetime import date

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def expand_pleio(pleio_file):
    """Expand each pleiotropic test into one reconciled perturbation per
    expected_outcome. test_id becomes PLEIO_NNN__PHENOTYPE."""
    p = load(pleio_file)
    out = []
    for t in p["pleiotropic_tests"]:
        for i, oc in enumerate(t["expected_outcomes"]):
            gm = dict(t.get("gene_modifiers") or {})
            es = dict(t.get("exogenous_supply") or {})
            sub_perts = []
            for node, val in gm.items():
                sub_perts.append({"node": node, "modifier_type": "gene_modifier", "value": float(val)})
            for node, val in es.items():
                sub_perts.append({"node": node, "modifier_type": "exogenous_supply", "value": float(val)})
            out.append({
                "test_id": f"{t['test_id']}__{oc['phenotype_node']}",
                "gene": t.get("gene", ""),
                "perturbation_type": t.get("perturbation_type", "knockout"),
                "expected_direction": oc["expected_direction"],
                "in_network": True,
                "network_gene": list(gm.keys()) if gm else [],
                "gene_modifiers": {k: float(v) for k, v in gm.items()},
                "exogenous_supply": {k: float(v) for k, v in es.items()},
                "perturbations": sub_perts,
                "notes": f"Expanded from pleiotropic {t['test_id']} (outcome {i+1}/{len(t['expected_outcomes'])})",
                "evidence": t.get("evidence", []),
                "phenotype_node": oc["phenotype_node"],
                "comparison_baseline": "WT",
                "condition": "both",
                "expected_magnitude": "",
                "species": "Arabidopsis thaliana",
            })
    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python Agent/validate_pleiotropic.py <merged_network_dir>")
        sys.exit(1)
    net_dir = os.path.abspath(sys.argv[1])
    if not os.path.exists(net_dir):
        print(f"not found: {net_dir}"); sys.exit(1)

    pleio_src = os.path.join(net_dir, "data", "pleiotropic_perturbation_dataset.json")
    expanded = expand_pleio(pleio_src)
    total_pairs = len(expanded)
    print(f"expanded {total_pairs} pleiotropic outcome pairs")

    shadow = os.path.join(net_dir, "_pleio_shadow")
    if os.path.exists(shadow):
        shutil.rmtree(shadow)
    os.makedirs(os.path.join(shadow, "network"))
    os.makedirs(os.path.join(shadow, "data"))

    # Copy the main network files
    shutil.copy(os.path.join(net_dir, "network", "network.json"),             os.path.join(shadow, "network", "network.json"))
    shutil.copy(os.path.join(net_dir, "network", "algebraic_equations.json"), os.path.join(shadow, "network", "algebraic_equations.json"))
    # Propagate equation_spec if present (max_iterations override, etc)
    eq_spec = os.path.join(net_dir, "network", "equation_spec.json")
    if os.path.exists(eq_spec):
        shutil.copy(eq_spec, os.path.join(shadow, "network", "equation_spec.json"))

    recon = {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": "merged_arabidopsis",
            "species": "Arabidopsis thaliana",
            "created": str(date.today()),
            "total_tests": total_pairs,
            "in_network": total_pairs,
            "not_in_network": 0,
            "phenotype_node": "",
            "convention": "increased/decreased/unchanged relative to comparison_baseline",
        },
        "direction_threshold": 0.05,
        "perturbations": expanded,
    }
    save(os.path.join(shadow, "data", "reconciled_perturbation_dataset.json"), recon)

    # Run the three validators on the shadow dir
    shared = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared")
    pyexe = sys.executable
    # ODE best params observed via sensitivity sweep on the merged network.
    # Linear Hill (n=1) with K=0.5 — at n>=2 cooperative kinetics, the
    # dense feedback loops in the merged graph oscillate and prevent
    # convergence (62% accuracy vs 81% at n=1).
    for name, script, extra in [("algebraic", "flashp_validator.py", []),
                                ("ode",       "ode_validator.py",    ["--K", "0.5", "--n", "1"]),
                                ("rwr",       "rwr_validator.py",    [])]:
        print(f"\n-- {name} --")
        cmd = [pyexe, os.path.join(shared, script), shadow, "--csv", "--full-state"] + extra
        subprocess.run(cmd, check=True)

    # Copy results back with pleiotropic_ prefix
    val_dir = os.path.join(net_dir, "validation")
    os.makedirs(val_dir, exist_ok=True)

    copymap = [
        ("validation/script_validation_results.json", "pleiotropic_algebraic_results.json"),
        ("validation/validation_results.csv",         "pleiotropic_algebraic_results.csv"),
        ("validation/ode_validation_results.json",    "pleiotropic_ode_results.json"),
        ("validation/ode_validation_results.csv",     "pleiotropic_ode_results.csv"),
        ("validation/rwr_validation_results.json",    "pleiotropic_rwr_results.json"),
        ("validation/rwr_validation_results.csv",     "pleiotropic_rwr_results.csv"),
    ]
    for src_rel, dst_name in copymap:
        src = os.path.join(shadow, src_rel)
        dst = os.path.join(val_dir, dst_name)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"  wrote {os.path.basename(dst)}")

    # Build a combined summary CSV (same as v1 format)
    acc = {}
    for method, fname in [("algebraic", "pleiotropic_algebraic_results.csv"),
                          ("ode",       "pleiotropic_ode_results.csv"),
                          ("rwr",       "pleiotropic_rwr_results.csv")]:
        with open(os.path.join(val_dir, fname), encoding='utf-8') as f:
            for row in csv.DictReader(f):
                tid = row.get("test_id","")
                acc.setdefault(tid, {})[method] = (row.get("predicted_direction","") or row.get("predicted","") or "", row.get("correct","").lower()=="true")

    # Write pleiotropic_summary.csv
    out_path = os.path.join(val_dir, "pleiotropic_summary.csv")
    with open(out_path, "w", encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(["test_id","phenotype_node","expected_direction",
                    "algebraic_predicted","algebraic_correct",
                    "ode_predicted","ode_correct",
                    "rwr_predicted","rwr_correct"])
        # Cross-reference original expected_direction by reloading expanded list
        expected = {e["test_id"]: (e["phenotype_node"], e["expected_direction"]) for e in expanded}
        for tid in sorted(acc):
            pn, exp = expected.get(tid, ("",""))
            a = acc[tid].get("algebraic", ("",""))
            o = acc[tid].get("ode",       ("",""))
            r = acc[tid].get("rwr",       ("",""))
            w.writerow([tid, pn, exp, a[0], a[1], o[0], o[1], r[0], r[1]])
    print(f"  wrote {os.path.basename(out_path)}")

    # Compute headline numbers
    hits = {m: sum(1 for v in acc.values() if v.get(m,(None,False))[1]) for m in ("algebraic","ode","rwr")}
    total = len(acc)
    print("\n=== PLEIOTROPIC ACCURACY ===")
    for m in ("algebraic","ode","rwr"):
        a = 100*hits[m]/total if total else 0
        print(f"  {m:10s}: {hits[m]}/{total} = {a:.1f}%")

    # Clean up shadow dir
    shutil.rmtree(shadow)
    print(f"\nremoved shadow dir")

if __name__ == "__main__":
    main()
