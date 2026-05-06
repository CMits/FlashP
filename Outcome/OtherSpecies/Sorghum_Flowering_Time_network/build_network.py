"""
Build network.json, algebraic_equations.json, ode_equations.json, and
node_annotations.json for Sorghum Flowering Time from the merged curated_edges.

Renames Sb-prefixed gene names to the FLASH-P canonical ALL_CAPS (per GENE
regex `^[A-Z][A-Z0-9_]*$`). Ma-locus names captured in node aliases/description.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "network"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Name remap: curated -> canonical
# ---------------------------------------------------------------------------
NAME_MAP = {
    # Environment (unchanged; regex allows mixed case)
    "Light": "Light",
    "Blue_Light": "Blue_Light",
    "Photoperiod_LD": "Photoperiod_LD",
    "Photoperiod_SD": "Photoperiod_SD",
    # Hormones
    "Gibberellin": "Gibberellin",
    "Ethylene": "Ethylene",
    # Photoreceptors
    "SbPhyB": "PHYB",
    "SbPhyC": "PHYC",
    "SbPhyA": "PHYA",
    "SbCRY1": "CRY1",
    # Clock
    "SbCCA1": "CCA1",
    "SbLHY": "LHY",
    "SbTOC1": "TOC1",
    "SbGI": "GI",
    "SbFKF1": "FKF1",
    "SbELF3": "ELF3",
    "SbELF4": "ELF4",
    "SbLUX": "LUX",
    # Ma-locus integrators
    "SbPRR37": "PRR37",
    "SbGhd7": "GHD7",
    "Ma2_SMYD": "MA2_SMYD",
    # Master regulators
    "SbID1": "ID1",
    "SbCO": "CO",
    "SbHd1": "CO",   # G008: SbHd1 is alias of SbCO
    "SbEhd1": "EHD1",
    # Florigens
    "SbFT1": "FT1",
    "SbFT8": "FT8",
    "SbFT10": "FT10",
    "SbFT12": "FT12",
    "SbFT2": "FT2",
    "SbFT6": "FT6",
    # FAC
    "SbFD1": "FD1",
    "Sb14-3-3": "GF14",
    # Meristem identity
    "SbSOC1": "SOC1",
    "SbLFY": "LFY",
    "SbAP1": "AP1",
    "SbAP2": "AP2",
    # Age pathway
    "SbSBP19": "SBP19",
    "SbSBP4": "SBP4",
    "sbi-MIR156h": "miR156h",
    "sbi-MIR172a": "miR172a",
    # Clock abstract (dropped)
    "Circadian_Clock": "Circadian_Clock",
    # Phenotype
    "Flowering_Time": "Flowering_Time",
}

# ---------------------------------------------------------------------------
# Nodes to include in the model
# ---------------------------------------------------------------------------
NODES = [
    # (id, type, full_name, description, is_source_hint)
    ("Light", "ENVIRONMENT",
     "Ambient light",
     "Environmental light input; activates photoreceptors PHYB/PHYC and entrains the morning clock (CCA1/LHY).",
     True),
    ("Blue_Light", "ENVIRONMENT",
     "Blue-light photon flux",
     "Blue light input to the LOV-domain F-box protein FKF1.",
     True),
    ("Photoperiod_LD", "ENVIRONMENT",
     "Long-day photoperiod regime",
     "Binary/continuous LD regime indicator: under LD the evening light window coincides with PRR37/GHD7 transcriptional peaks.",
     True),
    ("Gibberellin", "HORMONE",
     "Gibberellin",
     "Bioactive GA pool (GA1/GA20); mild flowering-promoting hormone in cereals. Encoded as a source hormone; exogenous GA3 treatment maps to exogenous_supply.",
     True),
    ("PHYB", "GENE",
     "Phytochrome B (Ma3 locus, Sobic.001G394400)",
     "Red-light photoreceptor; primary photoperiod sensor. ma3^R null causes ~60-day-earlier LD flowering (Childs 1997, Yang 2014). Ma-locus alias: Ma3.",
     False),
    ("PHYC", "GENE",
     "Phytochrome C (Ma5 locus, Sobic.001G087100)",
     "Secondary red-light photoreceptor; acts in parallel with PHYB to activate PRR37/GHD7. Ma-locus alias: Ma5.",
     False),
    ("CCA1", "GENE",
     "CIRCADIAN CLOCK ASSOCIATED 1",
     "Morning-phased MYB transcription factor; light-entrained at dawn; represses TOC1, GI, and PRR37.",
     False),
    ("LHY", "GENE",
     "LATE ELONGATED HYPOCOTYL",
     "Morning-phased MYB transcription factor partially redundant with CCA1; represses TOC1.",
     False),
    ("TOC1", "GENE",
     "TIMING OF CAB EXPRESSION 1 (PRR1)",
     "Evening-phased PRR protein; core oscillator component that represses CCA1 (negative feedback loop).",
     False),
    ("GI", "GENE",
     "GIGANTEA",
     "Afternoon/evening-phased clock protein; activates PRR37, CO, and EHD1 as part of the photoperiod-sensing module. sbgi-ems1 delays flowering ~30 days.",
     False),
    ("FKF1", "GENE",
     "FLAVIN-BINDING KELCH REPEAT F-BOX 1 (SbFFL)",
     "LOV-domain F-box protein activated by blue light; co-stabilises CO with GI in the late afternoon. Repressed by GHD7 (Tadesse 2024).",
     False),
    ("ELF3", "GENE",
     "EARLY FLOWERING 3",
     "Evening Complex scaffold; represses PRR37 and GHD7 (rice ortholog evidence). Inactivated post-translationally by PHYB. Reciprocally repressed by GHD7.",
     False),
    ("ELF4", "GENE",
     "EARLY FLOWERING 4",
     "Evening Complex subunit that assembles with LUX onto ELF3 docking protein (Nusinow 2011); required for EC activity.",
     True),
    ("LUX", "GENE",
     "LUX ARRHYTHMO",
     "Evening Complex DNA-binding subunit that targets PRR/Ghd7 promoters (rice OsLUX evidence; Andrade 2022).",
     True),
    ("PRR37", "GENE",
     "PSEUDO-RESPONSE REGULATOR 37 (Ma1 locus, Sobic.006G057866)",
     "Key LD floral repressor; directly represses EHD1 and florigens (FT1/FT8/FT10), and activates GHD7 and CO. Dominant Ma1 gives latest flowering. Ma-locus alias: Ma1.",
     False),
    ("GHD7", "GENE",
     "Grain number, plant height and heading date 7 (Ma6 locus, Sobic.006G004400)",
     "Major LD floral repressor; directly represses EHD1, FT1/FT8/FT10, ELF3, FKF1 (Tadesse 2024 ChIP-seq). Ma-locus alias: Ma6.",
     False),
    ("MA2_SMYD", "GENE",
     "MATURITY 2 (SMYD-family lysine methyltransferase, Sobic.002G302700)",
     "Enhances amplitude of PRR37 and CO transcription in LD. ma2 (L141*) flowers ~100 days earlier. Source node: no curated upstream regulator.",
     True),
    ("ID1", "GENE",
     "INDETERMINATE 1 (conserved maize ID1 / rice Ehd2 ortholog)",
     "Master regulator of sorghum flowering; activates CO, PRR37, GHD7, EHD1 and the florigens. sbid1-2 (Q199*) delays flowering ~170 days. Source node (no curated upstream regulator).",
     True),
    ("CO", "GENE",
     "CONSTANS (also SbHd1; CO-like transcription factor)",
     "B-box TF; activator of EHD1 and florigens in permissive backgrounds. Stabilised by FKF1-GI; destabilised by PHYB in LD daylight (E095). SbHd1 is treated as alias of CO (Judge G008).",
     False),
    ("EHD1", "GENE",
     "EARLY HEADING DATE 1",
     "B-type response regulator; primary direct activator of FT1/FT8/FT10. Repressed by PRR37 and GHD7 in LD.",
     False),
    ("FT1", "GENE",
     "FLOWERING LOCUS T 1 (SbCN15; Hd3a-subclade florigen)",
     "Mobile florigen; forms florigen activation complex with FD1 and GF14 at the SAM. Directly repressed by PHYB even under PRR37/GHD7-null background.",
     False),
    ("FT8", "GENE",
     "FLOWERING LOCUS T 8 (SbCN8; ZCN8-subclade florigen)",
     "Principal florigen in sorghum; binds GF14 (not FD1) for FAC. Activates SOC1 at the SAM.",
     False),
    ("FT10", "GENE",
     "FLOWERING LOCUS T 10 (SbCN12; ZCN8-subclade paralog)",
     "Major florigen; directly repressed by GHD7 (Tadesse 2024 ChIP-seq). Binds GF14.",
     False),
    ("FT12", "GENE",
     "FLOWERING LOCUS T 12 (FlrAvgD1, Sb06g012260, panicoid-specific PEBP)",
     "Floral suppressor; loss-of-function drove photoperiod-insensitive temperate adaptation (Cuevas 2016). Source node — no curated upstream regulator.",
     True),
    ("FD1", "GENE",
     "FLOWERING LOCUS D 1",
     "bZIP transcription factor; binds FT1 at the SAM to assemble the florigen activation complex (FAC) and activate AP1/SOC1.",
     False),
    ("GF14", "GENE",
     "General Regulatory Factor 14 (14-3-3 scaffold; Sb14-3-3 composite)",
     "14-3-3 scaffold; required component of the FAC with FT1/FT8/FT10 (Cai 2016, Wolabu 2016). Promotes flowering.",
     False),
    ("SOC1", "GENE",
     "SUPPRESSOR OF OVEREXPRESSION OF CO 1 (SbMADS31, Sobic.004G003434)",
     "MADS-box flowering integrator at the SAM; activated by florigens, SBP4, and LFY/AP1 feedback.",
     False),
    ("LFY", "GENE",
     "LEAFY",
     "Meristem-identity integrator; activated by SOC1 and activates AP1 in a mutual reinforcement loop.",
     False),
    ("AP1", "GENE",
     "APETALA 1 (SbMADS7, Sobic.002G010100; AP1/FUL clade)",
     "Terminal meristem-identity MADS-box; commits shoot apical meristem to floral fate.",
     False),
    ("AP2", "GENE",
     "APETALA 2 (Sobic.001G036800; rap2.7-ortholog)",
     "AP2-like floral repressor; targeted for cleavage by miR172a in the age pathway. Represses FT8 and directly delays flowering.",
     False),
    ("SBP19", "GENE",
     "SQUAMOSA PROMOTER BINDING PROTEIN 19 (Sobic.002G312300; SPL19)",
     "Age-pathway SPL TF; targeted by miR156h; activates miR172a transcription (age-pathway amplifier).",
     False),
    ("SBP4", "GENE",
     "SQUAMOSA PROMOTER BINDING PROTEIN 4",
     "Age-pathway SPL TF; targeted by miR156h; activates SOC1 at the SAM (age-pathway convergence with photoperiod pathway).",
     False),
    ("miR156h", "REGULATORY_RNA",
     "sbi-MIR156h",
     "Age-pathway microRNA; high at juvenile phase, declines with age. Cleaves SBP19 and SBP4 transcripts. Source node — intrinsic age program.",
     True),
    ("miR172a", "REGULATORY_RNA",
     "sbi-MIR172a",
     "Age-pathway microRNA; activated by SBP19 upon decline of miR156h. Cleaves AP2 transcripts to relieve flowering repression.",
     False),
    ("Flowering_Time", "PHENOTYPE",
     "Flowering time (days to anthesis)",
     "Days to flowering / heading in sorghum. Higher value = later flowering. Florigens (FT1/FT8/FT10), SOC1, AP1, GF14, and Gibberellin reduce days (sign=-1); FT12 and AP2 delay flowering (sign=+1).",
     False),
]

# ---------------------------------------------------------------------------
# Edge selection from the 111 curated edges
# ---------------------------------------------------------------------------
# Ordered by cascade layer. (curated_edge_id, sorghum_source, sorghum_target).
SELECTED_EDGES = [
    # Layer 0 — environmental inputs
    "E001",  # Light -> SbPhyB
    "E003",  # Light -> SbPhyC
    "E101",  # Light -> SbCCA1
    "E102",  # Light -> SbLHY
    "E005",  # Blue_Light -> SbFKF1
    "E073",  # Photoperiod_LD -> SbPRR37
    "E074",  # Photoperiod_LD -> SbGhd7
    # Layer 1 — photoreceptor outputs
    "E006",  # SbPhyB -> SbPRR37
    "E007",  # SbPhyB -> SbGhd7
    "E008",  # SbPhyB -> SbFT1 (PRR37/Ghd7-independent direct repression)
    "E095",  # SbPhyB -> SbCO (post-translational destabilisation in LD)
    "E106",  # SbPhyB -> SbELF3 (post-translational inactivation)
    "E009",  # SbPhyC -> SbPRR37
    "E010",  # SbPhyC -> SbGhd7
    # Layer 1 — clock core
    "E011",  # SbCCA1 -> SbTOC1
    "E012",  # SbTOC1 -> SbCCA1
    "E013",  # SbLHY -> SbTOC1
    "E014",  # SbCCA1 -> SbGI
    "E103",  # SbCCA1 -> SbPRR37
    # Layer 1 — Evening Complex
    "E100",  # SbELF4 -> SbELF3
    "E096",  # SbELF3 -> SbPRR37
    "E097",  # SbELF3 -> SbGhd7
    "E098",  # SbLUX -> SbPRR37
    "E099",  # SbLUX -> SbGhd7
    "E015",  # SbGhd7 -> SbELF3 (mutual inhibition)
    "E016",  # SbGhd7 -> SbFKF1
    # Layer 2 — GI/FKF1 module
    "E017",  # SbGI -> SbPRR37
    "E018",  # SbGI -> SbCO
    "E019",  # SbGI -> SbEhd1
    "E023",  # SbFKF1 -> SbCO
    # Layer 2 — Ma-locus / master regulators
    "E040",  # Ma2 -> SbPRR37
    "E041",  # Ma2 -> SbCO
    "E042",  # SbID1 -> SbCO
    "E045",  # SbID1 -> SbPRR37
    "E046",  # SbID1 -> SbGhd7
    "E104",  # SbID1 -> SbEhd1
    "E043",  # SbID1 -> SbFT8
    "E044",  # SbID1 -> SbFT10
    # Layer 3 — PRR37 / GHD7 / CO outputs
    "E024",  # SbPRR37 -> SbCO
    "E025",  # SbPRR37 -> SbEhd1
    "E026",  # SbPRR37 -> SbFT1
    "E027",  # SbPRR37 -> SbFT8
    "E028",  # SbPRR37 -> SbFT10
    "E029",  # SbGhd7 -> SbEhd1
    "E030",  # SbGhd7 -> SbFT1
    "E031",  # SbGhd7 -> SbFT8
    "E032",  # SbGhd7 -> SbFT10
    "E033",  # SbCO -> SbEhd1
    "E034",  # SbCO -> SbFT8
    "E035",  # SbCO -> SbFT10
    "E036",  # SbCO -> SbFT1
    # Layer 4 — Ehd1 -> florigens
    "E037",  # SbEhd1 -> SbFT1
    "E038",  # SbEhd1 -> SbFT8
    "E039",  # SbEhd1 -> SbFT10
    # Layer 5 — florigens -> FAC / SAM
    "E052",  # SbFT1 -> SbFD1
    "E053",  # SbFT1 -> Sb14-3-3
    "E054",  # SbFT8 -> Sb14-3-3
    "E055",  # SbFT10 -> Sb14-3-3
    "E056",  # SbFT1 -> SbSOC1
    "E057",  # SbFT8 -> SbSOC1
    "E058",  # SbFT10 -> SbSOC1
    # Layer 6 — SAM identity
    "E059",  # SbSOC1 -> SbLFY
    "E060",  # SbSOC1 -> SbAP1
    "E061",  # SbLFY -> SbAP1
    "E107",  # SbFD1 -> SbAP1
    # Age pathway
    "E047",  # miR156h -> SbSBP19
    "E048",  # miR156h -> SbSBP4
    "E049",  # SbSBP19 -> miR172a
    "E050",  # miR172a -> SbAP2
    "E051",  # SbAP2 -> SbFT8
    "E110",  # SbSBP4 -> SbSOC1
    # Phenotypic outputs (direct to Flowering_Time)
    "E062",  # SbFT1 -> Flowering_Time
    "E063",  # SbFT8 -> Flowering_Time
    "E064",  # SbFT10 -> Flowering_Time
    "E065",  # SbFT12 -> Flowering_Time
    "E067",  # SbAP2 -> Flowering_Time
    "E068",  # SbSOC1 -> Flowering_Time
    "E069",  # SbAP1 -> Flowering_Time
    "E109",  # Sb14-3-3 -> Flowering_Time
    "E071",  # Gibberellin -> Flowering_Time
]

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def main() -> None:
    with open(DATA / "curated_edges.json", "r", encoding="utf-8") as f:
        curated = json.load(f)

    curated_by_id = {e["edge_id"]: e for e in curated["edges"]}

    # 1) Build edges (rename nodes via NAME_MAP)
    edges_out = []
    for i, eid in enumerate(SELECTED_EDGES, start=1):
        e = curated_by_id[eid]
        src = NAME_MAP[e["source"]]
        tgt = NAME_MAP[e["target"]]
        evidence = []
        for ev in e.get("evidence", []):
            evidence.append({
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
        edges_out.append({
            "source": src,
            "target": tgt,
            "sign": int(e["sign"]),
            "edge_id": f"N{i:03d}",
            "effect": e.get("effect", ""),
            "mechanism": e.get("mechanism", ""),
            "evidence": evidence,
        })

    # 2) Compute in/out degree and correct is_source flags
    incoming = defaultdict(int)
    outgoing = defaultdict(int)
    activators = defaultdict(list)
    inhibitors = defaultdict(list)
    for e in edges_out:
        incoming[e["target"]] += 1
        outgoing[e["source"]] += 1
        if e["sign"] == 1:
            activators[e["target"]].append(e["source"])
        else:
            inhibitors[e["target"]].append(e["source"])

    # 3) Build nodes
    nodes_out = []
    for nid, ntype, full_name, desc, _hint in NODES:
        # is_source is true iff has no incoming edges
        is_src = incoming[nid] == 0
        nodes_out.append({
            "id": nid,
            "type": ntype,
            "full_name": full_name,
            "description": desc,
            "is_source": is_src,
        })

    src_count = sum(1 for n in nodes_out if n["is_source"])
    total_nodes = len(nodes_out)
    total_edges = len(edges_out)
    src_pct = round(100.0 * src_count / total_nodes, 1)

    # 4) Write network.json
    network = {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": "flowering_time",
            "phenotype_node": "Flowering_Time",
            "species": "Sorghum bicolor",
            "created": "2026-04-21",
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "source_nodes": src_count,
            "source_percentage": src_pct,
            "node_synonyms": {
                "PHYB": ["SbPhyB", "Ma3", "Sobic.001G394400"],
                "PHYC": ["SbPhyC", "Ma5", "Sobic.001G087100"],
                "PRR37": ["SbPRR37", "Ma1", "Sobic.006G057866"],
                "GHD7": ["SbGhd7", "Ma6", "Sb06g000570", "Sobic.006G004400"],
                "MA2_SMYD": ["Ma2", "SbSMYD", "Sobic.002G302700"],
                "CO": ["SbCO", "SbHd1", "CONSTANS", "SbCOL"],
                "ID1": ["SbID1", "INDETERMINATE1"],
                "EHD1": ["SbEhd1", "Early Heading Date 1"],
                "FT1": ["SbFT1", "SbCN15"],
                "FT8": ["SbFT8", "SbCN8", "Sobic.003G295300"],
                "FT10": ["SbFT10", "SbCN12"],
                "FT12": ["SbFT12", "FlrAvgD1", "Sb06g012260"],
                "GF14": ["Sb14-3-3", "14-3-3"],
                "SOC1": ["SbSOC1", "SbMADS31", "Sobic.004G003434"],
                "AP1": ["SbAP1", "SbMADS7", "Sobic.002G010100"],
                "AP2": ["SbAP2", "Sobic.001G036800", "rap2.7-ortholog"],
                "FKF1": ["SbFKF1", "SbFFL"],
                "GI": ["SbGI", "SbGIGANTEA"],
                "CCA1": ["SbCCA1"],
                "LHY": ["SbLHY"],
                "TOC1": ["SbTOC1", "SbPRR1"],
                "ELF3": ["SbELF3"],
                "ELF4": ["SbELF4"],
                "LUX": ["SbLUX"],
                "FD1": ["SbFD1"],
                "LFY": ["SbLFY"],
                "SBP19": ["SbSBP19", "SbSPL19", "Sobic.002G312300"],
                "SBP4": ["SbSBP4"],
                "miR156h": ["sbi-MIR156h"],
                "miR172a": ["sbi-MIR172a"],
            },
            "residual_gaps_for_builder_applied": [
                "G008: SbHd1 consolidated with SbCO; E092 (SbHd1->SbGhd7) DROPPED as rice-only mechanism (Hd1-Ghd7 complex) without sorghum-direct evidence.",
                "G005: SbPhyA and SbCRY1 DROPPED from model (no downstream edges; option (a) per judge recommendation).",
                "G011: SbGI has 1 curated inhibitor (CCA1) and 5 outgoing edges; flagged literature_gap for missing TOC1->GI and EC->GI edges.",
                "G014: SbFT13 NOT included (Wolabu 2016 reports non-detectable in tested tissues).",
                "G003_residual: EC edges (E096/E097/E098/E099/E100/E106/E111) retained in v1 with original confidence levels; rice ortholog inference noted in edge mechanisms."
            ],
            "motifs_applied": [
                "Perception Gate: Light -> PHYB -> PRR37 / GHD7 (no Light bypass to PRR37/GHD7/FT/Flowering_Time)",
                "Multi-Output Scaffold: PRR37 -> (FT1, FT8, FT10, EHD1, CO); GHD7 -> (FT1, FT8, FT10, EHD1, ELF3, FKF1); ID1 -> 6 targets",
                "Coherent Feed-Forward: PRR37 -| FT + PRR37 -> GHD7 -| EHD1 -> FT; ELF3 -| both PRR37 and GHD7",
                "Mutual Inhibition: CCA1 -| TOC1 -| CCA1 oscillator; GHD7 -| ELF3 / ELF3 -| GHD7 daylength switch",
                "Age-pathway convergence: miR156h -| SBP -> miR172a -| AP2; miR156h -| SBP4 -> SOC1"
            ],
            "bypass_policy": "Light NOT connected directly to PRR37/GHD7/FT/Flowering_Time. Photoperiod_SD DROPPED (direct FT activation bypass). Photoperiod_LD retained as coincidence-regime input to PRR37 and GHD7 (separate from raw Light)."
        },
        "nodes": nodes_out,
        "edges": edges_out,
    }
    (OUT / "network.json").write_text(json.dumps(network, indent=2), encoding="utf-8")

    # 5) Build algebraic equations
    alg_params = {
        "epsilon": 0.1,
        "K": 10.0,
        "activator_floor": 0.01,
        "damping": 0.7,
        "direction_threshold": 0.05,
        "max_iterations": 100,
        "convergence_tolerance": 0.0001,
    }

    alg_equations = []
    ode_equations = []
    node_annotations = []

    for nid, ntype, full_name, desc, _hint in NODES:
        acts = activators[nid]
        inhs = inhibitors[nid]
        is_src = (incoming[nid] == 0)

        # Algebraic formula
        if is_src:
            alg_formula = f"{nid} = gene_modifier + exogenous_supply"
        else:
            # Activation term
            if acts:
                if len(acts) == 1:
                    a_term = f"max({acts[0]}, 0.01)^(1/1)"
                else:
                    prod = " * ".join(f"max({a}, 0.01)" for a in acts)
                    a_term = f"({prod})^(1/{len(acts)})"
            else:
                a_term = "1.0"  # no activators → neutral
            # Inhibition term
            if inhs:
                if len(inhs) == 1:
                    i_prod = inhs[0]
                else:
                    i_prod = " * ".join(inhs)
                i_term = f"min(1/max({i_prod}, 0.1), 10.0)"
            else:
                i_term = "1.0"
            alg_formula = f"{nid} = {a_term} * {i_term} * gene_modifier + exogenous_supply"

        alg_equations.append({
            "node": nid,
            "type": ntype,
            "is_source": is_src,
            "activators": acts,
            "inhibitors": inhs,
            "formula": alg_formula,
        })

        # ODE formula (Hill, K=1.0, n=2)
        if is_src:
            ode_formula = f"{nid} = gene_modifier + exogenous_supply"
        else:
            if acts:
                a_term = " * ".join(f"f({a})" for a in acts)
            else:
                a_term = "1.0"
            if inhs:
                i_term = " * ".join(f"g({i})" for i in inhs)
            else:
                i_term = "1.0"
            ode_formula = f"{nid} = {a_term} * {i_term} * gene_modifier + exogenous_supply"

        ode_equations.append({
            "node": nid,
            "activators": acts,
            "inhibitors": inhs,
            "formula": ode_formula,
        })

        # Node annotation
        node_annotations.append({
            "node": nid,
            "full_name": full_name,
            "type": ntype,
            "description": desc,
            "in_degree": incoming[nid],
            "out_degree": outgoing[nid],
            "total_degree": incoming[nid] + outgoing[nid],
            "is_source": is_src,
            "n_activators": len(acts),
            "n_inhibitors": len(inhs),
        })

    alg_file = {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": "flowering_time",
            "species": "Sorghum bicolor",
            "created": "2026-04-21",
            "total_equations": len(alg_equations),
        },
        "parameters": alg_params,
        "equations": alg_equations,
    }
    (OUT / "algebraic_equations.json").write_text(
        json.dumps(alg_file, indent=2), encoding="utf-8"
    )

    ode_file = {
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
        "equations": ode_equations,
    }
    (OUT / "ode_equations.json").write_text(
        json.dumps(ode_file, indent=2), encoding="utf-8"
    )

    ann_file = {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": "flowering_time",
            "species": "Sorghum bicolor",
            "created": "2026-04-21",
            "total_nodes": len(node_annotations),
        },
        "annotations": node_annotations,
    }
    (OUT / "node_annotations.json").write_text(
        json.dumps(ann_file, indent=2), encoding="utf-8"
    )

    # Summary
    print(f"Wrote {total_nodes} nodes, {total_edges} edges")
    print(f"Sources: {src_count} ({src_pct}%)")
    print("Per-node input counts:")
    for nid, _, _, _, _ in NODES:
        if incoming[nid] > 0:
            print(
                f"  {nid}: {len(activators[nid])} activators, "
                f"{len(inhibitors[nid])} inhibitors"
            )


if __name__ == "__main__":
    main()
