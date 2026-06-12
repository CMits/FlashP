---
description: Autonomously run the full FLASH-M Light (Medical) pipeline (Steps 1→6) for a readout — hands-off and token-lean.
argument-hint: <readout> in <system>  e.g. "Cell Proliferation in EGFR-driven NSCLC"
model: opus
---

# Autonomous FLASH-M Light run

Target readout: **$ARGUMENTS**

You are the pipeline **orchestrator**. Run the ENTIRE pipeline (Steps 1 → 6) to completion in one
go, **fully autonomously**. The user has started this run and walked away — they expect to return to a
finished, schema-valid network. Do **not** stop to ask questions. If a step hits a blocking error,
follow `CLAUDE.md` → *Error Handling* (save partial results, document, then continue or stop), and
report it at the end — never hang waiting for input.

Follow the **Pipeline Handoff Table** and **Rules per step** in `CLAUDE.md` exactly. The pipeline is
file-driven: each step reads the previous step's files from disk, so you never need to keep prior
chat history in context.

## Execution plan

1. **Step 1 — LITERATURE REVIEW — run in THIS (main) thread.** Single agent, no subagents, no WebFetch.
   Read `Agent/LITERATURE_REVIEW_AGENT.md`, then go knowledge-first and verify each edge/test with
   **WebSearch** (DOI taken from the search hit). Write `data/curated_edges.json` +
   `data/perturbation_dataset.json`. **Token hygiene:** batch independent WebSearches in one turn; do
   NOT paste full search results into the reply — extract the DOI and move on.

2. **Steps 1.5 → 6 — dispatch the matching `flashp-*` subagent, one at a time, in strict order.**
   Each subagent has its own model pinned and its own isolated context, so its big reads never enter
   this thread. Pass it only the phenotype/species and the project root (`.`); it reads its inputs
   from disk. Wait for each to finish and return its slim summary before starting the next.

   | After Step 1 | `flashp-literature-judge` (1.5) → `flashp-builder` (2) → `flashp-judge` (2.5) → `flashp-perturbation` (3) → `flashp-validator` (4) → `flashp-refinement` (5) → `flashp-export` (6) |

3. **Final report.** When Step 6 finishes, run
   `python Agent/shared/validate_schema.py --network . --quiet` and report: best method + accuracy +
   Cohen's κ, node/edge/test counts, FRS/DARS, any failures, and the list of generated artifact dirs.

## Token discipline (keep cache writes minimal — this is the whole point of the autonomous run)

- **Lean prefix, untouched.** Do NOT edit `CLAUDE.md`, `.claude/settings.json`, or any `Agent/*.md` /
  `.claude/agents/*.md` file during the run, and do NOT add/remove MCP servers or switch the main
  model mid-run — each invalidates the entire cached prefix and forces a full re-write.
- **Let autocompact work.** `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=55` sheds context automatically between
  steps — hands-off. Do not request manual compaction unless a step is about to overflow.
- **Targeted reads only.** Prefer `Grep` over `Read`; use `Read` `offset`/`limit` on big files; never
  re-read a file already in context. Pipe script stdout through `tail`/`grep` and read only summary
  JSON fields — never dump full validators output into the thread.
- **Subagents do the heavy lifting.** Everything except Step 1 runs in a subagent, so this main
  thread stays small and its per-turn cache-write delta stays tiny.

## Held-out integrity (do not break)

Steps 1.5, 2, and 2.5 must **never** see perturbation test outcomes or `validation/` / `refinement/`
results. The repository is audited, the network is built, and the network is biologically reviewed —
all from literature only. Perturbation-driven changes belong to REFINEMENT (Step 5).

Begin with Step 1 now.
