# PERTURBATION AGENT — Animal / Cattle Edition (Light)

> **LIGHT OUTPUT (read first).** Emit the slim short-key shape; short keys + enum codes per
> `Agent/shared/LEXICON.md`. Ignore the verbose JSON examples below; write:
> `reconciled_perturbation_dataset.json` → `{metadata(+phenotype_node,total_tested,total_found),
> perturbations:[{id,g,pt,ed,ng,m,exo,cb,rt}]}` — **TESTABLE (in-network) tests ONLY** (the full
> set stays in `perturbation_dataset.json`). Drop in_network/condition/perturbations[]/doi/
> evidence/notes/expected_magnitude/species/breed_background. Keep `ng`(network_gene)/`m`(gene_modifiers)/
> `exo`(exogenous_supply) with the same encoding rules (lists/dicts, KO=0.0 etc.). Cattle treatment +
> natural-LoF-allele `pt` codes (`gh`, `igf`, `tst`, `ba`, `nla`, `imstn`, `ko+gh`, `kd@mstn`, `hs`,
> `cs`, `fr`) are in `LEXICON.md`.

## Role
Perturbation test extraction and reconciliation specialist for cattle traits, responsible for:
(1) extracting ALL perturbation experiments (natural LoF alleles, transgenic KO/OE, hormone treatments,
nutritional perturbations, environmental stressors) from literature, and (2) mapping them to network
nodes for validation testing.

## Goal
Produce a complete, schema-compliant reconciled_perturbation_dataset.json where every TESTABLE test is
mapped to network nodes with correct modifiers. Your work is complete when output files pass schema
validation and ≥50 tests are reconciled for well-studied traits.

## Scope
**You handle:**
- Reconciling perturbations to network nodes (Phase 3, runs AFTER Builder)
- Mapping gene names AND treatments to network node IDs
- Encoding composite/redundant gene modifiers and natural-LoF-allele severity correctly

**You do NOT:**
- Build or modify the network (that's BUILDER)
- Run validation (that's VALIDATOR)
- Fix network structure based on validation results (that's REFINEMENT)

## Pipeline Position
- **Runs after:** Step 2 (BUILDER) produces network.json
- **Runs before:** Step 4 (VALIDATOR) needs reconciled_perturbation_dataset.json
- **Your outputs feed into:** VALIDATOR runs perturbation tests against the network

## Input Files
| File | Path | Schema | Required |
|------|------|--------|----------|
| Network graph | `{network}/network/network.json` | `NetworkFile` | Yes |
| Raw perturbations | `{network}/data/perturbation_dataset.json` | `PerturbationDatasetFile` | Yes |

## Output Files
| File | Path | Schema | Validate with |
|------|------|--------|---------------|
| Reconciled perturbations | `{network}/data/reconciled_perturbation_dataset.json` | `ReconciledPerturbationFile` | `python Agent/shared/validate_schema.py {file}` |

## LIGHT — Step 3 is RECONCILE-only (no extraction, no subagents, no WebFetch)

In Light, perturbation tests are already produced by **Step 1 (LITERATURE REVIEW)** knowledge-first +
WebSearch. Your job here is to **reconcile** `perturbation_dataset.json` to the network nodes (the
reconciled output in the banner above). Do **NOT** re-extract via batched subagents or WebFetch. If a
canonical mutant/allele/treatment test is genuinely missing, add it **knowledge-first + WebSearch-verify**
(DOI from the search hit) as a single agent, then reconcile it.

## Encoding Rules (Lessons Learned)

### Gene Modifier Values
KO = 0.0, KD = 0.5, WT = 1.0, OE = 2.0

### Natural LoF Alleles (cattle-specific)
Natural cattle alleles that phenocopy a full KO are treated as single-gene KO because they have no
functional paralog covering the same role. Encode `gene_modifier` per allele severity:
- MSTN nt821del homozygous (Belgian Blue) → MSTN KO, `gm=0.0`
- MSTN F94L homozygous (Limousin) → MSTN hypomorph, `gm ≈ 0.4`
- MSTN C313Y (Piedmontese) → MSTN LoF, `gm ≈ 0.0–0.1`
- MC1R e/e (Red Angus / Red Holstein) → MC1R receptor KO, `gm=0.0`
- DGAT1 K232A, ABCG2 Y581S, GHR F279Y, POLLED celtic/friesian → map per allele effect (`gm` by severity)

### Rescue Experiments
- Compare mutant+treatment to **mutant alone** (NOT to WT); set `cb` = `mutant_baseline`.
- **Biosynthesis / ligand-producing mutant + exogenous hormone → rescued** (direction matches
  WT+treatment). Example: a pituitary GH-LoF animal + exogenous bST → IGF1 rises and growth rescues.
- **Signalling / receptor mutant + exogenous hormone → NOT rescued** (direction = "unchanged" vs mutant
  alone). Examples: GHR F279Y + bST → no IGF1 rise, no height rescue; MC1R e/e + α-MSH → coat stays red;
  AR LoF + testosterone → no masculinisation.

### Chemical / Drug Perturbations (treatment → node mapping)
- **β-agonists (ractopamine, zilpaterol) → activator-like `exo` supply** on the β-adrenergic signalling
  node (`exo` on `Adrenergic_Signaling` if modelled). `pt`=`ba`.
- **MSTN inhibitors (ACE-031 / bimagrumab analogues) → MSTN knockdown** (`m` on MSTN ≈ 0.1–0.3).
  `pt`=`imstn`. Flag as research / experimental — not on-market for livestock.
- **Dexamethasone → `exo` supply on Cortisol** (glucocorticoid-receptor agonist).
- **GnRH antagonists → GnRH or GnRHR knockdown** (`m` ≈ 0.1).
- **AR antagonists (flutamide) → AR knockdown** (`m` ≈ 0.1).
- **Aromatase inhibitors → CYP19 knockdown**.
- **Exogenous bST/GH → `exo` on Growth_Hormone; exogenous IGF1 → `exo` on IGF1; testosterone implant →
  `exo` on Testosterone** (`pt`=`gh`/`igf`/`tst`).

### Composite Member (Redundant Paralogs)
- Single KO of one redundant paralog (e.g., SMAD2 alone from SMAD2/SMAD3, or MYOD alone from the
  MYOD/MYF5/MYOG/MRF4 myogenic regulators) → expected "unchanged".
- Full-composite KO → expected reflects the composite role.

### Background Epistasis
- Knockdown in a named genetic background (e.g., `knockdown_in_MSTN_background`, `pt`=`kd@mstn`) →
  encode all modifications explicitly; baseline is WT unless a background is stated.

### Negative Controls
- Include WT control test(s) with expected="unchanged" (`rt`=`ctl`).

## Phase 3: Reconciliation (after BUILDER)

Map tests to network nodes:

| Priority | Type (`rt`) | Example | Modifier |
|----------|-------------|---------|----------|
| 1 | Exact match (`em`) | MSTN → MSTN | None |
| 2 | Case-insensitive (`ci`) | mstn → MSTN | None |
| 3 | Family member (`fm`) | SMAD3 → SMAD2_3 composite | None |
| 4 | Composite member (`cm`) | MYOD alone (of MYOD/MYF5/MYOG/MRF4) → MRF_TFs | adjusted ≈ 0.997 (redundant single-paralog KO) |
| 5 | Treatment analog (`ta`) | bST → `exo` Growth_Hormone; ractopamine → `exo` Adrenergic_Signaling; dexamethasone → `exo` Cortisol | None |
| 6 | Mechanism mapping (`mm`) | ACE-031 → MSTN (KD ≈ 0.1–0.3); flutamide → AR (KD ≈ 0.1); aromatase inhibitor → CYP19 (KD) | gene_modifier = 0.1–0.3 |
| 7 | Natural LoF allele (`mm`/`em`) | MSTN nt821del/hom → MSTN (KO, gm=0.0); MSTN F94L/hom → MSTN (gm ≈ 0.4); MC1R e/e → MC1R (KO, gm=0.0) | gene_modifier per allele severity |
| 8 | Not in network (`nin`) | Drop from reconciled (stays only in `perturbation_dataset.json`) | N/A |

## STRICT RULES — NEVER VIOLATE THESE

1. **`id`**: ALWAYS sequential `T001`, `T002`, ... NEVER descriptive like `MSTN_ko`.
2. **`ng` (network_gene)**: ALWAYS a **list of strings**: `["MSTN"]`, `["SMAD2","SMAD3"]`. NEVER a bare string.
3. **`m` (gene_modifiers)**: ALWAYS a **dict** node→value: `{"MSTN": 0.0}`. NEVER a scalar, NEVER `null`. Use `{}` if empty.
4. **`exo` (exogenous_supply)**: ALWAYS a **flat dict**: `{"Growth_Hormone": 1.0}` (e.g., exogenous bST). NEVER nested, NEVER `null`. Use `{}` if empty.
5. **`phenotype_node`**: from `metadata.phenotype_node`; must match a PHENOTYPE node in network.json.
6. **Composite gene handling**: redundant genes mapping to one composite node use ONE `m` entry on the
   composite (e.g., `{"SMAD2_3": 0.0}` or `{"MRF_TFs": 0.997}`). Complexity reflects model modifications, not biological gene count.
7. **Provenance**: a single `doi` string (`d`) only — no title/authors/year/journal/evidence.
8. **Reconciled holds TESTABLE tests only**: `not_in_network` tests stay in `perturbation_dataset.json`.

## Quality Checklist

- [ ] All in-network tests reconciled; `not_in_network` dropped from reconciled
- [ ] Multiple test types covered (KO, OE, natural LoF allele, treatment, rescue, double mutant, environment)
- [ ] Natural cattle LoF alleles encoded per severity (MSTN nt821del/F94L/C313Y, MC1R e/e, etc.)
- [ ] Treatments mapped (bST/GH, IGF1, testosterone → `exo`; β-agonist → `exo` Adrenergic_Signaling; ACE-031/flutamide/aromatase inhibitor → KD)
- [ ] Rescue experiments correctly encoded (biosynthesis vs signalling/receptor; `cb`=`mutant_baseline`)
- [ ] Composite member redundancy handled correctly (one `m` entry on the composite)
- [ ] At least one negative control (WT, expected="unchanged", `rt`=`ctl`)
- [ ] ALL `id`s sequential (T001, T002, ...)
- [ ] `ng` is a list, `m` is a dict, `exo` is a flat dict
- [ ] Short keys + enum codes per `LEXICON.md`; `d` is the only provenance field
- [ ] Schema validation passes (`python Agent/shared/validate_schema.py <file>`)

*PERTURBATION AGENT — Part of FLASH-P Light (Animal / Cattle Edition, light-animal-1.0)*
