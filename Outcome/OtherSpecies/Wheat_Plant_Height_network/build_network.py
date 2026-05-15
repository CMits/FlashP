"""One-off BUILDER helper for wheat plant height.

Reads data/curated_edges.json, applies the selection decisions made
by the BUILDER agent, and writes the four network/*.json output files.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
NETWORK = ROOT / "network"

# --------------------------------------------------------------------------
# Node table — (id, type, full_name, description, is_source)
# Names chosen to satisfy check_network_structure.py NAMING_REGEX:
#   GENE regex = ^[A-Z][A-Z0-9_]*$  (ALL_CAPS; no hyphens, no lowercase)
# Hyphenated locus names ("Rht-B1", "Ppd-D1") → underscore-joined ALL_CAPS.
# --------------------------------------------------------------------------

NODES = [
    # ENVIRONMENT (source)
    ("Vernalization", "ENVIRONMENT", "Vernalization (prolonged cold)",
     "Long cold exposure required to activate VRN1 and promote spring growth.", True),
    ("Photoperiod", "ENVIRONMENT", "Photoperiod (day length)",
     "Light-cycle input that entrains Ppd-1 and coordinates flowering and stem elongation.", True),
    ("Light", "ENVIRONMENT", "Light (red/far-red)",
     "Phytochrome-sensed red/far-red light; targets PIF transcription factors for degradation.", True),
    ("Nitrogen", "ENVIRONMENT", "Nitrogen / nitrate availability",
     "Nitrate signal that upregulates GA biosynthesis and destabilises DELLA proteins.", True),

    # HORMONE (non-source — regulated by biosynthesis/degradation balance)
    ("Gibberellin", "HORMONE", "Bioactive gibberellin (GA1/GA4)",
     "Bioactive gibberellin pool; balance of TaGA20ox/TaGA3ox biosynthesis vs TaGA2ox catabolism.", False),
    ("Brassinosteroid", "HORMONE", "Brassinolide (BL) / active brassinosteroid",
     "Active brassinosteroid pool produced by TaD11 and rate-limiting TaDWF4.", False),
    ("Auxin", "HORMONE", "Indole-3-acetic acid (IAA)",
     "Active auxin pool; conjugated (inactivated) by TaGH3.", False),

    # GENE — source (constitutive, biosynthesis, allele-specific Rht variants)
    ("TASLY1", "GENE", "TaSLEEPY1 / GID2 F-box",
     "SCF F-box component that ubiquitinates GA-bound DELLA for proteasomal degradation.", True),
    ("TAGA3OX", "GENE", "Ta GA 3-oxidase (TaGA3ox1/2/3)",
     "GA 3-oxidase; catalyses 3β-hydroxylation of GA20→GA1 and GA9→GA4 (bioactive step).", True),
    ("TAGA1OX1", "GENE", "Ta GA 1-oxidase (TaGA1ox1)",
     "1β-hydroxylase that diverts GA9/GA20 to inactive GA61/GA60.", True),
    ("TASERK", "GENE", "TaSERK / BAK1 co-receptor family",
     "BR co-receptor; heterodimerises with TaBRI1 upon BR binding.", True),
    ("TAZNF", "GENE", "TaZnF RING E3 ligase",
     "BR signalling activator; ubiquitinates TaBKI1 for proteasomal destruction.", True),
    ("TAARF4", "GENE", "TaARF4 auxin response factor",
     "Homeolog-specific ARF4 associated with plant height and root QTLs.", True),
    ("TAERF_A1", "GENE", "TaERF-A1 AP2/ERF transcription factor",
     "AP2/ERF TF that directly activates TaPIF4 transcription; JD6 semi-dwarf allele (F178S).", True),
    ("RHT8", "GENE", "Rht8 / TaRNHL-D1 ribonuclease-H-like",
     "Green-Revolution replacement semi-dwarfing locus; modifies GA biosynthesis; GA-responsive.", True),
    ("RHT13", "GENE", "Rht13 autoactive NB-LRR",
     "Rht13 (Rht-B13b S240F) is an autoactive NB-LRR that triggers PR-gene upregulation.", True),
    ("RHT18", "GENE", "Rht18 (TaGA2ox-A9 overexpression variant)",
     "Semi-dwarf allele that upregulates TaGA2ox-A9 (~4-fold), lowering bioactive GA.", True),
    ("RHT24", "GENE", "Rht24 / Rht24b (TaGA2ox-A9 cis-regulatory variant)",
     "Ancient dwarfing allele that elevates TaGA2ox-A9 expression in stems.", True),
    ("RHT12", "GENE", "Rht12 / Rht12b (TaGA2oxA13 cis-regulatory variant)",
     "Dwarfing allele whose SNP-390(C/A) elevates TaGA2oxA13 expression.", True),
    ("TAOSCA1_4", "GENE", "TaOSCA1.4 hyperosmolality-gated Ca2+ channel",
     "Novel Rht gene; GA-independent Ca2+-signalling route. RNAi reduces plant height 11-16%.", True),
    ("TAD11", "GENE", "TaD11 / TaCYP724B BR C6-oxidase",
     "Late-step BR biosynthesis enzyme (C6-oxidase).", True),
    ("TADWF4", "GENE", "TaDWF4 / TaCYP90B1 rate-limiting BR biosynthesis",
     "22α-hydroxylation of campesterol; rate-limiting branch-point of BR biosynthesis.", True),

    # GENE — non-source
    ("TAGID1", "GENE", "TaGID1 gibberellin receptor (A/B/D homeologs)",
     "GA receptor; GA-bound TaGID1 recruits SCF-TaSLY1 to degrade DELLA.", False),
    ("TAGA20OX", "GENE", "Ta GA 20-oxidase (TaGA20ox1/2/3)",
     "GA 20-oxidase; rate-limiting late GA biosynthesis enzyme.", False),
    ("TAGA2OX", "GENE", "Ta GA 2-oxidase (TaGA2ox family; A9, A13, A3)",
     "GA catabolism; inactivates GA1/GA4 and precursor GA12.", False),
    ("RHT_B1", "GENE", "Rht-B1 DELLA homeolog (chromosome 4B)",
     "DELLA growth repressor on 4B; Rht-B1b/c are GA-insensitive Green Revolution alleles.", False),
    ("RHT_D1", "GENE", "Rht-D1 DELLA homeolog (chromosome 4D)",
     "DELLA homeolog on 4D; Rht-D1b is the second Green Revolution dwarfing allele.", False),
    ("PLATZ_A1", "GENE", "PLATZ-A1 transcription factor (Rht25)",
     "PLATZ TF that physically interacts with DELLA-GRAS; promotes GRF1/CYCD4 expression.", False),
    ("TAGRF4", "GENE", "TaGRF4 growth-regulating factor 4",
     "GRF TF that antagonises DELLA; OE increases yield and N/C assimilation.", False),
    ("PIF", "GENE", "Phytochrome-interacting factor (TaPIF4)",
     "bHLH TF activating cell-elongation genes; sequestered by DELLA and degraded by phytochromes.", False),
    ("PPD_D1", "GENE", "Ppd-D1 pseudo-response regulator (Photoperiod-1)",
     "Photoperiod-1 homeolog on 2D; dominant Ppd-D1a allele shortens internodes and reduces height.", False),
    ("VRN1", "GENE", "VRN1 MADS-box transcription factor",
     "Vernalization-induced MADS-box TF that activates TaGA20ox2.", False),
    ("TABRI1", "GENE", "TaBRI1 brassinosteroid receptor kinase",
     "BR receptor LRR-RLK; heterodimerises with TaSERK upon BL binding.", False),
    ("TABKI1", "GENE", "TaBKI1 BRI1 kinase inhibitor",
     "Plasma-membrane inhibitor of TaBRI1 in the BR-off state; degraded by TaZnF upon BR signalling.", False),
    ("TABIN2", "GENE", "TaBIN2 GSK3-like kinase",
     "Negative regulator of BR signalling; inactivated via BSK/CDG/BSU1 upon BR perception.", False),
    ("TABZR1", "GENE", "TaBZR1 / TaBES1 transcription factor",
     "Dephosphorylated active BZR1/BES1 drives BR-response growth genes.", False),
    ("TATIR1", "GENE", "TaTIR1/AFB auxin receptor F-box",
     "Auxin co-receptor F-box; auxin-loaded TaTIR1 targets TaIAA for degradation.", False),
    ("TAIAA", "GENE", "TaAux/IAA transcriptional repressors",
     "Aux/IAA repressors that sequester TaARF in the auxin-off state.", False),
    ("TAARF", "GENE", "TaARF auxin response factors",
     "Auxin-response TF family; activates cell-elongation genes upon TaIAA removal.", False),
    ("TAHB33", "GENE", "TaHB33 HD-Zip transcription factor",
     "Auxin-linked HD-Zip TF that represses TaGH3 expression.", False),
    ("TAGH3", "GENE", "TaGH3 (Gretchen Hagen 3) auxin-amido synthetase",
     "Conjugates IAA to amino acids, reducing the active auxin pool.", False),

    # PROCESS
    ("Pathogenesis_Related_Genes", "PROCESS", "Class-III peroxidases / PR genes",
     "Cell-wall cross-linking enzymes whose upregulation limits cell elongation.", False),

    # PHENOTYPE
    ("Plant_Height", "PHENOTYPE", "Plant height (cumulative internode elongation)",
     "Wheat plant height; integrated output of GA-DELLA, BR, auxin, light, and specialty-Rht pathways.", False),
]

# --------------------------------------------------------------------------
# Edge table — (edge_id, source, target, sign, effect, mechanism, curated_edge_id)
# Evidence is copied from curated_edges.json (primary entry) at write-time.
# --------------------------------------------------------------------------

EDGES = [
    # --- GA biosynthesis / catabolism (Motif 4: Biosynthesis-Degradation Balance) ---
    ("N001", "TAGA20OX", "Gibberellin", 1, "activation",
     "GA 20-oxidase catalyses GA12→GA9 and GA53→GA20; rate-limiting late GA biosynthesis.", "E008"),
    ("N002", "TAGA3OX", "Gibberellin", 1, "activation",
     "GA 3-oxidase catalyses 3β-hydroxylation GA20→GA1 producing bioactive GA.", "E009"),
    ("N003", "TAGA2OX", "Gibberellin", -1, "inhibition",
     "GA 2-oxidase catabolises bioactive GA1/GA4 to inactive GA8/GA34.", "E010"),
    ("N004", "TAGA1OX1", "Gibberellin", -1, "inhibition",
     "TaGA1ox1 1β-hydroxylates GA9/GA20 to inactive GA61/GA60, diverting from bioactive pool.", "E011"),
    ("N005", "RHT8", "Gibberellin", 1, "activation",
     "Rht8 (TaRNHL-D1) promotes bioactive GA biosynthesis in stem.", "E048"),
    ("N006", "Nitrogen", "Gibberellin", 1, "activation",
     "Nitrate signalling activates GA metabolism gene expression, raising bioactive GA.", "E078"),

    # --- GA homeostatic feedback (Motif 2: safe negative feedback) ---
    ("N007", "Gibberellin", "TAGA2OX", 1, "activation",
     "GA induces its own catabolism — classic GA homeostasis (GA→TaGA2ox↑→GA↓).", "E016"),

    # --- TaGA20ox regulation ---
    ("N008", "VRN1", "TAGA20OX", 1, "activation",
     "VRN1 binds and activates the TaGA20ox2 promoter, coupling vernalization to GA biosynthesis.", "E044"),
    ("N009", "RHT_B1", "TAGA20OX", 1, "activation",
     "DELLA promotes TaGA20ox transcription (negative-feedback GA homeostasis: DELLA↑→GA↑→DELLA↓).", "E018"),

    # --- TaGA2ox activation by specialty Rht alleles (G002 gap closure) ---
    ("N010", "RHT18", "TAGA2OX", 1, "activation",
     "Rht18 allele drives ~4-fold upregulation of TaGA2ox-A9, increasing GA catabolism.", "E068"),
    ("N011", "RHT24", "TAGA2OX", 1, "activation",
     "Rht24b cis-regulatory variant elevates TaGA2ox-A9 expression in stems.", "E069"),
    ("N012", "RHT12", "TAGA2OX", 1, "activation",
     "Rht12b SNP-390(C/A) elevates TaGA2oxA13 expression; causal variant of the Rht12 locus.", "E070"),

    # --- Perception Gate: GA → TaGID1 → DELLA (Motif 1) ---
    # CRITICAL: GA has ONLY outgoing edges to TaGID1 and to TaGA2ox (homeostasis).
    # Direct GA→Rht-B1, GA→Rht-D1, GA→TaEXP bypass edges (curated E012, E013, E041)
    # deliberately EXCLUDED so Rht-B1b + GA3 cannot rescue via bypass (Trap 3).
    ("N013", "Gibberellin", "TAGID1", 1, "activation",
     "GA binding in the TaGID1 pocket induces conformational change enabling DELLA interaction.", "E001"),
    ("N014", "TAGID1", "RHT_B1", -1, "inhibition",
     "GA-bound TaGID1 binds Rht-B1 DELLA N-terminal motif, recruiting SCF-SLY1 for ubiquitination.", "E002"),
    ("N015", "TAGID1", "RHT_D1", -1, "inhibition",
     "GA-bound TaGID1 binds Rht-D1 DELLA homeolog for SCF-SLY1-mediated degradation.", "E003"),
    ("N016", "TASLY1", "RHT_B1", -1, "inhibition",
     "SCF-TaSLY1 F-box ubiquitinates Rht-B1 DELLA for 26S proteasomal degradation.", "E004"),
    ("N017", "TASLY1", "RHT_D1", -1, "inhibition",
     "SCF-TaSLY1 ubiquitinates Rht-D1 DELLA homeolog (parallel to Rht-B1).", "E005"),
    ("N018", "Nitrogen", "RHT_B1", -1, "inhibition",
     "Nitrate promotes GA-mediated destabilisation of DELLA (partial rescue by global-della mutant).", "E079"),

    # --- DELLA → Plant_Height (the canonical Green-Revolution repression) ---
    ("N019", "RHT_B1", "Plant_Height", -1, "repression",
     "Rht-B1 DELLA represses GA-responsive growth; Rht-B1b reduces height ~20%, Rht-B1c ~50%.", "E006"),
    ("N020", "RHT_D1", "Plant_Height", -1, "repression",
     "Rht-D1 DELLA homeolog represses growth; Rht-D1b Green-Revolution dwarfing allele ~20%.", "E007"),

    # --- DELLA-TF antagonism (Multi-Output Scaffold, Motif 5) ---
    ("N021", "RHT_B1", "PLATZ_A1", -1, "inhibition",
     "DELLA GRAS PFYRE subdomain physically binds and sequesters PLATZ-A1 (Y2H + genetics).", "E020"),
    ("N022", "RHT_B1", "TAGRF4", -1, "inhibition",
     "DELLA binds and inhibits TaGRF4 growth output; antagonistic balance (Li et al 2018).", "E063"),
    ("N023", "TAGRF4", "RHT_B1", -1, "inhibition",
     "TaGRF4 competes with PLATZ1 for DELLA binding and antagonises DELLA repression.", "E022"),
    ("N024", "PLATZ_A1", "Plant_Height", 1, "activation",
     "PLATZ-A1 (Rht25) LOF reduces height ~12.7%; OE increases height (causal Rht25 gene).", "E019"),

    # --- DELLA → PIF sequestration (light / elongation) ---
    ("N025", "RHT_B1", "PIF", -1, "inhibition",
     "DELLA sequesters PIF TFs; accumulated Rht-B1c constitutively blocks PIF activity.", "E060"),
    ("N026", "PIF", "Plant_Height", 1, "activation",
     "PIFs activate cell-elongation genes; DELLA-sequestration decreases stem elongation.", "E061"),
    ("N027", "Light", "PIF", -1, "inhibition",
     "Red/far-red light via phytochromes targets PIFs for degradation.", "E062"),
    ("N028", "TAERF_A1", "PIF", 1, "activation",
     "TaERF-A1 directly binds the TaPIF4 promoter and activates its transcription (EMSA/ChIP).", "E073"),

    # --- BR biosynthesis ---
    ("N029", "TAD11", "Brassinosteroid", 1, "activation",
     "TaD11 (C6-oxidase) catalyses late BR biosynthesis step; tad11-2a reduces endogenous BR.", "E034"),
    ("N030", "TADWF4", "Brassinosteroid", 1, "activation",
     "TaDWF4 (CYP90B) 22α-hydroxylation of campesterol — rate-limiting BR biosynthesis branch-point.", "E071"),

    # --- BR Perception Gate (Motif 1) ---
    # BL has ONLY outgoing edge to TaBRI1; no BL→TaEXP bypass (curated E042 excluded).
    ("N031", "Brassinosteroid", "TABRI1", 1, "activation",
     "BL ligand binds TaBRI1 extracellular domain, activating receptor kinase and downstream cascade.", "E024"),
    ("N032", "TASERK", "TABRI1", 1, "activation",
     "TaSERK (BAK1 co-receptor) heterodimerises with TaBRI1, required for BR perception.", "E072"),
    ("N033", "TABKI1", "TABRI1", -1, "inhibition",
     "TaBKI1 represses TaBRI1 kinase activity in the BR-off state.", "E027"),
    ("N034", "TABRI1", "TABKI1", -1, "inhibition",
     "Activated TaBRI1 facilitates TaZnF-mediated ubiquitination of TaBKI1 (mutual release loop).", "E025"),
    ("N035", "TAZNF", "TABKI1", -1, "inhibition",
     "TaZnF RING E3 ligase ubiquitinates TaBKI1 for proteasomal destruction.", "E026"),
    ("N036", "TABRI1", "TABIN2", -1, "inhibition",
     "BRI1-BSK-CDG-BSU1 cascade dephosphorylates and inactivates TaBIN2 (GSK3-like kinase).", "E028"),
    ("N037", "TABIN2", "TABZR1", -1, "inhibition",
     "TaBIN2 phosphorylates TaBZR1/TaBES1, blocking nuclear localisation and DNA binding.", "E029"),
    ("N038", "TABZR1", "Plant_Height", 1, "activation",
     "Dephosphorylated TaBZR1/TaBES1 activates BR-response growth and cell-elongation genes.", "E030"),

    # --- BR↔GA crosstalk ---
    ("N039", "TABZR1", "RHT_B1", -1, "inhibition",
     "TaBZR1 physically binds DELLA proteins; reciprocal sequestration (BR-GA antagonism).", "E032"),
    ("N040", "TABIN2", "RHT_B1", 1, "activation",
     "TaBIN2 phosphorylates and stabilises DELLA (when BR low); BR-GA crosstalk.", "E033"),

    # --- Auxin Perception Gate (Motif 1) ---
    # Auxin has ONLY outgoing edge to TaTIR1; no Auxin→TaEXP bypass (curated E040 excluded).
    ("N041", "Auxin", "TATIR1", 1, "activation",
     "Auxin binds TaTIR1/AFB F-box forming co-receptor with Aux/IAA substrate.", "E036"),
    ("N042", "TATIR1", "TAIAA", -1, "inhibition",
     "Auxin-loaded TaTIR1 targets TaAux/IAA proteins for proteasomal degradation.", "E037"),
    ("N043", "TAIAA", "TAARF", -1, "inhibition",
     "TaAux/IAA binds and represses TaARF TFs; removal de-represses ARF activity.", "E038"),
    ("N044", "TAARF", "Plant_Height", 1, "activation",
     "TaARF4-B haplotypes associate with plant height QTL; ARFs activate growth/elongation genes.", "E039"),

    # --- Auxin homeostasis via TaARF4→TaHB33→TaGH3 ---
    ("N045", "TAARF4", "TAHB33", 1, "activation",
     "TaARF4-A regulates TaHB33 expression (auxin-response pathway).", "E052"),
    ("N046", "TAHB33", "TAGH3", -1, "repression",
     "TaHB33 represses TaGH3 expression, indirectly raising active auxin.", "E053"),
    ("N047", "TAGH3", "Auxin", -1, "inhibition",
     "TaGH3 enzymes conjugate IAA with amino acids, reducing the active auxin pool.", "E054"),

    # --- Photoperiod / Vernalization ---
    ("N048", "Vernalization", "VRN1", 1, "activation",
     "Cold epigenetically induces VRN1 in shoot apex.", "E046"),
    ("N049", "Photoperiod", "PPD_D1", 1, "activation",
     "Ppd-1 is a pseudo-response regulator entrained by day length; long-day activates Ppd-1.", "E076"),
    ("N050", "PPD_D1", "Plant_Height", -1, "repression",
     "Dominant Ppd-D1a shortens each internode by ~10%, reducing overall plant height.", "E075"),

    # --- Rht13 autoimmunity pathway ---
    ("N051", "RHT13", "Pathogenesis_Related_Genes", 1, "activation",
     "Autoactive Rht-B13b (S240F) NB-LRR upregulates PR genes including class-III peroxidases.", "E049"),
    ("N052", "Pathogenesis_Related_Genes", "Plant_Height", -1, "inhibition",
     "Class-III peroxidases cross-link cell-wall compounds, limiting elongation and reducing height.", "E050"),

    # --- TaOSCA1.4 GA-independent Ca2+ pathway ---
    ("N053", "TAOSCA1_4", "Plant_Height", 1, "activation",
     "TaOSCA1.4 hyperosmolality-gated Ca2+ channel; RNAi reduces height 11-16% via GA-independent route.", "E077"),
]

# --------------------------------------------------------------------------
# Load curated edges, build lookup by curated ID
# --------------------------------------------------------------------------

with open(DATA / "curated_edges.json", encoding="utf-8") as f:
    curated = json.load(f)
curated_by_id = {e["edge_id"]: e for e in curated["edges"]}


def build_evidence(curated_id: str):
    """Copy primary evidence block(s) from curated edge, flat v1.0 shape."""
    if curated_id not in curated_by_id:
        raise KeyError(f"Curated edge {curated_id} not found")
    ev_list = curated_by_id[curated_id].get("evidence", [])
    # Keep at most the two most-authoritative entries to reduce file size
    # while preserving the DOI + sentence quote.
    out = []
    for ev in ev_list[:2]:
        out.append({
            "doi": ev.get("doi", ""),
            "title": ev.get("title", ""),
            "authors": ev.get("authors", ""),
            "year": ev.get("year"),
            "journal": ev.get("journal", ""),
            "evidence_sentence": ev.get("evidence_sentence", ""),
            "claim": ev.get("claim", ""),
            "verification": ev.get("verification"),
            "full_text_read": ev.get("full_text_read"),
        })
    return out


# --------------------------------------------------------------------------
# Write network.json
# --------------------------------------------------------------------------

node_objs = []
for nid, ntype, full_name, desc, is_src in NODES:
    node_objs.append({
        "id": nid,
        "type": ntype,
        "full_name": full_name,
        "description": desc,
        "is_source": is_src,
    })

edge_objs = []
for eid, src, tgt, sign, effect, mech, curated_id in EDGES:
    edge_objs.append({
        "source": src,
        "target": tgt,
        "sign": sign,
        "edge_id": eid,
        "effect": effect,
        "mechanism": mech,
        "evidence": build_evidence(curated_id),
    })

source_count = sum(1 for n in node_objs if n["is_source"])
network = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "phenotype_node": "Plant_Height",
        "species": "Triticum aestivum",
        "created": "2026-04-20",
        "total_nodes": len(node_objs),
        "total_edges": len(edge_objs),
        "source_nodes": source_count,
        "source_percentage": round(source_count / len(node_objs) * 100, 1),
        "homeolog_convention": "DELLA split (Rht-B1, Rht-D1 separate); GA-pathway and BR-receptor genes composite (TaGA20ox, TaGA3ox, TaGA2ox, TaGID1, TaBRI1, TaBZR1, TaBIN2, VRN1, TaGRF4, TaARF, TaIAA, TaTIR1); allele-specific where phenotype is driven by named allele (PLATZ-A1, TaARF4, TaERF-A1, Ppd-D1, TaOSCA1.4, Rht18, Rht24, Rht12).",
        "naming_notes": "Canonical names (Rht-B1, TaGID1, Ppd-D1, TaERF-A1 etc) are normalised to ALL_CAPS with underscores (RHT_B1, TAGID1, PPD_D1, TAERF_A1) to satisfy the GENE naming regex. Lowercase enzyme suffixes such as 'ox' in TaGA2ox → TAGA2OX. Aliases preserved in description / node_annotations.json.",
        "residual_gaps_handled": [
            "G001 (TaCPS/TaKS/TaKO/TaKAO early GA biosynthesis): documented in curated_edges.json only; no perturbation tests map to these enzymes, so excluding them from network.json keeps Gibberellin activator count within the 7-cap without losing test coverage (literature_gap).",
            "G005 (Rht8 upstream): no published regulator in wheat — retained as source, matches biology.",
            "G006 (TaTB1): review-level only — OMITTED from network.json (literature_gap) rather than adding with weak edges.",
            "G007 (Auxin→TaGA20ox crosstalk): no OA wheat primary paper — OMITTED (literature_gap); would bridge auxin to GA in future iterations.",
            "G009 partial (TaGA20ox RNAi, Uniconazole primary): paywalled — perturbation coverage limited but TaGA20ox node included so mapping is possible.",
            "TaGRF1 sink-only: OMITTED (alternative (b) from judge report).",
            "Rht4/5/26 uncloned: OMITTED at network level (documented in curated_edges literature_gap_log)."
        ]
    },
    "nodes": node_objs,
    "edges": edge_objs,
}

with open(NETWORK / "network.json", "w", encoding="utf-8") as f:
    json.dump(network, f, indent=2, ensure_ascii=False)

# --------------------------------------------------------------------------
# Compute activators / inhibitors per node from edges
# --------------------------------------------------------------------------

activators = {n["id"]: [] for n in node_objs}
inhibitors = {n["id"]: [] for n in node_objs}
for e in edge_objs:
    if e["sign"] == 1:
        activators[e["target"]].append(e["source"])
    else:
        inhibitors[e["target"]].append(e["source"])


def fmt_algebraic(node_id: str, ntype: str, acts, inhs, is_source: bool) -> str:
    if is_source:
        return f"{node_id} = gene_modifier + exogenous_supply"
    n = len(acts)
    if n == 0:
        activation = "1.0"
    elif n == 1:
        activation = f"max({acts[0]}, 0.01)"
    else:
        parts = " * ".join(f"max({a}, 0.01)" for a in acts)
        activation = f"({parts})^(1/{n})"
    m = len(inhs)
    if m == 0:
        inhibition = "1.0"
    else:
        inh_parts = " * ".join(inhs)
        inhibition = f"min(1/max({inh_parts}, 0.1), 10.0)"
    return f"{node_id} = {activation} * {inhibition} * gene_modifier + exogenous_supply"


def fmt_ode(node_id: str, acts, inhs, is_source: bool) -> str:
    if is_source:
        return f"{node_id} = gene_modifier + exogenous"
    act_part = f"prod(f({', '.join(acts)}))" if acts else "1.0"
    inh_part = f"prod(g({', '.join(inhs)}))" if inhs else "1.0"
    return f"{node_id} = {act_part} * {inh_part} * gene_modifier + exogenous"


# --------------------------------------------------------------------------
# Write algebraic_equations.json
# --------------------------------------------------------------------------

algebraic_eqs = []
for n in node_objs:
    nid = n["id"]
    is_src = n["is_source"]
    algebraic_eqs.append({
        "node": nid,
        "type": n["type"],
        "is_source": is_src,
        "activators": activators[nid],
        "inhibitors": inhibitors[nid],
        "formula": fmt_algebraic(nid, n["type"], activators[nid], inhibitors[nid], is_src),
    })

algebraic = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "species": "Triticum aestivum",
        "created": "2026-04-20",
        "total_equations": len(algebraic_eqs),
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
    "equations": algebraic_eqs,
}

with open(NETWORK / "algebraic_equations.json", "w", encoding="utf-8") as f:
    json.dump(algebraic, f, indent=2, ensure_ascii=False)

# --------------------------------------------------------------------------
# Write ode_equations.json
# --------------------------------------------------------------------------

ode_eqs = []
for n in node_objs:
    nid = n["id"]
    is_src = n["is_source"]
    ode_eqs.append({
        "node": nid,
        "activators": activators[nid],
        "inhibitors": inhibitors[nid],
        "formula": fmt_ode(nid, activators[nid], inhibitors[nid], is_src),
    })

ode = {
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
    "equations": ode_eqs,
}

with open(NETWORK / "ode_equations.json", "w", encoding="utf-8") as f:
    json.dump(ode, f, indent=2, ensure_ascii=False)

# --------------------------------------------------------------------------
# Write node_annotations.json
# --------------------------------------------------------------------------

in_degree = {n["id"]: 0 for n in node_objs}
out_degree = {n["id"]: 0 for n in node_objs}
for e in edge_objs:
    in_degree[e["target"]] += 1
    out_degree[e["source"]] += 1

annotations = []
for n in node_objs:
    nid = n["id"]
    annotations.append({
        "node": nid,
        "full_name": n["full_name"],
        "type": n["type"],
        "description": n["description"],
        "in_degree": in_degree[nid],
        "out_degree": out_degree[nid],
        "total_degree": in_degree[nid] + out_degree[nid],
        "is_source": n["is_source"],
        "n_activators": len(activators[nid]),
        "n_inhibitors": len(inhibitors[nid]),
    })

node_annotations = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Plant_Height",
        "species": "Triticum aestivum",
        "created": "2026-04-20",
        "total_nodes": len(annotations),
    },
    "annotations": annotations,
}

with open(NETWORK / "node_annotations.json", "w", encoding="utf-8") as f:
    json.dump(node_annotations, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(node_objs)} nodes, {len(edge_objs)} edges.")
print(f"Source nodes: {source_count} ({source_count/len(node_objs)*100:.1f}%)")
print("max activators on any node:",
      max(len(activators[n]) for n in activators))
print("max inhibitors on any node:",
      max(len(inhibitors[n]) for n in inhibitors))
print("Plant_Height activators:", activators["Plant_Height"])
print("Plant_Height inhibitors:", inhibitors["Plant_Height"])
