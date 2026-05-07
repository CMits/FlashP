<p align="center">
  <img src="Images/FlashP.png" alt="FLASH-P" width="100%" />
</p>

<h1 align="center">FLASH-P</h1>

<p align="center">
  <em>A multi-agent system that turns primary literature into validated, perturbation-testable causal signalling networks &mdash; for any trait, in any species.</em>
</p>

<p align="center">
  <a href="#what-is-flash-p">What is FLASH-P</a> &nbsp;&middot;&nbsp;
  <a href="#install-claude-code">Install</a> &nbsp;&middot;&nbsp;
  <a href="#run-the-flash-p-pipeline--three-ways">Run</a> &nbsp;&middot;&nbsp;
  <a href="#repository-layout">Layout</a> &nbsp;&middot;&nbsp;
  <a href="#flash-p-gui--coming-soon">GUI</a>
</p>

---

## What is FLASH-P?

FLASH-P is a **multi-agent system** that reads primary scientific literature directly from the web and turns it into a validated, perturbation-testable causal signalling network for any (trait, species) pair. Eight specialised agents pass a strict sequence of handoff files between each other — *literature reviewer → literature judge → builder → network judge → perturbation reconciler → validator → refiner → exporter* — and the two half-step audit gates (Step 1.5 and Step 2.5) review the previous stage's output before downstream agents are allowed to consume it. Every edge in the resulting network carries a DOI and an evidence sentence; every node is wired into closed-form algebraic, Hill-function ODE, and signed Random-Walk-with-Restart prediction equations so that the network is both human-readable and numerically simulable; and every perturbation experiment in the test set is scored under all three methods.

For the manuscript run packaged in this repository, FLASH-P was implemented and executed end-to-end inside [Claude Code](https://www.claude.com/product/claude-code) using the **Claude Opus 4.7** model. The agents themselves, however, are **model-agnostic prompts and structured handoff files** — they are not specific to any single model or provider. The upcoming [FLASH-P GUI](#flash-p-gui--coming-soon) will let users run the exact same pipeline against any frontier or open-source model: OpenAI (GPT / Codex), Google Gemini, Moonshot Kimi, DeepSeek, Qwen, and any local or self-hosted model exposed through provider-agnostic agent frameworks such as [OpenCode](https://github.com/opencode-ai/opencode), [Goose](https://github.com/block/goose), or [Aider](https://github.com/Aider-AI/aider).

The pipeline has already been used to build **13 networks** packaged in this repository: 6 per-phenotype Arabidopsis networks (flowering time, hypocotyl length, lateral root density, plant height, seed size, shoot branching), 1 merged six-trait Arabidopsis network exposing all six phenotype outputs simultaneously, and 6 other-species networks (*E. coli* lycopene, maize kernel-row number, poplar lignin S/G ratio, rice tillering, sorghum flowering time, wheat plant height). On a head-to-head benchmark against networks rebuilt from a cleaned PlantConnectome knowledge-base baseline using the same validation pipeline, FLASH-P networks reach substantially higher direction-call accuracy at a fraction of the size — see [`Outcome/FLASH-P_VS_KG/`](Outcome/FLASH-P_VS_KG) and [Supplementary Data 6](Supplementary%20Data/Supplementary%20Data%206.xlsx).

<p align="center">
  <img src="Images/FLASHP_Pipeline_Addition.svg" alt="FLASH-P multi-agent pipeline overview" width="100%" />
</p>

<p align="center">
  <em>The FLASH-P multi-agent pipeline &mdash; eight specialised agents and two half-step audit gates turn primary literature into a validated, perturbation-testable causal network.</em>
</p>

---

## What's in this repo

| Folder | Contents |
|---|---|
| [`Flash-P/`](Flash-P) | **The pipeline.** 8 agent definitions, the `CLAUDE.md` orchestrator, shared utilities. **This is the folder you open Claude Code in.** |
| [`Outcome/`](Outcome) | All paper outputs from our own runs — every network, validation result, refinement history, Cytoscape export, head-to-head KG-Cleaned comparison, supporting case studies, and the local open-source-model reproduction. |
| [`Supplementary Data/`](Supplementary%20Data) | Seven supplementary `.xlsx` tables, their build scripts, and per-dataset descriptions. |
| [`Images/`](Images) | Repository figures: `FlashP.png` (banner), `FLASHP_Pipeline_Addition.svg` (pipeline diagram), `FLASH_P_GUI.png` (GUI preview). |

---

## Install Claude Code

FLASH-P runs as a set of prompts inside [Claude Code](https://www.claude.com/product/claude-code). Install it once with one of:

```bash
# Cross-platform (requires Node.js ≥ 18)
npm install -g @anthropic-ai/claude-code
```

Or download the **Claude Desktop app** for macOS or Windows from <https://www.claude.com/product/claude-code>. Both the CLI (`claude` command) and the desktop app run the same pipeline.

You will also need a Claude.ai account (login the first time you start `claude`). Full install instructions and troubleshooting live in the official docs: <https://docs.claude.com/en/docs/claude-code>.

---

## Get the repo and open Claude Code in `Flash-P/`

> **Important — open Claude Code *inside* the `Flash-P/` subfolder, not at the repo root.** The pipeline reads `CLAUDE.md` and `Agent/*.md` as relative paths, and the other top-level folders (`Outcome/`, `Supplementary Data/`) are paper outputs that should stay outside the agent's working context.

```bash
git clone https://github.com/CMits/FlashP.git
cd FlashP/Flash-P          # ← note the second "Flash-P"
claude                     # starts Claude Code in this folder
```

Or with the **desktop app**: open Claude Desktop → *File → Open Project* → pick the **`Flash-P`** subfolder (not the repo root).

---

## Run the FLASH-P pipeline — three ways

All three modes produce the same artefacts. Pick whichever fits your task:

- **Option A — One-shot prompt** is fastest. Best for small / well-curated traits.
- **Option B — Step-by-step** is recommended when the trait has a large literature base. Each step starts with a fresh-ish context window so the pipeline stays meticulous, and the half-step judge gates (1.5, 2.5) get a chance to audit before the next agent picks up the output.
- **Option C — FLASH-P GUI** *(coming soon)*. An interactive desktop app: build, browse, save, and merge FLASH-P networks; run AI-driven analyses across many networks at once; and chat with your networks in natural language — all driven by the model and provider of your choice. See [FLASH-P GUI — coming soon](#flash-p-gui--coming-soon).

All command-line prompts (Options A and B) assume you opened Claude Code from inside `Flash-P/`, so paths are written relative to that folder. Replace `<TRAIT>` and `<SPECIES>` (e.g. `Shoot Branching`, `Arabidopsis thaliana`) before pasting.

### Option A — One-shot prompt

```text
Run the full FLASH-P pipeline for the trait <TRAIT> in <SPECIES>.
```

### Option B — Step-by-step prompts

Run these one at a time, each in its own Claude Code session (or back-to-back with `/clear` between). Each prompt is fully self-contained.

#### Step 1 — Literature Review

```text
Run Step 1 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 1.5 — Literature Review Judge

```text
Run Step 1.5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 2 — Builder

```text
Run Step 2 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 2.5 — Judge

```text
Run Step 2.5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 3 — Perturbation

```text
Run Step 3 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 4 — Validator

```text
Run Step 4 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 5 — Refinement

```text
Run Step 5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 6 — Export

```text
Run Step 6 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>.
```

### Option C — FLASH-P GUI *(coming soon)*

An interactive desktop application that lets you build, visualise, save, edit, and merge FLASH-P networks; run AI-driven analyses (validation, perturbations, head-to-head comparisons across many networks at once); and chat with your networks in natural language to ask questions about specific genes, pathways, or experiments. The pipeline can be driven from any frontier or open-source LLM. See [FLASH-P GUI — coming soon](#flash-p-gui--coming-soon) below.

---

## Repository layout

> Only `Flash-P/` is needed to run the pipeline. The other folders are paper outputs and supporting case studies, included so reviewers can browse and cite without re-running anything.

### `Flash-P/` — the pipeline

The 8 agent definitions live in [`Flash-P/Agent/`](Flash-P/Agent), the orchestrator rules and handoff table in [`Flash-P/CLAUDE.md`](Flash-P/CLAUDE.md), and shared validation/structure-check utilities in `Flash-P/shared/`. **This is the folder Claude Code must be opened in.**

### `Outcome/` — paper outputs from our own runs

| Subfolder | What it holds |
|---|---|
| [`Arabidopsis/`](Outcome/Arabidopsis) | The six per-phenotype Arabidopsis networks (network JSON, Cytoscape export, validation, refinement history). |
| [`ArabMerged/`](Outcome/ArabMerged) | The merged six-trait Arabidopsis network exposing all six phenotype outputs simultaneously. |
| [`OtherSpecies/`](Outcome/OtherSpecies) | The six other-species networks (*E. coli*, maize, poplar, rice, sorghum, wheat). |
| [`FLASH-P_VS_KG/`](Outcome/FLASH-P_VS_KG) | Head-to-head comparison: FLASH-P vs networks rebuilt from a cleaned knowledge-base baseline, validated on the same test set. |
| [`Networks/`](Outcome/Networks) | All 13 FLASH-P networks **plus** 7 KG-Cleaned networks repackaged as `.graphml` for one-click Cytoscape import, with the manuscript's `Style_Cytoscape.xml` style file and a [dedicated README](Outcome/Networks/README.md). |
| [`Extra_Analysis/`](Outcome/Extra_Analysis) | Supporting case studies for the manuscript: BRI1 cascade subgraph and the MAX2 KO Figure 2A propagation trace. |
| [`Local_FlashP_Outcome/`](Outcome/Local_FlashP_Outcome) | **Local open-source-model reproduction.** The shoot-branching network rebuilt with a local LLM (Qwen3 via [Ollama](https://ollama.com/)) instead of Claude — same agent prompts, same handoff schema, fully local stack. |

#### `Outcome/Extra_Analysis/` — supporting case studies for the paper

- [`BRI1/`](Outcome/Extra_Analysis/BRI1) — BRI1 cascade subgraph extracted from the merged Arabidopsis network, plus the comparison metrics underlying [Supplementary Data 6](Supplementary%20Data/Supplementary%20Data%206.xlsx).
- [`max2KO/`](Outcome/Extra_Analysis/max2KO) — Figure 2A propagation: MAX2-knockout iteration trace through the Arabidopsis Shoot Branching network. Has its own [README](Outcome/Extra_Analysis/max2KO/README.md) describing how to regenerate every artefact.

#### `Outcome/Local_FlashP_Outcome/` — local open-source-model run

A reproduction of the shoot-branching network using a **local open-source LLM** (Qwen3 served through [Ollama](https://ollama.com/)) instead of Claude. The same agent prompts and handoff schema drive the run; the only thing that changes is the model behind them. This folder ships the network, validation, refinement history, and the build / reconcile / refine scripts so reviewers can see — and re-run — FLASH-P end-to-end against a fully local stack. It's a concrete demonstration of the model-agnostic claim and a preview of what the upcoming GUI will let users do with any model of their choice.

### `Supplementary Data/` — supplementary tables

Seven `.xlsx` files (`Supplementary Data 1.xlsx` … `Supplementary Data 7.xlsx`), each with a README sheet and a Combined_Data sheet, plus the Python build script and a `Supplementary_Data_N_description.md` per dataset (short / medium / long title-and-description options for the SI document).

---

## Visualise the networks in Cytoscape

Every network in [`Outcome/Networks/`](Outcome/Networks) is shipped as a `.graphml` — drop any one of them onto Cytoscape, then import [`Outcome/Networks/Style_Cytoscape.xml`](Outcome/Networks/Style_Cytoscape.xml) (style name: **FLASH-P**) to render it with the published palette and arrowheads. Full step-by-step recipe in [`Outcome/Networks/README.md`](Outcome/Networks/README.md).

---

## FLASH-P GUI — coming soon

<p align="center">
  <img src="Images/FLASH_P_GUI.png" alt="FLASH-P GUI preview — interactive network explorer" width="100%" />
</p>

A desktop GUI is in development that turns FLASH-P into an interactive workbench: build new networks, browse and edit existing ones, save and version them locally, merge several networks into a unified graph, run AI-driven analyses (validation, perturbations, head-to-head comparisons across many networks at once), and chat with your networks in natural language to ask questions about specific genes, pathways, or experiments.

The single most important thing the GUI adds is **freedom to choose any LLM**. This repository's manuscript run used Claude Code with Opus 4.7 because that's what we benchmarked on, but the agents are model-agnostic: the GUI lets users plug in any frontier provider — **OpenAI** (GPT / Codex), **Google Gemini**, **Moonshot Kimi**, **DeepSeek**, **Qwen** — or any local / open-source model exposed through provider-agnostic agent frameworks such as [OpenCode](https://github.com/opencode-ai/opencode), [Goose](https://github.com/block/goose), or [Aider](https://github.com/Aider-AI/aider). One pipeline, every model.

**Stay tuned at <https://flash-p.com/>.** The GUI will live in a separate repository at `https://github.com/CMits/FlashP-GUI` to keep its release cycle and dependencies independent of the pipeline source. **Status: not yet released — watch this repository's releases (and the website above) for the announcement.**

---

## Creators

**Christos Mitsanis** &middot; **David Kainer**
*The University of Queensland*

---

## Contact

For questions, collaborations, or issues:

- **Christos Mitsanis** — [c.mitsanis@uq.edu.au](mailto:c.mitsanis@uq.edu.au)
- **David Kainer** — [d.kainer@uq.edu.au](mailto:d.kainer@uq.edu.au)

Or open a [GitHub issue](https://github.com/CMits/FlashP/issues) on this repository.
