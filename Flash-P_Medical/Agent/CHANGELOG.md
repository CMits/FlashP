# Changelog — FLASH-M (Medical edition)

## [light-medical-1.0] — Light fork

Forked the medical edition to the **Light** token-lean form (mirroring plant FLASH-P Light), while
**preserving all medical-specific biology** (the `DRUG` node type, drug-response perturbations,
resistance-mutation handling, and the Perception-Gate / RTK-RAS-MAPK / PI3K-AKT-mTOR reference content).

### Token-lean changes (vs FLASH-M v2.0)
- **Short keys + short enum values** across all data files; `doi` (`d`) is the only paper field —
  `title`/`authors`/`year`/`journal`/`evidence_sentence` dropped. Full legend in `shared/LEXICON.md`
  (incl. `DRUG`→`D` and medical drug-response `pt` short codes).
- **Schemas** ported to slim `populate_by_name` form (`shared/schemas/`), emitting short aliases via
  `model_dump(by_alias=True)`. `DRUG` `NodeType` and the medical `PerturbationType` vocabulary retained.
  Removed `merged.py`, `candidate_papers`/`pleiotropic`/`merge_log` schemas.
- **Heavy reference relocated** from `CLAUDE.md` into `shared/PIPELINE_REFERENCE.md` (equation math,
  medical traps, node naming, FRS/DARS, file tree, QA architecture) so the per-turn prefix stays lean.
- **Step 1 LITERATURE REVIEW** is now a single main-thread agent: knowledge-first → WebSearch verify
  (DOI from the search hit). No subagents, no WebFetch, **no `candidate_papers.json`**.
- **Judges run ONE pass** (Step 1.5 and Step 2.5); BUILDER applies suggestions once (no judge loop).
- **REFINEMENT capped at 2 iterations** with diagnose-before-fixing.
- Removed unused shared scripts: `export_json_schemas.py`, `json_schemas/`, `literature_retriever.py`,
  `migrate_v1_to_v2.py`, stray `validation/`.
- Added Light I/O (`light_io.py`, `toon_codec.py`, `compact.py`), the non-blocking write-time schema
  hook (`hook_validate_on_write.py`), and a `.claude/` orchestration folder (7 `flashp-*` subagents,
  `run-flashp` command, `settings.json` pinning sonnet + autocompact + schema hook).

### Preserved domain logic
- `check_network_structure.py` keeps the `DRUG` node-name rule; `network_to_cytoscape.py` keeps the
  `DRUG` color. The corpus exporters keep medical auto-discovery defaults.
