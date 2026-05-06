# Gemma4:31b run — shoot branching

**Model**: `gemma4:31b` (Q4_K_M, 19 GB, 256K ctx, MoE, has tools/thinking)
**Date**: 2026-05-02 / 2026-05-03

## Step 1 — LITERATURE REVIEW (PDF-based)

- 68 papers extracted via direct Ollama-API loop (`extract_edges.py`)
- 390 edges, 175 perturbations
- Schema-clean (DOIs valid, sign as int, flat evidence, sequential IDs)
- 1 timeout retried successfully (Rameau 2015)
- 5 papers came back with no DOI (Beveridge 2023, Ligerot 2017, Nahas 2025, Tal 2022, dun 2023)

## Step 2 — BUILDER (single-shot Ollama call + Python polish)

- 12 nodes, 20 edges (after polish)
- 58.3% source nodes
- All 5 structural checks PASS
- Network covers BRC1, MAX2, SMXL678, Auxin, Cytokinin, Strigolactone, Sucrose, GA, FT, D53, Decapitation, Shoot_Branching
- **Missing canonical genes**: D14 (the SL receptor!), MAX1, MAX3, MAX4, D27 — Gemma struggled to construct deeper cascade

Two iterations were tried: v1 had 26 nodes / 100 edges raw (69% source — over cap); v2 had 15 nodes / 42 edges raw (66% source). Both polished down to similar end state (~12 nodes).

## Step 3 — PERTURBATION reconciliation (deterministic Python)

- 64 / 175 tests reconciled in-network (36.6%)
- 111 tests target genes outside the 12-node network
- Top in-network: MAX2 (26 tests), BRC1 (20)
- Top missed: D14 (10), MAX1 (8), MAX4 (7), D27 (6)

## Step 4 — VALIDATOR

- **Accuracy: 85.9% (55/64)**
- **Cohen's κ: 0.6626** — substantial agreement
- MCC: 0.4762
- Convergence: 100%
- KO accuracy: 93.8% (45/48)
- OE accuracy: 50% (6/12) — weakest
- Treatment accuracy: 100% (4/4)

## Bottom line

Gemma4:31b's BUILDER was the bottleneck. Strong literature extraction (Step 1) and solid validation accuracy on the tests it could model — but the network was too small (12 nodes vs gold-standard 38) which capped coverage at 36.6%.
