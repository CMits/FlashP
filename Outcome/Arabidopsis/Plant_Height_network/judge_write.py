"""
Emit judge_review_iteration_1.json for the Plant_Height network.

This mirrors the spec in JUDGE_AGENT.md §8. Content reflects JUDGE's analysis
of the BUILDER iteration-1 network (52 nodes, 64 edges) against the full
curated edges pool (244 edges).
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "network" / "judge_review_iteration_1.json"

# ---------------------------------------------------------------------------
# Per-node audit (one entry per node in the network)
# ---------------------------------------------------------------------------
# Format: node -> (inputs, outputs, excluded_regulators, verdict, comment)
PER_NODE = [
    # ---- Environment / source nodes ----
    ("Light",
     ["(source)"],
     ["PHYB(+)", "HFR1(+)"],
     ["CRY1(E159 Light->CRY1)", "FKF1(E140 Light->FKF1)"],
     "under-specified",
     "Source node. Missing Light->CRY1 and Light->FKF1 — both tie into FT/CO photoperiod circuit. FKF1 is the key Light→photoperiod input and should be added with CO/GI."),
    ("Temperature",
     ["(source)"],
     ["PIF4_5_7(+)"],
     ["ARP6/H2A_Z(E148) ambient-temp chromatin arm"],
     "appropriate",
     "Drives warm-temp PIF4 elongation. The H2A.Z chromatin arm (Temperature -> H2A_Z -| FT) is a parallel SVP/FLM-linked channel worth adding if a flowering-temperature effect is to be simulated."),
    ("Cold_Vernalization",
     ["(source)"],
     ["VIN3(+)"],
     [],
     "appropriate",
     "Correctly feeds VIN3; VIN3 is the canonical cold-sensor output."),
    ("Sucrose",
     ["(source)"],
     ["miR156(-)"],
     ["T6P(E163 Sucrose->TPS1->T6P in curated)"],
     "appropriate",
     "Only curated outgoing is Sucrose -| miR156 (E043). The T6P arm bypasses Sucrose in our curated set (TPS1 -> T6P -> FT) so Sucrose itself is well-represented at this scale."),
    ("FRI",
     ["(source)"],
     ["FLC(+)"],
     [],
     "appropriate",
     "Canonical FLC activator, standalone source."),
    ("BAK1",
     ["(source)"],
     ["BSU1(+)"],
     [],
     "appropriate",
     "Constitutive co-receptor for BR perception gate. Single outgoing edge intentional."),
    ("SLY1",
     ["(source)"],
     ["DELLA(-)"],
     [],
     "appropriate",
     "F-box in the GA Perception Gate acting with GID1 as co-inhibitor of DELLA — correctly modelled."),
    ("PAR1",
     ["(source)"],
     ["PIF4_5_7(-)"],
     [],
     "appropriate",
     "Shade avoidance negative regulator of PIFs; minimal but correct."),
    ("NCED3",
     ["(source)"],
     ["ABA(+)"],
     [],
     "appropriate",
     "Rate-limiting ABA biosynthesis; single edge suffices as source."),
    ("ACS_ACO",
     ["(source)"],
     ["Ethylene(+)"],
     [],
     "appropriate",
     "Composite ethylene biosynthesis; single outgoing is correct."),
    # ---- Regulatory RNAs ----
    ("miR156",
     ["Sucrose(-)"],
     ["SPL9(-)"],
     ["SPL2(E001)", "SPL3(E002)", "SPL10(E004)", "SPL13(E005)", "SPL15(E006)",
      "Plant_Height direct (E044)"],
     "under-specified",
     "Only one downstream target (SPL9). Canonical miR156→SPL family is partly captured by the SPL9 composite but miR156→Plant_Height direct (E044) is also curated and was dropped; also miR156 should regulate MIR172B indirectly via SPL. Coverage 2/9 = 0.22 — KEY PLAYER flag."),
    # ---- Hormones ----
    ("Gibberellin",
     ["GA20OX(+)", "GA3OX(+)", "GA2OX(-)"],
     ["GA20OX(-)", "GA3OX(-)", "GA2OX(+)", "GID1(+)", "Plant_Height direct (E105) — excluded"],
     ["Plant_Height direct (E105)"],
     "topology_hazard",
     "Perception Gate purity warning: Gibberellin has 4 outgoing edges (GID1 receptor + 3 direct feedback on GAox enzymes). The GA→GA20OX/GA3OX/GA2OX edges are well-documented biology but functionally BYPASS the GID1 receptor (Motif 1 states the ligand must have only ONE outgoing edge). Biologically correct to route feedback through DELLA→GAox, but those curated edges don't exist. Accept with Trap-5 disclosure or re-route."),
    ("Brassinosteroid",
     ["BR_SYN(+)"],
     ["BRI1(+)"],
     ["Plant_Height direct (E123) — correctly excluded via Gate"],
     "appropriate",
     "Clean Perception Gate: hormone has only one outgoing edge (to BRI1). Motif 1 compliant."),
    ("Auxin",
     ["YUC_TAA(+)"],
     ["TIR1(+)", "IPT(-)"],
     ["Plant_Height direct (E103)", "SAUR19(E099)", "GA20ox1(E100)",
      "PIN1(E101)"],
     "topology_hazard_minor",
     "Two outgoing edges: TIR1 (receptor, correct) and IPT (-1) (hormone crosstalk to CK biosynthesis). Auxin→IPT is a bypass of TIR1 — exogenous auxin in tir1 KO will still reduce IPT. Consider routing as ARF6_7_8→IPT (-1) to preserve gate purity."),
    ("Cytokinin",
     ["IPT(+)", "CKX3(-)"],
     ["AHK3(+)", "CKX3(+)"],
     ["Plant_Height direct (E188)", "AHK2(E207)", "AHK4(E209)"],
     "appropriate",
     "Biosynthesis-Degradation Balance (Motif 4) correctly applied. Cyt→CKX3 is a legitimate negative feedback, not a bypass. Coverage 4/10 = 0.40 is right at threshold."),
    ("Ethylene",
     ["ACS_ACO(+)"],
     ["ETR1(-)"],
     ["Plant_Height direct (E197)"],
     "appropriate",
     "Clean gate. ETR1 is deactivated by ethylene (inverted compared to most receptors) — topology handled correctly via the ETR1→CTR1→EIN2→EIN3 chain."),
    ("ABA",
     ["NCED3(+)"],
     ["PYL(+)", "GA20OX(-)"],
     ["Plant_Height direct (E218)"],
     "topology_hazard_minor",
     "Bypass edge ABA→GA20OX (-1) alongside ABA→PYL receptor. Same issue as Auxin→IPT. Consider routing via ABI5→GA20OX. Minor Trap-5 risk."),
    # ---- GA biosynthesis / catabolism ----
    ("GA20OX",
     ["Gibberellin(-)", "PIF4_5_7(+)", "ABA(-)"],
     ["Gibberellin(+)"],
     ["Auxin(E100)", "TEM1(E168)"],
     "appropriate",
     "Properly connected; 3 inputs drive GA biosynthesis response; PIF4-induction is the warm-temp elongation feed-forward arm."),
    ("GA3OX",
     ["Gibberellin(-)"],
     ["Gibberellin(+)"],
     [],
     "appropriate",
     "Minimal but functional; negative feedback from GA is present."),
    ("GA2OX",
     ["Gibberellin(+)"],
     ["Gibberellin(-)"],
     [],
     "appropriate",
     "Catabolism arm of Motif 4; GA→GA2OX positive feedback is homeostatic."),
    # ---- BR ----
    ("BR_SYN",
     ["BZR_BES(-)"],
     ["Brassinosteroid(+)"],
     [],
     "appropriate",
     "BZR-feedback correctly applied. Composite of 4 biosynthesis enzymes."),
    ("BRI1",
     ["Brassinosteroid(+)"],
     ["BSU1(+)"],
     ["BKI1(E115 BKI1-|BRI1)"],
     "appropriate",
     "BKI1 inhibitor of BRI1 correctly excluded (low importance without explicit BKI1 phosphorylation modelling)."),
    ("BAK1",  # listed again because it's in NODES list order wise above
     ["(source)"], ["BSU1(+)"], [], "appropriate",
     "(See environment block — duplicate entry suppressed)"),
    ("BSU1",
     ["BRI1(+)", "BAK1(+)"],
     ["BIN2(-)"],
     [],
     "appropriate",
     "Gate completion for BR perception: BRI1+BAK1 co-activate BSU1 which removes BIN2 → BZR_BES released. Good."),
    ("BIN2",
     ["BSU1(-)"],
     ["BZR_BES(-)"],
     ["KIB1(E119)"],
     "appropriate",
     "GSK3 kinase correctly positioned; KIB1 regulation (single paper, E119) can be excluded."),
    ("BZR_BES",
     ["DELLA(-)", "BIN2(-)"],
     ["Plant_Height(+)", "BR_SYN(-)"],
     ["PP2A(E118 PP2A->BZR1)", "PIF4->BES1 (E126)", "MAX2->BES1 (E127)"],
     "appropriate",
     "Well-integrated TF with BR + DELLA inputs and BR-biosynthesis feedback. PP2A is a notable missing activator."),
    # ---- Auxin ----
    ("YUC_TAA",
     ["PIF4_5_7(+)"],
     ["Auxin(+)"],
     [],
     "appropriate",
     "Feed-forward via PIFs correctly encoded."),
    ("IPT",
     ["Auxin(-)"],
     ["Cytokinin(+)"],
     [],
     "appropriate",
     "Composite IPT3/5/7; auxin repression reflected."),
    ("CKX3",
     ["Cytokinin(+)"],
     ["Cytokinin(-)"],
     [],
     "appropriate",
     "Degradation arm of CK Motif 4 correctly modelled."),
    ("GID1",
     ["Gibberellin(+)"],
     ["DELLA(-)"],
     ["Individual DELLA paralogs already composited"],
     "appropriate",
     "Composite receptor; paired with SLY1 as co-inhibitor of DELLA. Coverage 2/7=0.29 largely explained by composite collapse."),
    ("DELLA",
     ["GID1(-)", "SLY1(-)"],
     ["PIF4_5_7(-)", "BZR_BES(-)", "ARF6_7_8(-)", "Plant_Height(-)"],
     ["SPY->GAI (E069)"],
     "appropriate",
     "Multi-Output Scaffold (Motif 5) applied well. SPY activator of GAI is the only notable missing regulator."),
    ("BRI1",
     ["Brassinosteroid(+)"], ["BSU1(+)"], [], "appropriate",
     "(duplicate placeholder — see above)"),
    ("TIR1",
     ["Auxin(+)"],
     ["IAA19(-)"],
     [],
     "appropriate",
     "Receptor in Auxin Perception Gate; minimal but correct."),
    ("IAA19",
     ["TIR1(-)"],
     ["ARF6_7_8(-)"],
     [],
     "appropriate",
     "Aux/IAA repressor correctly gated by TIR1."),
    ("ARF6_7_8",
     ["DELLA(-)", "IAA19(-)"],
     ["Plant_Height(+)"],
     [],
     "appropriate",
     "Composite growth-promoting ARFs; two inputs (IAA19 gate + DELLA) captures both auxin-release and DELLA-sequestration."),
    # ---- Light ----
    ("PHYB",
     ["Light(+)"],
     ["PIF4_5_7(-)"],
     ["PIF3(E076)", "COP1(E162)", "CO(E135)", "Plant_Height direct (E087)"],
     "under-specified",
     "Coverage 2/8 = 0.25 — KEY PLAYER flag. PHYB has five additional curated outputs (PIF3, COP1, CO, CRY1, Plant_Height) that tie into the photoperiod circuit. Add PHYB→COP1 and PHYB→CO if photoperiod is added."),
    ("HFR1",
     ["Light(+)"],
     ["PIF4_5_7(-)"],
     ["Plant_Height direct (E233)"],
     "appropriate",
     "Light -> HFR1 -| PIFs correctly wired. Direct edge to Plant_Height is redundant with PIF route."),
    ("PIF4_5_7",
     ["PHYB(-)", "HFR1(-)", "PAR1(-)", "Temperature(+)", "DELLA(-)"],
     ["YUC_TAA(+)", "GA20OX(+)", "Plant_Height(+)"],
     ["ELF3(E219)", "ELF4(E220)", "LUX(E221)", "JMJ17(E244)", "BES1(E126)"],
     "under-specified",
     "Coverage 8/22 = 0.36 — close to threshold. Evening Complex (ELF3/4/LUX) is the canonical circadian repressor of PIF4 and is completely absent; highly recommended to add as composite EC or individual nodes."),
    # ---- CK signaling ----
    ("AHK3",
     ["Cytokinin(+)"],
     ["AHP1(+)"],
     [],
     "appropriate",
     "Receptor; linear chain to AHP1."),
    ("AHP1",
     ["AHK3(+)"],
     ["ARR1(+)"],
     [],
     "appropriate",
     "Phosphorelay; linear."),
    ("ARR1",
     ["AHP1(+)"],
     ["Plant_Height(+)"],
     ["ARR5(E196)"],
     "appropriate",
     "Type-B ARR integrator; ARR5 negative feedback low-priority."),
    # ---- Ethylene ----
    ("ETR1",
     ["Ethylene(-)"],
     ["CTR1(+)"],
     [],
     "appropriate",
     "Inverse-logic receptor correctly modelled (Ethylene inhibits ETR1)."),
    ("CTR1",
     ["ETR1(+)"],
     ["EIN2(-)"],
     ["Plant_Height direct (E198)"],
     "appropriate",
     "Linear chain continuation; direct edge excluded in favor of EIN3 route — defensible."),
    ("EIN2",
     ["CTR1(-)"],
     ["EIN3(+)"],
     [],
     "appropriate",
     "Linear; correct."),
    ("EIN3",
     ["EIN2(+)"],
     ["Plant_Height(-)"],
     ["ERF1(E203)", "EBF1(E199)"],
     "appropriate",
     "EBF1 feedback is minor; ERF1 downstream TF not needed for height prediction."),
    # ---- ABA ----
    ("PYL",
     ["ABA(+)"],
     ["ABI1(-)"],
     [],
     "appropriate",
     "Receptor correctly positioned."),
    ("ABI1",
     ["PYL(-)"],
     ["SNRK2(-)"],
     [],
     "appropriate",
     "PP2C phosphatase correctly modelled as SnRK2 inhibitor."),
    ("SNRK2",
     ["ABI1(-)"],
     ["ABI5(+)"],
     [],
     "appropriate",
     "Linear; correct."),
    ("ABI5",
     ["SNRK2(+)"],
     ["Plant_Height(-)"],
     [],
     "appropriate",
     "Good integrator; drives ABA-repression arm on height."),
    # ---- Vernalization/flowering ----
    ("VIN3",
     ["Cold_Vernalization(+)"],
     ["FLC(-)"],
     [],
     "appropriate",
     "Vernalization-induced FLC silencer; single edge is sufficient for direct cold sensing but PRC2 machinery (VRN2/CLF/SWN/FIE) is missing (see FLC audit)."),
    ("FLC",
     ["VIN3(-)", "FRI(+)"],
     ["FT(-)"],
     ["FCA(E030)", "FPA(E031)", "FLD(E033)", "FVE(E034)", "LD(E035)",
      "FY(E036)", "LDL1(E045)", "VRN2(E154)", "CLF(E155)", "SWN(E156)",
      "FIE(E157)", "COOLAIR(E158)", "SPL3/SPL15 (E040/E041) downstream",
      "Plant_Height direct (E160)", "SOC1 (E038)"],
     "MAJOR UNDER-SPECIFICATION",
     "Coverage 3/19 = 0.16 — KEY PLAYER flag. FLC is documented as receiving inputs from the ENTIRE autonomous pathway (7 genes), the full PRC2 vernalization machinery (4 genes + COOLAIR lncRNA), and the FRI/VIN3 pair. Only FRI/VIN3 modelled. This is the classic case §9.11 was written for."),
    ("FT",
     ["FLC(-)"],
     ["Plant_Height(-)"],
     ["CO(E134)", "GI(E137)", "SVP(E146)", "FLM(E147)", "H2A_Z(E150)",
      "T6P(E164)", "TEM1(E167)", "AP2(E017)", "TOE1(E018)", "TOE2(E019)",
      "SMZ(E020)", "FD (downstream)"],
     "MAJOR UNDER-SPECIFICATION",
     "Coverage 2/16 = 0.12 — KEY PLAYER flag. FT is the florigen integrator with 10+ curated regulators (photoperiod, autonomous, age, sugar, temperature). Only FLC→FT modelled. Requires CO/GI, SVP/FLM, AP2/TOE composite, and ideally T6P."),
    ("SPL9",
     ["miR156(-)"],
     ["Plant_Height(-)"],
     ["MIR172B(E015)", "SOC1(E037)", "FUL(E038)", "AP1(E039)", "MIR156(E013)"],
     "under-specified",
     "Coverage 2/8 = 0.25 — KEY PLAYER flag. SPL9 direct-to-phenotype route is a shortcut; the canonical age-pathway flow is SPL9 → MIR172 ⊣ AP2/TOE ⊣ FT, currently broken. Recommend restoring the miR172/AP2 arm."),
    # ---- Phenotype ----
    ("Plant_Height",
     ["SPL9(-)", "FT(-)", "DELLA(-)", "EIN3(-)", "ABI5(-)",
      "BZR_BES(+)", "ARF6_7_8(+)", "ARR1(+)", "PIF4_5_7(+)"],
     ["(leaf)"],
     ["42 curated direct edges including SL, SOC1, LFY, AP1, HY5, BP, PIN1, "
      "Auxin_Transport, HFR1 direct"],
     "appropriate_but_missing_SL_integrator",
     "Coverage 9/42 = 0.21 — but almost all excluded direct edges are correctly rerouted through their master TFs (DELLA, BZR_BES, ARF, PIF, ARR1, EIN3, ABI5). Missing: Strigolactone integrator (no SL pathway in network), HY5 light-growth inhibitor branch. 4 activators + 5 inhibitors = good balance."),
]


# ---------------------------------------------------------------------------
# Per-pathway audit
# ---------------------------------------------------------------------------
PER_PATHWAY = [
    {
        "pathway": "Gibberellin biosynthesis-signaling-catabolism",
        "completeness": "high",
        "comment": "GA20OX/GA3OX/GA2OX composites + GID1+SLY1 Perception Gate + DELLA Multi-Output Scaffold are all present. Negative feedback on GA enzymes implemented. Minor: Gibberellin has 4 outgoing edges (1 to GID1, 3 bypass to GA enzymes) violating Motif 1 gate purity — accept with Trap-5 disclosure OR route via DELLA→GAox if curated edges are found.",
        "missing_pieces": ["CPS/KS/KO/KAO early biosynthesis (low priority — implied by GA20OX composite)", "SPY->GAI DELLA activator (E069)"],
    },
    {
        "pathway": "Brassinosteroid signaling",
        "completeness": "high",
        "comment": "Clean Perception Gate (BR→BRI1, BRI1+BAK1→BSU1→-BIN2 →+BZR_BES); BZR_BES→BR_SYN negative feedback present. Missing PP2A (E118) activation of BZR1 as minor addition.",
        "missing_pieces": ["PP2A -> BZR1 (E118)"],
    },
    {
        "pathway": "Auxin signaling",
        "completeness": "medium",
        "comment": "Perception Gate applied linearly (Auxin→TIR1→-IAA19→-ARF). Auxin→IPT crosstalk is a mild gate bypass. Upstream auxin biosynthesis is a single composite (YUC_TAA). Missing SAUR19/GA20ox1 downstream targets of auxin — acceptable since they route through ARF6_7_8.",
        "missing_pieces": ["Auxin -> SAUR19 (E099)", "Route Auxin -> IPT via ARF6_7_8 to preserve gate"],
    },
    {
        "pathway": "Cytokinin biosynthesis-signaling",
        "completeness": "high",
        "comment": "Motif 4 Biosynthesis-Degradation Balance applied (IPT vs CKX3). Two-component signaling chain (AHK3→AHP1→ARR1) present. Minor missing: AHK2/AHK4 direct edges (covered by AHK3 as representative).",
        "missing_pieces": ["AHK2/AHK4 representation (accepted composite approximation)"],
    },
    {
        "pathway": "Ethylene signaling",
        "completeness": "high",
        "comment": "Clean inverted-receptor chain (ET⊣ETR1→CTR1⊣EIN2→EIN3). ACS+ACO composite is acceptable. EIN3→Plant_Height(-) is the growth-inhibition output.",
        "missing_pieces": [],
    },
    {
        "pathway": "ABA signaling",
        "completeness": "high",
        "comment": "Canonical PYR/PYL→PP2C→SnRK2→ABI5 chain wired. ABA→GA20OX crosstalk is a minor gate bypass. Missing catabolism (CYP707A not in curated) is Step 1 coverage gap.",
        "missing_pieces": ["ABA catabolism (literature gap)"],
    },
    {
        "pathway": "Strigolactone signaling",
        "completeness": "absent",
        "comment": "Entire SL arm missing. Curated has D27/MAX3/MAX4/MAX1→Strigolactone (E209-E212), SL→D14→MAX2→SMXL6 chain (E213-E217), and SL→Plant_Height(+1) (E211) direct edge. In Arabidopsis SL weakly promotes primary shoot elongation; omitting loses any SL-mutant predictability.",
        "missing_pieces": ["D27 -> SL (E209)", "MAX3 -> SL (E210)", "MAX4 -> SL (E212)", "MAX1 -> SL (E211)", "SL Perception Gate (SL→D14, MAX2+D14→SMXL6)", "Strigolactone->Plant_Height (E211)"],
    },
    {
        "pathway": "Light / PHYB / shade avoidance",
        "completeness": "medium",
        "comment": "Core Light→PHYB→PIF4_5_7 and Light→HFR1→PIF4_5_7 present. Evening Complex (ELF3/4/LUX) repressing PIF4 is completely missing (4 curated edges E219-E222). HY5/COP1 light-growth inhibition branch (E158-E161, E163) absent.",
        "missing_pieces": ["ELF3->PIF4 (E219)", "ELF4->PIF4 (E220)", "LUX->PIF4 (E221)", "COP1->HY5 (E162)", "HY5->Plant_Height (E161)"],
    },
    {
        "pathway": "Photoperiod (CO/GI/FKF1/CDF1→FT)",
        "completeness": "absent",
        "comment": "Photoperiod flowering circuit completely missing. Curated has Light→FKF1, FKF1→CO, FKF1⊣CDF1⊣CO, GI→CO, GI→FT, CO→FT, ZTL⊣CO — a full cascade. With FT already in the network, photoperiod is the biggest missing input.",
        "missing_pieces": ["CO->FT (E134)", "GI->FT (E137)", "GI->CO (E139) via FKF1/CDF1", "phyA->CO (E131)", "FKF1 hub"],
    },
    {
        "pathway": "Vernalization (FRI/FLC/VIN3/PRC2/COOLAIR)",
        "completeness": "low",
        "comment": "FRI→FLC and VIN3⊣FLC present. Missing PRC2 components VRN2, CLF, SWN, FIE (E154-E157) and COOLAIR lncRNA (E158). PRC2 silences FLC after vernalization and is a core mechanism.",
        "missing_pieces": ["VRN2->FLC (E154)", "CLF->FLC (E155)", "SWN->FLC (E156)", "FIE->FLC (E157)", "COOLAIR->FLC (E158)"],
    },
    {
        "pathway": "Autonomous (FCA/FPA/FLD/FVE/LD/FY → FLC)",
        "completeness": "absent",
        "comment": "Entire autonomous arm missing. FCA, FPA, FLD, FVE, LD, FY are constitutive FLC repressors (E030-E036). Flowering in fca/fld mutants is delayed — highly relevant to plant-height timing.",
        "missing_pieces": ["FCA->FLC (E030)", "FPA->FLC (E031)", "FLD->FLC (E033)", "FVE->FLC (E034)", "LD->FLC (E035)", "FY->FLC (E036)"],
    },
    {
        "pathway": "Age (miR156/SPL/miR172/AP2-TOE)",
        "completeness": "low",
        "comment": "Only Sucrose⊣miR156⊣SPL9→Plant_Height modelled. miR172 and its targets (AP2, TOE1/2, SMZ, SNZ) entirely missing. Canonical age-to-flowering chain SPL9→miR172⊣AP2⊣FT is broken. The direct SPL9→Plant_Height edge is a shortcut that loses resolution of miR172-overexpression mutants.",
        "missing_pieces": ["miR172 (node)", "SPL9->MIR172B (E015)", "miR172->AP2 (E021) or composite AP2_TOE", "AP2->FT (E017)"],
    },
    {
        "pathway": "Ambient temperature (SVP/FLM/H2A_Z → FT)",
        "completeness": "medium",
        "comment": "Temperature→PIF4 is captured but the parallel ambient-temp control of FT via SVP/FLM and the ARP6/H2A_Z chromatin arm are absent.",
        "missing_pieces": ["SVP->FT (E146)", "FLM->FT (E147)", "ARP6->H2A_Z (E148)", "H2A_Z->FT (E150)"],
    },
    {
        "pathway": "Flowering integrators (SOC1/LFY/AP1)",
        "completeness": "absent",
        "comment": "SOC1, LFY, AP1 are the canonical floral integrators downstream of FT and all three are curated as Plant_Height inhibitors (E170/E171/E172). Network routes FT directly to Plant_Height — defensible but loses integrator-mutant resolution (soc1, lfy, ap1 single mutants).",
        "missing_pieces": ["FT->SOC1 (E176)", "SOC1->LFY (E177)", "LFY->AP1 (E179)", "SOC1->Plant_Height (E170)", "LFY->Plant_Height (E171)", "AP1->Plant_Height (E172)"],
    },
    {
        "pathway": "Sugar / T6P",
        "completeness": "low",
        "comment": "Only Sucrose⊣miR156 present. TPS1→T6P→FT arm (E163, E164) missing — trehalose-6-phosphate is a primary sugar-signalling link to flowering/height.",
        "missing_pieces": ["TPS1->T6P (E163)", "T6P->FT (E164)", "T6P->miR156 (E165)"],
    },
]


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------
SUGGESTIONS = [
    {
        "id": "S001",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Add photoperiod input pathway to FT: CO and GI as new nodes with CO→FT(+1) and GI→FT(+1); optionally include FKF1/CDF1/phyA intermediates.",
        "biological_justification": "Photoperiod (long-day perception via the GI-FKF1-CO-FT module) is THE canonical activator of FT in Arabidopsis. With FT already in the network, its sole input being FLC(-1) means day-length-dependent perturbations cannot be simulated. The orchestrator prompt explicitly lists photoperiod (CO/GI/FT) as required biology.",
        "curated_edge_ids": ["E131", "E134", "E137", "E138", "E139", "E140", "E141", "E142", "E143"],
        "pathway_name": "Photoperiod (GI-FKF1-CDF1-CO-FT)",
        "implementation": "Add CO (GENE), GI (GENE), FKF1 (GENE); edges Light→FKF1(+1, E140), GI→FKF1(+1, E138), FKF1→CDF1(-1, E141) OR drop CDF1 for parsimony, FKF1→CO(+1, E142), phyA→CO(+1, E132), ZTL→CO(-1, E143), PHYB→CO(-1, E135), GI→FT(+1, E137), CO→FT(+1, E134). Minimal add: CO and GI as nodes, GI→CO(+1), CO→FT(+1), GI→FT(+1), Light→GI(+1 implicit). PHYB→CO(-1) closes the light integration loop."
    },
    {
        "id": "S002",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Complete the autonomous pathway as a single composite AUT_SYN (collapsed FCA/FPA/FLD/FVE/LD/FY) → FLC(-1).",
        "biological_justification": "The autonomous pathway (FCA/FPA/FLD/FVE/LD/FY) is one of the three canonical FLC-suppression arms (alongside vernalization and age). Currently FLC has only 2 inputs (VIN3-, FRI+) when 9+ are curated. FLC coverage ratio is 0.16 — KEY PLAYER UNDER-REPRESENTATION flag.",
        "curated_edge_ids": ["E030", "E031", "E033", "E034", "E035", "E036"],
        "pathway_name": "Autonomous flowering pathway -> FLC",
        "implementation": "Add a PROTEIN_COMPLEX composite 'AUT_SYN' (FCA+FPA+FLD+FVE+LD+FY) with composite as source node and single edge AUT_SYN→FLC(-1) carrying evidence from all 6 curated edges. Alternative: split into 2-3 representatives (e.g., FCA, FLD, FVE) as individual GENEs."
    },
    {
        "id": "S003",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Complete vernalization PRC2 machinery: composite PRC2 (VRN2/CLF/SWN/FIE) → FLC(-1); optionally add COOLAIR.",
        "biological_justification": "Vernalization silences FLC not only via VIN3 but through the PRC2 complex (VRN2/CLF/SWN/FIE) and the COOLAIR lncRNA. Missing this makes vrn2/clf/swn mutants non-predictable. 5 curated edges silently excluded.",
        "curated_edge_ids": ["E154", "E155", "E156", "E157", "E158"],
        "pathway_name": "Vernalization PRC2 machinery -> FLC",
        "implementation": "Add PROTEIN_COMPLEX 'PRC2' (VRN2+CLF+SWN+FIE) as source (or activated by Cold_Vernalization via VRN2→FLC via VIN3), with PRC2→FLC(-1). Optionally add COOLAIR (REGULATORY_RNA) → FLC(-1)."
    },
    {
        "id": "S004",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Reinstate age-to-flowering miR172/AP2 arm: add miR172 (REGULATORY_RNA), AP2_TOE (composite AP2/TOE1/TOE2/SMZ), and the chain SPL9→miR172(+1)→AP2_TOE(-1)→FT(-1).",
        "biological_justification": "The SPL9→miR172⊣AP2⊣FT cascade is canonical for age-controlled flowering and was partially built (Sucrose⊣miR156⊣SPL9) but the miR172/AP2 half was dropped. Currently SPL9→Plant_Height(-1) is a direct shortcut. Adding the miR172/AP2 arm gives proper resolution of miR172-OE and ap2 mutants and restores the age-integrator role.",
        "curated_edge_ids": ["E015", "E016", "E017", "E018", "E019", "E020", "E021"],
        "pathway_name": "Age pathway miR172/AP2-TOE arm",
        "implementation": "Add nodes: miR172 (REGULATORY_RNA), AP2_TOE (PROTEIN_COMPLEX of AP2+TOE1+TOE2+SMZ). Add edges: SPL9→miR172(+1, E015 SPL9->MIR172B), miR172→AP2_TOE(-1, composite of E021+E022+E023+E024), AP2_TOE→FT(-1, composite of E017+E018+E019+E020). Keep SPL9→Plant_Height(-1) as a parallel shortcut OR drop it for cascade purity."
    },
    {
        "id": "S005",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Add ambient-temperature FT regulators: SVP→FT(-1), FLM→FT(-1) (and optionally the ARP6-H2A_Z chromatin arm).",
        "biological_justification": "Temperature affects plant height in Arabidopsis through two independent arms: thermomorphogenesis (Temperature→PIF4, already modelled) AND flowering-temperature (Temperature→SVP/FLM→FT). Currently only the first arm exists.",
        "curated_edge_ids": ["E146", "E147", "E148", "E149", "E150"],
        "pathway_name": "Ambient temperature -> FT",
        "implementation": "Add SVP (GENE) and FLM (GENE); edges SVP→FT(-1, E146), FLM→FT(-1, E147), Temperature→SVP(-1 or +1 per E149). Optionally add ARP6→H2A_Z(+1, E148), H2A_Z→FT(-1, E150)."
    },
    {
        "id": "S006",
        "type": "add_edge",
        "priority": "high",
        "description": "Add Evening Complex repression of PIF4_5_7: composite EC (ELF3+ELF4+LUX) → PIF4_5_7(-1).",
        "biological_justification": "The Evening Complex (ELF3/ELF4/LUX) is the primary circadian repressor of PIF4 at night and in cool temperatures. Four curated edges (E219, E220, E221, E222) all excluded. PIF4_5_7 coverage ratio 0.36 — near KEY PLAYER threshold; adding EC restores the major pre-dawn growth rhythm.",
        "curated_edge_ids": ["E219", "E220", "E221", "E222"],
        "implementation": "Add PROTEIN_COMPLEX 'EC' (ELF3+ELF4+LUX) as a source node (or driven by Light if wanted), with EC→PIF4_5_7(-1) using composite evidence from E219+E220+E221."
    },
    {
        "id": "S007",
        "type": "restructure_pathway",
        "priority": "high",
        "description": "Add Strigolactone pathway (biosynthesis + Perception Gate + Plant_Height output).",
        "biological_justification": "Curated has the full SL pathway (D27/MAX3/MAX4/MAX1 → Strigolactone, SL→D14→MAX2→SMXL6, SL→Plant_Height+1) — completely absent from the network. In Arabidopsis SL has a documented effect on primary shoot height; max3/max4 mutants show branching and stature phenotypes. Omitting loses every SL-related perturbation.",
        "curated_edge_ids": ["E209", "E210", "E211", "E212", "E213", "E214", "E215", "E216"],
        "pathway_name": "Strigolactone biosynthesis + signaling",
        "implementation": "Add nodes: Strigolactone (HORMONE), SL_SYN (composite D27+MAX3+MAX4+MAX1), D14 (GENE), MAX2 (GENE, constitutive source-like), SMXL6 (GENE). Add edges: SL_SYN→Strigolactone(+1), Strigolactone→D14(+1), D14+MAX2 as co-inhibitors of SMXL6(-1), SMXL6→? → Plant_Height. The simplest Plant_Height link is Strigolactone→Plant_Height(+1, E211) direct; the full Perception Gate version uses SMXL6 as the output node. Given SL in Arabidopsis primarily affects architecture through BRC1 (not in network for height), a compact add is SL_SYN→SL→D14→MAX2→SMXL6→Plant_Height(-1) chain or direct SL→Plant_Height(+1)."
    },
    {
        "id": "S008",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add floral integrators SOC1, LFY, AP1 as nodes: FT→SOC1(+1)→LFY(+1)→AP1(+1), each with →Plant_Height(-1).",
        "biological_justification": "SOC1/LFY/AP1 are the classic FT-downstream integrators. Three curated Plant_Height-direct edges (E170/E171/E172) were silently dropped. soc1, lfy, ap1 single mutants have documented height-at-flowering phenotypes.",
        "curated_edge_ids": ["E170", "E171", "E172", "E176", "E177", "E179"],
        "implementation": "Add SOC1, LFY, AP1 as GENE nodes. Edges: FT→SOC1(+1, E176), SOC1→LFY(+1, E177), LFY→AP1(+1, E179), SOC1→Plant_Height(-1, E170), LFY→Plant_Height(-1, E171), AP1→Plant_Height(-1, E172). Alternative: composite FLOWER_INT (SOC1+LFY+AP1) with single input FT(+1) and single output Plant_Height(-1) if full resolution isn't needed."
    },
    {
        "id": "S009",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add HY5/COP1 light-growth inhibition branch: COP1→HY5(-1), HY5→Plant_Height(-1).",
        "biological_justification": "HY5 is the master photomorphogenic TF suppressing hypocotyl/stem elongation under light; cop1 and hy5 mutants have robust height phenotypes. Two curated edges (E161, E162) excluded. Adds a PHYB-independent light-to-phenotype route.",
        "curated_edge_ids": ["E161", "E162"],
        "implementation": "Add COP1 (GENE), HY5 (GENE). Edges: PHYB→COP1(-1, E163) [or Light→COP1(-1) composite], COP1→HY5(-1, E162), HY5→Plant_Height(-1, E161). This also improves PHYB coverage ratio (currently 0.25)."
    },
    {
        "id": "S010",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add T6P sugar-signaling arm: TPS1→T6P(+1), T6P→FT(+1), T6P⊣miR156(-1).",
        "biological_justification": "T6P is the sucrose-sensing metabolite upstream of both FT and miR156; two highly-cited links (Wahl 2013, Ponnu 2020). Adds a second Sucrose-to-phenotype route beyond the Sucrose⊣miR156 chain.",
        "curated_edge_ids": ["E163", "E164", "E165"],
        "implementation": "Add nodes: TPS1 (GENE), T6P (METABOLITE). Edges: TPS1→T6P(+1, E163), T6P→FT(+1, E164), T6P→miR156(-1, E165)."
    },
    {
        "id": "S011",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add PP2A→BZR_BES(+1) to complete BR signaling antagonism with BIN2.",
        "biological_justification": "PP2A dephosphorylates BZR1 and activates it — complements the BIN2 repressive arm. Single curated edge (E118). Makes BR Perception Gate symmetric.",
        "curated_edge_ids": ["E118"],
        "implementation": "Add PP2A (GENE, constitutive source). Edge PP2A→BZR_BES(+1, E118)."
    },
    {
        "id": "S012",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add SPY→DELLA(+1) activator of DELLAs.",
        "biological_justification": "SPY O-fucosylates DELLAs enhancing their repressive activity — a modest but well-documented DELLA-stabilising edge (E069). Improves DELLA hub coverage and provides an additional GA-independent DELLA activator.",
        "curated_edge_ids": ["E069"],
        "implementation": "Add SPY (GENE, constitutive source). Edge SPY→DELLA(+1, E069)."
    },
    {
        "id": "S013",
        "type": "mechanism_improvement",
        "priority": "medium",
        "description": "Gibberellin has 4 outgoing edges (GID1 receptor + GA20OX/GA3OX/GA2OX feedback). Annotate the 3 GAox edges with an explicit Trap-5 disclosure in the `mechanism` field, or restructure the feedback through DELLA→GAox edges (requires new LITERATURE REVIEW search).",
        "biological_justification": "Motif 1 specifies the ligand must have only one outgoing edge. Gibberellin violates this with direct transcriptional feedback on GA enzymes. Biologically the feedback is mediated by DELLAs (Zentella 2007) but those curated edges don't exist in the repository. Exogenous-GA in a gid1 KO will still down-regulate GA20OX, causing Trap 5 (signaling-mutant rescue) mispredictions.",
        "curated_edge_ids": ["E063", "E065", "E054"],
        "target_edge": "Gibberellin->GA20OX (-1) and Gibberellin->GA3OX (-1) and Gibberellin->GA2OX (+1)",
        "proposed_mechanism": "GA signaling (via DELLA-mediated transcriptional programs) feeds back on GA biosynthesis/catabolism; this edge is a framework compromise because DELLA->GAox curated edges are absent. Exogenous-GA in gid1 KO will still modulate GA enzyme transcription in the model — a known Trap-5 limitation.",
        "implementation": "Add disclosure text to mechanism field. Flag DELLA->GA20OX/GA3OX/GA2OX as a literature_gap for Step 1."
    },
    {
        "id": "S014",
        "type": "mechanism_improvement",
        "priority": "low",
        "description": "Auxin has outgoing to IPT (crosstalk) outside the TIR1 gate; ABA has outgoing to GA20OX outside the PYL gate. Annotate both with Trap-5 disclosure or route via ARF6_7_8 (Auxin) and ABI5 (ABA).",
        "biological_justification": "Same Perception Gate purity concern as S013 but milder (these are cross-hormone crosstalk rather than self-feedback).",
        "curated_edge_ids": ["E190", "E054"],
        "target_edge": "Auxin->IPT(-1) and ABA->GA20OX(-1)",
        "proposed_mechanism": "Crosstalk edge at the hormone-level; Trap-5 caveat noted.",
        "implementation": "Add disclosure to both `mechanism` fields; accept as-is."
    },
    {
        "id": "S015",
        "type": "literature_gap",
        "priority": "low",
        "description": "DELLA→GA20OX(+1)/GA3OX(+1)/GA2OX(-1) edges (GA feedback homeostasis via DELLAs) are documented in Zentella 2007 and others but are NOT in the curated_edges.json repository.",
        "biological_justification": "Required to close Motif 1 Perception Gate for Gibberellin. With these edges, all GA feedback can flow through DELLA rather than direct GA->enzyme bypasses.",
        "curated_edge_ids": [],
        "implementation": "Step 1 LITERATURE REVIEW should search 'DELLA transcriptional regulation GA20ox GA3ox GA2ox' (Zentella 2007 Plant Cell; Hirano 2012; etc.)."
    },
    {
        "id": "S016",
        "type": "literature_gap",
        "priority": "low",
        "description": "BR catabolism (BAS1/CYP72C1 or similar) is not curated — Motif 4 Biosynthesis-Degradation Balance is incomplete for Brassinosteroid.",
        "biological_justification": "Every other hormone has both synthesis and degradation; BR only has synthesis in the curated pool, so bas1/sob7 BR-catabolism mutants cannot be predicted.",
        "curated_edge_ids": [],
        "implementation": "Step 1 LITERATURE REVIEW should search 'BAS1 brassinosteroid catabolism CYP72C1'."
    },
]


# ---------------------------------------------------------------------------
# Rubric scores
# ---------------------------------------------------------------------------
RUBRIC = {
    "pathway_completeness": {
        "score": 2,
        "justification": "Hormone pathways (GA, BR, Auxin, CK, Ethylene, ABA) are well represented with proper biosynthesis + signaling + some negative feedback. However, four of the eight phenotype-critical pathways the orchestrator enumerated are absent or fragmentary: photoperiod (CO/GI/FT) MISSING, autonomous (FCA/FPA/FLD/FVE→FLC) MISSING, vernalization PRC2 machinery MISSING, age miR172/AP2 arm MISSING. Strigolactone pathway is completely absent despite eight curated edges. Evening Complex is missing. Score cannot exceed 2 with this many orchestrator-listed arms unmodelled."
    },
    "mechanistic_depth": {
        "score": 4,
        "justification": "Strong layered cascades: GA biosynthesis→GA→GID1→DELLA→integrators; BR biosynthesis→BR→BRI1→BAK1→BSU1⊣BIN2⊣BZR_BES; full auxin, ABA, ethylene, CK chains. Some shortcuts: SPL9→Plant_Height direct (should route via miR172/AP2/FT); FLC→FT→Plant_Height is a single link where more integrators (SOC1/LFY/AP1) would add resolution. Overall cascade depth is good (4-6 hops typical)."
    },
    "motif_coverage": {
        "score": 4,
        "justification": "Perception Gate applied for GA+GID1+SLY1→DELLA and BR+BRI1+BAK1 (via BSU1→-BIN2) and Auxin+TIR1→IAA19. Multi-Output Scaffold applied excellently for DELLA (4 outputs). Biosynthesis-Degradation Balance applied for GA and CK. Coherent Feed-Forward applied (PIF4_5_7→Plant_Height direct + via YUC_TAA + via GA20OX). Missing: SL Perception Gate not applied (no SL pathway at all); evening complex AND-gate-like repression of PIFs not applied; no self-limiting feedback attempted."
    },
    "cascade_balance": {
        "score": 3,
        "justification": "Source count 10/52 = 19.2% — below 30-50% target. Not a hard failure (60% cap) but low side. No overloaded hubs (Plant_Height has 9 inputs: 4 activators + 5 inhibitors, within limits). All intermediate nodes have ≤5 inputs. Low source % is partly driven by literature-dense internal regulation but also by the missing upstream photoperiod/autonomous genes (adding them would raise source %). After S001-S005 are applied, expect source % to land in 25-35% range."
    },
    "composite_node_handling": {
        "score": 5,
        "justification": "Paralog composites are handled correctly: DELLA (RGA/GAI/RGL1/RGL2), GID1 (A/B/C), PIF4_5_7, BZR_BES, ARF6_7_8, IPT3/5/7, GA20OX/GA3OX/GA2OX, BR_SYN (DWF4/DET2/CPD/CYP85A1), YUC_TAA, ACS_ACO. Naming convention (ALL_CAPS composites) is consistent. No over-collapsing — non-paralog nodes kept separate (BRI1, BAK1, BIN2, BSU1 etc. each a single node)."
    },
    "hub_completeness": {
        "score": 2,
        "justification": "Critical hubs severely under-represented: FLC has 3/19 = 0.16 (11 regulators excluded, see S002/S003), FT has 2/16 = 0.12 (10 regulators excluded, see S001/S005/S004), miR156 has 2/9 = 0.22. These are primary flowering/age integrators. DELLA hub well covered (6/18 but most rejected edges are composite-consolidated). PIF4_5_7 hub missing Evening Complex."
    },
    "topology_hazards": {
        "score": 3,
        "justification": "One notable hazard: Gibberellin has 4 outgoing edges (1 to GID1 receptor + 3 direct feedback to GA20OX/GA3OX/GA2OX), violating Motif 1 Perception Gate purity. Minor hazards: Auxin→IPT and ABA→GA20OX are cross-hormone bypass edges outside the TIR1/PYL gates. No positive-feedback Trap 1 loops detected. No sole-activator collapse risks (Plant_Height has 4 activators). No undocumented self-loops. These hazards are documented in S013/S014 — accept with Trap-5 disclosure or restructure via literature_gap (S015)."
    },
    "evidence_quality": {
        "score": 4,
        "justification": "All 64 edges have DOI (passed QA check 2). Mechanism strings are carried through directly from curated_edges.json and are specific (e.g. 'miR156 targets SPL mRNA for cleavage and translational repression'). Many edges still carry `verification: abstract_read` — not a blocker but a low-priority follow-up. Did not sample individual evidence_sentence accuracy but random spot-check of Gibberellin→GID1A, MAX2 signalling analogues, and BR edges showed sentence-to-claim fidelity."
    },
    "phenotype_audit": {
        "score": 4,
        "justification": "Plant_Height has 4 activators (PIF4_5_7, BZR_BES, ARF6_7_8, ARR1) + 5 inhibitors (DELLA, ABI5, EIN3, FT, SPL9) = 9 inputs. Activator count exactly at 3-5 target. Major effector classes represented: PIFs (light/temp TF), BZR (BR TF), ARF (auxin TF), ARR (CK TF), DELLA (GA inhibitor), ABI5 (ABA inhibitor), EIN3 (ethylene inhibitor), FT (florigen inhibitor), SPL9 (age inhibitor). Missing effector classes: Strigolactone integrator, HY5 (light-inhibition), and flowering integrators SOC1/LFY/AP1. Arms reasonably balanced (4 promoting / 5 repressing)."
    },
    "rejected_edges_review": {
        "score": 3,
        "justification": "244 curated edges, 95 represented (composite-aware), 149 rejected. Of rejected edges, ~50 are defensible (peripheral SPLs, individual DELLA paralogs, single-paper MEDIUM confidence, rare downstream like BRC1 for a plant-height context). ~50 are SILENT DROPS that should be re-examined (the photoperiod / autonomous / vernalization / age / integrator / SL pathways above). The ratio of defensible vs silent-drop rejections is ~1:1, which is not acceptable for a literature-dense build."
    },
    "key_player_density": {
        "score": 2,
        "justification": "Seven key players flagged with coverage ratio < 0.30 and ≥5 curated edges: FLC (0.16), FT (0.12), miR156 (0.22), PHYB (0.25), SPL9 (0.25), GID1 (0.29 but explained by composite), Plant_Height (0.21 but explained by re-routing through TF integrators). Of these, FLC/FT/miR156/SPL9/PHYB represent REAL under-representation that masks entire pathway arms. GID1 and Plant_Height are defensible via composite/indirection. This is the exact §9.11 failure mode described in the spec — §11/§15 mandate a HIGH suggestion per flag.",
        "per_player_ratios": {
            "Plant_Height": 0.21,
            "PIF4_5_7": 0.36,
            "FLC": 0.16,
            "DELLA": 0.33,
            "Gibberellin": 0.39,
            "FT": 0.12,
            "BZR_BES": 0.36,
            "Cytokinin": 0.40,
            "miR156": 0.22,
            "Auxin": 0.38,
            "PHYB": 0.25,
            "SPL9": 0.25,
            "GID1": 0.29
        }
    }
}

LITERATURE_GAPS = [
    "DELLA -> GA20OX(+1) / GA3OX(+1) / GA2OX(-1) curated edges are absent; needed to close Motif-1 Perception Gate for Gibberellin (Zentella 2007 Plant Cell).",
    "BR catabolism genes (BAS1, CYP72C1, CYP734A1) are absent; Motif-4 Biosynthesis-Degradation Balance is incomplete for Brassinosteroid.",
    "ABA catabolism (CYP707A1/2) is absent; Motif-4 incomplete for ABA.",
    "Auxin conjugation/degradation (GH3, DAO, ILL5) is absent; Motif-4 incomplete for Auxin.",
    "Ethylene signaling-to-DELLA stabilization (EIN3->RGA/GAI) documented in Achard 2003/2007 but not curated; currently ethylene only routes to Plant_Height via EIN3 without DELLA integration."
]


# ---------------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------------
per_node_audit = []
seen = set()
for tup in PER_NODE:
    node = tup[0]
    if node in seen:
        continue
    seen.add(node)
    per_node_audit.append({
        "node": node,
        "inputs": tup[1],
        "outputs": tup[2],
        "curated_regulators_excluded": tup[3],
        "verdict": tup[4],
        "comment": tup[5]
    })

# Compute verdict
high_count = sum(1 for s in SUGGESTIONS if s["priority"] == "high")
med_count  = sum(1 for s in SUGGESTIONS if s["priority"] == "medium")
low_count  = sum(1 for s in SUGGESTIONS if s["priority"] == "low")
if high_count >= 1 or med_count >= 3:
    verdict = "iterate"
else:
    verdict = "approved"

mean_score = round(sum(v["score"] for v in RUBRIC.values()) / len(RUBRIC), 2)

review = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "phenotype_node": "Plant_Height",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
        "iteration": 1,
        "judge_model": "Claude Opus 4.7"
    },
    "verdict": verdict,
    "summary": (
        f"Iteration-1 network is mechanistically solid on the hormone-signaling side "
        f"(GA, BR, auxin, CK, ethylene, ABA all well-wired with proper Perception Gates "
        f"and DELLA Multi-Output Scaffold), but systematically thin on flowering / age / "
        f"light-time biology: photoperiod (CO/GI/FT), autonomous (FCA/FPA/FLD/FVE), "
        f"vernalization PRC2, and the age miR172/AP2 arm are all missing or fragmentary. "
        f"Strigolactone pathway is absent entirely. FLC, FT, miR156, PHYB, SPL9 all flagged "
        f"as §9.11 key-player under-representation (ratio < 0.30). Mean rubric score {mean_score}/5. "
        f"Verdict: iterate — apply HIGH priority suggestions (S001-S007) first."
    ),
    "rubric_scores": RUBRIC,
    "per_node_audit": per_node_audit,
    "per_pathway_audit": PER_PATHWAY,
    "suggestions": SUGGESTIONS,
    "literature_gaps": LITERATURE_GAPS,
    "stop_reason": None,
    "suggestion_counts": {
        "high": high_count,
        "medium": med_count,
        "low": low_count,
        "total": len(SUGGESTIONS)
    },
    "key_player_under_representation_flags": [
        {"node": "FLC", "curated": 19, "network": 3, "ratio": 0.16},
        {"node": "FT", "curated": 16, "network": 2, "ratio": 0.12},
        {"node": "miR156", "curated": 9, "network": 2, "ratio": 0.22},
        {"node": "PHYB", "curated": 8, "network": 2, "ratio": 0.25},
        {"node": "SPL9", "curated": 8, "network": 2, "ratio": 0.25},
        {"node": "GID1", "curated": 7, "network": 2, "ratio": 0.29,
         "note": "Defensible — composite collapsed GID1A/B/C"},
        {"node": "Plant_Height", "curated": 42, "network": 9, "ratio": 0.21,
         "note": "Mostly defensible — 33 excluded direct edges correctly re-routed "
                 "through master TFs (DELLA/BZR/ARF/PIF/ARR1/EIN3/ABI5/FT/SPL9). "
                 "Only SL and HY5 integrators are genuine gaps."}
    ]
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(review, f, indent=2, ensure_ascii=False)

print(f"Wrote {OUT}")
print(f"Verdict: {verdict}")
print(f"Mean score: {mean_score}")
print(f"Suggestions: {high_count} HIGH / {med_count} MEDIUM / {low_count} LOW")
