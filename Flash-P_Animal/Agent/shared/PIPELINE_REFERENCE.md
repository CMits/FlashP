# FLASH-P Pipeline Reference (on-demand detail, Animal / Cattle edition)

> **Why this file exists.** This is the heavy reference material that used to live in
> `CLAUDE.md`. `CLAUDE.md` is auto-loaded into **every** turn of the main thread *and every
> subagent*, so keeping bulk reference there is paid on every request. This file loads **only when an
> agent reads it**. Agents that need the detail (BUILDER, REFINEMENT, EXPORT) read it explicitly.
> Animal edition: same math/structure as plant FLASH-P Light, with cattle (*Bos taurus*) trait biology.

---

## Agent QA Architecture — Scripts Enforce, Prompts Guide

Every FLASH-P agent has two distinct quality-assurance responsibilities:

- **SCRIPT-enforced invariants**: Deterministic, schema-derivable checks. Scripts run every time, cannot be skipped by an LLM, and can report or auto-fix violations. This is the **guarantee layer**.
- **LLM-judgment responsibilities**: Biological plausibility, mechanism descriptions, paralog/breed-allele collapsing, evidence-quality reasoning. Only an expert agent can perform these. This is the **guidance layer** (the agent's MD file).

Each agent's instruction file must contain a **QA Split** section that enumerates both. Scripts live in `Agent/shared/` following the naming pattern `check_<domain>_structure.py`.

### Current state

- **BUILDER**: Full QA split documented in `BUILDER_AGENT.md §1.2`. Enforcement via `Agent/shared/check_network_structure.py` covering 5 invariants (connectivity, DOI presence, naming, `is_source` flag, phenotype node sanity). Auto-fixable: connectivity and `is_source`. Report-only: DOI, naming, phenotype.

### Applying the QA Split to other agents (roadmap)

- **LITERATURE REVIEW** — SCRIPT: every curated edge/test has a resolvable `doi`. LLM: relevance, DOI verification against the search hit, breed-allele / treatment accuracy.
- **PERTURBATION** — SCRIPT: `test_id` sequential from `T001`; `expected_direction` ∈ {`up`,`dn`,`nc`}; `comparison_baseline` ∈ {`WT`,`mutant`}; every test has a DOI. LLM: reconciliation reasoning (mapping genes/treatments to network nodes), composite-collapse decisions.
- **REFINEMENT** — SCRIPT: every fix has `biological_justification`; `source`/`target` are valid node names; iteration snapshot integrity; **post-removal connectivity re-check**. LLM: which edge to add/remove and why.
- **VALIDATOR / EXPORT** — already fully script-based; no LLM component.

### Non-blocking by design

Structural checks report failures and exit non-zero, but they are **not** registered as blocking `settings.json` hooks (the only hook is a non-blocking schema check on write). They are invoked explicitly by the agent (post-build self-check) or by the user manually.

---

## Schema Compliance — critical field rules (most common violations)

ALL output files MUST conform to Pydantic schemas in `Agent/shared/schemas/`. Run validation manually:
```bash
python Agent/shared/validate_schema.py --network {dir}
```

| Field | CORRECT (Light) | WRONG |
|-------|----------------|-------|
| `network_gene` | `["MSTN"]` (always a list) | `"MSTN"` (bare string) |
| `gene_modifiers` | `{"MSTN": 0.0}` (always a dict) | `0.0` (scalar) |
| `exogenous_supply` | `{"GH": 1.0}` (flat dict) | `{"node": "GH", "value": 1.0}` (nested) |
| `exogenous_supply` (none) | `{}` (empty dict) | `null` or omitted |
| `test_id` | `"T001"` (sequential) | `"mstn_ko"` (descriptive) |
| `sign` | `1` or `-1` (int) | `"positive"` (string) |
| Evidence | single `doi` string (`d`) | any fat/nested evidence object |
| Keys/enums | short form per `LEXICON.md` (`gene_modifiers`→`m`, `knockout`→`ko`) | — (long form accepted, not emitted) |

---

## Equation Formulas (fixed math — same for ALL node types)

```
Node = Activation * Inhibition * Gene_Modifier + Exogenous_Supply
Activation  = (product(max(activators, 0.01)))^(1/n_activators)    # geometric mean
Inhibition  = min(1/max(product(inhibitors), 0.1), 10.0)           # bounded inverse
Source nodes: Node = gene_modifier + exogenous_supply

Gene_Modifier: KO=0.0, KD=0.5, WT=1.0 (default), OE=2.0
Exogenous_Supply: default=0.0, treatment (e.g. bST/GH, testosterone)=1.0

Parameters: epsilon=0.1, K=10.0, activator_floor=0.01, damping=0.7
direction_threshold=0.05, max_iterations=50, convergence_tolerance=0.0001
```
**Gene_modifier applies to EVERY node** (GENE, PROTEIN_COMPLEX, HORMONE, METABOLITE, ENVIRONMENT, etc.). Every node can be perturbed.
**WT baseline = 1.0** for all nodes (guaranteed when all inputs = 1.0).

### ODE Hill Function Rules
```
Hill activation:  f(x) = x^n * (K^n + 1) / (K^n + x^n)
Hill inhibition:  g(x) = (K^n + 1) / (K^n + x^n)
Sensitivity: K in {0.1, 0.5, 1.0, 2.0, 5.0, 10.0}, n in {1, 2, 3, 4}
```

### RWR Rules
```
Signed graph propagation, alpha sweep: {0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99}
```

---

## Equation Dynamics

**Geometric mean activation**: Adding more activators DILUTES the signal. `(a1 * a2)^(1/2)` is less than `a1` if `a2 < 1`. A node with 5 activators is HARDER to move than one with 1 activator — but downstream cascade amplification often compensates.

**Bounded inverse inhibition**: If an inhibitor goes to 0 (KO — e.g. MSTN loss-of-function), the bounded inverse hits K=10.0 (max) — a STRONG upward push on the node it inhibits (muscle mass surges when MSTN is lost).

**Signal dilution through cascades**: Every intermediate step dampens the signal. `GH→GHR→IGF1→...→Phenotype` propagates weaker than a shortcut. Sometimes the shortcut IS the better modeling choice.

**Feedback loops**: Can cause oscillation (damping=0.7 stabilizes) or non-convergence. The GH–IGF1 axis has physiological NEGATIVE feedback (IGF1 suppresses GH secretion) that STABILIZES — include it.

---

## Signal Propagation Traps (cattle)

**TRAP 1 — POSITIVE feedback loops**: A mutual-activation loop (e.g. an apical hormone and a receptor/transporter that each up-regulate the other) lets an upstream KO spike the whole axis, producing WRONG predictions.
**FIX**: Break the loop — make the apical hormone a near-source (driven by ENVIRONMENT/treatment only) and route downstream forward, not back onto the apex. **NEGATIVE feedback** (GH→IGF1→(–)GH; cortisol→(–)GnRH) STABILIZES and should be INCLUDED. Only POSITIVE mutual activation causes runaway amplification. See `BUILDER_AGENT.md` §12 Motif 2.

**TRAP 2 — Redundant paralog single KO with geometric mean**: A redundant family (myogenic regulators MYOD/MYF5/MYOG/MRF4; keratin/pigment paralogs) modeled as a composite node needs single-KO modifier ≈ 0.99, NOT 0.667. Even 0.9 can cascade and wrongly predict "decreased" when expected is "unchanged" (paralogs compensate).

**TRAP 3 — Signaling/treatment rescue experiments**: When a signaling gene (e.g. GHR) is KO'd and exogenous hormone (bST/GH) is applied, the model adds the hormone regardless of whether the receptor is functional → rescue always "works" wrongly (GHR-KO + GH). Framework limitation.
**MITIGATION**: Use the **Perception Gate** motif (`BUILDER_AGENT.md` §12 Motif 1). Model the receptor as the gate: the hormone node has ONE outgoing edge (`GH → GHR`) and ALL downstream effects flow through the receptor, NOT directly from the hormone. With no bypass edges, receptor KO blocks the response regardless of exogenous hormone.

**TRAP 4 — Dead-end nodes creating false unchanged predictions**: If a node has no path to the phenotype, any perturbation of it predicts "unchanged". Every node with perturbation tests must connect to the trait.

**TRAP 5 — Missing is_source flag**: Nodes with no activators AND no inhibitors MUST have `is_source: true`. ENVIRONMENT nodes (Nutrition, Heat_Stress, Cold_Stress, Photoperiod, Age, Pregnancy_Status), constitutive genes, and unregulated hormones are sources. Missing this flag can cause validator convergence issues and RWR failures.

---

## Node Naming

| Type | Style | Examples |
|------|-------|---------|
| GENE | ALL_CAPS | MSTN, GHR, IGF1, PLAG1, HMGA2, MC1R, ASIP, NCAPG, LCORL |
| PROTEIN_COMPLEX | CAPS_underscore | MRF_complex, AR_complex |
| HORMONE | Title_Case | GH, IGF1, Testosterone, Cortisol, Alpha_MSH |
| METABOLITE | Title_Case | Glucose, NEFA |
| ENVIRONMENT | Title_Case | Nutrition, Heat_Stress, Cold_Stress, Photoperiod, Age, Pregnancy_Status |
| PHENOTYPE | Title_Case | Height, Muscle_Mass, Milk_Yield, Coat_Colour, Feed_Efficiency |
| REGULATORY_RNA | lowercase_prefix | miR1, miR133 |

Enforced by `check_network_structure.py` check 3 (report-only). Note GENE is strict ALL_CAPS — `Mstn` fails; use `MSTN`.

---

## Comparison Rules

| Perturbation Type | Compare To |
|-------------------|------------|
| Single gene KO/KD/OE/natural-LoF-allele | WT |
| WT + treatment (e.g. bST/GH, β-agonist) | WT (no treatment) |
| Mutant + treatment (rescue) | **Mutant alone** (`comparison_baseline: mutant`) |
| Double mutant / background epistasis | WT (or the stated background) |

---

## Source-node percentage rule

Target **30–50%**, hard cap **60%**. Literature-built networks have an inherent source-count floor because peripheral genes, biosynthesis enzymes, ENVIRONMENT inputs, and many regulators lack curated upstream regulation. Below 30% is fine (well-connected). If source % > 50%, BUILDER must trim or document a `literature_gap` for the missing upstream regulators. Above 60% is rejected.

---

## Network Quality Metric — FLASH Rigor Score (FRS) + DARS

Accuracy alone is class-imbalance-sensitive and scale-blind. We report quality in four tiers:

**Tier 1 — Quality** (per method): Cohen's κ (chance-corrected), κ 95% CI (Fleiss–Cohen), MCC. Landis & Koch (1977) bands: κ > 0.81 almost perfect, 0.61–0.80 substantial, 0.41–0.60 moderate, < 0.41 fair/weak.

**Tier 2 — Scope**: N (nodes), E (edges), T (tests), T_eff (difficulty-weighted = Σ complexity_score), L̄ (mean path length to phenotype).

**Tier 3 — Composite**: `FRS = κ × log₂(T × (N + E))` — "chance-corrected bits of validated mechanistic claim."

**Tier 4 — Difficulty-Adjusted**: `DARS = κ × log₂(T_eff × (N + E))`, where `complexity_score ∈ {1=easy, 2=medium, 3+=hard}` = n_mutations + n_treatments per test. Also report per-stratum κ/accuracy (easy/medium/hard); stratum κ suppressed at n < 5.

**Shared bands**: 0–3 weak • 3–6 small-scale solid • 6–9 medium-scale solid • 9–12 large-scale strong • 12+ exceptional.

**Why reward complexity**: FLASH-P networks are literature-built and held-out-validated (BUILDER never sees perturbation results), so complexity is a scope *claim*, not an overfitting risk. Implementation: `Agent/shared/rigor_score.py`. FRS/DARS/stratified appear in `metrics.*` of each `validation/*.json` and in Tables S8/S9 + `Fig_Data/network_summary.csv`.

---

## File Structure

```
<NET>/   (networks/<Trait_Slug>/)
  data/
    curated_edges.json             <- ALL edges {nodes:{NAME:TYPE}, edges:[{eid,s,t,x,d}]} (full repository)
    perturbation_dataset.json      <- ALL perturbation experiments {perturbations:[{id,g,pt,ed,sp,d}]}
    reconciled_perturbation_dataset.json  <- TESTABLE tests mapped to network {perturbations:[{id,g,pt,ed,ng,m,exo,cb,rt}]}
    literature_judge_report.json   <- Step 1.5 slim gap report
  network/
    network.json                   <- nodes + edges USED in model (subset of curated_edges)
    algebraic_equations.json       <- equations (formula field MANDATORY)
    ode_equations.json             <- generated/optimized by ODE validator
    node_annotations.json
    judge_review_iteration_1.json  <- Step 2.5 slim {verdict, suggestions[]}
    cytoscape/                     <- GraphML, SIF, attributes (NO disconnected nodes)
  validation/
    script_validation_results.json (Algebraic) | ode_validation_results.json | rwr_validation_results.json
    ode_sensitivity_results.json | rwr_sensitivity_results.json
    accuracy_metrics.json | failure_analysis.json | method_comparison.json
    *.csv | *steady_state_dump.json
  refinement/
    refinement_report.json | refined_network.json | refined_equations.json | iteration_N/
  supplementary/
    Table_S1..S9 *.csv | master_test_level.csv | Fig_Data/
  provenance/  pipeline_manifest.json
```

### Supplementary principle
- S1 = everything FOUND (edges). S2 = everything FOUND (perturbations).
- S3–S7 = what was USED/TESTED in the model. S8/S9 = metrics.
- This shows comprehensive curation → intelligent selection.
