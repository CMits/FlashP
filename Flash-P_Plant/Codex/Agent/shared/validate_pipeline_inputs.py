#!/usr/bin/env python3
"""
FLASH-P v1.0 — Pipeline Input Validation

Validates that required input files exist and are valid BEFORE each pipeline step.

Usage:
    python validate_pipeline_inputs.py <network_dir> --step <1|2|3|4|5>

Step dependencies:
    Step 1 (Literature): No inputs required (starts from scratch)
    Step 2 (Builder):    curated_edges.json must exist and be valid
    Step 3 (Perturbation): network.json + perturbation_dataset.json must exist
    Step 4 (Validator):  network.json + algebraic_equations.json + reconciled_perturbation_dataset.json
    Step 5 (Refinement): All validation results must exist
"""

import json
import sys
from pathlib import Path

STEP_REQUIREMENTS = {
    1: {
        "name": "Literature Review",
        "files": [],
        "description": "No prerequisites — starts from scratch.",
    },
    2: {
        "name": "Builder",
        "files": [
            ("data/curated_edges.json", "Curated edges from literature review"),
        ],
        "description": "Requires completed literature review.",
    },
    3: {
        "name": "Perturbation Reconciliation",
        "files": [
            ("network/network.json", "Network graph from builder"),
            ("network/algebraic_equations.json", "Equations from builder"),
            ("data/perturbation_dataset.json", "Raw perturbations from literature review"),
        ],
        "description": "Requires completed builder and literature review.",
    },
    4: {
        "name": "Validator",
        "files": [
            ("network/network.json", "Network graph"),
            ("network/algebraic_equations.json", "Algebraic equations"),
            ("data/reconciled_perturbation_dataset.json", "Reconciled perturbations"),
        ],
        "description": "Requires completed reconciliation.",
    },
    5: {
        "name": "Refinement",
        "files": [
            ("network/network.json", "Network graph"),
            ("network/algebraic_equations.json", "Algebraic equations"),
            ("data/reconciled_perturbation_dataset.json", "Reconciled perturbations"),
            ("validation/script_validation_results.json", "Algebraic validation results"),
            ("validation/ode_validation_results.json", "ODE validation results"),
            ("validation/rwr_validation_results.json", "RWR validation results"),
        ],
        "description": "Requires completed validation.",
    },
}


def validate_step(net_dir, step):
    req = STEP_REQUIREMENTS[step]
    print(f"Step {step}: {req['name']}")
    print(f"  {req['description']}")
    print()

    errors = []
    for rel_path, desc in req["files"]:
        full_path = net_dir / rel_path
        if not full_path.exists():
            errors.append(f"MISSING: {rel_path} ({desc})")
            print(f"  FAIL: {rel_path} — NOT FOUND")
        else:
            # Basic JSON validity check
            try:
                data = json.loads(full_path.read_text(encoding="utf-8"))
                if not data:
                    errors.append(f"EMPTY: {rel_path}")
                    print(f"  FAIL: {rel_path} — EMPTY FILE")
                else:
                    print(f"  OK:   {rel_path}")
            except json.JSONDecodeError as e:
                errors.append(f"INVALID JSON: {rel_path}: {e}")
                print(f"  FAIL: {rel_path} — INVALID JSON")

    if not req["files"]:
        print("  No prerequisites required.")

    return errors


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate pipeline step inputs")
    parser.add_argument("network_dir", help="Path to network directory")
    parser.add_argument("--step", type=int, required=True, choices=[1, 2, 3, 4, 5])
    args = parser.parse_args()

    net_dir = Path(args.network_dir)
    if not net_dir.exists():
        print(f"ERROR: {net_dir} does not exist")
        sys.exit(1)

    errors = validate_step(net_dir, args.step)

    print()
    if errors:
        print(f"BLOCKED: Cannot proceed with Step {args.step}. "
              f"{len(errors)} missing/invalid input(s).")
        sys.exit(1)
    else:
        print(f"READY: All inputs for Step {args.step} are present and valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
