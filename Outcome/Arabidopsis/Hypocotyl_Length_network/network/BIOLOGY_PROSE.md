# Hypocotyl Length in Arabidopsis thaliana — Biology-First Prose (BUILDER Phase 1)

## Paragraph 1 — The core question
Hypocotyl elongation is the proximal read-out of a decision the seedling makes between **skotomorphogenesis** (long, spindly, etiolated growth seeking light) and **photomorphogenesis** (short, green, open-cotyledoned growth). This decision is integrated at the level of a small set of transcription factors that converge on cell-wall loosening and expansion in the hypocotyl epidermis. In the dark, PIF transcription factors (PIF1/3/4/5) and the BR-responsive BZR1 are stable, auxin signaling is permissive via ARF6, DELLA proteins are held low by GA, and COP1/SPA1/DET1 degrade HY5 in the nucleus — net result: long hypocotyl. In the light, photoreceptors (phyA, phyB, CRY1, CRY2, UVR8) inhibit COP1 activity; HY5 stabilizes and BBX21 partners with it; PIFs are phosphorylated and degraded; BR catabolism rises through BAS1; DELLA accumulates as GA signaling is tuned down — net result: short hypocotyl.

## Paragraph 2 — The four-hormone integration
Four hormones converge on elongation and form the heart of the network: brassinosteroid (BR), gibberellin (GA), auxin, and (in darkness) ethylene. **BR**: DET2/DWF4 biosynthesize BR; BAS1/SOB7 catabolize it; BR binds BRI1 at the plasma membrane, which together with the BAK1 co-receptor inhibits the GSK3-like kinase BIN2; unphosphorylated BZR1 enters the nucleus (helped by the PP2A phosphatase) and promotes elongation. **GA**: GA20ox/GA3ox synthesize GA4; GA2ox inactivates it; GA4 binds GID1, which recruits DELLA proteins to SCF^SLY1 for degradation. DELLA directly sequesters PIF3/PIF4/ARF6 and represses BZR1 activity, so DELLA loss releases elongation. **Auxin**: PIF4 and PIF7 induce YUC8 and TAA1 (auxin biosynthesis) in warm temperature and shade; auxin binds TIR1/AFB, targeting Aux/IAA repressors for degradation; freed ARF6/7/8 activate SAUR/expansins/PRE1 to loosen cell walls. **Ethylene** (relevant in dark triple-response): ethylene inactivates CTR1, activating EIN2 and stabilizing EIN3; in dark, EIN3 shortens the hypocotyl (ctr1 = constitutive ethylene → short; ein3 loss → long under ACC).

## Paragraph 3 — Light perception and the COP1 hub
All five photoreceptors (phyA far-red, phyB red, CRY1/CRY2 blue, UVR8 UV-B) converge on one central node: **COP1**. COP1, supported by SPA1 in the nucleus, is a multi-target E3 ubiquitin ligase (Motif 5, Multi-Output Scaffold) that degrades **HY5**, **HFR1**, **BBX21/22**, and **HYH**. Light-activated photoreceptors physically interact with COP1/SPA1 and promote their export from the nucleus, reducing effective COP1 activity — this is a *Perception Gate* (Motif 1) where the photoreceptors are co-inhibitors of COP1 function. The down-stream TFs then follow: HY5 directly represses elongation genes; HFR1 heterodimerizes with and antagonizes PIFs; BBX21 partners with and stabilizes HY5. A parallel arm is **DET1**, a constitutive source node that positively regulates PIF1/3/4/5 abundance in darkness and is counteracted by light through COP1-independent mechanisms (residual gap: COP10/DDB1 regulation of DET1 not curated — treat DET1 as source).

## Paragraph 4 — Temperature and shade
Thermomorphogenesis at warm temperature (28 °C) and shade avoidance in low R:FR both converge on **PIF4 stabilization**. Three mechanisms cooperate: (i) warm temperature releases the **Evening Complex** (ELF3/ELF4/LUX composite, here `ELF3_complex`) from PIF4 promoters; (ii) phyB reverts thermally from active Pfr to inactive Pr, relieving PIF4/PIF5/PIF7 phosphorylation; (iii) HSFA1-family TFs directly bind PIF4 and stabilize it. Shade (low R:FR) inactivates phyB in a similar way and specifically accumulates PIF7 via dephosphorylation and 14-3-3 release. PIF4 and PIF7 in turn induce **YUC8** and **TAA1** (auxin biosynthesis) and **IAA19/IAA29**, amplifying elongation through auxin. HFR1 is induced as a negative-feedback brake on PIF7, but its induction is too slow to fully counter the response — this is a *Coherent Feed-Forward Loop with negative feedback* (Motif 3 + Motif 2).

## Paragraph 5 — Integration at the phenotype
At the hypocotyl, five TF-type activators promote elongation and three repressors block it. **Activators**: PIF3, PIF4, PIF5 (dark/warm/shade elongation), BZR1 (BR pathway output), ARF6 (auxin pathway output). **Inhibitors**: HY5 (light photomorphogenesis), DELLA (GA absence), EIN3 (dark ethylene). The PIF-BZR1-ARF6 triad represents the classic *Coherent Feed-Forward* where PIF4 directly binds SAUR/expansin promoters, activates ARF6 expression, and induces BR biosynthesis (DWF4) — three assurances of elongation. DELLA sits at the convergence of many pathways: it directly inhibits PIF3, PIF4, BZR1, and ARF6, so *GA absence* (high DELLA) blocks all four axes of elongation simultaneously. PIF7 does not directly edge to the phenotype in this network; instead it routes through YUC8→Auxin→TIR1→AUX_IAA→ARF6 — this keeps PIF7 on-cascade while respecting the 5-activator cap at the phenotype (Trap 4).

## Motifs applied
- **Perception Gate (Motif 1)**: BR→BRI1 with BAK1 as co-inhibitor of BIN2; GA4→GID1 inhibits DELLA; Auxin→TIR1 degrades AUX_IAA; light (5 photoreceptors) as co-inhibitors of COP1 with SPA1 as co-activator.
- **Biosynthesis-Degradation Balance (Motif 4)**: BR (DET2+DWF4 vs. BAS1+SOB7); GA4 (GA20ox1+GA3ox1 vs. GA2ox1).
- **Multi-Output Scaffold (Motif 5)**: COP1 → HY5, HFR1, BBX21 (three targets); BIN2 → BZR1 (single output in this build, BES1 dropped).
- **Coherent Feed-Forward (Motif 3)**: PIF4 has direct edge to Hypocotyl_Length AND routes through YUC8→Auxin→ARF6→Hypocotyl_Length; photoreceptors directly inhibit PIFs AND stabilize HY5 via COP1.
- **Hormone Crosstalk Feedback (Motif 2)**: ABA ⊣ GA4 biosynthesis + ABA → GA2ox1 (catabolism) + ABA → DELLA = coherent triple-assurance of growth restriction by ABA, a stabilizing negative loop on growth.
- **Mutual Inhibition in disguise**: HY5 and PIFs compete at shared promoters, but no direct edge — biology captured via their opposing signs on the phenotype.

## Positive-feedback loops broken (Trap 1)
- **BZR1 ↔ ARF6**: dropped ARF6 → BZR1 (+); kept BZR1 → ARF6 (+).
- **PIF4 ↔ ARF6**: dropped ARF6 → PIF4 (+); kept PIF4 → ARF6 (+).
- **phyB ↔ PIF3/4/5/7** (mutual inhibition creates positive feedback): dropped PIF3/4/5/7 → phyB (-); kept phyB → PIFs (-).
- **PIF4 → BAK1 → ⊣ BIN2 → ⊣ PIF4**: dropped PIF4 → BAK1 (+); BAK1 kept as source co-receptor for the BR Perception Gate.
- **PIF4 → DWF4 → BR → BRI1 → ⊣ BIN2 → BZR1 → PIF4**: dropped PIF4 → DWF4 (+); DWF4 kept under BZR1 auto-feedback only (safe negative loop).
- **BIN2 → PIF4 (-)**: dropped to avoid closing the BR-PIF4 positive loop; PIF4 still gets BR signal via BZR1 → PIF4 (+).

## Residual literature gaps handled
- **DET1, SPA1, BAK1, GA20ox1, SOB7, DET2, PP2A**: treated as source nodes (residual gaps — no curated upstream regulators for this phenotype).
- **ABA**: treated as source per residual gap; NCED biosynthesis not curated for hypocotyl.
- **GA4_hormone vs. GA4**: unified to a single `GA4` node to match residual-gap recommendation ("include GA20ox/GA3ox → GA4 → GID1 → DELLA rather than treating GA4_hormone as source").
- **PHYB vs. phyB**: consistently use `phyB` (lowercase) for the photoreceptor; the BR-catabolism `PHYB` ambiguity resolved by using `BAS1` and `SOB7` for BR catabolism.
- **PAR1, FHY3/FAR1, ROT3/BR6ox1**: documented in curated_edges.json but NOT in network (low impact on core cascade).
- **PIF7 → phyB -**: dropped (would close phyB↔PIF7 positive-feedback loop); phyB → PIF7 (-) kept.
- **SLY1**: dropped (GID1 → DELLA (-) edge carries the GA-degradation mechanism without adding a source-only co-factor that doesn't change outputs).
