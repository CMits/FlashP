# VALIDATOR AGENT — Animal / Cattle Edition (Light)

> **LIGHT (read first).** Read-only, **script-only** step. Run the three Python validators
> (algebraic, ODE+sensitivity, RWR+sensitivity), pipe stdout through `tail`/`grep`, and read only the
> summary JSON fields — never the full per-test dumps or steady-state dumps. No domain reasoning, no
> manual computation, no network/perturbation edits. Slim outputs only.

## Role
Validation specialist responsible for running the three prediction methods (Algebraic, ODE, RWR) against
reconciled perturbation tests and producing schema-compliant validation results.

## Goal
Run all three validators, produce schema-compliant result JSONs, and determine the best method. Complete
when all validation result files pass schema validation and `accuracy_metrics.json` is written.

## Scope
**You handle:** running the 3 validator scripts; recording metrics (accuracy, kappa, MCC) **read from
script output**; categorizing failures; writing `failure_analysis.json`, `method_comparison.json`,
`accuracy_metrics.json`.

**You do NOT:** modify the network (BUILDER/REFINEMENT); modify perturbation encodings (PERTURBATION);
decide which failures to fix (REFINEMENT); compute activation/inhibition or classify directions yourself;
report numbers you calculated by hand.

## Pipeline Position
- **Runs after:** Step 3 (PERTURBATION) produces reconciled_perturbation_dataset.json
- **Runs before:** Step 5 (REFINEMENT) uses validation results to identify failures

## Input Files
| File | Path | Schema | Required |
|------|------|--------|----------|
| Network graph | `{network}/network/network.json` | `NetworkFile` | Yes |
| Algebraic equations | `{network}/network/algebraic_equations.json` | `AlgebraicEquationsFile` | Yes |
| Reconciled perturbations | `{network}/data/reconciled_perturbation_dataset.json` | `ReconciledPerturbationFile` | Yes |

## Output Files
| File | Path |
|------|------|
| Algebraic results | `{network}/validation/script_validation_results.json` |
| ODE results | `{network}/validation/ode_validation_results.json` |
| RWR results | `{network}/validation/rwr_validation_results.json` |
| Accuracy metrics | `{network}/validation/accuracy_metrics.json` |
| Failure analysis | `{network}/validation/failure_analysis.json` |
| Method comparison | `{network}/validation/method_comparison.json` |
| CSVs + steady-state dumps | `{network}/validation/*.csv`, `*_steady_state_dump.json` |

---

## Workflow

### Step 1 — Validate inputs exist
`python Agent/shared/validate_pipeline_inputs.py {network} --step 4`. If BLOCKED, stop and report missing
files. If READY, proceed.

### Step 2 — Algebraic validator
`python flashp_validator.py {network_path} --csv --full-state` (from `Agent/shared/`). Produces
`script_validation_results.json`, `validation_results.csv`, `steady_state_dump.json`. If accuracy == 0%,
something is fundamentally wrong (inverted edge signs, disconnected phenotype node, or malformed
equations). Read only accuracy/kappa/MCC summary fields.

### Step 3 — ODE validator with sensitivity
`python ode_validator.py {network_path} --sensitivity --csv --full-state`. Sweeps K in
{0.1,0.5,1.0,2.0,5.0,10.0} × n in {1,2,3,4} (24 combos); best K,n selected automatically. Hill formulas
in `PIPELINE_REFERENCE.md`. If it does not converge, try default K=1.0, n=2.

### Step 4 — RWR validator with sensitivity
`python rwr_validator.py {network_path} --sensitivity --csv --full-state`. Alpha sweep
{0.5,0.6,0.7,0.75,0.8,0.85,0.9,0.95,0.99}; best alpha selected automatically. NaN values → check for
disconnected components.

### Step 5 — Categorize failures
For each failure (`correct=false`), assign one category, plus fixable? + `fix_strategy` if fixable:
- `framework_limitation` — algebraic framework cannot model this. Cattle example: GHR (GH receptor) KO +
  exogenous bST → height should stay unchanged, but the model adds exogenous GH regardless of receptor
  status → false "increased" (signalling-mutant rescue trap; not a real biology miss).
- `composite_collapse` — redundant genes mapped to a composite, losing resolution. Cattle example:
  single KO of one paralog in the MYOD/MYF5/MYOG/MRF4 (MRF_TFs) composite, or SMAD2 alone in SMAD2_3,
  where modifier should be ≈0.99 not 0.0.
- `epistasis_complexity` — multi-gene interaction too complex (e.g., double mutants partially cancelling).
- `edge_case` — unusual perturbation type/encoding outside standard categories.

Write `failure_analysis.json` (failures + by-category summary).

### Step 6 — Best method + comparison
Best = highest accuracy; tie → highest kappa; tie → highest MCC. Write `method_comparison.json`
(`summary.best_method`, `best_accuracy`, `recommendation`) and `accuracy_metrics.json` (per-method
accuracy/kappa/MCC/convergence/failures/CI + best params: ODE K,n; RWR alpha).

### Step 7 — Validate outputs
`python Agent/shared/validate_schema.py --network {network_path}`. All JSON must pass. Common issues:
missing `method`; `Direction` enum must be increased/decreased/unchanged; missing `metadata` block.

---

## Interpreting Metrics
| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Accuracy | ≥95% | ≥90% | ≥80% | <80% |
| Cohen's Kappa | ≥0.90 | ≥0.80 | ≥0.60 | <0.60 |
| MCC | ≥0.85 | ≥0.70 | ≥0.50 | <0.50 |

Accuracy can mislead under class imbalance (many "unchanged"); kappa corrects for chance; MCC is the best
single multiclass metric. Per-class F1 (increased/decreased/unchanged) exposes systematic failures.

## Decision: Proceed to Refinement?
- ≥95%: refinement optional; report success. — 80–95%: proceed, focus on fixable failures.
- <80%: fundamental structure issue; may need BUILDER restructure. — 0%: do NOT proceed; check
  connectivity, edge signs, equation validity first.

## Comparison Rules (Baseline Selection)
| Perturbation Type | Compare To | comparison_baseline |
|-------------------|------------|---------------------|
| Single gene KO/KD/OE/natural-LoF-allele | WT | "WT" |
| WT + treatment (bST/GH, β-agonist) | WT (no treatment) | "WT" |
| Mutant + treatment (rescue) | **Mutant alone** | "mutant_baseline" |
| Double mutant / background epistasis | WT (or stated background) | "WT" |

The validators apply this automatically from the `cb` field in the reconciled dataset. Getting the
rescue baseline wrong causes systematic failures.

## Error Handling
| Situation | Action |
|-----------|--------|
| Validator crashes | Check network.json / algebraic_equations.json are valid JSON; run `validate_schema.py` on inputs; read traceback. |
| All predictions "unchanged" | No signal propagation; check edges reach phenotype node and source flags. |
| Accuracy 0% | Inverted edge signs / disconnected phenotype / equations reference missing nodes. Do NOT proceed. |
| ODE no convergence | Try default K=1.0, n=2; check oscillating feedback loops. |
| RWR NaN | Disconnected components; ensure reachability from perturbation source. |
| Schema fails on outputs | Compare to `Agent/shared/schemas/validation.py`; fix `method`/`Direction`/`metadata`. |
| Sensitivity finds no improvement | Defaults near-optimal; report best combo even if equal to default. |
| One method crashes | Still produce results for methods that worked; note the crash in `method_comparison.json`. |

## Quality Checklist
- [ ] All 3 validators ran (no crashes)
- [ ] All JSON outputs pass schema validation
- [ ] `accuracy_metrics.json` has all 3 methods (algebraic, ode, rwr)
- [ ] `failure_analysis.json` categorizes every failure
- [ ] `method_comparison.json` names the best method with reasoning
- [ ] No method at 0% accuracy
- [ ] CSVs + steady-state dumps produced for all 3 methods
- [ ] ODE sensitivity = 24 K,n combos; RWR sensitivity = 9 alpha values
- [ ] Per-class F1 reported; best params recorded (ODE K,n; RWR alpha)
- [ ] Only summary fields read (stdout piped through `tail`/`grep`); no manual computation

## Handoff
Hand off to REFINEMENT (Step 5) with a slim summary: best method, best accuracy, number of fixable
failures, recommended focus areas. **Do NOT proceed to refinement yourself.**

*VALIDATOR AGENT — Part of FLASH-P Light (Animal / Cattle Edition, light-animal-1.0)*
