#!/usr/bin/env python3
"""Step 5 — REFINEMENT. Reads validation failures, asks the LLM to propose
edge changes drawn from curated_edges.json (so DOI evidence is preserved),
applies them, snapshots, re-validates. Up to 3 iterations or stop on
<0.5% gain in 2 consecutive iters."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NET = ROOT / "network"
VAL = ROOT / "validation"
REF = ROOT / "refinement"
REF.mkdir(exist_ok=True)
REPO_ROOT = ROOT.parents[2]
VALIDATOR = REPO_ROOT / "Flash-P/Claude/Agent/shared/flashp_validator.py"
OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPT = """You are refining a mechanistic signaling network for shoot branching in Arabidopsis thaliana. The current network is failing the {n_fail} tests below. Propose 2–5 coordinated, evidence-based fixes per the FLASH-P REFINEMENT protocol.

CURRENT NETWORK ({n_nodes} nodes, {n_edges} edges):
{network_summary}

FAILING TESTS (with diagnostic ratios — ratio≈1.0 means no signal propagated; ratio>5 or <0.2 means cascade amplification; ratio 0.5–2.0 wrong direction means inverted dominant path):
{failure_list}

CANDIDATE EDGES from the 390-edge curated literature repository (you MUST pick fixes from these — do NOT invent edges; each has a DOI):
{candidate_edges}

DIAGNOSTIC PROTOCOL:
1. Cluster failures by mechanism (not by gene).
2. For each cluster, identify the structural cause from the ratio profile.
3. Propose 2–5 fixes that, together, address most of the clusters. Prefer fixes that close cascade gaps (e.g., add D14 → SMXL678 if D14 is missing from a SL cascade).
4. Every fix must reference a curated_edge_id (from the candidate list above) so DOI evidence is preserved.
5. Allowed actions: ADD_EDGE (using a curated_edge_id), REMOVE_EDGE (using current network edge_id), FLIP_SIGN (using current edge_id).

Return ONE JSON object with this EXACT shape (no surrounding text, no markdown):

{{
  "diagnosis": "2–4 sentences summarizing the failure clusters and root causes",
  "fixes": [
    {{
      "action": "ADD_EDGE",
      "curated_edge_id": "E057",
      "rationale": "Adds D14 -> SMXL678 to close the SL receptor gap; expected to fix T013, T071 (D14 KO cluster)"
    }},
    {{
      "action": "REMOVE_EDGE",
      "network_edge_id": "N018",
      "rationale": "Removes redundant Strigolactone -> Shoot_Branching shortcut; cascade now flows via D14 -> SMXL678 -> BRC1"
    }},
    {{
      "action": "FLIP_SIGN",
      "network_edge_id": "N005",
      "rationale": "Literature consensus is opposite direction; ..."
    }}
  ],
  "predicted_accuracy_gain_pct": 4.5
}}

Output ONLY the JSON object."""


def call_ollama(model, prompt, num_ctx=131072, timeout=2400):
    body = json.dumps({"model": model, "prompt": prompt, "format": "json",
        "stream": False, "options": {"temperature": 0.2, "num_ctx": num_ctx}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    print(f"  calling Ollama (model={model}, num_ctx={num_ctx}) ...", flush=True)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    print(f"  Ollama returned in {time.time()-t0:.0f}s", flush=True)
    return resp.get("response", "")


def read_failures():
    import csv
    csv_path = VAL / "validation_results.csv"
    failures = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            # the validator marks correct=True/False, not status=pass/fail
            if row.get("correct", "").strip().lower() == "false":
                failures.append({
                    "test_id": row["test_id"],
                    "expected": row.get("expected_direction"),
                    "predicted": row.get("predicted_direction"),
                    "ratio": float(row.get("ratio", 1.0) or 1.0),
                    "gene": row.get("gene", ""),
                    "perturbation_type": row.get("perturbation_type", ""),
                })
    return failures


def get_accuracy():
    p = VAL / "script_validation_results.json"
    if not p.exists(): return None
    d = json.load(p.open())
    # try several known shapes
    for path in [("metrics","accuracy"), ("summary","accuracy"), ("accuracy",),
                 ("metrics","overall_accuracy"), ("overall_accuracy",)]:
        cur = d
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False; break
        if ok and isinstance(cur, (int, float)):
            return float(cur)
    # fall back: derive from CSV correct/total
    try:
        import csv
        csv_path = VAL / "validation_results.csv"
        total = correct = 0
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                total += 1
                if row.get("correct","").strip().lower() == "true":
                    correct += 1
        return correct/total if total else None
    except Exception:
        return None


def run_validator():
    cmd = [sys.executable, str(VALIDATOR), str(ROOT), "--csv"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if r.returncode != 0:
        print("validator stderr:", r.stderr[:500], file=sys.stderr)
    return get_accuracy()


def network_summary(net):
    in_d = defaultdict(int); out_d = defaultdict(int)
    for ed in net["edges"]:
        in_d[ed["target"]] += 1; out_d[ed["source"]] += 1
    nodes = sorted(net["nodes"], key=lambda n: -(in_d[n["id"]] + out_d[n["id"]]))
    return "\n".join(
        f"  {n['id']:25s} {n['type']:15s} in={in_d[n['id']]:2d} out={out_d[n['id']]:2d}{' (source)' if n['is_source'] else ''}"
        for n in nodes
    )


def candidate_edges_repr(curated, current_net):
    """List curated edges that could fill cascade gaps — show ones touching at least
    one node already in the network or one of the canonical missing genes."""
    canonical_gap_nodes = {"D14", "MAX1", "MAX3", "MAX4", "D27", "CCD7", "CCD8", "KAI2",
                            "ABI3", "ABI4", "ABI5", "PIN1", "TIR1", "ARF", "TPL", "T6P",
                            "HXK1", "TPS1", "BA1", "HB21", "HB40", "HB53", "TIE1", "TIE2",
                            "miR156", "SPL9", "SPL15", "FT", "FUL", "SMXL6", "SMXL7", "SMXL8"}
    in_net = {n["id"] for n in current_net["nodes"]}
    relevant = []
    for ed in curated["edges"]:
        if ed["source"] in in_net or ed["target"] in in_net or \
           ed["source"] in canonical_gap_nodes or ed["target"] in canonical_gap_nodes:
            relevant.append(ed)
    # cap to avoid prompt bloat
    relevant = relevant[:200]
    out = []
    for ed in relevant:
        ev = ed.get("evidence", {})
        doi = ev.get("doi", "?") if isinstance(ev, dict) else "?"
        claim = ev.get("claim", "")[:60] if isinstance(ev, dict) else ""
        out.append(f"  {ed['edge_id']}  {ed['source']:25s} -[{ed['sign']:+d}]-> {ed['target']:25s}  {doi:30s} | {claim}")
    return "\n".join(out)


def apply_fix(net, fix, curated_by_id):
    action = fix.get("action", "")
    if action == "ADD_EDGE":
        cid = fix.get("curated_edge_id")
        ce = curated_by_id.get(cid)
        if ce is None:
            return False, f"curated_edge_id {cid} not found"
        # check no duplicate
        for ed in net["edges"]:
            if ed["source"] == ce["source"] and ed["target"] == ce["target"]:
                return False, f"edge {ce['source']}->{ce['target']} already in network"
        next_n = max((int(e["edge_id"][1:]) for e in net["edges"] if e["edge_id"].startswith("N")), default=0) + 1
        ev = ce.get("evidence", {})
        new_edge = {
            "edge_id": f"N{next_n:03d}",
            "source": ce["source"], "target": ce["target"], "sign": ce["sign"],
            "effect": "activation" if ce["sign"] > 0 else "inhibition",
            "mechanism": ev.get("claim", "") if isinstance(ev, dict) else "",
            "evidence": [ev] if isinstance(ev, dict) else [],
        }
        net["edges"].append(new_edge)
        # if endpoints not in nodes, add (best-effort typing — refinement should rarely add new nodes)
        existing_ids = {n["id"] for n in net["nodes"]}
        for endpoint in (ce["source"], ce["target"]):
            if endpoint not in existing_ids:
                net["nodes"].append({"id": endpoint, "type": "GENE",
                    "full_name": endpoint.replace("_", " "),
                    "description": f"gene {endpoint} (added in refinement)",
                    "is_source": False})
                existing_ids.add(endpoint)
        return True, f"added {ce['source']}->{ce['target']} from curated {cid}"
    if action == "REMOVE_EDGE":
        eid = fix.get("network_edge_id")
        before = len(net["edges"])
        net["edges"] = [ed for ed in net["edges"] if ed["edge_id"] != eid]
        if len(net["edges"]) < before:
            return True, f"removed {eid}"
        return False, f"network_edge_id {eid} not found"
    if action == "FLIP_SIGN":
        eid = fix.get("network_edge_id")
        for ed in net["edges"]:
            if ed["edge_id"] == eid:
                ed["sign"] = -ed["sign"]
                ed["effect"] = "activation" if ed["sign"] > 0 else "inhibition"
                return True, f"flipped sign of {eid}"
        return False, f"network_edge_id {eid} not found"
    return False, f"unknown action {action!r}"


def regenerate_equations(net):
    by_target = defaultdict(lambda: {"act": [], "inh": []})
    for ed in net["edges"]:
        by_target[ed["target"]]["act" if ed["sign"]>0 else "inh"].append(ed["source"])
    in_d = defaultdict(int); out_d = defaultdict(int)
    for ed in net["edges"]:
        in_d[ed["target"]] += 1; out_d[ed["source"]] += 1
    for n in net["nodes"]:
        n["is_source"] = (in_d[n["id"]] == 0)

    alg_eqs = []
    for n in sorted(net["nodes"], key=lambda x: x["id"]):
        nid = n["id"]; acts = by_target[nid]["act"]; inhs = by_target[nid]["inh"]
        if n["is_source"]:
            f = f"{nid} = gene_modifier + exogenous_supply"
        else:
            at = "1.0" if not acts else f"max({'*'.join(f'max({a},0.01)' for a in acts)},0.01)^(1/{len(acts)})"
            it = "1.0" if not inhs else f"min(1/max({'*'.join(inhs)},0.1),10.0)"
            f = f"{nid} = ({at}) * ({it}) * gene_modifier + exogenous_supply"
        alg_eqs.append({"node": nid, "type": n["type"], "is_source": n["is_source"],
                        "activators": acts, "inhibitors": inhs, "formula": f})

    K, nh = 1.0, 2
    ode_eqs = []
    for nd in sorted(net["nodes"], key=lambda x: x["id"]):
        nid = nd["id"]; acts = by_target[nid]["act"]; inhs = by_target[nid]["inh"]
        if nd["is_source"]:
            f = f"{nid} = 1.0 * 1.0 * gene_modifier + exogenous"
        else:
            at = " * ".join(f"({a}^{nh} * ({K**nh}+1) / ({K**nh} + {a}^{nh}))" for a in acts) or "1.0"
            it = " * ".join(f"(({K**nh}+1) / ({K**nh} + {i}^{nh}))" for i in inhs) or "1.0"
            f = f"{nid} = ({at}) * ({it}) * gene_modifier + exogenous"
        ode_eqs.append({"node": nid, "activators": acts, "inhibitors": inhs, "formula": f})

    n_src = sum(1 for n in net["nodes"] if n["is_source"])
    net["metadata"]["total_nodes"] = len(net["nodes"])
    net["metadata"]["total_edges"] = len(net["edges"])
    net["metadata"]["source_nodes"] = n_src
    net["metadata"]["source_percentage"] = round(100*n_src/max(len(net["nodes"]),1), 1)
    return alg_eqs, ode_eqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="awaescher/qwen3-235b-2507-unsloth-q3-k-xl:latest")
    ap.add_argument("--max-iters", type=int, default=3)
    ap.add_argument("--gain-threshold", type=float, default=0.5)
    args = ap.parse_args()

    curated = json.load((DATA/"curated_edges.json").open())
    curated_by_id = {ed["edge_id"]: ed for ed in curated["edges"]}

    base_acc = get_accuracy()
    print(f"baseline accuracy: {base_acc*100:.1f}%" if base_acc else "no prior validation found")

    best_iter = 0
    best_acc = base_acc or 0
    consec_low_gain = 0

    for it in range(1, args.max_iters + 1):
        print(f"\n=== iteration {it} ===")
        snap_dir = REF / f"iteration_{it}"
        snap_dir.mkdir(exist_ok=True)

        net = json.load((NET/"network.json").open())
        failures = read_failures()
        if not failures:
            print("no failures — stopping"); break

        prompt = PROMPT.format(
            n_fail=len(failures), n_nodes=len(net["nodes"]), n_edges=len(net["edges"]),
            network_summary=network_summary(net),
            failure_list="\n".join(
                f"  {f['test_id']:6s} {f['gene']:20s} {f['perturbation_type']:8s} expected={f['expected']:10s} predicted={f['predicted']:10s} ratio={f['ratio']:.4f}"
                for f in failures
            ),
            candidate_edges=candidate_edges_repr(curated, net),
        )

        resp = call_ollama(args.model, prompt)
        try:
            plan = json.loads(resp)
        except Exception as e:
            print(f"  failed to parse plan: {e}"); break

        print(f"  diagnosis: {plan.get('diagnosis', '')[:300]}")
        print(f"  proposed {len(plan.get('fixes', []))} fixes:")
        applied = []
        for f in plan.get("fixes", []):
            ok, msg = apply_fix(net, f, curated_by_id)
            print(f"    [{'ok' if ok else 'skip'}] {msg}")
            if ok:
                applied.append({**f, "status": "applied"})
            else:
                applied.append({**f, "status": "skipped", "reason": msg})

        if not [a for a in applied if a["status"] == "applied"]:
            print("  no fixes applied — stopping"); break

        # regenerate equations
        alg_eqs, ode_eqs = regenerate_equations(net)
        json.dump(net, (NET/"network.json").open("w"), indent=2, ensure_ascii=False)
        alg = json.load((NET/"algebraic_equations.json").open())
        alg["equations"] = alg_eqs; alg["metadata"]["total_equations"] = len(alg_eqs)
        json.dump(alg, (NET/"algebraic_equations.json").open("w"), indent=2, ensure_ascii=False)
        ode = json.load((NET/"ode_equations.json").open())
        ode["equations"] = ode_eqs; ode["metadata"]["total_equations"] = len(ode_eqs)
        json.dump(ode, (NET/"ode_equations.json").open("w"), indent=2, ensure_ascii=False)

        # snapshot
        shutil.copy(NET/"network.json", snap_dir/"network_snapshot.json")
        shutil.copy(NET/"algebraic_equations.json", snap_dir/"equations_snapshot.json")
        json.dump({"iteration": it, "diagnosis": plan.get("diagnosis"),
                   "predicted_gain_pct": plan.get("predicted_accuracy_gain_pct"),
                   "fixes": applied}, (snap_dir/"fixes_applied.json").open("w"), indent=2, ensure_ascii=False)

        # rerun validator
        new_acc = run_validator()
        shutil.copy(VAL/"script_validation_results.json", snap_dir/"validation_results.json")
        print(f"  baseline {best_acc*100:.1f}% -> after iter {it}: {new_acc*100:.1f}%" if new_acc else "  no accuracy reported")

        if new_acc is None:
            print("  validator failed — stopping"); break
        gain_pct = (new_acc - best_acc) * 100
        if gain_pct >= args.gain_threshold:
            best_acc = new_acc; best_iter = it
            consec_low_gain = 0
            print(f"  KEPT (+{gain_pct:.2f}%)")
        else:
            consec_low_gain += 1
            print(f"  reverted (gain {gain_pct:+.2f}% below {args.gain_threshold}%)")
            # restore previous snapshot
            if best_iter == 0:
                shutil.copy(REF.parent/"runs/qwen235/network/network.json", NET/"network.json") if (REF.parent/"runs/qwen235/network/network.json").exists() else None
            else:
                prev = REF / f"iteration_{best_iter}" / "network_snapshot.json"
                if prev.exists():
                    shutil.copy(prev, NET/"network.json")
                    al, od = regenerate_equations(json.load((NET/"network.json").open()))
                    alg = json.load((NET/"algebraic_equations.json").open()); alg["equations"]=al
                    json.dump(alg, (NET/"algebraic_equations.json").open("w"), indent=2, ensure_ascii=False)
                    ode = json.load((NET/"ode_equations.json").open()); ode["equations"]=od
                    json.dump(ode, (NET/"ode_equations.json").open("w"), indent=2, ensure_ascii=False)
            if consec_low_gain >= 2:
                print("  stopping: 2 consecutive iterations below threshold"); break

    final_acc = get_accuracy()
    report = {
        "metadata": {"flash_p_version":"1.0", "phenotype":"shoot_branching",
                     "species":"Arabidopsis thaliana", "created":"2026-05-03",
                     "model": args.model},
        "baseline_accuracy": base_acc,
        "best_iteration": best_iter,
        "best_accuracy": best_acc,
        "final_accuracy": final_acc,
    }
    json.dump(report, (REF/"refinement_report.json").open("w"), indent=2, ensure_ascii=False)
    print(f"\nrefinement complete. baseline={base_acc*100:.1f}% best={best_acc*100:.1f}% (iter {best_iter})")


if __name__ == "__main__":
    main()
