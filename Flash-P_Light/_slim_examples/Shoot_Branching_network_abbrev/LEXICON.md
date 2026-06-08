# FLASH-P Light — Abbreviation Lexicon

All Light JSON files use short keys/values. Expand with this legend (also the source of truth
for schemas + agent prompts). `metadata` and `parameters` blocks keep readable names.

## Field keys
| full | short |
|---|---|
| `test_id` | `id` |
| `gene` | `g` |
| `perturbation_type` | `pt` |
| `expected_direction` | `ed` |
| `predicted_direction` | `pd` |
| `network_gene` | `ng` |
| `gene_modifiers` | `m` |
| `exogenous_supply` | `exo` |
| `comparison_baseline` | `cb` |
| `comparison_baseline_value` | `cbv` |
| `reconciliation_type` | `rt` |
| `edge_id` | `eid` |
| `source` | `s` |
| `target` | `t` |
| `sign` | `x` |
| `doi` | `d` |
| `full_name` | `fn` |
| `is_source` | `src` |
| `type` | `ty` |
| `species` | `sp` |
| `perturbations` | `P` |
| `node` | `n` |
| `activators` | `a` |
| `inhibitors` | `inh` |
| `formula` | `f` |
| `gene_modifier` | `gmod` |
| `wt_value` | `wt` |
| `perturbed_value` | `pv` |
| `ratio` | `r` |
| `log2_fold_change` | `lfc` |
| `direction_threshold` | `dt` |
| `correct` | `ok` |
| `phenotype_node` | `pn` |
| `converged` | `cv` |
| `iterations` | `it` |
| `complexity_score` | `cs` |
| `complexity_label` | `cl` |
| `path_length` | `pl` |
| `path` | `pth` |
| `evidence_doi` | `vd` |
| `exogenous_node` | `exn` |
| `exogenous_value` | `exv` |
| `description` | `desc` |
| `effect` | `ef` |
| `mechanism` | `mech` |

## perturbation_type (`pt`)
| `knockout` | `ko` |
| `knockdown` | `kd` |
| `overexpression` | `oe` |
| `double_knockout` | `dko` |
| `triple_knockout` | `tko` |
| `quadruple_knockout` | `qko` |
| `quintuple_knockout` | `pko` |
| `gain_of_function` | `gof` |
| `loss_of_function` | `lof` |
| `rescue` | `rsc` |
| `rescue_experiment` | `rsc` |
| `treatment` | `trt` |
| `exogenous_treatment` | `trt` |
| `double_mutant` | `dm` |
| `combined` | `cmb` |
| `epistasis` | `ep` |
## expected_direction / predicted_direction (`ed`/`pd`)
| `increased` | `up` |
| `decreased` | `dn` |
| `unchanged` | `nc` |
## reconciliation_type (`rt`)
| `exact_match` | `em` |
| `case_insensitive` | `ci` |
| `family_member` | `fm` |
| `composite_collapse` | `cc` |
| `composite_member` | `cm` |
| `treatment_analog` | `ta` |
| `mechanism_mapping` | `mm` |
| `not_in_network` | `nin` |
| `control` | `ctl` |
## node type (`ty`)
| `GENE` | `G` |
| `HORMONE` | `H` |
| `METABOLITE` | `M` |
| `ENVIRONMENT` | `E` |
| `PROTEIN_COMPLEX` | `PC` |
| `REGULATORY_RNA` | `R` |
| `PHENOTYPE` | `P` |
| `PROCESS` | `PR` |
## complexity_label (`cl`)
| `easy` | `e` |
| `medium` | `m` |
| `hard` | `h` |
