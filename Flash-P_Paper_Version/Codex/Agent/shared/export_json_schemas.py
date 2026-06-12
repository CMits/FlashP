#!/usr/bin/env python3
"""
Export Pydantic models to JSON Schema files.

Makes schemas language-agnostic — usable by R, JavaScript, etc.

Usage:
    python export_json_schemas.py [--output <dir>]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas import (
    AccuracyMetricsFile, AlgebraicEquationsFile, CandidatePapersFile,
    CuratedEdgesFile, FailureAnalysisFile, MergeLogFile,
    MethodComparisonFile, NetworkFile, NodeAnnotationsFile,
    ODEEquationsFile, ODESensitivityFile, PerturbationDatasetFile,
    PleiotropicPerturbationFile, ReconciledPerturbationFile,
    RefinementReportFile, RWRSensitivityFile, ValidationResultsFile,
)

SCHEMAS = {
    "candidate_papers": CandidatePapersFile,
    "curated_edges": CuratedEdgesFile,
    "perturbation_dataset": PerturbationDatasetFile,
    "reconciled_perturbation_dataset": ReconciledPerturbationFile,
    "network": NetworkFile,
    "algebraic_equations": AlgebraicEquationsFile,
    "ode_equations": ODEEquationsFile,
    "node_annotations": NodeAnnotationsFile,
    "validation_results": ValidationResultsFile,
    "ode_sensitivity_results": ODESensitivityFile,
    "rwr_sensitivity_results": RWRSensitivityFile,
    "accuracy_metrics": AccuracyMetricsFile,
    "failure_analysis": FailureAnalysisFile,
    "method_comparison": MethodComparisonFile,
    "refinement_report": RefinementReportFile,
    "merge_log": MergeLogFile,
    "pleiotropic_perturbation_dataset": PleiotropicPerturbationFile,
}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="Agent/shared/json_schemas")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    for name, model in SCHEMAS.items():
        schema = model.model_json_schema()
        path = out / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        print(f"  {path.name}")

    print(f"\nExported {len(SCHEMAS)} JSON Schema files to {out}")


if __name__ == "__main__":
    main()
