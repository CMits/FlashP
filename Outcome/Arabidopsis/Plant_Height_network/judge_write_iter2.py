"""
Emit judge_review_iteration_2.json for the Plant_Height network iteration 2.

Network state: 71 nodes, 89 edges, 20 sources (28.2%), coverage 145/244 (59%).
Iter-1 HIGH suggestions (S001-S007) all addressed; MEDIUM S008-S012 applied.
Mechanism-annotation S013/S014 deferred; literature_gap S015/S016 forwarded.

Per Anti-Pattern 5 ("Rubber-stamping iteration 2"), we re-run the full rubric,
not just check that iter-1 items were applied. New issues surfaced by the
iteration-2 network are flagged fresh.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "network" / "judge_review_iteration_2.json"


# ---------------------------------------------------------------------------
# Rubric scores - compared to iter 1 in deltas
# ---------------------------------------------------------------------------
RUBRIC = {
    "pathway_completeness": {
        "score": 4,
        "previous_score": 2,
        "justification": "Substantial improvement from iter 1. Photoperiod (GI/FKF1/CO->FT), autonomous (AUT_SYN->FLC), vernalization PRC2 composite, age miR172/AP2_TOE arm, ambient-temperature SVP/FLM, Evening Complex, HY5/COP1 light-inhibition, T6P sugar arm, and a minimal Strigolactone branch are all now present. Remaining gap: SL Perception Gate is truncated (D14/MAX2/SMXL6_7_8 not added) — SL currently runs SL_SYN->Strigolactone->Plant_Height as a two-step shortcut rather than the full receptor gate. Score capped at 4 until SL gate completion."
    },
    "mechanistic_depth": {
        "score": 4,
        "previous_score": 4,
        "justification": "Cascades remain strong. New additions follow layered structure: Light->FKF1->CO->FT, PHYB->COP1->HY5->Plant_Height, SPL9->miR172->AP2_TOE->FT, TPS1->T6P->FT/miR156. SPL9->Plant_Height direct edge still retained as coherent feed-forward with the new miR172/AP2_TOE arm — acceptable but could be reviewed."
    },
    "motif_coverage": {
        "score": 4,
        "previous_score": 4,
        "justification": "Unchanged — all hormone-signaling motifs remain correctly applied. Evening Complex added as proper parallel repressor of PIFs (adds to Motif 5 multi-output context for PIF4_5_7's 6 regulators). Multi-Output Scaffold now applied to PHYB (3 outgoing: PIF4_5_7, CO, COP1). Perception Gate for SL is INCOMPLETE — hormone has 1 outgoing (->Plant_Height direct) without a receptor intermediate, which is simpler than SL biology actually warrants. Score capped at 4 until SL gate applied."
    },
    "cascade_balance": {
        "score": 4,
        "previous_score": 3,
        "justification": "Source % improved from 19.2 to 28.2%, approaching the 30-50% target. No overloaded hubs (FT at 7 inputs is at cap but not over; PIF4_5_7 at 6 inputs). Phenotype 5 activators + 6 inhibitors (both within caps). Still slightly below target source % but not a hard failure."
    },
    "composite_node_handling": {
        "score": 5,
        "previous_score": 5,
        "justification": "New iter-2 composites (AUT_SYN, PRC2, AP2_TOE, EC, SL_SYN, FLOWER_INT) all follow §9.3 criteria: functionally redundant paralogs, same downstream target, same direction. Naming (ALL_CAPS for PROTEIN_COMPLEX) consistent. No over-collapsing observed."
    },
    "hub_completeness": {
        "score": 4,
        "previous_score": 2,
        "justification": "Major hubs dramatically improved. FLC now 5 inputs (VIN3, FRI, AUT_SYN, PRC2 composites) covering all three canonical FLC-control arms; coverage 0.26 is explained by composite collapse (true per-paralog coverage higher). FT now 7 inputs (FLC, CO, GI, AP2_TOE, SVP, FLM, T6P) — all canonical arms. PHYB now 3 outputs (PIF4_5_7, CO, COP1) covering its main function. Remaining: COOLAIR lncRNA and LDL1 excluded from FLC regulators (minor); TEM1/H2A_Z excluded from FT."
    },
    "topology_hazards": {
        "score": 3,
        "previous_score": 3,
        "justification": "Unchanged from iter 1 — iter-1 S013 (Gibberellin->GAox bypass Trap-5 disclosure) and S014 (Auxin->IPT, ABA->GA20OX bypass annotations) were DEFERRED, not applied. The mechanism fields on these edges still lack the Trap-5 caveat. No new hazards introduced by iter-2 additions. New Perception Gate for SL is structurally absent (not a hazard, but motif non-application) — SL_SYN->Strigolactone->Plant_Height is a clean shortcut without a receptor whose KO would need special handling. Promote S013/S014 to MEDIUM this iteration."
    },
    "evidence_quality": {
        "score": 4,
        "previous_score": 4,
        "justification": "All 89 edges have DOIs (QA check 2 PASS). Composite edges use representative-paralog evidence with fallbacks documented in build log. Mechanism strings remain specific and carried through from curated_edges.json."
    },
    "phenotype_audit": {
        "score": 5,
        "previous_score": 4,
        "justification": "Plant_Height now has 5 activators (PIF4_5_7, BZR_BES, ARF6_7_8, ARR1, Strigolactone) — exactly at §10 cap of 5. 6 inhibitors (SPL9, DELLA, EIN3, ABI5, FLOWER_INT, HY5) — within 5-7 target. All major effector classes represented: light TFs (PIF4_5_7, HY5), hormone TFs (BZR_BES, ARF6_7_8, ARR1, EIN3, ABI5), hormone integrator (DELLA), age integrator (SPL9), flowering integrator (FLOWER_INT), and hormone (Strigolactone). Balance 5 promoting / 6 repressing is appropriate for a growth phenotype where constraints are more common than drivers."
    },
    "rejected_edges_review": {
        "score": 4,
        "previous_score": 3,
        "justification": "99 curated edges rejected out of 244 (40.6%), down from 149 in iter 1. Of remaining rejections: ~30 are Plant_Height direct bypasses correctly re-routed through TF integrators (defensible — §9.11 §15 allows rerouting); ~20 are intra-composite edges (defensible — composite collapse); ~20 are peripheral SPL3/SPL15 family / PIN1 / Auxin_Transport / BP/STM which simply aren't instantiated as nodes (defensible — minor pathways). Residual silent drops: CO robustness regulators (ZTL, CDF1, phyA), COOLAIR lncRNA, LDL1, H2A_Z/TEM1 — see S101-S104."
    },
    "key_player_density": {
        "score": 4,
        "previous_score": 2,
        "justification": "Of 9 remaining flagged nodes, 7 are explained by composite collapse: AUT_SYN (6 paralogs collapsed), PRC2 (4 paralogs), AP2_TOE (4 paralogs), FLOWER_INT (3 paralogs), EC (3 paralogs), SL_SYN (4 paralogs), GID1 (3 paralogs). Per §9.11 this is documented-reason lower coverage, not silent under-representation. Genuine under-representation: Strigolactone (0.25 coverage, no D14/MAX2/SMXL added) and Plant_Height (0.26 coverage, but most remainder is legitimately TF-rerouted). Score 4: the legitimate §9.11 concerns have been addressed; residual is mostly composite-explained or genuinely low-priority.",
        "per_player_ratios": {
            "Plant_Height": 0.26,
            "PIF4_5_7": 0.41,
            "FLC": 0.26,
            "Gibberellin": 0.39,
            "DELLA": 0.39,
            "FT": 0.50,
            "FLOWER_INT": 0.18,
            "BZR_BES": 0.45,
            "AP2_TOE": 0.18,
            "Cytokinin": 0.40,
            "miR172": 0.20,
            "miR156": 0.33,
            "Strigolactone": 0.25,
            "EC": 0.12,
            "Auxin": 0.38,
            "PHYB": 0.50,
            "SPL9": 0.38,
            "AUT_SYN": 0.14,
            "GID1": 0.29,
            "CO": 0.50,
            "SL_SYN": 0.20,
            "PRC2": 0.25
        }
    }
}


# ---------------------------------------------------------------------------
# Per-pathway audit (fresh, post-iter 2)
# ---------------------------------------------------------------------------
PER_PATHWAY = [
    {"pathway": "Gibberellin (biosynthesis / signaling / catabolism)",
     "completeness": "high",
     "comment": "Unchanged and still strong. SPY->DELLA added in iter 2 (S012) completes GA-independent DELLA activator arm. Gibberellin bypass edges on GA20OX/GA3OX/GA2OX remain unannotated — S013 carries over.",
     "missing_pieces": ["DELLA->GA20OX(+1)/GA3OX(+1)/GA2OX(-1) (literature_gap)",
                        "CPS/KS/KO/KAO early-biosynthesis (low priority)"]},
    {"pathway": "Brassinosteroid signaling",
     "completeness": "high",
     "comment": "PP2A->BZR_BES added in iter 2 (S011). Symmetric BIN2(-)/PP2A(+) on BZR_BES now modelled. Missing: SL-BR crosstalk MAX2->BES1 (E127) — see S101.",
     "missing_pieces": ["MAX2->BZR_BES (E127) as SL-BR crosstalk"]},
    {"pathway": "Auxin signaling",
     "completeness": "medium",
     "comment": "Unchanged from iter 1. Auxin->IPT crosstalk is a mild gate bypass (S014 deferred).",
     "missing_pieces": ["S014 mechanism annotation"]},
    {"pathway": "Cytokinin biosynthesis-signaling",
     "completeness": "high",
     "comment": "Unchanged from iter 1. Motif 4 applied cleanly.",
     "missing_pieces": []},
    {"pathway": "Ethylene signaling",
     "completeness": "high",
     "comment": "Unchanged.",
     "missing_pieces": []},
    {"pathway": "ABA signaling",
     "completeness": "high",
     "comment": "Unchanged. ABA->GA20OX crosstalk annotation (S014) still deferred.",
     "missing_pieces": ["S014 mechanism annotation"]},
    {"pathway": "Strigolactone signaling",
     "completeness": "low",
     "comment": "IMPROVED from 'absent' to 'low': SL_SYN->Strigolactone->Plant_Height minimal branch added (S007 partial). Still missing Perception Gate: D14, MAX2 co-receptors and SMXL6_7_8 repressor node. Without the gate, signaling mutants (d14, max2) will be mispredicted; the SL branch behaves like a pure hormone-level input with no Trap-5 immunity. BUILDER documented that SMXL6_7_8 has no curated downstream to Plant_Height, which is a real literature_gap. Can still wire MAX2 with MAX2->BZR_BES (-1) (E127) giving an on-cascade output for MAX2 through BR; SMXL6_7_8 becomes a dead-end handled like SPL9 was in iter 1.",
     "missing_pieces": ["D14 (GENE)", "MAX2 (GENE, source)", "SMXL6_7_8 (PROTEIN_COMPLEX)",
                        "SL->D14 (E213)", "D14->MAX2 (E214)", "MAX2->SMXL6_7_8 (-1, E215)",
                        "MAX2->BZR_BES (-1, E127) SL-BR crosstalk"]},
    {"pathway": "Light / PHYB / shade avoidance",
     "completeness": "high",
     "comment": "IMPROVED: Evening Complex (EC) added as repressor of PIF4_5_7. HY5/COP1 branch added. PHYB now has 3 outputs. Residual: ZTL/CDF1/phyA regulators of CO are missing — see S102.",
     "missing_pieces": ["ZTL->CO (-1)", "CDF1->CO (-1)", "phyA->CO (+1) (see S102)"]},
    {"pathway": "Photoperiod (CO/GI/FKF1/CDF1->FT)",
     "completeness": "medium",
     "comment": "IMPROVED from 'absent' to 'medium': GI, FKF1, CO added with GI->FKF1, FKF1->CO, GI->FT, CO->FT, PHYB->CO. Residual: ZTL circadian F-box (E143), CDF1 (E141 as FKF1 target), phyA (E132 phyA->CO). These fine-tune photoperiod sensitivity but the core circuit is now present.",
     "missing_pieces": ["ZTL->CO (E143)", "CDF1->CO (E141)", "phyA->CO (E132)"]},
    {"pathway": "Vernalization (FRI/FLC/VIN3/PRC2/COOLAIR)",
     "completeness": "high",
     "comment": "IMPROVED from 'low' to 'high': PRC2 composite added. Only COOLAIR lncRNA remains missing (S104).",
     "missing_pieces": ["COOLAIR->FLC (E158)"]},
    {"pathway": "Autonomous (FCA/FPA/FLD/FVE/LD/FY -> FLC)",
     "completeness": "high",
     "comment": "IMPROVED from 'absent' to 'high': AUT_SYN composite added. LDL1 (E045) missing — small arm of histone demethylation; see S104.",
     "missing_pieces": ["LDL1->FLC (E045)"]},
    {"pathway": "Age (miR156/SPL/miR172/AP2-TOE)",
     "completeness": "high",
     "comment": "IMPROVED from 'low' to 'high': miR172 (REGULATORY_RNA) and AP2_TOE composite added. Age cascade Sucrose-|miR156-|SPL9->miR172-|AP2_TOE-|FT is now complete. T6P-|miR156 parallel repression added. Direct SPL9->Plant_Height retained as feed-forward.",
     "missing_pieces": []},
    {"pathway": "Ambient temperature (SVP/FLM/H2A_Z -> FT)",
     "completeness": "high",
     "comment": "IMPROVED: SVP->FT and FLM->FT added. ARP6/H2A_Z chromatin arm still missing (minor).",
     "missing_pieces": ["ARP6->H2A_Z->FT (E148, E150)"]},
    {"pathway": "Flowering integrators (SOC1/LFY/AP1)",
     "completeness": "high",
     "comment": "FLOWER_INT composite added between FT and Plant_Height. FT->Plant_Height direct replaced with FT->FLOWER_INT->Plant_Height. Loss of mutant-level resolution between SOC1/LFY/AP1 individually, but composite approach is justified for a height model.",
     "missing_pieces": []},
    {"pathway": "Sugar / T6P",
     "completeness": "high",
     "comment": "IMPROVED: TPS1->T6P->FT and T6P-|miR156 added. Two parallel sugar-to-flowering routes now modelled.",
     "missing_pieces": []},
    {"pathway": "Shoot apical meristem (BP/STM)",
     "completeness": "absent",
     "comment": "Not previously flagged. BP->Plant_Height (E226) curated; STM->BP (E227) curated. Low priority for plant height since BP/STM primarily affect meristem identity.",
     "missing_pieces": ["BP (GENE)", "STM (GENE)", "BP->Plant_Height (E226)", "STM->BP (E227)"]},
]


# ---------------------------------------------------------------------------
# Suggestions for iteration 3
# ---------------------------------------------------------------------------
SUGGESTIONS = [
    {
        "id": "S101",
        "type": "restructure_pathway",
        "priority": "medium",
        "description": "Complete the Strigolactone Perception Gate by adding D14 (GENE), MAX2 (GENE, source), and SMXL6_7_8 (PROTEIN_COMPLEX). Wire Strigolactone->D14(+1), D14->MAX2(+1), MAX2->SMXL6_7_8(-1), and add MAX2->BZR_BES(-1) as the SL-BR crosstalk on-cascade output. Keep Strigolactone->Plant_Height(+1) direct if biology supports it.",
        "biological_justification": "Currently SL is a minimal shortcut (SL_SYN->Strigolactone->Plant_Height) without a receptor gate. SL-signaling mutants (d14, max2) will be mispredicted because exogenous SL treatment passes straight to Plant_Height without needing D14/MAX2 function (Trap 5). Adding the gate with MAX2->BZR_BES (-1) as a downstream on-cascade edge gives MAX2 a real function and makes max2 KO affect growth through BR. SMXL6_7_8 can be included as a dead-end node with an attached literature_gap for its missing Plant_Height output (for BRC1/grass context).",
        "curated_edge_ids": ["E213", "E214", "E215", "E216", "E127"],
        "pathway_name": "Strigolactone Perception Gate completion",
        "implementation": "Add 3 nodes: D14 (GENE), MAX2 (GENE, source, constitutive F-box), SMXL6_7_8 (PROTEIN_COMPLEX composite of SMXL6/7/8). Add edges: Strigolactone->D14(+1, E213), D14->MAX2(+1, E214), MAX2->SMXL6_7_8(-1, E215 as rep), MAX2->BZR_BES(-1, E127). Flag SMXL6_7_8 as floating-adjacent since it has no on-cascade output — either remove after add (auto-fixable) OR add a speculative SMXL6_7_8->Plant_Height(-1) with literature_gap flag."
    },
    {
        "id": "S102",
        "type": "add_edge",
        "priority": "medium",
        "description": "Complete CO photoperiod robustness: ZTL->CO(-1), CDF1->CO(-1), phyA->CO(+1).",
        "biological_justification": "ZTL is the dark-phase F-box that degrades CO protein; CDF1 is the transcriptional repressor of CO that FKF1 targets; phyA activates CO under far-red. Currently CO has only FKF1(+) and PHYB(-) - the nighttime degradation (ZTL) and baseline repression (CDF1) arms are missing. These edges make ztl, cdf1, phya mutants predictable.",
        "curated_edge_ids": ["E132", "E133", "E136"],
        "implementation": "Add 3 nodes: ZTL (GENE, source), CDF1 (GENE), phyA (GENE). Edges: ZTL->CO(-1, E143), CDF1->CO(-1, E141), phyA->CO(+1, E136), FKF1->CDF1(-1, E141) so CDF1 has an incoming regulator. CDF1 is also activated by GI in curated (optional). Alternative compact version: add ZTL and phyA only, skip CDF1."
    },
    {
        "id": "S103",
        "type": "mechanism_improvement",
        "priority": "medium",
        "description": "Apply S013/S014 mechanism annotations (Trap-5 disclosures on Gibberellin->GAox, Auxin->IPT, ABA->GA20OX bypass edges).",
        "biological_justification": "Deferred in iteration 2. These edges still violate Motif 1 Perception Gate purity. Annotating the mechanism field with a Trap-5 disclosure is a zero-structural-risk admin fix that documents the known limitation for downstream readers and preserves current topology. §9.7 topology_hazards score stuck at 3 until this is done.",
        "curated_edge_ids": ["E063", "E065", "E054", "E190"],
        "target_edge": "Gibberellin->GA20OX(-1), Gibberellin->GA3OX(-1), Gibberellin->GA2OX(+1), Auxin->IPT(-1), ABA->GA20OX(-1)",
        "proposed_mechanism": "Append to each: '[Framework note: Motif 1 purity compromise — this is a direct hormone->enzyme transcriptional feedback that biologically runs through DELLA (GA) or ARF/ABI5 (Auxin/ABA) but those intermediate curated edges are absent. Exogenous-hormone in receptor-KO backgrounds will still modulate this target — a known Trap-5 limitation.]'",
        "implementation": "Edit the 5 mechanism fields in network.json directly; no structural change."
    },
    {
        "id": "S104",
        "type": "add_edge",
        "priority": "medium",
        "description": "Add COOLAIR lncRNA and LDL1 to FLC repression arms.",
        "biological_justification": "COOLAIR is a cold-induced lncRNA that cotranscriptionally silences FLC (parallel to PRC2). LDL1 is an LSD1-like histone demethylase active on the FLC locus (part of autonomous pathway but demethylation-based). Both improve FLC control fidelity. LDL1 could fold into AUT_SYN composite; COOLAIR must be a separate REGULATORY_RNA.",
        "curated_edge_ids": ["E158", "E045"],
        "implementation": "Add COOLAIR (REGULATORY_RNA, source or driven by Cold_Vernalization->COOLAIR if curated). Edge COOLAIR->FLC(-1, E158). Expand AUT_SYN composite to include LDL1 OR add LDL1 (GENE, source)->FLC(-1, E045)."
    },
    {
        "id": "S105",
        "type": "literature_gap",
        "priority": "low",
        "description": "SMXL6_7_8 -> Plant_Height direct edge is absent from curated_edges.json for Arabidopsis height context. In rice and Arabidopsis branching, SMXL6 -> BRC1 (-1) is documented; for height, SMXL6_7_8 output would need Step 1 literature search on 'SMXL primary stem elongation' or 'smxl678 plant stature'.",
        "biological_justification": "Needed to close SL Perception Gate if SMXL6_7_8 is added as part of S101. Without this edge, SMXL6_7_8 is a dead-end floating node.",
        "curated_edge_ids": [],
        "implementation": "Step 1 LITERATURE REVIEW extension. Search terms: 'SMXL6 SMXL7 SMXL8 plant height Arabidopsis', 'smxl678 stature elongation'."
    },
    {
        "id": "S106",
        "type": "add_node",
        "priority": "low",
        "description": "Add BP (BREVIPEDICELLUS) and STM (SHOOT MERISTEMLESS) meristem-identity branch.",
        "biological_justification": "BP->Plant_Height(+1) (E226) is curated; STM->BP(+1) (E227) provides the SAM-identity upstream. Not critical for height in Arabidopsis (primary effect is on meristem) but completes the set of curated Plant_Height inputs.",
        "curated_edge_ids": ["E226", "E227"],
        "implementation": "Add BP (GENE), STM (GENE, source). Edges: STM->BP(+1, E227), BP->Plant_Height(+1, E226). Note: this adds a 6th activator on Plant_Height which exceeds §10 cap of 5 — requires re-routing OR composite or skipping."
    },
    {
        "id": "S107",
        "type": "literature_gap",
        "priority": "low",
        "description": "Add early GA biosynthesis (CPS/KS/KO/KAO) as composite GA_UPSTREAM or as rate-limiting flag. Currently composite GA20OX covers only the late GA20ox steps.",
        "biological_justification": "For ga1 (= CPS) and other early-biosynthesis mutants, the network needs an upstream node. Composite GA_UPSTREAM (CPS+KS+KO+KAO) -> GA20OX (+1) would give those mutants a path. Currently those 4 curated edges are rejected.",
        "curated_edge_ids": ["E046", "E047", "E048", "E049"],
        "implementation": "Add GA_UPSTREAM (PROTEIN_COMPLEX, source) with GA_UPSTREAM->GA20OX(+1). Alternative: leave ga1 KO unmodelable and note as limitation."
    }
]

LITERATURE_GAPS = [
    "SMXL6_7_8 -> Plant_Height direct edge (for height phenotype context) - required to close SL Perception Gate output; see S105.",
    "DELLA -> GA20OX/GA3OX/GA2OX feedback edges remain uncurated; carried over from iter 1.",
    "BR catabolism (BAS1/CYP72C1) remains absent; carried over.",
    "ABA catabolism (CYP707A) remains absent; carried over.",
    "Auxin conjugation/degradation (GH3/DAO) remains absent; carried over.",
    "CDF1 transcriptional activation by GI (for S102): confirm curated_edge E141 covers FKF1-|CDF1; if not, need GI->CDF1 search."
]


# ---------------------------------------------------------------------------
# Per-node audit (concise — 71 nodes)
# New audit entries for iter-2-added nodes are flagged; unchanged nodes get
# short confirmations.
# ---------------------------------------------------------------------------
# For brevity, we generate this programmatically from the network file.
with open(ROOT / "network" / "network.json", encoding="utf-8") as f:
    NET = json.load(f)

net_out = {}
net_in = {}
for e in NET["edges"]:
    net_out.setdefault(e["source"], []).append((e["target"], e["sign"]))
    net_in.setdefault(e["target"], []).append((e["source"], e["sign"]))

# Nodes that are new in iter 2
NEW_IN_ITER_2 = {"GI", "FKF1", "CO", "AUT_SYN", "PRC2", "miR172", "AP2_TOE",
                 "SVP", "FLM", "EC", "SL_SYN", "Strigolactone", "FLOWER_INT",
                 "COP1", "HY5", "TPS1", "T6P", "PP2A", "SPY"}

# Quick verdict lookup for nodes with remaining comment-worthy issues
FLAGS_ITER2 = {
    "Gibberellin": ("topology_hazard_carried_over",
                    "Gibberellin->GA20OX/GA3OX/GA2OX bypass edges still unannotated (S103)."),
    "Auxin": ("topology_hazard_carried_over",
              "Auxin->IPT bypass still unannotated (S103)."),
    "ABA": ("topology_hazard_carried_over",
            "ABA->GA20OX bypass still unannotated (S103)."),
    "Strigolactone": ("under-specified",
                      "Direct shortcut to Plant_Height without Perception Gate. See S101."),
    "SL_SYN": ("appropriate_minimal",
               "Composite biosynthesis source; minimal branch as agreed in iter 2."),
    "CO": ("under-specified",
           "Only FKF1(+) and PHYB(-) inputs; missing ZTL, CDF1, phyA (S102)."),
    "FLC": ("appropriate_composite",
            "5 inputs via AUT_SYN + PRC2 + VIN3 + FRI. Coverage ratio 0.26 explained by composite collapse. COOLAIR/LDL1 still missing (S104)."),
    "FT": ("appropriate",
           "7 inputs (cap): FLC, CO, GI, AP2_TOE, SVP, FLM, T6P. All canonical arms present. Minor H2A_Z/TEM1 omissions."),
    "SPL9": ("appropriate_feed_forward",
             "Both Plant_Height direct (coherent feed-forward) and miR172 output present."),
}

per_node_audit = []
for node in NET["nodes"]:
    nid = node["id"]
    ins = net_in.get(nid, [])
    outs = net_out.get(nid, [])
    ins_list = [f"{s}({'+' if sg==1 else '-'})" for s, sg in ins] or ["(source)"]
    outs_list = [f"{t}({'+' if sg==1 else '-'})" for t, sg in outs] or ["(leaf)"]
    if nid in FLAGS_ITER2:
        verdict, comment = FLAGS_ITER2[nid]
    elif nid in NEW_IN_ITER_2:
        verdict = "appropriate_new_in_iter_2"
        comment = f"Added in iter 2. In-degree {len(ins)}, out-degree {len(outs)}. No new concerns."
    else:
        verdict = "appropriate"
        comment = "Unchanged from iter 1; no new concerns."
    per_node_audit.append({
        "node": nid,
        "inputs": ins_list,
        "outputs": outs_list,
        "verdict": verdict,
        "comment": comment
    })


# ---------------------------------------------------------------------------
# Compute verdict
# ---------------------------------------------------------------------------
high_count = sum(1 for s in SUGGESTIONS if s["priority"] == "high")
med_count  = sum(1 for s in SUGGESTIONS if s["priority"] == "medium")
low_count  = sum(1 for s in SUGGESTIONS if s["priority"] == "low")

if high_count >= 1 or med_count >= 3:
    verdict = "iterate"
else:
    verdict = "approved"

mean_score = round(sum(v["score"] for v in RUBRIC.values()) / len(RUBRIC), 2)
prev_mean = round(sum(v.get("previous_score", v["score"]) for v in RUBRIC.values()) / len(RUBRIC), 2)

# ---------------------------------------------------------------------------
# Key-player flags (composite-aware, documented reasons)
# ---------------------------------------------------------------------------
KEY_PLAYER_FLAGS = [
    {"node": "Strigolactone", "curated": 8, "network": 2, "ratio": 0.25,
     "status": "genuine_under_representation",
     "note": "SL Perception Gate truncated - see S101."},
    {"node": "Plant_Height", "curated": 42, "network": 11, "ratio": 0.26,
     "status": "defensible_rerouted",
     "note": "Most excluded direct edges correctly re-routed through TF integrators (DELLA/BZR/ARF/PIF/ARR1/EIN3/ABI5/FLOWER_INT/HY5/SPL9)."},
    {"node": "FLC", "curated": 19, "network": 5, "ratio": 0.26,
     "status": "defensible_composite",
     "note": "AUT_SYN(6 paralogs) + PRC2(4 paralogs) composites explain collapsed coverage."},
    {"node": "AP2_TOE", "curated": 11, "network": 2, "ratio": 0.18,
     "status": "defensible_composite",
     "note": "Composite of 4 AP2-like TFs."},
    {"node": "FLOWER_INT", "curated": 11, "network": 2, "ratio": 0.18,
     "status": "defensible_composite",
     "note": "Composite of SOC1/LFY/AP1."},
    {"node": "EC", "curated": 8, "network": 1, "ratio": 0.12,
     "status": "defensible_composite",
     "note": "Composite of ELF3/ELF4/LUX; direct EC-to-Plant_Height edges routed via PIF4_5_7."},
    {"node": "miR172", "curated": 10, "network": 2, "ratio": 0.20,
     "status": "defensible_composite",
     "note": "Multiple AP2-like targets collapsed into AP2_TOE composite."},
    {"node": "AUT_SYN", "curated": 7, "network": 1, "ratio": 0.14,
     "status": "defensible_composite",
     "note": "Composite of 6 autonomous-pathway paralogs."},
    {"node": "SL_SYN", "curated": 5, "network": 1, "ratio": 0.20,
     "status": "defensible_composite",
     "note": "Composite of D27/MAX1/MAX3/MAX4."},
    {"node": "GID1", "curated": 7, "network": 2, "ratio": 0.29,
     "status": "defensible_composite",
     "note": "Composite of GID1A/B/C."},
]


review = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "phenotype_node": "Plant_Height",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
        "iteration": 2,
        "judge_model": "Claude Opus 4.7",
        "based_on_build_log": "network/build_log_iteration_2.json",
        "previous_review": "network/judge_review_iteration_1.json"
    },
    "verdict": verdict,
    "summary": (
        f"Iteration 2 is a substantial improvement over iteration 1. Mean rubric score "
        f"rose from {prev_mean} to {mean_score}. All 7 HIGH iter-1 suggestions "
        f"(photoperiod, autonomous pathway, PRC2 vernalization, age miR172/AP2_TOE, "
        f"ambient-temperature SVP/FLM, Evening Complex, Strigolactone minimal branch) "
        f"were applied, and 5 MEDIUM (FLOWER_INT integrator, HY5/COP1, T6P sugar arm, "
        f"PP2A, SPY) were applied. Key player under-representation is now mostly "
        f"composite-explained rather than silent omission. Remaining gaps: SL "
        f"Perception Gate is truncated, CO lacks 3 photoperiod robustness regulators, "
        f"Trap-5 mechanism annotations (S013/S014 carried over as S103) remain "
        f"unapplied, and COOLAIR/LDL1 minor FLC arms missing. "
        f"Verdict: iterate. {med_count} MEDIUM suggestions trigger the 3+ threshold."
    ),
    "iteration_1_compliance_check": {
        "S001_photoperiod": "applied",
        "S002_autonomous": "applied",
        "S003_PRC2": "applied",
        "S004_miR172_AP2_TOE": "applied",
        "S005_ambient_temp_SVP_FLM": "applied",
        "S006_Evening_Complex": "applied",
        "S007_Strigolactone": "partially_applied (minimal branch; no Perception Gate)",
        "S008_FLOWER_INT": "applied",
        "S009_HY5_COP1": "applied",
        "S010_T6P": "applied",
        "S011_PP2A": "applied",
        "S012_SPY": "applied",
        "S013_S014_mechanism_annotations": "deferred (carried over as S103)",
        "S015_S016_literature_gaps": "forwarded_to_step_1 (acknowledged)"
    },
    "rubric_scores": RUBRIC,
    "rubric_deltas_vs_iter_1": {
        dim: {"previous": v.get("previous_score", v["score"]),
              "current": v["score"],
              "delta": v["score"] - v.get("previous_score", v["score"])}
        for dim, v in RUBRIC.items()
    },
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
    "key_player_under_representation_flags": KEY_PLAYER_FLAGS,
    "mean_score": mean_score,
    "previous_mean_score": prev_mean
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(review, f, indent=2, ensure_ascii=False)

print(f"Wrote {OUT}")
print(f"Verdict: {verdict}  (iter 1: iterate)")
print(f"Mean score: {mean_score} (iter 1: {prev_mean}, Delta +{round(mean_score-prev_mean,2)})")
print(f"Suggestions: {high_count} HIGH / {med_count} MEDIUM / {low_count} LOW")
