"""
FLASH-P v1.0 Step 2 BUILDER - Lateral_Root_Density (Arabidopsis thaliana)

ITERATION 2 - Applied JUDGE iteration_1 suggestions (see build_log_iteration_2.json)

Reads curated_edges.json (Step 1 + Step 1.5 merged) and emits:
    network/network.json
    network/algebraic_equations.json
    network/ode_equations.json
    network/node_annotations.json

All evidence is pulled FROM the curated edges (no fabrication).
Composite nodes (LBD, PLT, PIN, AHK, ARR_B, CLE, BZR, ABI4_5) reuse a
representative member's evidence entry and note composite membership.

HARD RULES honoured:
  * NO floating nodes
  * DOI on every edge
  * Fixed equation formulas
  * Did NOT read perturbation_dataset.json or any validation output

Iter-2 CHANGES vs iter-1:
  ADD GATA23 founder-cell marker + 3 edges (S001 HIGH)
  ADD WOX11 founder-to-organ transition + 2 edges (S002 HIGH) [accepts mild Auxin gate leak]
  ADD BR module (Brassinosteroid, BRI1, BIN2, BZR composite) + 4 edges (S003 HIGH)
  ADD HY5 + PHYB light-integration + 2 edges routed via ARF19 (S004 MEDIUM)
  MERGE ABI4+ABI5 into ABI4_5 composite + ABA->ABI4_5 bypass (S005 MEDIUM)
  DROP PUCHI node and 2 edges (required to fit BR under LR activator hard-cap 7)
  REJECT S007 TOLS2/RLK7/PUCHI (depends on PUCHI which was dropped - defer to iter 3)
  REJECT S008 AFB3/NAC4 (NAC4->LR would exceed LR activator cap)

Perception gates:
  * Auxin: 2 outgoing edges (TIR1 + WOX11) - minor documented leak for WOX11 founder TF
  * Cytokinin: sole outgoing to AHK
  * Ethylene: sole outgoing to EIN2
  * ABA: 2 outgoing (PYL8 + ABI4_5 composite) - minor leak for ABI5 arm
  * Brassinosteroid: sole outgoing to BRI1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CURATED_PATH = DATA / "curated_edges.json"
OUT_NETWORK = HERE / "network.json"
OUT_ALG = HERE / "algebraic_equations.json"
OUT_ODE = HERE / "ode_equations.json"
OUT_ANN = HERE / "node_annotations.json"

PHENO = "Lateral_Root_Density"

# ---------------------------------------------------------------------------
# Node catalogue
# Tuple: (id, type, full_name, description)
# ---------------------------------------------------------------------------
NODES: List[Tuple[str, str, str, str]] = [
    (PHENO, "PHENOTYPE", "Lateral root density", "Number of initiated+emerged lateral roots per unit primary-root length"),

    # Hormones
    ("Auxin", "HORMONE", "Auxin (IAA)", "Master LR-inducing hormone, perceived via TIR1/AFB. iter2: minor Perception Gate leak via Auxin->WOX11 accepted for founder-to-organ TF coverage."),
    ("Cytokinin", "HORMONE", "Cytokinin", "LR-inhibiting hormone, antagonistic to auxin"),
    ("Ethylene", "HORMONE", "Ethylene", "Gaseous hormone; net LR-inhibiting via EIN2"),
    ("ABA", "HORMONE", "Abscisic acid", "Stress hormone; represses LR via ABI4 and ABI5 (composite ABI4_5). iter2: ABA has 2 outgoing (PYL8 gate-main + ABI4_5 composite bypass for ABI5)."),
    ("GA", "HORMONE", "Gibberellin", "Modest LR-promoting via DELLA degradation"),
    ("Strigolactone", "HORMONE", "Strigolactone", "LR-inhibiting via MAX2/D14"),
    ("Brassinosteroid", "HORMONE", "Brassinosteroid (BL/EBR)", "iter2: added per JUDGE S003. Modest LR-promoting hormone; bzr1-1D and bes1-D GoF alleles increase LR."),

    # Environment
    ("Low_Nitrate", "ENVIRONMENT", "Low nitrate (<100 uM N)", "Shoot-demand N limitation; induces CLE peptides"),
    ("Low_Phosphate", "ENVIRONMENT", "Low phosphate (<10 uM P)", "P-starvation; promotes LR density via TIR1 and STOP1-ALMT1 (latter abstracted)"),

    # Auxin perception / signalling
    ("TIR1", "GENE", "TRANSPORT INHIBITOR RESPONSE 1", "F-box auxin co-receptor (SCF-TIR1) - degrades Aux/IAAs"),
    ("IAA14", "GENE", "INDOLE-3-ACETIC ACID INDUCIBLE 14 / SLR", "Dominant LR-suppressing Aux/IAA (aliases: SLR)"),
    ("IAA28", "GENE", "INDOLE-3-ACETIC ACID INDUCIBLE 28", "Aux/IAA repressor of LR founder-cell specification"),
    ("ARF7", "GENE", "AUXIN RESPONSE FACTOR 7", "LR-initiation TF, redundant with ARF19"),
    ("ARF19", "GENE", "AUXIN RESPONSE FACTOR 19", "LR-initiation TF, redundant with ARF7"),

    # LR initiation / primordium (composites)
    ("LBD", "PROTEIN_COMPLEX", "LBD16/18/29 family", "Composite of LBD16, LBD18, LBD29 (LATERAL ORGAN BOUNDARIES DOMAIN) - LR-initiation TFs; asymmetric division triggers"),
    ("PLT", "PROTEIN_COMPLEX", "PLT3/5/7 family", "Composite of PLETHORA3/5/7 - LR primordium organogenesis TFs"),
    # iter2: PUCHI dropped to free LR-activator slot for BR module (S003 HIGH). PUCHI biology overlaps with LBD composite's LR-morphogenesis role. puchi mutant maps to LBD composite member in Step 3 reconciliation.
    ("GATA23", "GENE", "GATA TRANSCRIPTION FACTOR 23", "iter2: added per JUDGE S001. Xylem-pole-pericycle founder-cell marker (De Rybel 2010)."),
    ("WOX11", "GENE", "WUSCHEL-RELATED HOMEOBOX 11", "iter2: added per JUDGE S002. Founder-to-organ transition TF (Hu 2014); parallel LBD activator alongside ARF7/ARF19."),

    # Auxin transport
    ("PIN", "PROTEIN_COMPLEX", "PIN1/2/3/7 family", "Composite of PIN-FORMED polar-auxin efflux carriers (PIN1/2/3/7)"),
    ("AUX1", "GENE", "AUXIN RESISTANT 1", "Auxin influx carrier - uptake into pericycle/emerging primordium"),
    ("LAX3", "GENE", "LIKE AUX1 3", "Auxin influx carrier induced in endodermis/cortex during LR emergence"),

    # Auxin biosynthesis / degradation
    ("TAA1", "GENE", "TRYPTOPHAN AMINOTRANSFERASE OF ARABIDOPSIS 1", "IPA biosynthesis step (Trp to IPA); rate-limiting for local IAA production"),
    ("TAR2", "GENE", "TRYPTOPHAN AMINOTRANSFERASE RELATED 2", "TAA1 paralog; N- and ethylene-induced auxin biosynthesis"),
    ("YUC4", "GENE", "YUCCA 4", "Flavin monooxygenase converting IPA to IAA (represents YUC family)"),
    ("GH3", "GENE", "GRETCHEN HAGEN 3 (composite)", "IAA-amino-acid conjugation - auxin inactivation"),
    ("DAO1", "GENE", "DIOXYGENASE FOR AUXIN OXIDATION 1", "Oxidative IAA catabolism"),

    # Cytokinin module
    ("AHK", "PROTEIN_COMPLEX", "AHK2/3/4 receptor family", "Composite of AHK2, AHK3, AHK4/CRE1 cytokinin receptors"),
    ("ARR_B", "PROTEIN_COMPLEX", "ARR1/10/12 type-B ARR family", "Composite of type-B response regulators ARR1, ARR10, ARR12"),
    ("IPT5", "GENE", "ISOPENTENYLTRANSFERASE 5", "CK biosynthesis (represents IPT3/5/7 family)"),
    ("CKX2", "GENE", "CYTOKININ OXIDASE 2", "CK degradation (represents CKX1-7 family)"),

    # Nitrate signalling
    ("CHL1", "GENE", "CHLORATE RESISTANT 1 / NRT1.1 / NPF6.3", "Dual nitrate transceptor; drives NLP7/ANR1 and TAR2 modulation (aliases: NRT1.1, NPF6.3)"),
    ("NLP7", "GENE", "NIN-LIKE PROTEIN 7", "Master nitrate-response TF; relays CHL1 signal to ANR1"),
    ("ANR1", "GENE", "ARABIDOPSIS NITRATE REGULATED 1", "MADS TF required for LR elongation into nitrate-rich patches"),

    # CLE-CLV feedback
    ("CLE", "PROTEIN_COMPLEX", "CLE1/3/4/7 peptide family", "Composite of shoot-demand-N-responsive CLE peptides"),
    ("CLV1", "GENE", "CLAVATA 1", "LRR-RLK receiving phloem CLE peptides in pericycle; represses LR"),

    # Ethylene
    ("EIN2", "GENE", "ETHYLENE INSENSITIVE 2", "Central ethylene signalling integrator"),
    ("CTR1", "GENE", "CONSTITUTIVE TRIPLE RESPONSE 1", "Raf-like kinase repressing EIN2 in absence of ethylene"),
    ("ACS", "GENE", "ACC SYNTHASE (composite)", "Rate-limiting ethylene biosynthesis"),
    ("ACO", "GENE", "ACC OXIDASE (composite)", "Final step ethylene biosynthesis"),

    # ABA
    ("PYL8", "GENE", "PYR1-LIKE 8 / RCAR3", "ABA receptor (represents PYR/PYL/RCAR)"),
    ("ABI1", "GENE", "ABSCISIC ACID INSENSITIVE 1 (composite PP2C)", "PP2C phosphatase repressing SnRK2 (represents ABI1/ABI2/HAB1/HAB2)"),
    ("SNRK2", "GENE", "SNF1-RELATED PROTEIN KINASE 2 (composite)", "SnRK2 kinase activating ABF/ABI TFs"),
    ("ABI4_5", "PROTEIN_COMPLEX", "ABI4/ABI5 composite TFs", "iter2: composite of ABI4 (AP2/ERF) + ABI5 (bZIP) per JUDGE S005. Both are ABA-responsive LR repressors activated by SnRK2; ABI5 arm is SnRK2->ABI5 not in curated so we use ABA->ABI4_5 bypass supplementing the gate-pure SnRK2->ABI4_5 arm."),

    # GA
    ("DELLA", "GENE", "DELLA family", "Composite of RGA/GAI/RGL1-3 - GA-destabilised repressors"),

    # Strigolactone
    ("D14", "GENE", "DWARF14 / AtD14", "SL receptor"),
    ("MAX2", "GENE", "MORE AXILLARY GROWTH 2", "F-box protein for SL signalling"),
    ("MAX1", "GENE", "MAX1 (CYP711A1)", "SL biosynthesis"),
    ("MAX3", "GENE", "MAX3 (CCD7)", "SL biosynthesis - carotenoid cleavage"),
    ("MAX4", "GENE", "MAX4 (CCD8)", "SL biosynthesis - carotenoid cleavage"),

    # iter2: Brassinosteroid module (JUDGE S003 HIGH)
    ("BRI1", "GENE", "BRASSINOSTEROID INSENSITIVE 1", "iter2: BR receptor kinase; sole outgoing from Brassinosteroid."),
    ("BIN2", "GENE", "BRASSINOSTEROID INSENSITIVE 2", "iter2: GSK3-like kinase; phosphorylates BZR1/BES1 for destabilisation; repressed by BRI1-BAK1 activation."),
    ("BZR", "PROTEIN_COMPLEX", "BZR1/BES1 composite", "iter2: composite of BZR1 + BES1 (paralogous BR-responsive TFs); bzr1-1D and bes1-D gain-of-function alleles increase LR."),

    # iter2: HY5 light-integration (JUDGE S004 MEDIUM)
    ("HY5", "GENE", "ELONGATED HYPOCOTYL 5", "iter2: shoot-root light-integration bZIP TF (Chen 2016 Curr Biol); represses ARF19."),
    ("PHYB", "GENE", "PHYTOCHROME B", "iter2: red-light photoreceptor; activates HY5. Source node."),
]

# ---------------------------------------------------------------------------
# Edge plan (network_src, network_tgt, curated_edge_id used for evidence)
# Some edges reuse a representative curated-edge's evidence for composite nodes.
# The `note` field is used for composite-translation documentation only
# (it is not written into network.json).
# ---------------------------------------------------------------------------
EDGES: List[Dict] = [
    # Auxin biosynthesis + degradation
    {"source": "TAA1", "target": "Auxin", "sign": 1, "curated": "E053"},
    {"source": "TAR2", "target": "Auxin", "sign": 1, "curated": "E054"},
    {"source": "YUC4", "target": "Auxin", "sign": 1, "curated": "E055"},
    {"source": "AUX1", "target": "Auxin", "sign": 1, "curated": "E061"},
    {"source": "GH3",  "target": "Auxin", "sign": -1, "curated": "E075"},
    {"source": "DAO1", "target": "Auxin", "sign": -1, "curated": "E074"},

    # TAR2 regulation (N-sensing)
    {"source": "Low_Nitrate", "target": "TAR2", "sign": 1, "curated": "E112"},
    {"source": "CHL1", "target": "TAR2", "sign": -1, "curated": "E104"},

    # Auxin perception
    {"source": "Auxin", "target": "TIR1", "sign": 1, "curated": "E001"},
    {"source": "Low_Phosphate", "target": "TIR1", "sign": 1, "curated": "E124"},

    # TIR1 scaffold (Multi-Output motif): degrades IAA14 and IAA28
    {"source": "TIR1", "target": "IAA14", "sign": -1, "curated": "E002"},
    {"source": "TIR1", "target": "IAA28", "sign": -1, "curated": "E004"},

    # Aux/IAA - ARF derepression
    {"source": "IAA14", "target": "ARF7",  "sign": -1, "curated": "E011"},
    {"source": "IAA14", "target": "ARF19", "sign": -1, "curated": "E012"},
    {"source": "IAA28", "target": "ARF7",  "sign": -1, "curated": "E013"},
    {"source": "IAA28", "target": "ARF19", "sign": -1, "curated": "E014"},

    # ARF -> LBD / PLT (Coherent feed-forward)
    {"source": "ARF7",  "target": "LBD", "sign": 1, "curated": "E018"},  # E018: ARF7->LBD16
    {"source": "ARF19", "target": "LBD", "sign": 1, "curated": "E021"},  # E021: ARF19->LBD16
    {"source": "ARF7",  "target": "PLT", "sign": 1, "curated": "E034"},  # ARF7->PLT3
    {"source": "ARF19", "target": "PLT", "sign": 1, "curated": "E037"},  # ARF19->PLT3

    # LR organogenesis + emergence cascade
    # iter2: LBD->PUCHI edge dropped (PUCHI removed)
    {"source": "LBD", "target": "LAX3",  "sign": 1, "curated": "E027"},  # LBD29->LAX3
    {"source": "PLT", "target": "PIN",   "sign": 1, "curated": "E041"},  # PLT3->PIN1

    # iter2: WOX11 founder-to-organ (S002 HIGH)
    {"source": "Auxin",  "target": "WOX11", "sign": 1, "curated": "E220"},
    {"source": "WOX11",  "target": "LBD",   "sign": 1, "curated": "E221"},  # WOX11->LBD16 (composite LBD)

    # iter2: GATA23 founder-cell marker (S001 HIGH)
    {"source": "ARF7",   "target": "GATA23", "sign": 1,  "curated": "E033"},
    {"source": "IAA28",  "target": "GATA23", "sign": -1, "curated": "E200"},

    # Terminal LR activators
    {"source": "LBD",    "target": PHENO, "sign": 1, "curated": "E029"},
    {"source": "PLT",    "target": PHENO, "sign": 1, "curated": "E045"},
    # iter2: PUCHI->LR dropped (PUCHI removed)
    {"source": "LAX3",   "target": PHENO, "sign": 1, "curated": "E064"},
    {"source": "PIN",    "target": PHENO, "sign": 1, "curated": "E066"},  # PIN2->LR
    {"source": "ANR1",   "target": PHENO, "sign": 1, "curated": "E099"},
    {"source": "GATA23", "target": PHENO, "sign": 1, "curated": "E032"},

    # CK module (Perception Gate)
    {"source": "IPT5",      "target": "Cytokinin", "sign": 1, "curated": "E090"},
    {"source": "CKX2",      "target": "Cytokinin", "sign": -1, "curated": "E091"},
    {"source": "Cytokinin", "target": "AHK",       "sign": 1, "curated": "E078"},  # CK->AHK2
    {"source": "AHK",       "target": "ARR_B",     "sign": 1, "curated": "E081"},  # AHK2->ARR1
    {"source": "ARR_B",     "target": PHENO,       "sign": -1, "curated": "E206"},  # ARR1->LR

    # Nitrate signalling arm
    {"source": "CHL1", "target": "NLP7", "sign": 1, "curated": "E101"},
    {"source": "NLP7", "target": "ANR1", "sign": 1, "curated": "E100"},
    {"source": "CHL1", "target": "ANR1", "sign": 1, "curated": "E098"},

    # CLE-CLV systemic-N feedback
    {"source": "Low_Nitrate", "target": "CLE",  "sign": 1,  "curated": "E217"},  # Low_N->CLE3
    {"source": "CLE",         "target": "CLV1", "sign": 1,  "curated": "E211"},  # CLE3->CLV1
    {"source": "CLV1",        "target": PHENO,  "sign": -1, "curated": "E216"},

    # Ethylene module (Perception Gate)
    {"source": "ACS",      "target": "Ethylene", "sign": 1,  "curated": "E132"},
    {"source": "ACO",      "target": "Ethylene", "sign": 1,  "curated": "E133"},
    {"source": "Ethylene", "target": "EIN2",     "sign": 1,  "curated": "E126"},
    {"source": "CTR1",     "target": "EIN2",     "sign": -1, "curated": "E134"},
    {"source": "EIN2",     "target": PHENO,      "sign": -1, "curated": "E130"},

    # ABA module (Perception Gate + iter2 ABI4_5 composite for S005 MEDIUM)
    {"source": "ABA",    "target": "PYL8",   "sign": 1,  "curated": "E146"},
    {"source": "PYL8",   "target": "ABI1",   "sign": -1, "curated": "E147"},
    {"source": "ABI1",   "target": "SNRK2",  "sign": -1, "curated": "E148"},
    {"source": "SNRK2",  "target": "ABI4_5", "sign": 1,  "curated": "E149"},  # gate-pure arm via ABI4
    {"source": "ABA",    "target": "ABI4_5", "sign": 1,  "curated": "E247"},  # ABI5-bypass arm (acknowledged minor gate leak)
    {"source": "ABI4_5", "target": PHENO,    "sign": -1, "curated": "E140"},  # composite E140 (ABI4->LR) + E248 (ABI5->LR)

    # GA module
    {"source": "GA",    "target": "DELLA", "sign": -1, "curated": "E175"},
    {"source": "DELLA", "target": PHENO,   "sign": -1, "curated": "E176"},

    # Strigolactone module
    {"source": "MAX1",          "target": "Strigolactone", "sign": 1,  "curated": "E157"},
    {"source": "MAX3",          "target": "Strigolactone", "sign": 1,  "curated": "E155"},
    {"source": "MAX4",          "target": "Strigolactone", "sign": 1,  "curated": "E156"},
    {"source": "Strigolactone", "target": "D14",           "sign": 1,  "curated": "E153"},
    {"source": "D14",           "target": PHENO,           "sign": -1, "curated": "E150"},
    {"source": "MAX2",          "target": PHENO,           "sign": -1, "curated": "E152"},

    # iter2: Brassinosteroid module (S003 HIGH)
    {"source": "Brassinosteroid", "target": "BRI1",  "sign": 1,  "curated": "E204"},
    {"source": "BRI1",            "target": "BIN2",  "sign": -1, "curated": "E235"},
    {"source": "BIN2",            "target": "BZR",   "sign": -1, "curated": "E236"},  # composite: E236 BIN2->BZR1 + E237 BIN2->BES1
    {"source": "BZR",             "target": PHENO,   "sign": 1,  "curated": "E238"},  # composite: E238 BZR1->LR + E239 BES1->LR

    # iter2: HY5 shoot-root light integration (S004 MEDIUM)
    {"source": "PHYB", "target": "HY5",   "sign": 1,  "curated": "E161"},
    {"source": "HY5",  "target": "ARF19", "sign": -1, "curated": "E162"},
]


def load_curated() -> Dict[str, Dict]:
    with open(CURATED_PATH, "r", encoding="utf-8") as f:
        return {e["edge_id"]: e for e in json.load(f)["edges"]}


def build_network(curated: Dict[str, Dict]) -> Dict:
    net_nodes = []
    node_ids = set()
    for nid, ntype, fname, desc in NODES:
        net_nodes.append({
            "id": nid,
            "type": ntype,
            "full_name": fname,
            "description": desc,
        })
        node_ids.add(nid)

    # incoming count drives is_source
    incoming_count: Dict[str, int] = {nid: 0 for nid in node_ids}
    for e in EDGES:
        incoming_count[e["target"]] = incoming_count.get(e["target"], 0) + 1

    for n in net_nodes:
        n["is_source"] = incoming_count.get(n["id"], 0) == 0

    net_edges = []
    for idx, e in enumerate(EDGES, start=1):
        curated_edge = curated[e["curated"]]
        evidence = curated_edge.get("evidence", [])
        effect = "activation" if e["sign"] == 1 else "inhibition"
        mechanism = curated_edge.get("mechanism", "")
        # For composite edges, prepend a short note
        composite_note = ""
        src_is_composite = any(
            n[0] == e["source"] and n[1] == "PROTEIN_COMPLEX" for n in NODES
        )
        tgt_is_composite = any(
            n[0] == e["target"] and n[1] == "PROTEIN_COMPLEX" for n in NODES
        )
        if src_is_composite or tgt_is_composite:
            composite_note = (
                f" [Edge represents composite family; evidence drawn from curated "
                f"{e['curated']} ({curated_edge['source']}->{curated_edge['target']}).]"
            )

        net_edges.append({
            "source": e["source"],
            "target": e["target"],
            "sign": e["sign"],
            "edge_id": f"N{idx:03d}",
            "effect": effect,
            "mechanism": (mechanism + composite_note).strip(),
            "evidence": evidence,
        })

    source_count = sum(1 for n in net_nodes if n["is_source"])
    total_nodes = len(net_nodes)
    total_edges = len(net_edges)
    source_pct = round(source_count / total_nodes * 100, 1) if total_nodes else 0.0

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "Lateral_Root_Density",
            "phenotype_node": PHENO,
            "species": "Arabidopsis thaliana",
            "created": "2026-04-19",
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "source_nodes": source_count,
            "source_percentage": source_pct,
        },
        "nodes": net_nodes,
        "edges": net_edges,
    }


def build_algebraic(network: Dict) -> Dict:
    nodes_by_id = {n["id"]: n for n in network["nodes"]}
    activators: Dict[str, List[str]] = {nid: [] for nid in nodes_by_id}
    inhibitors: Dict[str, List[str]] = {nid: [] for nid in nodes_by_id}
    for e in network["edges"]:
        if e["sign"] == 1:
            activators[e["target"]].append(e["source"])
        else:
            inhibitors[e["target"]].append(e["source"])

    equations = []
    for n in network["nodes"]:
        nid = n["id"]
        ntype = n["type"]
        is_src = n["is_source"]
        acts = activators[nid]
        inhs = inhibitors[nid]
        if is_src:
            formula = f"{nid} = gene_modifier + exogenous_supply"
        else:
            if acts:
                if len(acts) == 1:
                    act_part = f"max({acts[0]}, 0.01)^(1/1)"
                else:
                    prod = " * ".join(f"max({a}, 0.01)" for a in acts)
                    act_part = f"({prod})^(1/{len(acts)})"
            else:
                # No activators but has inhibitors: default activation=1.0
                act_part = "1.0"
            if inhs:
                if len(inhs) == 1:
                    inh_inner = f"max({inhs[0]}, 0.1)"
                else:
                    inh_inner = "max(" + " * ".join(inhs) + ", 0.1)"
                inh_part = f"min(1/{inh_inner}, 10.0)"
            else:
                inh_part = "1.0"
            formula = f"{nid} = {act_part} * {inh_part} * gene_modifier + exogenous_supply"
        equations.append({
            "node": nid,
            "type": ntype,
            "is_source": is_src,
            "activators": acts,
            "inhibitors": inhs,
            "formula": formula,
        })

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "Lateral_Root_Density",
            "species": "Arabidopsis thaliana",
            "created": "2026-04-19",
            "total_equations": len(equations),
        },
        "parameters": {
            "epsilon": 0.1,
            "K": 10.0,
            "activator_floor": 0.01,
            "damping": 0.7,
            "direction_threshold": 0.05,
            "max_iterations": 100,
            "convergence_tolerance": 0.0001,
        },
        "equations": equations,
    }


def build_ode(network: Dict) -> Dict:
    activators: Dict[str, List[str]] = {n["id"]: [] for n in network["nodes"]}
    inhibitors: Dict[str, List[str]] = {n["id"]: [] for n in network["nodes"]}
    for e in network["edges"]:
        if e["sign"] == 1:
            activators[e["target"]].append(e["source"])
        else:
            inhibitors[e["target"]].append(e["source"])

    equations = []
    for n in network["nodes"]:
        nid = n["id"]
        is_src = n["is_source"]
        acts = activators[nid]
        inhs = inhibitors[nid]
        if is_src:
            formula = f"{nid} = gene_modifier + exogenous"
        else:
            parts = []
            if acts:
                parts.append("prod(f(" + ", ".join(acts) + "))")
            else:
                parts.append("1.0")
            if inhs:
                parts.append("prod(g(" + ", ".join(inhs) + "))")
            formula = f"{nid} = " + " * ".join(parts) + " * gene_modifier + exogenous"
        equations.append({
            "node": nid,
            "activators": acts,
            "inhibitors": inhs,
            "formula": formula,
        })

    return {
        "metadata": {
            "method": "ODE (Hill Functions)",
            "K": 1.0,
            "n": 2,
            "accuracy": None,
            "hill_activation_formula": "f(x) = x^n * (K^n + 1) / (K^n + x^n)",
            "hill_inhibition_formula": "g(x) = (K^n + 1) / (K^n + x^n)",
            "dt": 0.01,
            "max_time": 50.0,
            "convergence_tolerance": 0.001,
            "direction_threshold": 0.05,
            "activator_floor": 0.01,
        },
        "equations": equations,
    }


def build_annotations(network: Dict) -> Dict:
    activators: Dict[str, List[str]] = {n["id"]: [] for n in network["nodes"]}
    inhibitors: Dict[str, List[str]] = {n["id"]: [] for n in network["nodes"]}
    outgoing: Dict[str, int] = {n["id"]: 0 for n in network["nodes"]}
    for e in network["edges"]:
        if e["sign"] == 1:
            activators[e["target"]].append(e["source"])
        else:
            inhibitors[e["target"]].append(e["source"])
        outgoing[e["source"]] = outgoing.get(e["source"], 0) + 1

    annotations = []
    for n in network["nodes"]:
        nid = n["id"]
        n_act = len(activators[nid])
        n_inh = len(inhibitors[nid])
        in_deg = n_act + n_inh
        out_deg = outgoing[nid]
        annotations.append({
            "node": nid,
            "full_name": n.get("full_name", ""),
            "type": n["type"],
            "description": n.get("description", ""),
            "in_degree": in_deg,
            "out_degree": out_deg,
            "total_degree": in_deg + out_deg,
            "is_source": n["is_source"],
            "n_activators": n_act,
            "n_inhibitors": n_inh,
        })

    return {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "Lateral_Root_Density",
            "species": "Arabidopsis thaliana",
            "created": "2026-04-19",
            "total_nodes": len(annotations),
        },
        "annotations": annotations,
    }


def main() -> None:
    curated = load_curated()

    # Validate all referenced curated edges exist
    missing = [e["curated"] for e in EDGES if e["curated"] not in curated]
    if missing:
        raise SystemExit(f"Missing curated edge IDs: {missing}")

    # Validate referenced nodes appear in NODES list
    declared = {n[0] for n in NODES}
    for e in EDGES:
        if e["source"] not in declared:
            raise SystemExit(f"Edge source not declared as node: {e['source']}")
        if e["target"] not in declared:
            raise SystemExit(f"Edge target not declared as node: {e['target']}")

    net = build_network(curated)
    alg = build_algebraic(net)
    ode = build_ode(net)
    ann = build_annotations(net)

    OUT_NETWORK.write_text(json.dumps(net, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_ALG.write_text(json.dumps(alg, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_ODE.write_text(json.dumps(ode, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_ANN.write_text(json.dumps(ann, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {OUT_NETWORK.name}: {net['metadata']['total_nodes']} nodes, {net['metadata']['total_edges']} edges")
    print(f"  source_nodes={net['metadata']['source_nodes']} ({net['metadata']['source_percentage']}%)")
    print(f"Wrote {OUT_ALG.name}: {alg['metadata']['total_equations']} equations")
    print(f"Wrote {OUT_ODE.name}: {len(ode['equations'])} equations")
    print(f"Wrote {OUT_ANN.name}: {ann['metadata']['total_nodes']} annotations")


if __name__ == "__main__":
    main()
