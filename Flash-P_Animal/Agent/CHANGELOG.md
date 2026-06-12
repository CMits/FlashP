# Changelog — FLASH-P (Animal / Cattle edition)

## [light-animal-1.0] — Light fork

Forked the cattle edition to the **Light** token-lean form (mirroring plant FLASH-P Light), while
**preserving all cattle-specific biology** (somatotropic GH-IGF1 axis, double-muscling MSTN, breed/QTL
hubs HMGA2/PLAG1/NCAPG-LCORL, pigmentation MC1R/ASIP, and the livestock treatment/perturbation
vocabulary — bST/GH, β-agonists, ACE-031, background epistasis).

### Token-lean changes (vs FLASH-P v2.0 cattle)
- **Short keys + short enum values** across all data files; `doi` (`d`) is the only paper field —
  `title`/`authors`/`year`/`journal`/`evidence_sentence` dropped. Full legend in `shared/LEXICON.md`
  (incl. cattle treatment `pt` short codes).
- **Schemas** ported to slim `populate_by_name` form (`shared/schemas/`), emitting short aliases via
  `model_dump(by_alias=True)`. Standard 8 `NodeType`s (no DRUG); the cattle `PerturbationType`
  vocabulary retained for reference. Removed `merged.py`, `candidate_papers`/`merge_log` schemas.
- **Heavy reference relocated** from `CLAUDE.md` into `shared/PIPELINE_REFERENCE.md` (equation math,
  cattle traps, node naming, FRS/DARS, file tree, QA architecture) so the per-turn prefix stays lean.
- **Step 1 LITERATURE REVIEW** is now a single main-thread agent: knowledge-first → WebSearch verify
  (DOI from the search hit). No subagents, no WebFetch, **no `candidate_papers.json`**.
- **Judges run ONE pass** (Step 1.5 and Step 2.5); BUILDER applies suggestions once (no judge loop).
- **REFINEMENT capped at 2 iterations** with diagnose-before-fixing.
- Removed unused shared scripts: `export_json_schemas.py`, `json_schemas/`, `literature_retriever.py`,
  `migrate_v1_to_v2.py`, stray `validation/`.
- Added Light I/O (`light_io.py`, `toon_codec.py`, `compact.py`), the non-blocking write-time schema
  hook (`hook_validate_on_write.py`), and a `.claude/` orchestration folder (7 `flashp-*` subagents,
  `run-flashp` command, `settings.json` pinning sonnet + autocompact + schema hook).
- Corpus exporters (`export_master_csv.py`, `export_all_csvs.py`) retuned to cattle (autodiscover,
  `Bos taurus` default).
