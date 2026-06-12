# FLASH-M Pipeline Reference (on-demand detail, Medical edition)

> **Why this file exists.** This is the heavy reference material that used to live in
> `CLAUDE.md`. `CLAUDE.md` is auto-loaded into **every** turn of the main thread *and every
> subagent*, so keeping bulk reference there is paid on every request. This file loads **only when an
> agent reads it**. Agents that need the detail (BUILDER, REFINEMENT, EXPORT) read it explicitly.
> Medical edition: same math/structure as plant FLASH-P Light, plus the `DRUG` node type and
> drug-response traps.

---

## Agent QA Architecture — Scripts Enforce, Prompts Guide

Every FLASH-M agent has two distinct quality-assurance responsibilities:

- **SCRIPT-enforced invariants**: Deterministic, schema-derivable checks. Scripts run every time, cannot be skipped by an LLM, and can report or auto-fix violations. This is the **guarantee layer**.
- **LLM-judgment responsibilities**: Biological plausibility, mechanism descriptions, paralog/isoform collapsing, evidence-quality reasoning, drug mechanism-of-action interpretation. Only an expert agent can perform these. This is the **guidance layer** (the agent's MD file).

Each agent's instruction file must contain a **QA Split** section that enumerates both. Scripts live in `Agent/shared/` following the naming pattern `check_<domain>_structure.py`.

### Current state

- **BUILDER**: Full QA split documented in `BUILDER_AGENT.md §1.2`. Enforcement via `Agent/shared/check_network_structure.py` covering 5 invariants (connectivity, DOI presence, naming, `is_source` flag — incl. DRUG sources, phenotype/readout node sanity). Auto-fixable: connectivity and `is_source`. Report-only: DOI, naming, phenotype.

### Applying the QA Split to other agents (roadmap)

- **LITERATURE REVIEW** — SCRIPT: every curated edge/test has a resolvable `doi`. LLM: relevance, DOI verification against the search hit, drug MoA accuracy.
- **PERTURBATION** — SCRIPT: `test_id` sequential from `T001`; `expected_direction` ∈ {`up`,`dn`,`nc`}; `comparison_baseline` ∈ {`WT`,`mutant`}; every test has a DOI. LLM: reconciliation reasoning (mapping genes/drugs to network nodes), composite-collapse and drug→target decisions.
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
| `network_gene` | `["EGFR"]` (always a list) | `"EGFR"` (bare string) |
| `gene_modifiers` | `{"EGFR": 0.0}` (always a dict) | `0.0` (scalar) |
| `exogenous_supply` | `{"EGF": 1.0}` (flat dict) | `{"node": "EGF", "value": 1.0}` (nested) |
| `exogenous_supply` (none) | `{}` (empty dict) | `null` or omitted |
| `test_id` | `"T001"` (sequential) | `"egfr_ko"` (descriptive) |
| `sign` | `1` or `-1` (int) | `"positive"` (string) |
| Evidence | single `doi` string (`d`) | any fat/nested evidence object |
| Keys/enums | short form per `LEXICON.md` (`gene_modifiers`→`m`, `knockout`→`ko`, `DRUG`→`D`) | — (long form accepted, not emitted) |

---

## Equation Formulas (fixed math — same for ALL node types, incl. DRUG)

```
Node = Activation * Inhibition * Gene_Modifier + Exogenous_Supply
Activation  = (product(max(activators, 0.01)))^(1/n_activators)    # geometric mean
Inhibition  = min(1/max(product(inhibitors), 0.1), 10.0)           # bounded inverse
Source nodes: Node = gene_modifier + exogenous_supply

Gene_Modifier: KO=0.0, KD=0.5, WT=1.0 (default), OE=2.0
Exogenous_Supply: default=0.0, treatment/ligand=1.0

Parameters: epsilon=0.1, K=10.0, activator_floor=0.01, damping=0.7
direction_threshold=0.05, max_iterations=50, convergence_tolerance=0.0001
```
**Gene_modifier applies to EVERY node** (GENE, PROTEIN_COMPLEX, HORMONE/ligand, METABOLITE, DRUG, etc.). Every node can be perturbed.
**WT baseline = 1.0** for all nodes (guaranteed when all inputs = 1.0).

**Drug nodes**: A `DRUG` node is normally an `is_source` input set to `0.0` (absent) at WT baseline and `1.0` (administered) under treatment via `exogenous_supply`. A kinase inhibitor is modeled as an **inhibitor edge** onto its target; a degrader/PROTAC as a strong KD/KO `gene_modifier` on the target; an agonist/ligand as an **activator edge**.

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

**Bounded inverse inhibition**: If an inhibitor goes to 0 (KO, or a drug that fully inhibits its target), the bounded inverse hits K=10.0 (max) — a STRONG upward push on the node it inhibits.

**Signal dilution through cascades**: Every intermediate step dampens the signal. `Drug→Target→...→Readout` propagates weaker than a shortcut. Sometimes the shortcut IS the better modeling choice.

**Feedback loops**: Can cause oscillation (damping=0.7 stabilizes) or non-convergence. Oncogenic signaling is full of them (see TRAP 1).

---

## Signal Propagation Traps (medical)

**TRAP 1 — POSITIVE feedback loops in oncogenic signaling**: e.g. RTK→PI3K→PIP3→AKT and a positive arm back onto the RTK (or RAS↔RAF reactivation). A perturbation that lifts an upstream inhibitor can make the whole axis SPIKE via the positive loop, producing WRONG predictions.
**FIX**: Break the loop — make the apical input a near-source (driven by ligand/DRUG only) and route downstream effects forward, not back onto the apex. **NEGATIVE feedback** (ERK→DUSP6→ERK, mTORC1→S6K1→IRS1) STABILIZES and should be INCLUDED. Only POSITIVE mutual activation causes runaway amplification. See `BUILDER_AGENT.md` §12 Motif 2.

**TRAP 2 — Redundant paralog single KO with geometric mean**: A redundant family (HRAS/KRAS/NRAS → RAS; AKT1/2/3 → AKT) modeled as a composite node needs single-KO modifier ≈ 0.99, NOT 0.667. Even 0.9 can cascade and wrongly predict "decreased" when the expected result is "unchanged" (the paralogs compensate).

**TRAP 3 — Drug-resistance mutation rescue experiments**: When a target is inhibited by a drug but carries a resistance mutation (EGFR **T790M**/**C797S**, BCR-ABL **T315I**, gatekeeper mutations), the model naively removes the target's activity regardless of whether the drug can still bind → it wrongly predicts the drug still works. Framework limitation.
**MITIGATION**: Use the **Perception Gate** motif (`BUILDER_AGENT.md` §12 Motif 1). Model the drug and its target-binding as CO-REQUIRED for inhibition: the resistance mutation breaks the gate so the drug edge no longer propagates. **CRITICAL**: the DRUG node must route its effect through ONE binding/target node — no bypass edges directly onto the readout — so a resistance mutation at the target blocks the drug entirely. Contrast with a **sensitizing** mutation (EGFR L858R), where the gate stays intact and rescue/response succeeds.

**TRAP 4 — Dead-end nodes creating false unchanged predictions**: If a node (including a DRUG node left after pruning) has no path to the readout, any perturbation of it predicts "unchanged". Every node with perturbation tests must connect to the phenotype/readout.

**TRAP 5 — Missing is_source flag (esp. DRUG nodes)**: Nodes with no activators AND no inhibitors MUST have `is_source: true`. DRUG nodes, ligands/growth factors, environmental context (Hypoxia, Radiation), and constitutive genes are sources. Missing this flag can cause validator convergence issues and RWR failures.

**TRAP 6 — Drug pleiotropy / off-target without explicit edges**: A multi-target drug (e.g. dasatinib hits BCR-ABL + SRC family) modeled with a single target edge mispredicts off-target experiments. Add explicit edges for each clinically relevant target rather than relying on one.

---

## Node Naming

| Type | Style | Examples |
|------|-------|---------|
| GENE | ALL_CAPS | EGFR, KRAS, TP53, AKT1, BRAF, PTEN |
| PROTEIN_COMPLEX | CAPS_underscore | PI3K, NF_KB, mTORC1 |
| HORMONE (ligand/cytokine/GF) | Title_Case / mixed | EGF, TGF_Alpha, TNF_Alpha, IL_6 |
| METABOLITE | Title_Case | Lactate, Glucose, ROS |
| ENVIRONMENT (cellular context) | Title_Case | Hypoxia, Serum_Starvation, Radiation |
| PHENOTYPE (readout) | Title_Case | Cell_Proliferation, Apoptosis, Phospho_AKT, Tumor_Volume_in_vivo |
| REGULATORY_RNA | lowercase_prefix | miR21, miR34a |
| DRUG | Title_Case | Erlotinib, Osimertinib, Imatinib, Trastuzumab, Anti_PD1 |

Enforced by `check_network_structure.py` check 3 (report-only). Note GENE is strict ALL_CAPS — `Egfr` fails; use `EGFR`.

---

## Comparison Rules

| Perturbation Type | Compare To |
|-------------------|------------|
| Single gene LoF/GoF/KO/KD/OE | WT / parental / untransduced |
| WT cells + drug | WT (untreated) |
| Mutant cells + drug (rescue/resistance) | **Mutant alone** (`comparison_baseline: mutant`) |
| Double mutant | WT |
| Combination therapy | either monotherapy, or vehicle |

---

## Source-node percentage rule

Target **30–50%**, hard cap **60%**. Literature-built networks have an inherent source-count floor because peripheral genes, ligands, and many regulators lack curated upstream regulation (and DRUG nodes are always sources). Below 30% is fine (well-connected). If source % > 50%, BUILDER must trim or document a `literature_gap` for the missing upstream regulators. Above 60% is rejected.

---

## Network Quality Metric — FLASH Rigor Score (FRS) + DARS

Accuracy alone is class-imbalance-sensitive and scale-blind. We report quality in four tiers:

**Tier 1 — Quality** (per method): Cohen's κ (chance-corrected), κ 95% CI (Fleiss–Cohen), MCC. Landis & Koch (1977) bands: κ > 0.81 almost perfect, 0.61–0.80 substantial, 0.41–0.60 moderate, < 0.41 fair/weak.

**Tier 2 — Scope**: N (nodes), E (edges), T (tests), T_eff (difficulty-weighted = Σ complexity_score), L̄ (mean path length to readout).

**Tier 3 — Composite**: `FRS = κ × log₂(T × (N + E))` — "chance-corrected bits of validated mechanistic claim."

**Tier 4 — Difficulty-Adjusted**: `DARS = κ × log₂(T_eff × (N + E))`, where `complexity_score ∈ {1=easy, 2=medium, 3+=hard}` = n_mutations + n_treatments per test (so a resistance-mutation+drug combo scores higher). Also report per-stratum κ/accuracy (easy/medium/hard); stratum κ suppressed at n < 5.

**Shared bands**: 0–3 weak • 3–6 small-scale solid • 6–9 medium-scale solid • 9–12 large-scale strong • 12+ exceptional.

**Why reward complexity**: FLASH-M networks are literature-built and held-out-validated (BUILDER never sees perturbation results), so complexity is a scope *claim*, not an overfitting risk. Implementation: `Agent/shared/rigor_score.py`. FRS/DARS/stratified appear in `metrics.*` of each `validation/*.json` and in Tables S8/S9 + `Fig_Data/network_summary.csv`.

---

## File Structure

```
<NET>/   (networks/<Readout_Slug>/)
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
