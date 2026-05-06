# PropagationFigure — Figure 2A regeneration

Source artifacts for the paper Figure 2A: how a MAX2 knockout propagates
through the **current** Arabidopsis shoot branching network
(`Arabidopsis/Shoot_Branching_network/`, 38 nodes / 75 edges, iteration 4
refinement 1, 76% acc, κ=0.62, FRS=7.86).

The mutant is **MAX2 KO** (test_id **T005**). Predicted: increased branching;
expected: increased; CORRECT (run = 17.378, dump = 17.378).

---

## Subgraph shown in the figure (13 nodes, 18 edges)

```
Strigolactone ─(+)→ D14 ─(−)→ SMXL678 ─(−)→ BRC1 ─(+)→ HB21 ─(+)→ NCED3 ─(+)→ ABA ─(−)→ Shoot_Branching
                                              │              ├─(−)→ PIN3 ──────(+)──────→ Shoot_Branching
                                              │              └─(−)→ Shoot_Branching (direct)
                                              ├─(−)→ SPL9 (also activates BRC1)
                                              └─(+)→ PIN1 ──(+)→ Shoot_Branching
                            MAX2 ─(−)→ SMXL678
                            MAX2 ─(−)→ BES1   (also inhibits BRC1)
                            D14  ─(−)→ D14    (self-degradation after SL binding)
```

**Diff vs the old `Network_Figure_old/` 12-node module:** the new refined
network drops `BRC2`, `HB40`, `HB53`, `FT` (no longer downstream of BRC1) and
adds `SPL9`, `PIN1`, `PIN3` to the propagation spine. The post-BRC1 ABA branch
is now a clean linear chain `BRC1 → HB21 → NCED3 → ABA`.

---

## How to re-run

```bash
cd PropagationFigure
python propagate_max2_ko.py     # data/max2_ko_iteration_trace.csv + max2_ko_steady_state.json
python extract_subgraph.py      # cytoscape/* + data/subgraph_edges.csv
python plot_iteration_traces.py # figures/iteration_traces.{png,svg}
python build_equations_docx.py  # docs/MAX2_equations_and_values.docx
```

All scripts are self-contained and read from
`Arabidopsis/Shoot_Branching_network/`. To regenerate against a future
refinement of the network, just re-run — no edits needed.

To swap the mutant or the network, edit the `PERTURBATION`, `TEST_ID`,
`NET_DIR` constants at the top of each script.

---

## Layout

```
PropagationFigure/
├── README.md                       # this file
├── color_palette.py                # Okabe-Ito (copied from Network_Figure_old)
├── propagate_max2_ko.py            # Jacobi+damping propagator
├── extract_subgraph.py             # 13-node subgraph + Cytoscape exports
├── plot_iteration_traces.py        # iteration-trace line plot
├── build_equations_docx.py         # Word doc generator
├── data/
│   ├── max2_ko_iteration_trace.csv # iteration, max_abs_delta, [38 nodes]
│   ├── max2_ko_steady_state.json   # WT + KO + cross-check vs validator dump
│   └── subgraph_edges.csv          # source, target, sign, edge_id
├── cytoscape/
│   ├── subgraph.graphml            # Cytoscape native — open this
│   ├── subgraph.sif                # simple interaction format
│   ├── node_attributes.tsv         # id, type, role, WT_value, KO_value, log2fc
│   └── edge_attributes.tsv         # source, interaction, target, sign, edge_id
├── figures/
│   ├── iteration_traces.png        # the convergence plot
│   ├── iteration_traces.svg        # vector version for editing
│   └── (drop Cytoscape PNGs here after manual rendering)
└── docs/
    └── MAX2_equations_and_values.docx  # equations + WT/KO table (polish manually)
```

---

## Cytoscape rendering recipe (manual, after import)

The subgraph is wired to the **FLASH-P** vizmap (`PropagationFigure/styles (2).xml`).
Node `type` (HORMONE / GENE / PHENOTYPE) drives fill, shape, size, border;
edge `sign` (`"positive"` / `"negative"`) drives stroke colour and arrowhead
(DELTA = activation, T = inhibition); node `label` is the passthrough used
for visible labels. SMXL678 is a `PROTEIN_COMPLEX` in the source network but
is exported with `type=GENE` so the FLASH-P style applies (its raw type is
preserved in the `raw_type` column). Workflow:

1. **File → Import → Styles from File** → `PropagationFigure/styles (2).xml`
   (only needed once per Cytoscape session).
2. **File → Import → Network from File** → `cytoscape/subgraph.graphml`.
   All node and edge attributes (`label`, `type`, `sign`, `WT_value`,
   `KO_value`, `log2fc`, `role`, …) are loaded automatically.
3. **Control Panel → Style** → select the **FLASH-P** style. Nodes and edges
   immediately pick up FLASH-P fills, shapes, and arrowheads.
4. To make node size encode the perturbation magnitude (the panel-b feature),
   override **NODE_SIZE** with a continuous mapping on `KO_value`
   (e.g. sqrt scale, 30 → 100 px). For the WT panel, swap to `WT_value` —
   all nodes become uniform.
5. (Optional) override **NODE_BORDER_PAINT** with a discrete mapping on
   `role` to highlight `perturbed_gene` / `phenotype`.
6. **File → Export → Network to Image** → PNG (transparent), drop into
   `figures/` for the final composite.

---

## Provenance

- Generated against `Arabidopsis/Shoot_Branching_network/` (created
  2026-04-18, iteration 4, refinement_iteration 1).
- Algebraic dump: `validation/steady_state_dump.json`, ODE dump:
  `validation/ode_steady_state_dump.json`. Both contain T005 = MAX2 KO.
- Old template: `Network_Figure_old/shoot_branching_max2_downstream_network/`
  (now superseded — built against the obsolete 12-node module).
