# PERTURBATION AGENT — FLASH-M Light (Medical edition)

> **LIGHT OUTPUT (read first).** Emit the slim short-key shape; short keys + enum codes per
> `Agent/shared/LEXICON.md`. Ignore the verbose JSON examples below; write:
> `reconciled_perturbation_dataset.json` → `{metadata(+phenotype_node,total_tested,total_found),
> perturbations:[{id,g,pt,ed,ng,m,exo,cb,rt}]}` — **TESTABLE (in-network) tests ONLY** (the full
> set stays in `perturbation_dataset.json`). Drop in_network/condition/perturbations[]/doi/
> evidence/notes/expected_magnitude/species/cell_system. Keep `ng`(network_gene)/`m`(gene_modifiers)/
> `exo`(exogenous_supply) with the same encoding rules (lists/dicts, KO=0.0 etc.). Medical `pt`
> codes (`dt`,`ki`,`ab`,`lig`,`prot`,`rm+d`,`sm+d`,`combo`,`vc`, …) per LEXICON.

## Role
Perturbation reconciliation specialist responsible for mapping **genetic AND drug** perturbation
experiments to network nodes (including DRUG nodes) for validation testing.

## Goal
Produce a complete, schema-compliant `reconciled_perturbation_dataset.json` where every test is mapped
to network nodes with correct modifiers and `exo` entries. Done when output passes schema validation
and ≥50 tests are reconciled (≥80 for well-studied oncogenic drivers like EGFR, KRAS, BRAF).

## Scope
**You handle:**
- Reconciling perturbations (genes AND drugs) to network nodes
- Mapping clinical gene/drug names to network node IDs
- Encoding composite/redundant gene modifiers (RAS, AKT, ERK, MEK, RAF, BCL2 families)
- Encoding drug administration via `exo` and resistance mutations via the drug-node `m`

**You do NOT:**
- Build or modify the network (BUILDER)
- Run validation (VALIDATOR)
- Fix network structure from validation results (REFINEMENT)

## Pipeline Position
- Runs after Step 2 (BUILDER) produces `network.json`
- Runs before Step 4 (VALIDATOR), which consumes `reconciled_perturbation_dataset.json`

## Input / Output Files
| File | Path | Schema |
|------|------|--------|
| Network graph (in) | `{network}/network/network.json` | `NetworkFile` |
| Raw perturbations (in) | `{network}/data/perturbation_dataset.json` | `PerturbationDatasetFile` |
| Reconciled perturbations (out) | `{network}/data/reconciled_perturbation_dataset.json` | `ReconciledPerturbationFile` |

Validate: `python Agent/shared/validate_schema.py {file}`

## LIGHT — Step 3 is RECONCILE-only (no extraction, no subagents, no WebFetch)
In Light, perturbation tests are already produced by **Step 1 (LITERATURE REVIEW)** knowledge-first +
WebSearch. Your job is to **reconcile** `perturbation_dataset.json` to the network nodes (the reconciled
output in the banner above). Do **NOT** re-extract via batched subagents or WebFetch. If a canonical
mutant/drug/resistance test is genuinely missing, add it **knowledge-first + WebSearch-verify** (DOI
from the search hit) as a single agent, then reconcile it.

## Encoding Rules (medical edition)

### Gene modifier values
| Perturbation | `m` value | Notes |
|---|---|---|
| Wild-type / parental | 1.0 (default) | WT baseline |
| CRISPR knockout (full LoF) | 0.0 | Homozygous, biallelic |
| Heterozygous LoF / hypomorph | 0.5 | One functional allele |
| siRNA / shRNA knockdown | 0.5 (0.1 if >90% reduction) | |
| Oncogenic GoF (KRAS G12D, BRAF V600E, EGFR L858R) | 2.0 | Constitutive activation |
| Overexpression (cDNA, amplification) | 2.0 | Same multiplier as GoF |
| PROTAC / degron-induced degradation | 0.0 | Full LoF at protein level |
| Dominant-negative | 0.5 | Partial LoF on the WT allele's output |

### Drug → target mapping
- **Drug node present** (kinase inhibitor, mAb, etc.): administer via `exo` on the DRUG node;
  `m` empty. Dose: `1.0`=therapeutic, `2.0+`=super-pharmacological, `0.5`=sub-therapeutic.
- **Kinase inhibitor → target**: drug encoded as an inhibitor edge on its target (BUILDER's job);
  reconcile the drug test as `exo:{Drug:1.0}`. A tool compound with no DRUG node → encode as target
  knockdown `m:{Target:0.1}` (0.0 for irreversible covalent at saturating dose), `exo:{}` (medical
  analog of plant `NPA → PIN1 KD`; name compound + target in reasoning).
- **PROTAC / degrader**: encode as `m:{Target:0.0}` (mechanism_mapping `rt:mm`) — degrades the target
  protein rather than acting through a drug edge.
- **Agonist / ligand stimulation**: `exo:{Ligand:1.0}` (`pt:lig`).

### Drug rescue / resistance encoding (CRITICAL)
Medical analog of the plant biosynthesis-vs-signaling rescue rule. Drug has ONE outgoing edge to its
target (Perception Gate, BUILDER §12). Compare drug-on-mutant tests to **mutant alone** (`cb:mutant`).
- **Sensitizing mutation + drug → drug works** (`sm+d`): EGFR L858R + Erlotinib → `ed:dn`.
  `m:{EGFR:2.0}, exo:{Erlotinib:1.0}, cb:mutant`.
- **Resistance mutation + drug → drug fails** (`rm+d`): EGFR T790M + Erlotinib → `ed:nc`. Drug
  administered but inert: `m:{Erlotinib:0.0}, exo:{Erlotinib:1.0}, cb:mutant`. (T790M reduces drug
  binding ~50×; the drug variable stays present via `exo` but its inhibitory effect is neutralized via
  the bounded-inverse formula. Alternative: if a separate `EGFR_drug_pocket` node exists,
  `m:{EGFR_drug_pocket:0.0}`.)
- **Bypass-track resistance + 1st-line drug → drug fails** (`rm+d`): MET amplification + Erlotinib →
  `ed:nc`. `m:{MET:2.0}, exo:{Erlotinib:1.0}, cb:mutant`. (Bypass keeps proliferation up; drug is
  functional but the cascade has parallel input.)
- **Combination overcomes resistance**: EGFR T790M + Osimertinib → `ed:dn` (3rd-gen TKI binds T790M);
  encode like the sensitizing case with the alternative drug node.

### Combination therapy (`combo`)
Both drugs administered: `m:{}, exo:{Erlotinib:1.0, Trametinib:1.0}, cb:WT`, `ed:dn` (blocks both EGFR
and MEK; prevents negative-feedback rebound; compare to vehicle). For synergy tests, add a monotherapy
comparison (note it in reasoning; `cb` enum accepts `WT`/`mutant` — add a separate monotherapy test the
validator compares against).

### Composite member (redundant paralogs)
| Family | Composite node | Single-isoform KO `m` |
|---|---|---|
| HRAS / KRAS / NRAS | `RAS` | 0.99 |
| AKT1 / AKT2 / AKT3 | `AKT` | 0.99 |
| ERK1 / ERK2 (MAPK1/3) | `ERK` | 0.997 |
| MEK1 / MEK2 (MAP2K1/2) | `MEK` | 0.99 |
| ARAF / BRAF / CRAF | `RAF` | 0.99 (use 0.0 only for full pan-RAF KO) |
| BCL2 / BCL_XL / MCL1 | `BCL2_family` | 0.997 |

Single-isoform KO mapped to a composite uses ONE `m` entry at the redundancy value (not 0.0); full
family KO uses 0.0. **Caveat**: many clinical mutations are isoform-specific (`KRAS G12C`, `BRAF V600E`)
— if the network has a separate single-isoform node, encode against that node, not the composite.

### Cellular-context (ENVIRONMENT) perturbations
Hypoxia, serum starvation, radiation, nutrient deprivation → `exo:{Hypoxia:1.0}` etc. on the
ENVIRONMENT node, `cb:WT`.

### Negative controls
Include ≥1 vehicle control (`pt:vc`, `m:{}, exo:{}, ed:nc`).

## Phase 3: Reconciliation priority
| Priority | Type (`rt`) | Example | Modifier |
|---|---|---|---|
| 1 | exact_match (`em`) | `EGFR` → `EGFR` | None |
| 2 | case_insensitive (`ci`) | `egfr` → `EGFR` | None |
| 3 | family_member (`fm`) | `MAPK1` → `ERK` (composite) | None |
| 4 | composite_member (`cm`) | `KRAS` → `RAS` | `m:{RAS:0.99}` (redundant) |
| 5 | exact_match (`em`) — DRUG node | `Erlotinib` → `Erlotinib` | via `exo` |
| 6 | mechanism_mapping (`mm`) | tool compound `JQ1` → BRD4 KD | `m:{BRD4:0.1}` |
| 7 | mechanism_mapping (`mm`) — resistance | EGFR T790M + Erlotinib | `m:{Erlotinib:0.0}` |
| 8 | not_in_network (`nin`) | — | excluded from reconciled file |

## Output shape — STRICT (short keys)
Reconciled entry: `{id,g,pt,ed,ng,m,exo,cb,rt}`. TESTABLE (in-network) tests only.
1. **`id`**: sequential `T001`, `T002`, … NEVER descriptive.
2. **`ng`** (network_gene): ALWAYS a **list of strings** — `["EGFR"]`, `["Erlotinib","Trametinib"]` for combos. NEVER a bare string.
3. **`m`** (gene_modifiers): ALWAYS a **dict** — `{"EGFR":0.0}`. NEVER a scalar/`null`. Use `{}` if empty.
4. **`exo`** (exogenous_supply): ALWAYS a **flat dict** — `{"Erlotinib":1.0}`. NEVER nested/`null`. Use `{}` if empty.
5. **`cb`** (comparison_baseline): `WT` or `mutant`. Drug-on-mutant (rescue/resistance) → `mutant`.
6. **`rt`** (reconciliation_type): short code per LEXICON.
7. **`phenotype_node`**: in `metadata` (recovered per test). Must match a PHENOTYPE node in `network.json`.
8. **Provenance**: single `doi` string (`d`) only — no title/authors/year/evidence.
9. **Drug-resistance**: `m:{<DrugNode>:0.0}, exo:{<DrugNode>:1.0}, cb:mutant`.
10. **Composite**: ONE `m` entry on the composite node at the redundancy value.

## Comparison Rules
| Perturbation Type | Compare To | `cb` |
|---|---|---|
| Single gene LoF/GoF/KO/KD/OE | WT / parental | `WT` |
| WT cells + drug | WT untreated | `WT` |
| Mutant cells + drug (rescue/resistance) | **Mutant alone** | `mutant` |
| Double mutant | WT | `WT` |
| Combination therapy | vehicle (or monotherapy in a separate test) | `WT` |
| Drug withdrawal | drug-treated steady state | `mutant` |

## QA Split
| Layer | Role |
|---|---|
| SCRIPT | `id` sequential from T001; `ed`/`cb` ∈ enum; every `m`/`exo` node exists in `network.json`; drug-node refs match DRUG-typed nodes; each test has a `doi` |
| LLM (this agent) | Reconcile clinical mutation/drug names to nodes; isoform-specific vs composite; resistance vs sensitizing; drug-node vs target-KD encoding; composite-collapse for paralog families |

## Quality Checklist
- [ ] RECONCILE-only — no re-extraction via subagents/WebFetch
- [ ] Multiple perturbation types covered: KO, KD, OE, drug monotherapy, combination, resistance, environment
- [ ] Drug-resistance correctly encoded (`m` on drug node = 0.0, `cb:mutant`)
- [ ] Tool compounds without drug nodes encoded as target knockdowns
- [ ] Composite-family redundancy handled (single isoform = 0.99, full family = 0.0)
- [ ] PROTAC/degraders encoded as `m:{Target:0.0}` (mechanism_mapping)
- [ ] ≥1 vehicle control (`ed:nc`)
- [ ] All `id` sequential (T001, …); `ng` list, `m` dict, `exo` flat dict
- [ ] `phenotype_node` in metadata; every test has a `doi`
- [ ] Schema validation passes (`python Agent/shared/validate_schema.py <file>`)

*PERTURBATION AGENT — FLASH-M Light (light-medical-1.0)*
