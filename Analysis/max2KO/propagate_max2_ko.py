#!/usr/bin/env python3
"""
Algebraic propagation (Jacobi + damping) for the current Arabidopsis shoot
branching network — MAX2 knockout.

Reads `Arabidopsis/Shoot_Branching_network/network/algebraic_equations.json`
and applies the FLASH-P algebraic update with parameters from that file:

    x_i^(t) = (1 - lambda) * x_i^(t-1) + lambda * f_i(x^(t-1))

with the standard FLASH-P node formula

    f_i = Activation_i * Inhibition_i * gene_modifier_i + exogenous_supply_i

and source nodes f_i = gene_modifier_i + exogenous_supply_i.

Convergence: stop when max_i |x_i^(t) - x_i^(t-1)| < delta.

Outputs (under PropagationFigure/data/):
    max2_ko_iteration_trace.csv   (iteration, max_abs_delta_t, then ALL 38 node columns)
    max2_ko_steady_state.json     (WT + KO final values, comparison vs validator dump)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
NET_DIR = REPO / "Arabidopsis" / "Shoot_Branching_network" / "network"
VAL_DIR = REPO / "Arabidopsis" / "Shoot_Branching_network" / "validation"

ALG_JSON = NET_DIR / "algebraic_equations.json"
DUMP_JSON = VAL_DIR / "steady_state_dump.json"

OUT_CSV = ROOT / "data" / "max2_ko_iteration_trace.csv"
OUT_JSON = ROOT / "data" / "max2_ko_steady_state.json"

PERTURBATION = {"MAX2": 0.0}
TEST_ID = "T005"
MAX_ITER_TRACE = 200


def load_equations(path: Path) -> tuple[list[dict], dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["equations"], data.get("parameters", {})


def activation_factor(activators: list[str], state: dict[str, float], floor: float) -> float:
    if not activators:
        return 1.0
    prod = 1.0
    for a in activators:
        prod *= max(state[a], floor)
    return prod ** (1.0 / len(activators))


def inhibition_factor(
    inhibitors: list[str], state: dict[str, float], denom_floor: float, cap: float
) -> float:
    if not inhibitors:
        return 1.0
    if len(inhibitors) == 1:
        denom = max(state[inhibitors[0]], denom_floor)
    else:
        p = 1.0
        for h in inhibitors:
            p *= state[h]
        denom = max(p, denom_floor)
    return min(1.0 / denom, cap)


def compute_raw(eq: dict, state: dict[str, float], g_mod: dict[str, float], params: dict) -> float:
    node = eq["node"]
    g = float(g_mod.get(node, 1.0))
    if eq.get("is_source"):
        return g  # exogenous_supply default = 0
    a = activation_factor(eq["activators"], state, params["activator_floor"])
    inh = inhibition_factor(
        eq["inhibitors"], state, params["epsilon"], params["K"]
    )
    return a * inh * g


def jacobi_step(
    equations: list[dict],
    state: dict[str, float],
    g_mod: dict[str, float],
    params: dict,
) -> dict[str, float]:
    raw = {eq["node"]: compute_raw(eq, state, g_mod, params) for eq in equations}
    damp = params["damping"]
    return {
        eq["node"]: (1.0 - damp) * state[eq["node"]] + damp * raw[eq["node"]]
        for eq in equations
    }


def max_abs_delta(prev: dict[str, float], cur: dict[str, float]) -> float:
    return max(abs(cur[k] - prev[k]) for k in prev)


def propagate(
    equations: list[dict],
    params: dict,
    perturbation: dict[str, float],
    *,
    max_iter: int,
    stop_when_delta: float | None,
) -> tuple[list[dict[str, float]], list[float], int | None]:
    nodes = [eq["node"] for eq in equations]
    state = {n: 1.0 for n in nodes}
    g_mod = {n: 1.0 for n in nodes}
    g_mod.update(perturbation)
    history: list[dict[str, float]] = [dict(state)]
    deltas: list[float] = [float("nan")]
    converged_at: int | None = None
    for t in range(1, max_iter + 1):
        prev = state
        state = jacobi_step(equations, prev, g_mod, params)
        d = max_abs_delta(prev, state)
        history.append(dict(state))
        deltas.append(d)
        if stop_when_delta is not None and d < stop_when_delta:
            converged_at = t
            break
    return history, deltas, converged_at


def load_dump_block(test_id: str) -> dict:
    with open(DUMP_JSON, encoding="utf-8") as f:
        for block in json.load(f):
            if block.get("test_id") == test_id:
                return block
    raise RuntimeError(f"{test_id} not found in {DUMP_JSON}")


def main() -> int:
    equations, params = load_equations(ALG_JSON)
    print(f"Loaded {len(equations)} equations from {ALG_JSON.relative_to(REPO)}")
    print(
        f"Params: damping={params['damping']}, tol={params['convergence_tolerance']}, "
        f"K={params['K']}, eps={params['epsilon']}, floor={params['activator_floor']}"
    )

    # Pass 1: stop at convergence to record the actual convergence step.
    _, deltas_conv, converged_at = propagate(
        equations,
        params,
        PERTURBATION,
        max_iter=max(MAX_ITER_TRACE, params.get("max_iterations", 100)),
        stop_when_delta=params["convergence_tolerance"],
    )

    # Pass 2: full horizon (no early stop) for the figure trace.
    history, deltas, _ = propagate(
        equations,
        params,
        PERTURBATION,
        max_iter=MAX_ITER_TRACE,
        stop_when_delta=None,
    )

    nodes = [eq["node"] for eq in equations]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    cols = ["iteration", "max_abs_delta_t"] + nodes
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=cols)
        w.writeheader()
        for it, st in enumerate(history):
            row = {"iteration": it, "max_abs_delta_t": deltas[it] if it < len(deltas) else ""}
            for n in nodes:
                row[n] = f"{st[n]:.10g}"
            w.writerow(row)

    # Cross-check final values against the validator's steady_state_dump.
    block = load_dump_block(TEST_ID)
    ref_perturbed = block["steady_state_values"]["perturbed"]
    ref_wt = block["steady_state_values"]["WT"]
    final = history[-1]
    diffs = {n: abs(final[n] - ref_perturbed[n]) for n in nodes if n in ref_perturbed}
    max_diff_node = max(diffs, key=diffs.get)
    print(
        f"Converged at t={converged_at} "
        f"(delta={deltas_conv[converged_at] if converged_at else 'n/a'})"
    )
    print(
        f"Cross-check vs steady_state_dump.json [{TEST_ID}]: "
        f"max abs diff = {diffs[max_diff_node]:.6g} on {max_diff_node}; "
        f"Shoot_Branching_run={final['Shoot_Branching']:.4f}, "
        f"dump={ref_perturbed['Shoot_Branching']:.4f}"
    )

    out = {
        "test_id": TEST_ID,
        "perturbation": PERTURBATION,
        "parameters": params,
        "converged_at_iteration": converged_at,
        "n_iterations_in_trace": len(history),
        "wt": {n: ref_wt.get(n, 1.0) for n in nodes},
        "ko_run": final,
        "ko_dump": ref_perturbed,
        "max_abs_diff_vs_dump": {"node": max_diff_node, "value": diffs[max_diff_node]},
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_CSV} ({len(history)} rows, {len(nodes)} node cols)")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
