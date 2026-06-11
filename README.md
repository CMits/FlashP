<p align="center">
  <img src="Images/FlashP.png" alt="FLASH-P" width="100%" />
</p>

<h1 align="center">FLASH-P</h1>

<p align="center">
  <em>A multi-agent system that turns primary literature into validated, perturbation-testable causal networks &mdash; for any trait, in any species.</em>
</p>

<p align="center">
  <a href="#what-is-flash-p">What is FLASH-P</a> &nbsp;&middot;&nbsp;
  <a href="#pick-your-coding-agent">Pick a coding agent</a> &nbsp;&middot;&nbsp;
  <a href="#run-the-flash-p-pipeline">Run</a> &nbsp;&middot;&nbsp;
  <a href="#repository-layout">Layout</a> &nbsp;&middot;&nbsp;
  <a href="#flash-p-gui--coming-soon">GUI</a>
</p>

---

## What is FLASH-P?

FLASH-P is a **multi-agent system** that reads primary scientific literature directly from the web and turns it into a validated, perturbation-testable causal signalling network for any (trait, species) pair. Eight specialised agents pass a strict sequence of handoff files between each other &mdash; *literature reviewer → literature judge → builder → network judge → perturbation reconciler → validator → refiner → exporter* &mdash; and the two half-step audit gates (Step 1.5 and Step 2.5) review the previous stage's output before downstream agents are allowed to consume it. Every edge in the resulting network carries a DOI and an evidence sentence; every node is wired into closed-form algebraic, Hill-function ODE, and signed Random-Walk-with-Restart prediction equations so that the network is both human-readable and numerically simulable; and every perturbation experiment in the test set is scored under all three methods.

For the manuscript run packaged in this repository, FLASH-P was originally built and benchmarked inside [Claude Code](https://www.claude.com/product/claude-code) using the **Claude Opus 4.7** model. The agents themselves, however, are just plain-text prompts plus structured handoff files &mdash; nothing in them is specific to one model or one tool. **The exact same pipeline runs inside any coding agent that reads an `AGENTS.md` or `CLAUDE.md` file** &mdash; we ship ready-to-go folders for Claude Code, Codex CLI, and OpenCode (which also covers Aider, Goose, and any other AGENTS.md-aware tool). Pick whichever you already use; the prompts are identical.

The pipeline has already been used to build **13 networks** packaged in this repository: 6 per-phenotype Arabidopsis networks (flowering time, hypocotyl length, lateral root density, plant height, seed size, shoot branching), 1 merged six-trait Arabidopsis network exposing all six phenotype outputs simultaneously, and 6 other-species networks (*E. coli* lycopene, maize kernel-row number, poplar lignin S/G ratio, rice tillering, sorghum flowering time, wheat plant height). On a head-to-head benchmark against networks rebuilt from a cleaned PlantConnectome knowledge-base baseline using the same validation pipeline, FLASH-P networks reach substantially higher direction-call accuracy at a fraction of the size &mdash; see [`Outcome/FLASH-P_VS_KG/`](Outcome/FLASH-P_VS_KG) and [Supplementary Data 6](Supplementary%20Data/Supplementary%20Data%206.xlsx).

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
| [`Flash-P/`](Flash-P) | **The pipeline.** Three ready-to-go subfolders &mdash; one per coding agent &mdash; each carrying the 8 agent definitions, the orchestrator instructions, and shared utilities. Open whichever subfolder matches the tool you use (see [Pick a coding agent](#pick-your-coding-agent)). |
| [`Flash-P_Light/`](Flash-P_Light) | **Token-lean pipeline** for a single Claude Pro (or lower-tier) session &mdash; same science, DOI-only output. See [Which version?](#which-version) |
| [`Outcome/`](Outcome) | All paper outputs from our own runs &mdash; every network, validation result, refinement history, Cytoscape export, head-to-head KG-Cleaned comparison, supporting case studies, and the local open-source-model reproduction. |
| [`Supplementary Data/`](Supplementary%20Data) | Seven supplementary `.xlsx` tables, their build scripts, and per-dataset descriptions. |
| [`Images/`](Images) | Repository figures: `FlashP.png` (banner), `FLASHP_Pipeline_Addition.svg` (pipeline diagram), `FLASH_P_GUI.png` (GUI preview). |

---

## Which version?

- **Have Claude Max?** Run the full **[`Flash-P/`](Flash-P)** &mdash; every edge carries full provenance (DOI + title, authors, journal, evidence sentence) and the judges run multiple passes. Maximum transparency.
- **On Claude Pro or a lower tier** (same idea for the lower ChatGPT/Codex tiers)? Run **[`Flash-P_Light/`](Flash-P_Light)** &mdash; token-lean, fits one session: DOI-only output, single-pass judges. Same validation results.

**We suggest starting with Light.** Its quality is on par with the full Max run, so it's the fastest, cheapest way to build a real network and get a feel for the output &mdash; then move up to the full `Flash-P/` when you want the complete provenance record.

### Run Flash-P Light

**Claude Code** &mdash; open `Flash-P_Light/Claude/`, then run:

```text
/run-flashp <phenotype> in <species>
```

For example `/run-flashp Shoot Branching in Arabidopsis`. It runs Steps 1&rarr;6 autonomously.

**Codex / OpenCode / Aider / Goose** &mdash; open the matching `Flash-P_Light/` subfolder and paste:

> Run the full FLASH-P Light pipeline for `<phenotype>` in `<species>`. Single agent &mdash; no subagents, no WebFetch. Knowledge-first draft, then WebSearch to verify each edge/test and take the DOI from the result.

---

## Pick your coding agent

FLASH-P works inside any coding agent that reads an `AGENTS.md` or `CLAUDE.md` file. We ship one ready-to-go subfolder per agent. Install the tool you prefer, open the matching subfolder, and skip to [Run the FLASH-P pipeline](#run-the-flash-p-pipeline) &mdash; the prompts in the next section are the same no matter which agent you picked.

### Option 1 &mdash; Claude Code *(what the paper used)*

Install Claude Code:

```bash
npm install -g @anthropic-ai/claude-code
```

Or grab the desktop app for macOS or Windows from <https://www.claude.com/product/claude-code>. You will also need a Claude.ai account (login the first time you start `claude`).

Then clone the repo and open the **`Flash-P/Claude/`** subfolder:

```bash
git clone https://github.com/CMits/FlashP.git
cd FlashP/Flash-P/Claude
claude
```

The desktop app: *File → Open Project → pick `Flash-P/Claude/`*.

### Option 2 &mdash; Codex CLI

Install OpenAI's Codex CLI:

```bash
npm install -g @openai/codex
```

Full install and login instructions: <https://github.com/openai/codex>.

Then open the **`Flash-P/Codex/`** subfolder:

```bash
cd FlashP/Flash-P/Codex
codex
```

### Option 3 &mdash; OpenCode (or Aider / Goose / any AGENTS.md-aware agent)

Install the agent of your choice &mdash; [OpenCode](https://github.com/opencode-ai/opencode), [Aider](https://github.com/Aider-AI/aider), [Goose](https://github.com/block/goose), or anything else that reads an `AGENTS.md` file &mdash; per its own docs.

Then open the **`Flash-P/OpenCode_Aider_Any_Other/`** subfolder:

```bash
cd FlashP/Flash-P/OpenCode_Aider_Any_Other
# then start your agent of choice in this directory
```

> **Why open the subfolder, not the repo root?** The pipeline reads its orchestrator file (`CLAUDE.md` or `AGENTS.md`) and the `Agent/*.md` definitions as relative paths. Opening the matching subfolder is what makes the agent see them. The other top-level folders (`Outcome/`, `Supplementary Data/`) are paper outputs and should stay outside the agent's working context.

---

## Run the FLASH-P pipeline

Once you have a coding agent open in the right subfolder, paste one of the prompts below. **All three options work the same way in Claude Code, Codex CLI, and OpenCode** &mdash; the prompts are identical. Replace `<TRAIT>` and `<SPECIES>` (for example `Shoot Branching` and `Arabidopsis thaliana`) before pasting.

- **Option A &mdash; One-shot prompt** is fastest. Best for small or well-curated traits.
- **Option B &mdash; Step-by-step** is recommended when the trait has a large literature base. Each step starts with a fresh-ish context window so the pipeline stays meticulous, and the half-step judge gates (1.5, 2.5) get a chance to audit before the next agent picks up the output.
- **Option C &mdash; FLASH-P GUI** *(coming soon)*. An interactive desktop app: build, browse, save, and merge FLASH-P networks; run AI-driven analyses across many networks at once; and chat with your networks in natural language &mdash; all driven by the model and provider of your choice. See [FLASH-P GUI &mdash; coming soon](#flash-p-gui--coming-soon).

### Option A &mdash; One-shot prompt

```text
Run the full FLASH-P pipeline for the trait <TRAIT> in <SPECIES>.
```

### Option B &mdash; Step-by-step prompts

Run these one at a time, each in its own agent session (or back-to-back with `/clear` between). Each prompt is fully self-contained.

#### Step 1 &mdash; Literature Review

```text
Run Step 1 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 1.5 &mdash; Literature Review Judge

```text
Run Step 1.5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 2 &mdash; Builder

```text
Run Step 2 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 2.5 &mdash; Judge

```text
Run Step 2.5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 3 &mdash; Perturbation

```text
Run Step 3 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 4 &mdash; Validator

```text
Run Step 4 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 5 &mdash; Refinement

```text
Run Step 5 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>. Do not start the next step.
```

#### Step 6 &mdash; Export

```text
Run Step 6 of the FLASH-P pipeline for trait <TRAIT> in <SPECIES>.
```

### Option C &mdash; FLASH-P GUI *(coming soon)*

An interactive desktop application that lets you build, visualise, save, edit, and merge FLASH-P networks; run AI-driven analyses (validation, perturbations, head-to-head comparisons across many networks at once); and chat with your networks in natural language to ask questions about specific genes, pathways, or experiments. The pipeline can be driven from any frontier or open-source LLM. See [FLASH-P GUI &mdash; coming soon](#flash-p-gui--coming-soon) below.

---

## Repository layout

> Only `Flash-P/` is needed to run the pipeline. The other folders are paper outputs and supporting case studies, included so reviewers can browse and cite without re-running anything.

### `Flash-P/` &mdash; the pipeline

The pipeline ships in three sibling subfolders, one per coding agent. Each subfolder is self-contained: it has its own orchestrator file (`CLAUDE.md` for Claude Code, `AGENTS.md` for Codex CLI and OpenCode), the same eight `Agent/*.md` agent definitions, and the same shared validation and structure-check utilities in `Agent/shared/`.

| Subfolder | Open this in &hellip; |
|---|---|
| [`Flash-P/Claude/`](Flash-P/Claude) | Claude Code (the tool the paper used). |
| [`Flash-P/Codex/`](Flash-P/Codex) | OpenAI's Codex CLI. |
| [`Flash-P/OpenCode_Aider_Any_Other/`](Flash-P/OpenCode_Aider_Any_Other) | OpenCode, Aider, Goose, or any other coding agent that reads `AGENTS.md`. |

The three subfolders share the same prompts and the same handoff schema, so a network built with one agent is fully interchangeable with one built using another.

### `Outcome/` &mdash; paper outputs from our own runs

| Subfolder | What it holds |
|---|---|
| [`Arabidopsis/`](Outcome/Arabidopsis) | The six per-phenotype Arabidopsis networks (network JSON, Cytoscape export, validation, refinement history). |
| [`ArabMerged/`](Outcome/ArabMerged) | The merged six-trait Arabidopsis network exposing all six phenotype outputs simultaneously. |
| [`OtherSpecies/`](Outcome/OtherSpecies) | The six other-species networks (*E. coli*, maize, poplar, rice, sorghum, wheat). |
| [`FLASH-P_VS_KG/`](Outcome/FLASH-P_VS_KG) | Head-to-head comparison: FLASH-P vs networks rebuilt from a cleaned knowledge-base baseline, validated on the same test set. |
| [`Networks/`](Outcome/Networks) | All 13 FLASH-P networks **plus** 7 KG-Cleaned networks repackaged as `.graphml` for one-click Cytoscape import, with the manuscript's `Style_Cytoscape.xml` style file and a [dedicated README](Outcome/Networks/README.md). |
| [`Extra_Analysis/`](Outcome/Extra_Analysis) | Supporting case studies for the manuscript: BRI1 cascade subgraph and the MAX2 KO Figure 2A propagation trace. |
| [`Local_FlashP_Outcome/`](Outcome/Local_FlashP_Outcome) | **Local open-source-model reproduction.** The shoot-branching network rebuilt with a local LLM (Qwen3 via [Ollama](https://ollama.com/)) instead of Claude &mdash; same agent prompts, same handoff schema, fully local stack. |

#### `Outcome/Extra_Analysis/` &mdash; supporting case studies for the paper

- [`BRI1/`](Outcome/Extra_Analysis/BRI1) &mdash; BRI1 cascade subgraph extracted from the merged Arabidopsis network, plus the comparison metrics underlying [Supplementary Data 6](Supplementary%20Data/Supplementary%20Data%206.xlsx).
- [`max2KO/`](Outcome/Extra_Analysis/max2KO) &mdash; Figure 2A propagation: MAX2-knockout iteration trace through the Arabidopsis Shoot Branching network. Has its own [README](Outcome/Extra_Analysis/max2KO/README.md) describing how to regenerate every artefact.

#### `Outcome/Local_FlashP_Outcome/` &mdash; local open-source-model run

A reproduction of the shoot-branching network using a **local open-source LLM** (Qwen3 served through [Ollama](https://ollama.com/)) instead of Claude. The same agent prompts and handoff schema drive the run; the only thing that changes is the model behind them. This folder ships the network, validation, refinement history, and the build / reconcile / refine scripts so reviewers can see &mdash; and re-run &mdash; FLASH-P end-to-end against a fully local stack. It's a concrete demonstration of the model-agnostic claim and a preview of what the upcoming GUI will let users do with any model of their choice.

### `Supplementary Data/` &mdash; supplementary tables

Seven `.xlsx` files (`Supplementary Data 1.xlsx` &hellip; `Supplementary Data 7.xlsx`), each with a README sheet and a Combined_Data sheet, plus the Python build script and a `Supplementary_Data_N_description.md` per dataset (short / medium / long title-and-description options for the SI document).

---

## Visualise the networks in Cytoscape

Every network in [`Outcome/Networks/`](Outcome/Networks) is shipped as a `.graphml` &mdash; drop any one of them onto Cytoscape, then import [`Outcome/Networks/Style_Cytoscape.xml`](Outcome/Networks/Style_Cytoscape.xml) (style name: **FLASH-P**) to render it with the published palette and arrowheads. Full step-by-step recipe in [`Outcome/Networks/README.md`](Outcome/Networks/README.md).

---

## FLASH-P GUI &mdash; coming soon

<p align="center">
  <img src="Images/FLASH_P_GUI.png" alt="FLASH-P GUI preview — interactive network explorer" width="100%" />
</p>

A desktop GUI is in development that turns FLASH-P into an interactive workbench: build new networks, browse and edit existing ones, save and version them locally, merge several networks into a unified graph, run AI-driven analyses (validation, perturbations, head-to-head comparisons across many networks at once), and chat with your networks in natural language to ask questions about specific genes, pathways, or experiments.

The repository today already lets users run FLASH-P through Claude Code, Codex CLI, OpenCode, Aider, Goose, or any other AGENTS.md-aware coding agent &mdash; one pipeline, every tool. What the GUI adds on top of that is **a no-install, point-and-click experience and a broader provider menu**: a built-in model picker for **OpenAI** (GPT / Codex), **Anthropic Claude**, **Google Gemini**, **Moonshot Kimi**, **DeepSeek**, **Qwen**, and any local or self-hosted model. No terminal, no prompt copy-pasting &mdash; just pick a trait, a species, and a model, and watch the pipeline run.

**Stay tuned at <https://flash-p.com/>.** The GUI will live in a separate repository at `https://github.com/CMits/FlashP-GUI` to keep its release cycle and dependencies independent of the pipeline source. **Status: not yet released &mdash; watch this repository's releases (and the website above) for the announcement.**

---

## Creators

**Christos Mitsanis** &middot; **David Kainer**
*The University of Queensland*

---

## Contact

For questions, collaborations, or issues:

- **Christos Mitsanis** &mdash; [c.mitsanis@uq.edu.au](mailto:c.mitsanis@uq.edu.au)
- **David Kainer** &mdash; [d.kainer@uq.edu.au](mailto:d.kainer@uq.edu.au)

Or open a [GitHub issue](https://github.com/CMits/FlashP/issues) on this repository.

---

## License

FLASH-P is © 2026 **The University of Queensland** and is released under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)](LICENSE).

You are free to share and adapt FLASH-P for any **non-commercial purpose**, provided you:

- give appropriate credit to the creators (**Christos Mitsanis** and **David Kainer**) and **The University of Queensland** (**Attribution**), and
- license any derivative works under these same terms (**ShareAlike**).

See the [full licence text](LICENSE) or <https://creativecommons.org/licenses/by-nc-sa/4.0/> for details.

If you use FLASH-P in academic work, please cite:
> _Citation coming soon &mdash; bioRxiv preprint to be added._
