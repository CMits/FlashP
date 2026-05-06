# Networks — packaged GraphML exports

Self-contained collection of every Arabidopsis and other-species network
referenced in the manuscript, packaged as a `.graphml` per network so reviewers
can import any of them directly into Cytoscape, Gephi, or networkx.

Two families are included:

- **FLASH-P** — networks built by the FLASH-P agent pipeline directly from the
  primary literature (six Arabidopsis per-phenotype networks, the merged
  six-trait Arabidopsis network, and six other-species networks).
- **KG-Cleaned** — the matching Arabidopsis networks (six per-phenotype + one
  merged) rebuilt from the cleaned PlantConnectome knowledge-base baseline.
  Filenames are prefixed `KG_`.

Naming convention: `<Trait>_<Species>.graphml` for FLASH-P networks and
`KG_<Trait>_<Species>.graphml` for KG-Cleaned. Trait is in CamelCase
(`ShootBranching`, `KernelRowNumber`, `LigninSGRatio`, …); the merged
six-trait Arabidopsis network is named `Merged_Arabidopsis.graphml` /
`KG_Merged_Arabidopsis.graphml`.

The original files are untouched; this folder is a copy.

---

## File index

### FLASH-P — Arabidopsis per-phenotype networks

| File                                       | Trait                  | Nodes | Edges |
|--------------------------------------------|------------------------|------:|------:|
| `FloweringTime_Arabidopsis.graphml`        | Flowering Time         |    42 |    87 |
| `HypocotylLength_Arabidopsis.graphml`      | Hypocotyl Length       |    54 |   103 |
| `LateralRootDensity_Arabidopsis.graphml`   | Lateral Root Density   |    55 |    68 |
| `PlantHeight_Arabidopsis.graphml`          | Plant Height           |    78 |    98 |
| `SeedSize_Arabidopsis.graphml`             | Seed Size              |    80 |   134 |
| `ShootBranching_Arabidopsis.graphml`       | Shoot Branching        |    38 |    75 |

### FLASH-P — Arabidopsis merged six-trait network

| File                                       | Trait                  | Nodes | Edges |
|--------------------------------------------|------------------------|------:|------:|
| `Merged_Arabidopsis.graphml`               | All six phenotypes     |   237 |   497 |

### FLASH-P — other species

| File                                       | Trait                  | Nodes | Edges |
|--------------------------------------------|------------------------|------:|------:|
| `KernelRowNumber_Maize.graphml`            | Kernel Row Number      |    50 |    80 |
| `LigninSGRatio_Poplar.graphml`             | Lignin S/G Ratio       |    43 |    95 |
| `PlantHeight_Wheat.graphml`                | Plant Height           |    42 |    51 |
| `Tillering_Rice.graphml`                   | Tillering              |    69 |   100 |
| `Lycopene_Ecoli.graphml`                   | Lycopene yield         |    62 |    92 |
| `FloweringTime_Sorghum.graphml`            | Flowering Time         |    35 |    81 |

### KG-Cleaned — Arabidopsis per-phenotype networks

| File                                          | Trait                  | Nodes | Edges |
|-----------------------------------------------|------------------------|------:|------:|
| `KG_FloweringTime_Arabidopsis.graphml`        | Flowering Time         |   750 |   749 |
| `KG_HypocotylLength_Arabidopsis.graphml`      | Hypocotyl Length       |   917 |  1025 |
| `KG_LateralRootDensity_Arabidopsis.graphml`   | Lateral Root Density   |  1170 |  1170 |
| `KG_PlantHeight_Arabidopsis.graphml`          | Plant Height           |   206 |   205 |
| `KG_SeedSize_Arabidopsis.graphml`             | Seed Size              |   443 |   442 |
| `KG_ShootBranching_Arabidopsis.graphml`       | Shoot Branching        |   108 |   107 |

### KG-Cleaned — Arabidopsis merged six-trait network

| File                                          | Trait                  | Nodes | Edges |
|-----------------------------------------------|------------------------|------:|------:|
| `KG_Merged_Arabidopsis.graphml`               | All six phenotypes     |  3193 |  3698 |

---

## Where each file came from

The FLASH-P graphmls are direct copies of the Cytoscape exports already
written by the FLASH-P pipeline alongside each network's `network.json`. The
KG-Cleaned graphmls did not exist in cytoscape form in the source tree; they
were generated from the corresponding `network.json` using the same
node/edge schema as the FLASH-P exports (node attributes: `type`, `label`,
`color`; edge attributes: `sign` (`positive` / `negative`), `color`, `effect`,
`pmid`).

| File family                 | Source path (untouched)                                                                 |
|-----------------------------|------------------------------------------------------------------------------------------|
| FLASH-P Arabidopsis         | `Outcome/Arabidopsis/<Trait>_network/network/cytoscape/network.graphml`                  |
| FLASH-P Arabidopsis merged  | `Outcome/ArabMerged/network/cytoscape/network.graphml`                                   |
| FLASH-P other species       | `Outcome/OtherSpecies/<Species>_<Trait>_network/network/cytoscape/network.graphml`       |
| KG-Cleaned Arabidopsis      | `Outcome/FLASH-P_VS_KG/KB_Cleaned/<trait>_network/network/network.json`                  |
| KG-Cleaned merged           | `Outcome/FLASH-P_VS_KG/KB_Cleaned/merged_arabidopsis_network/network/network.json`       |

---

## Schema (all files)

All files share the same minimal GraphML schema:

**Node attributes**
- `type` — one of `GENE`, `HORMONE`, `METABOLITE`, `ENVIRONMENT`, `PHENOTYPE`,
  `REGULATORY_RNA`, `PROTEIN_COMPLEX`.
- `label` — display name (defaults to the node id).
- `color` — Okabe-Ito-friendly hex fill keyed off `type`.

**Edge attributes**
- `sign` — `positive` (activation) or `negative` (inhibition).
- `color` — green for positive, red for negative.
- `effect` — short verb (`activation`, `repression`, `phosphorylation`, …)
  when available.
- `pmid` — PubMed ID of the supporting paper for that edge (KG-Cleaned only;
  the FLASH-P exports use `doi` and `evidence_sentence` instead — both already
  present in the original cytoscape exports).

The graph is directed (`edgedefault="directed"`).

---

## Cytoscape style — `Style_Cytoscape.xml`

This folder ships the manuscript's Cytoscape vizmap as `Style_Cytoscape.xml`
(style name: **FLASH-P**). It is the same style used to render every network
figure in the paper. Importing it once per Cytoscape session lets every
GraphML in this folder render with the published look — node fill / shape /
size keyed off `type` (GENE, HORMONE, METABOLITE, ENVIRONMENT, PHENOTYPE,
REGULATORY_RNA, PROTEIN_COMPLEX) and edge stroke / arrowhead keyed off `sign`
(positive → green delta arrow, negative → red T-bar).

### How to import the style

1. Open Cytoscape.
2. **File → Import → Styles from File…** → select
   `Outcome/Networks/Style_Cytoscape.xml`.
3. A confirmation dialog will report that the **FLASH-P** style was added.
   The style now lives in the **Style** panel for the rest of the session.
   It only has to be imported once; Cytoscape persists imported styles to
   the user profile.

### How to apply the style to a network

1. **File → Import → Network from File…** → pick any `.graphml` from this
   folder. All node and edge attributes (`type`, `label`, `color`, `sign`,
   `effect`, `pmid`, …) load automatically.
2. Open the **Style** panel (left dock, Control Panel → Style).
3. From the dropdown at the top of the panel, choose **FLASH-P**. Nodes and
   edges immediately repaint with the published palette / shapes / arrowheads.
4. Apply a layout. Suggested defaults:
   - FLASH-P networks: **Layout → yFiles Hierarchic Layout** (or
     yFiles Organic for the merged network).
   - KG-Cleaned networks: these are very dense (≈100–3700 edges) — start
     with **Layout → Prefuse Force-Directed** and consider filtering to a
     degree- or neighbourhood-restricted subgraph before rendering, otherwise
     the layout collapses into a hairball.
5. (Optional) For perturbation panels like Figure 2A, override **NODE_SIZE**
   with a continuous mapping on a perturbation-value attribute (e.g. a
   `KO_value` column) — see `Analysis/max2KO/README.md` for the recipe.

### If the style does not appear in the dropdown

Cytoscape silently skips style imports when a style with the same name
already exists. To force a refresh: open **Style** panel → cog icon →
**Remove Style…** → delete the existing **FLASH-P** entry, then re-import
`Style_Cytoscape.xml`.
