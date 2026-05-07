# Qwen3-235B-A22B run — shoot branching (fully model-driven)

**Model**: `awaescher/qwen3-235b-2507-unsloth-q3-k-xl:latest` (Unsloth Q3_K_XL, 104 GB on disk, ~117 GB RAM at inference, MoE 235B / 22B active, has thinking + tools, 256K context)
**Hardware**: M4 Max 128 GB
**Date**: 2026-05-03

## Approach

All biological judgment by qwen3 via direct Ollama API calls (no opencode harness — too slow / fragile). Python only does deterministic plumbing (build network from selection, generate equations from fixed math, prune unreachable nodes, dedup, validator/exporter wrappers).

## Step 1 — LITERATURE REVIEW (already done by gemma4 in `runs/gemma4/`)

Re-used `data/curated_edges.json` (390 edges) + `perturbation_dataset.json` (175 tests) from the gemma4 PDF run. Step 1 wasn't redone — Step 1 output is shared between models.

## Step 2 — BUILDER

Single Ollama call. Prompt fed all 390 edges + node-naming rules + canonical-cascade hints + "no shortcut edges" rule. Qwen3 returned: list of selected_edge_ids + node_types + biology_prose.

- 31 nodes / 55 edges (after dedup), 45.2% source nodes
- All canonical SL pathway nodes present: D14, MAX1-4, D27, KAI2, SMXL678, SMXL6/7/8, BRC1
- 5 naming-pattern violations (Cytokinins, Strigolactones plurals; MAX_Pathway, OsCKX9, VInv) — left unfixed; refinement was supposed to address
- 14 direct edges to Shoot_Branching — over-shortcutted, causing geometric-mean dilution

Build time: 348 s (~5.8 min) for the qwen3 call.

## Step 3 — PERTURBATION reconciliation (LLM-driven, single Ollama call)

This step is critical and was originally being done by hardcoded Python — a deterministic synonym dict missed many cases. After moving to qwen3:

| | Deterministic | LLM-driven (qwen3) |
|---|---|---|
| Coverage | 100/175 (57.1%) | **132/175 (75.4%)** |
| Ortholog mappings | 0 | **48** (pea/rice/petunia → Arabidopsis) |
| Composite redundancy | 0 | **3** (single SMXL paralogs at 0.97 not 0.0) |
| Treatment exogenous mappings | 4 | **13** |

This was the biggest lever in the entire run — qwen3 knows hundreds of orthologs (RMS3=D14, D3=MAX2, DAD1=D14, FC1=BRC1, etc.) and properly handled redundant-paralog modifier values per the PERTURBATION_AGENT spec.

LLM call time: 1752 s (~29 min) for one big 4 K-token prompt with thinking-mode.

## Step 4 — VALIDATOR (deterministic Python)

`flashp_validator.py` on 132 reconciled tests:

- **Accuracy: 70.5% (93/132)**
- **Cohen's κ: 0.3939** ("fair–moderate" agreement, near 0.41 boundary of "moderate")
- MCC: 0.43
- KO: 69.5% (73/105)
- OE: 62.5% (15/24)
- Treatment: 100% (1/1)
- KD: 50% (1/2)

Per-class F1: increased=0.79, decreased=0.56, unchanged=0.40.

## Step 5 — REFINEMENT (LLM-driven, ran twice)

Refinement v1 (deterministic recon, baseline 9%): 2 iterations, no improvement, qwen3 kept proposing edges already in the network (under plural variants). Stopped at 9%.

Refinement v2 (LLM recon, baseline 70.5%): 2 iterations, **lost ground** to 68.2%. Qwen3 correctly diagnosed the SL-cascade gap clusters but its proposed edges:
1. Often duplicates of already-present edges (plural-vs-singular naming).
2. When applied, broke the existing equations (e.g. flipped a sign that was actually correct).

Both iterations reverted to baseline. Refinement gave **0.0% net gain** — the structural problems (14 direct edges to phenotype, plural-singular duplicates) need REMOVALS / RENAMES, not ADDS, and qwen3 didn't propose those.

## Step 6 — EXPORT

- Cytoscape GraphML + SIF generated to `network/cytoscape/`
- Tables S1, S3, S4, S5, S7a (algebraic), S8 (method comparison), S9 (stratified) generated to `supplementary/`
- Fig_Data CSVs: accuracy_summary, complexity_accuracy, pathlength_accuracy, edge_list, evidence_per_edge (390 edges), master_test_level (132 rows), network_summary
- **FRS = 5.33** ("small-scale solid")
- **DARS = 5.34** ("small-scale solid")

## Bottom line — what to report

Compared to gemma4 (`runs/gemma4/`):

| | gemma4:31b | **qwen3-235b-A22B** |
|---|---|---|
| Network nodes | 12 | **31** |
| Network edges | 20 | **55** |
| Tests reconciled | 64 (36.6%) | **132 (75.4%)** |
| Accuracy on covered | 85.9% | 70.5% |
| **Total correct / 175** | **55** | **93** |
| Cohen's κ | 0.66 | 0.39 |
| FRS | n/a (didn't reach S8) | **5.33 (small-scale solid)** |

**Qwen3 wins on coverage** (75% vs 37%) and **on absolute number of correct predictions** (93 vs 55). Gemma's small network has higher hit-rate on the few tests it could model, but the network excludes most of the literature's perturbation experiments.

**Refinement didn't help in either run** — local LLMs propose edge ADDS but rarely the structural REMOVALS (shortcut edges) and RENAMES (singular vs plural) that would actually move the needle.

The key bottleneck identified was the **PERTURBATION reconciliation step**, which was originally deterministic and gave 0% KO accuracy. LLM-driven reconciliation (single Ollama call, ortholog-aware, redundancy-aware) was the single biggest improvement in the entire run — taking accuracy from 9% to 70.5%.
