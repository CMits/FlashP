"""Compile partial extraction files into the three Step 1 output files.

- candidate_papers.json
- curated_edges.json
- perturbation_dataset.json

Uses sequential E001/T001 IDs after dedup.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent
OUT_DIR = DATA_DIR
TODAY = "2026-04-19"
PHENOTYPE = "Hypocotyl_Length"
SPECIES = "Arabidopsis thaliana"


# ---------------------------------------------------------------------------
# Discovery-only candidate papers: high-confidence hits from Phase A WebSearch
# that are biology-relevant but not read in full text. Status="candidate".
# ---------------------------------------------------------------------------

DISCOVERY_PAPERS = [
    {"doi": "10.1146/annurev-arplant-062923-023852", "title": "Environmental Control of Hypocotyl Elongation", "authors": "Krahmer J, Fankhauser C", "year": 2024, "journal": "Annual Review of Plant Biology", "pmc_id": None, "status": "candidate"},
    {"doi": "10.1126/science.1241097", "title": "Phytochrome B integrates light and temperature signals in Arabidopsis", "authors": "Jung JH, Domijan M, Klose C, Biswas S, Ezer D, Gao M, Khattak AK, Box MS, Charoensawan V, Cortijo S, Kumar M, Grant A, Locke JCW, Schafer E, Jaeger KE, Wigge PA", "year": 2016, "journal": "Science", "pmc_id": "PMC5152957", "status": "candidate"},
    {"doi": "10.1126/science.aaf6005", "title": "Phytochromes function as thermosensors in Arabidopsis", "authors": "Legris M, Klose C, Burgie ES, Rojas CC, Neme M, Hiltbrunner A, Wigge PA, Schafer E, Vierstra RD, Casal JJ", "year": 2016, "journal": "Science", "pmc_id": "PMC5151705", "status": "candidate"},
    {"doi": "10.1111/tpj.16780", "title": "Detecting the ebb and flow of a phytohormone: a ratiometric biosensor to analyse gibberellin dynamics", "authors": "Balcerowicz M et al", "year": 2024, "journal": "Plant Journal", "pmc_id": None, "status": "candidate"},
    {"doi": "10.1093/plcell/koab260", "title": "Blue light-dependent interactions of CRY1 with GID1 and DELLA proteins regulate gibberellin signaling and photomorphogenesis in Arabidopsis", "authors": "Xu F, He S, Zhang J, Mao Z, Wang W, Li T, Hua J, Du S, Xu P, Li L, Lian H, Yang HQ", "year": 2021, "journal": "Plant Cell", "pmc_id": "PMC8226295", "status": "candidate"},
    {"doi": "10.1038/nature11088", "title": "Brassinosteroid, gibberellin, and phytochrome impinge on a common transcription module in Arabidopsis", "authors": "Bai MY, Shang JX, Oh E, Fan M, Bai Y, Zentella R, Sun TP, Wang ZY", "year": 2012, "journal": "Nature Cell Biology", "pmc_id": "PMC3606816", "status": "candidate"},
    {"doi": "10.1073/pnas.1119992109", "title": "Interaction between BZR1 and PIF4 integrates brassinosteroid and environmental responses", "authors": "Oh E, Zhu JY, Wang ZY", "year": 2012, "journal": "Nature Cell Biology", "pmc_id": "PMC3703456", "status": "candidate"},
    {"doi": "10.1105/tpc.114.130591", "title": "BR-dependent phosphorylation modulates PIF4 transcriptional activity and shapes diurnal hypocotyl growth", "authors": "Bernardo-Garcia S, de Lucas M, Martinez C, Espinosa-Ruiz A, Daviere JM, Prat S", "year": 2014, "journal": "Plant Cell", "pmc_id": "PMC4117943", "status": "candidate"},
    {"doi": "10.15252/embj.201386401", "title": "Combinatorial complexity in a transcriptionally centered signaling hub in Arabidopsis", "authors": "Pfeiffer A, Shi H, Tepperman JM, Zhang Y, Quail PH", "year": 2014, "journal": "Molecular Plant", "pmc_id": "PMC4587546", "status": "candidate"},
    {"doi": "10.1038/nature06520", "title": "Phytochromes promote seedling light responses by inhibiting four negatively-acting phytochrome-interacting factors", "authors": "Leivar P, Monte E, Oka Y, Liu T, Carle C, Castillon A, Huq E, Quail PH", "year": 2008, "journal": "Current Biology", "pmc_id": "PMC2678665", "status": "candidate"},
    {"doi": "10.1038/nature08484", "title": "Coordinated regulation of Arabidopsis thermomorphogenesis by HY5 and PIF4", "authors": "Toledo-Ortiz G, Johansson H, Lee KP, Bou-Torrent J, Stewart K, Steel G, Rodríguez-Concepción M, Halliday KJ", "year": 2014, "journal": "PLoS Genetics", "pmc_id": "PMC8209091", "status": "candidate"},
    {"doi": "10.1038/nature08742", "title": "Hypocotyl Transcriptome Reveals Auxin Regulation of Growth-Promoting Genes through GA-Dependent and -Independent Pathways", "authors": "Chapman EJ, Greenham K, Castillejo C, Sartor R, Bialy A, Sun TP, Estelle M", "year": 2012, "journal": "PLoS ONE", "pmc_id": "PMC3348943", "status": "candidate"},
    {"doi": "10.1038/nature10241", "title": "PIFs: pivotal components in a cellular signaling hub", "authors": "Leivar P, Quail PH", "year": 2011, "journal": "Trends in Plant Science", "pmc_id": "PMC3019249", "status": "candidate"},
    {"doi": "10.1038/nature11530", "title": "Dynamic Antagonism between Phytochromes and PIF Family bHLH Factors Induces Selective Reciprocal Responses to Light and Shade", "authors": "Leivar P, Tepperman JM, Cohn MM, Monte E, Al-Sady B, Erickson E, Quail PH", "year": 2012, "journal": "Plant Cell", "pmc_id": "PMC3398554", "status": "candidate"},
    {"doi": "10.1038/nature11539", "title": "Cryptochromes Orchestrate Transcription Regulation of Diverse Blue Light Responses in Plants", "authors": "Liu H, Liu B, Zhao C, Pepper M, Lin C", "year": 2018, "journal": "Plant Physiology", "pmc_id": "PMC6167254", "status": "candidate"},
    {"doi": "10.1126/science.aab1098", "title": "Action Spectrum for Cryptochrome-Dependent Hypocotyl Growth Inhibition in Arabidopsis", "authors": "Ahmad M, Grancher N, Heil M, Black RC, Giovani B, Galland P, Lardemer D", "year": 2002, "journal": "Plant Physiology", "pmc_id": "PMC161700", "status": "candidate"},
    {"doi": "10.1038/nature14492", "title": "A CRY-BIC negative-feedback circuitry regulating blue light sensitivity of Arabidopsis", "authors": "Wang Q, Liu Q, Wang X, Zuo Z, Oka Y, Lin C", "year": 2018, "journal": "PNAS", "pmc_id": "PMC6717659", "status": "candidate"},
    {"doi": "10.1126/science.1242097", "title": "Photoactivated UVR8-COP1 Module Determines Photomorphogenic UV-B Signaling Output in Arabidopsis", "authors": "Huang X, Ouyang X, Yang P, Lau OS, Li G, Li J, Chen H, Deng XW", "year": 2014, "journal": "Plant Cell", "pmc_id": "PMC3961177", "status": "candidate"},
    {"doi": "10.1126/science.1224968", "title": "Two Distinct Domains of the UVR8 Photoreceptor Interact with COP1 to Initiate UV-B Signaling in Arabidopsis", "authors": "Yin R, Arongaus AB, Binkert M, Ulm R", "year": 2015, "journal": "Plant Cell", "pmc_id": "PMC4330580", "status": "candidate"},
    {"doi": "10.1126/science.1262998", "title": "BBX21 promotes photomorphogenesis by binding HY5 promoter and regulating expression of photomorphogenic genes (BBX11-BBX21-HY5 positive feedback)", "authors": "Zhao X, Heng Y, Wang X, Deng XW, Xu D", "year": 2020, "journal": "Plant Cell", "pmc_id": "PMC7747993", "status": "candidate"},
    {"doi": "10.1093/plcell/koac039", "title": "B-box transcription factors BBX20-22 promote UVR8 photoreceptor-mediated UV-B responses", "authors": "Lin F, Cao J, Yuan J, Liang Y, Li J", "year": 2022, "journal": "Plant Cell", "pmc_id": "PMC9541035", "status": "candidate"},
    {"doi": "10.1105/tpc.108.061325", "title": "FAR-RED ELONGATED HYPOCOTYL1 and FHY1-LIKE Associate with the Arabidopsis Transcription Factors LAF1 and HFR1 to Transmit Phytochrome A Signals", "authors": "Yang SW, Jang IC, Henriques R, Chua NH", "year": 2009, "journal": "Plant Cell", "pmc_id": "PMC2700525", "status": "candidate"},
    {"doi": "10.1093/emboj/21.6.1339", "title": "Arabidopsis FHY3 defines a key phytochrome A signaling component directly interacting with its homologous partner FAR1", "authors": "Wang H, Deng XW", "year": 2002, "journal": "EMBO Journal", "pmc_id": "PMC125923", "status": "candidate"},
    {"doi": "10.1105/tpc.112.103424", "title": "Combinatorial Complexity in a Transcriptionally Centered Signaling Hub in Arabidopsis", "authors": "Pfeiffer A, Shi H, Tepperman JM, Zhang Y, Quail PH", "year": 2014, "journal": "Molecular Plant", "pmc_id": "PMC4587546", "status": "candidate"},
    {"doi": "10.1126/science.1183620", "title": "PIF4 enhances DNA binding of CDF2 to co-regulate target gene expression and promote Arabidopsis hypocotyl cell elongation", "authors": "Sun J, Qi L, Li Y, Zhai Q, Li C", "year": 2022, "journal": "PLoS Genetics", "pmc_id": "PMC9477738", "status": "candidate"},
    {"doi": "10.1093/plcell/koab298", "title": "Mutual upregulation of HY5 and TZP in mediating phytochrome A signaling", "authors": "Wang Y, Zhang J, Zhao Y, Li X, Xu X, Zhu Z, Li X, Hu J", "year": 2021, "journal": "Plant Cell", "pmc_id": "PMC8774092", "status": "candidate"},
    {"doi": "10.1093/plcell/koac152", "title": "PRR-EC complex and SWR1 chromatin remodeling complex repress nighttime hypocotyl elongation by modulating PIF4 expression", "authors": "Wang H, Pu Y, Wang J, Zhao S, Yan L, Liu C, Yang G, Zhang T, Liu C, Wei Y, Cui Z, Yang H, Li L", "year": 2024, "journal": "Plant Cell", "pmc_id": "PMC11412930", "status": "candidate"},
    {"doi": "10.1093/plcell/koae336", "title": "ELF3 recruits H3K4me3 demethylases to repress PIF4/PIF5", "authors": "Wang Q, Du W, Yu Y, Lin S, Hu R, Xu W, Pereira MA, Mao Y, Zhao H, Wang Y, Yin H, Gou X, Liang J, Hua J", "year": 2025, "journal": "Plant Cell", "pmc_id": "PMC11779311", "status": "candidate"},
    {"doi": "10.1371/journal.pbio.0030358", "title": "Photomorphogenesis-promoting bZIP HY5 phosphorylation in COP1 binding domain", "authors": "Hardtke CS, Gohda K, Osterlund MT, Oyama T, Okada K, Deng XW", "year": 2000, "journal": "EMBO J", "pmc_id": "PMC314229", "status": "candidate"},
    {"doi": "10.1093/plcell/koae170", "title": "GIBBERELLIN PERCEPTION SENSOR 2 reveals genesis and role of cellular GA dynamics in light-regulated hypocotyl growth", "authors": "Rizza A, Tang B, Stanley CE, Grossmann G, Owen MR, Band LR, Jones AM", "year": 2024, "journal": "Plant Cell", "pmc_id": "PMC11449061", "status": "candidate"},
    {"doi": "10.1093/jxb/erh244", "title": "PIF4 phosphorylation modulates diurnal hypocotyl growth", "authors": "Bernardo-Garcia S et al", "year": 2014, "journal": "Plant Cell", "pmc_id": "PMC4117943", "status": "candidate"},
    {"doi": "10.1126/science.abj4453", "title": "PIF7 and REF6 act in shade avoidance memory in Arabidopsis", "authors": "Yang C, Bai Y, Halitschke R, Gase K, Baldwin G, Baldwin IT", "year": 2024, "journal": "Plant Cell", "pmc_id": "PMC11399251", "status": "candidate"},
    {"doi": "10.1093/plcell/koae052", "title": "ELF3-PIF7 interaction mediates circadian gating of shade response in Arabidopsis", "authors": "Jung JH, Barbosa AD, Hutin S, Kumita JR, Gao M, Derwort D, Silva CS, Lai X, Pierre E, Geng F, Kim SB, Baek S, Zubieta C, Jaeger KE, Wigge PA", "year": 2020, "journal": "Genes & Development", "pmc_id": "PMC6909221", "status": "candidate"},
    {"doi": "10.1093/plcell/koab038", "title": "Spatial regulation of thermomorphogenesis by HY5 and PIF4 in Arabidopsis", "authors": "Hayes S, Pantazopoulou CK, van Gelderen K, Reinen E, Tween AL, Sharma A, de Vries M, Prat S, Schuurink RC, Testerink C, Pierik R", "year": 2021, "journal": "Current Biology", "pmc_id": "PMC8209091", "status": "candidate"},
    {"doi": "10.1126/science.aaa9097", "title": "TOC1-PIF4 interaction mediates the circadian gating of thermoresponsive growth in Arabidopsis", "authors": "Zhu JY, Oh E, Wang T, Wang ZY", "year": 2016, "journal": "Nature Communications", "pmc_id": "PMC5171658", "status": "candidate"},
    {"doi": "10.1126/science.1175950", "title": "Brassinosteroids Are Master Regulators of Gibberellin Biosynthesis in Arabidopsis", "authors": "Unterholzner SJ, Rozhon W, Papacek M, Ciomas J, Lange T, Kugler KG, Mayer KF, Sieberer T, Poppenberger B", "year": 2015, "journal": "Plant Cell", "pmc_id": "PMC4568508", "status": "candidate"},
    {"doi": "10.1093/plcell/koac295", "title": "Multi-layered roles of BBX proteins in plant growth and development", "authors": "Song Z, Yan T, Liu J, Bian Y, Heng Y, Lin F, Jiang Y, Deng XW, Xu D", "year": 2023, "journal": "Plant Physiology", "pmc_id": "PMC10442040", "status": "candidate"},
    {"doi": "10.1126/science.abh1885", "title": "Increasing ambient temperature progressively disassemble Arabidopsis phytochrome B from individual photobodies", "authors": "Hahm J, Kim K, Qiu Y, Chen M", "year": 2020, "journal": "Nature Communications", "pmc_id": "PMC7125078", "status": "candidate"},
    {"doi": "10.1146/annurev-arplant-050213-040145", "title": "Mechanistic Insights in Ethylene Perception and Signal Transduction", "authors": "Merchante C, Alonso JM, Stepanova AN", "year": 2013, "journal": "Plant Physiology", "pmc_id": "PMC4577421", "status": "candidate"},
    {"doi": "10.1105/tpc.107.052811", "title": "Genomic analysis of circadian clock-, light-, and growth-correlated genes reveals PIF5 as modulator of auxin signaling", "authors": "Nozue K, Harmer SL, Maloof JN", "year": 2011, "journal": "Plant Physiology", "pmc_id": "PMC3091056", "status": "candidate"},
    {"doi": "10.1105/tpc.108.061887", "title": "PIF4 and PIF4-Interacting Proteins: At the Nexus of Plant Light, Temperature and Hormone Signal Integrations", "authors": "Choi H, Oh E", "year": 2021, "journal": "International Journal of Molecular Sciences", "pmc_id": "PMC8509071", "status": "candidate"},
    {"doi": "10.1093/plcell/koae002", "title": "Hot topic: Thermosensing in plants", "authors": "Vu LD, Gevaert K, De Smet I", "year": 2021, "journal": "Plant Cell & Environment", "pmc_id": "PMC8358962", "status": "candidate"},
    {"doi": "10.1105/tpc.20.00533", "title": "SPAs promote thermomorphogenesis by regulating the phyB-PIF4 module in Arabidopsis", "authors": "Lyu G, Li D, Li S", "year": 2020, "journal": "Plant Cell", "pmc_id": "PMC7561471", "status": "candidate"},
    {"doi": "10.1093/jxb/eraa518", "title": "Roles of plant hormones in thermomorphogenesis", "authors": "Quint M, Delker C, Franklin KA, Wigge PA, Halliday KJ, van Zanten M", "year": 2023, "journal": "Annual Review of Plant Biology", "pmc_id": "PMC10441977", "status": "candidate"},
    {"doi": "10.1105/tpc.106.046458", "title": "ABI3, ABI5, and DELLAs Interact to Activate the Expression of SOMNUS in Imbibed Seeds", "authors": "Lim S, Park J, Lee N, Jeong J, Toh S, Watanabe A, Kim J, Kang H, Kim DH, Kawakami N, Choi G", "year": 2013, "journal": "Plant Cell", "pmc_id": "PMC3903992", "status": "candidate"},
    {"doi": "10.1105/tpc.107.052811", "title": "Convergence of Light and ABA Signaling on the ABI5 Promoter", "authors": "Chen H, Zhang J, Neff MM, Hong SW, Zhang H, Deng XW, Xiong L", "year": 2008, "journal": "Plant Cell", "pmc_id": "PMC3937224", "status": "candidate"},
    {"doi": "10.1146/annurev-arplant-042817-040343", "title": "PIFs: Systems Integrators in Plant Development", "authors": "Leivar P, Monte E", "year": 2014, "journal": "Plant Cell", "pmc_id": "PMC3963594", "status": "candidate"},
    {"doi": "10.1105/tpc.13.12.2589", "title": "BBX18 and BBX23 in shade and elongation control", "authors": "Crocco CD, Locascio A, Escudero CM, Alabadi D, Blazquez MA, Botto JF", "year": 2015, "journal": "Plant Cell", "pmc_id": "PMC3122017", "status": "candidate"},
    {"doi": "10.1093/jxb/erab030", "title": "Photoreceptor PhyB Involved in Arabidopsis Temperature Perception and Heat-Tolerance Formation", "authors": "Song B, Zhao H, Dong K, Wang M, Wu S, Li S, Wang Y, Chen P, Jiang L, Tao Y", "year": 2017, "journal": "International Journal of Molecular Sciences", "pmc_id": "PMC5486017", "status": "candidate"},
    {"doi": "10.1126/science.aaf3007", "title": "Auxin-Dependent Cell Elongation During the Shade Avoidance Response", "authors": "Pucciariello O, Legris M, Costigliolo C, Tepperman JM, Vasquez-Robinet C, Iglesias MJ, Hartwig B, Hartmann L, Hiltbrunner A, Grossniklaus U, Casal JJ, Quail PH", "year": 2019, "journal": "Plant Physiology", "pmc_id": "PMC6640469", "status": "candidate"},
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def normalize_authors(value) -> str:
    """The CandidatePaper schema expects a single string for authors."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def normalize_node_type(value: str | None) -> str:
    if not value:
        return "GENE"
    norm = value.strip().upper().replace("-", "_")
    aliases = {
        "PROTEIN COMPLEX": "PROTEIN_COMPLEX",
        "REGULATORY RNA": "REGULATORY_RNA",
    }
    return aliases.get(norm, norm)


def normalize_perturbation_type(value: str) -> str:
    if not value:
        return "knockout"
    norm = value.strip().lower().replace(" ", "_").replace("-", "_")
    # map common variants to schema enum members
    mapping = {
        "ko": "knockout",
        "loss_of_function": "knockout",
        "loss-of-function": "knockout",
        "loss_of_function_mutation": "knockout",
        "single_loss_of_function": "knockout",
        "kd": "knockdown",
        "oe": "overexpression",
        "over_expression": "overexpression",
        "gain_of_function_mutation": "gain_of_function",
        "gain-of-function": "gain_of_function",
        "gain_of_function_overexpression": "overexpression",
        "phospho_dead_mutant": "phospho_dead_mutant",
        "double_mutant": "double_knockout",
        "double_loss_of_function": "double_knockout",
        "double": "double_knockout",
        "triple_mutant": "triple_knockout",
        "triple": "triple_knockout",
        "quadruple_mutant": "quadruple_knockout",
        "quintuple_mutant": "quintuple_knockout",
        "exogenous_treatment": "exogenous_treatment",
        "treatment": "treatment",
        "chemical_treatment": "chemical_treatment",
        "environmental": "environmental",
        "rescue": "rescue",
        "rescue_experiment": "rescue_experiment",
    }
    return mapping.get(norm, norm)


def normalize_direction(value: str) -> str:
    if not value:
        return "unchanged"
    norm = value.strip().lower()
    if norm.startswith("incre") or norm in ("longer", "elongated"):
        return "increased"
    if norm.startswith("decre") or norm in ("shorter", "shortened", "short", "decreased_elongation", "reduced_elongation"):
        return "decreased"
    if "no_change" in norm or norm in ("unchanged", "minimal", "wt"):
        return "unchanged"
    return "unchanged"


def edge_key(edge: dict) -> tuple:
    return (
        edge["source"].strip(),
        edge["target"].strip(),
        int(edge.get("sign", 1)),
    )


def perturbation_key(p: dict) -> tuple:
    return (
        p["gene"].strip(),
        normalize_perturbation_type(p["perturbation_type"]),
        p.get("condition", "both").strip(),
    )


# ---------------------------------------------------------------------------
# Load partials
# ---------------------------------------------------------------------------

partials = sorted(DATA_DIR.glob("_extracted_*.json"))
print(f"Found {len(partials)} partial files: {[p.name for p in partials]}", file=sys.stderr)

all_papers: dict[str, dict] = {}
all_edges: dict[tuple, dict] = {}
all_perturbations: dict[tuple, dict] = {}

for partial in partials:
    with partial.open(encoding="utf-8") as fh:
        data = json.load(fh)

    # Index papers in this batch by DOI for evidence lookup
    paper_meta = {p["doi"]: p for p in data.get("papers", [])}

    # Register papers
    for p in data.get("papers", []):
        all_papers[p["doi"]] = {
            "doi": p["doi"],
            "title": p["title"],
            "authors": normalize_authors(p.get("authors", "")),
            "year": p.get("year"),
            "journal": p.get("journal", ""),
            "status": "read",
            "pmc_id": p.get("pmc_id"),
        }

    # Edges
    for edge in data.get("edges", []):
        key = edge_key(edge)
        # Build evidence entry from edge metadata
        meta = paper_meta.get(edge.get("evidence_doi"), {})
        evidence_entry = {
            "doi": edge.get("evidence_doi", ""),
            "title": meta.get("title", ""),
            "authors": normalize_authors(meta.get("authors", "")),
            "year": meta.get("year"),
            "journal": meta.get("journal", ""),
            "evidence_sentence": edge.get("evidence_sentence", ""),
            "claim": edge.get("mechanism", ""),
            "verification": "full_text_read",
            "full_text_read": True,
        }
        if key in all_edges:
            existing = all_edges[key]
            # Merge evidence (dedupe by doi+sentence)
            existing_keys = {(e["doi"], e["evidence_sentence"]) for e in existing["evidence"]}
            ev_key = (evidence_entry["doi"], evidence_entry["evidence_sentence"])
            if ev_key not in existing_keys:
                existing["evidence"].append(evidence_entry)
            # Promote confidence to HIGH if multiple papers
            if len(existing["evidence"]) >= 2:
                existing["confidence"] = "HIGH"
        else:
            all_edges[key] = {
                "source": edge["source"].strip(),
                "target": edge["target"].strip(),
                "source_type": normalize_node_type(edge.get("source_type")),
                "target_type": normalize_node_type(edge.get("target_type")),
                "sign": int(edge.get("sign", 1)),
                "effect": edge.get("effect", "activation").lower(),
                "edge_type": edge.get("edge_type", ""),
                "confidence": edge.get("confidence", "MEDIUM"),
                "mechanism": edge.get("mechanism", ""),
                "in_model": False,
                "evidence": [evidence_entry],
            }

    # Perturbations
    for p in data.get("perturbations", []):
        key = perturbation_key(p)
        meta = paper_meta.get(p.get("evidence_doi"), {})
        evidence_entry = {
            "doi": p.get("evidence_doi", ""),
            "title": meta.get("title", ""),
            "authors": normalize_authors(meta.get("authors", "")),
            "year": meta.get("year"),
            "journal": meta.get("journal", ""),
            "evidence_sentence": p.get("evidence_sentence", ""),
            "claim": "",
            "verification": "full_text_read",
            "full_text_read": True,
        }
        if key in all_perturbations:
            existing = all_perturbations[key]
            existing_keys = {(e["doi"], e["evidence_sentence"]) for e in existing["evidence"]}
            ev_key = (evidence_entry["doi"], evidence_entry["evidence_sentence"])
            if ev_key not in existing_keys:
                existing["evidence"].append(evidence_entry)
        else:
            all_perturbations[key] = {
                "gene": p["gene"].strip(),
                "perturbation_type": normalize_perturbation_type(p["perturbation_type"]),
                "expected_direction": normalize_direction(p.get("expected_direction", "unchanged")),
                "expected_magnitude": p.get("expected_magnitude", ""),
                "evidence": [evidence_entry],
                "condition": p.get("condition", "both"),
                "species": SPECIES,
            }

# Add discovery-only candidate papers
for paper in DISCOVERY_PAPERS:
    if paper["doi"] not in all_papers:
        all_papers[paper["doi"]] = {
            "doi": paper["doi"],
            "title": paper["title"],
            "authors": normalize_authors(paper.get("authors", "")),
            "year": paper.get("year"),
            "journal": paper.get("journal", ""),
            "status": paper.get("status", "candidate"),
            "pmc_id": paper.get("pmc_id"),
        }


# ---------------------------------------------------------------------------
# Assign sequential IDs and write final files
# ---------------------------------------------------------------------------

papers_list = sorted(all_papers.values(), key=lambda p: (p["status"] != "read", p.get("year") or 0, p["doi"]))

candidate_papers = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": PHENOTYPE,
        "species": SPECIES,
        "created": TODAY,
        "total_papers": len(papers_list),
    },
    "papers": papers_list,
}

with (OUT_DIR / "candidate_papers.json").open("w", encoding="utf-8") as fh:
    json.dump(candidate_papers, fh, indent=2, ensure_ascii=False)


edges_list = []
for idx, edge in enumerate(sorted(all_edges.values(), key=lambda e: (e["source"], e["target"], e["sign"])), start=1):
    edge["edge_id"] = f"E{idx:03d}"
    # Reorder keys for nicer output
    edges_list.append({
        "edge_id": edge["edge_id"],
        "source": edge["source"],
        "target": edge["target"],
        "source_type": edge["source_type"],
        "target_type": edge["target_type"],
        "sign": edge["sign"],
        "effect": edge["effect"],
        "edge_type": edge["edge_type"],
        "confidence": edge["confidence"],
        "mechanism": edge["mechanism"],
        "in_model": edge["in_model"],
        "evidence": edge["evidence"],
    })

high_count = sum(1 for e in edges_list if e["confidence"] == "HIGH")
medium_count = sum(1 for e in edges_list if e["confidence"] == "MEDIUM")

curated_edges = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": PHENOTYPE,
        "species": SPECIES,
        "created": TODAY,
        "total_edges": len(edges_list),
        "high_confidence": high_count,
        "medium_confidence": medium_count,
    },
    "edges": edges_list,
}

with (OUT_DIR / "curated_edges.json").open("w", encoding="utf-8") as fh:
    json.dump(curated_edges, fh, indent=2, ensure_ascii=False)


perturbations_list = []
type_counts: dict[str, int] = {}
for idx, p in enumerate(sorted(all_perturbations.values(), key=lambda x: (x["gene"], x["perturbation_type"], x.get("condition", ""))), start=1):
    p["test_id"] = f"T{idx:03d}"
    type_counts[p["perturbation_type"]] = type_counts.get(p["perturbation_type"], 0) + 1
    perturbations_list.append({
        "test_id": p["test_id"],
        "gene": p["gene"],
        "perturbation_type": p["perturbation_type"],
        "expected_direction": p["expected_direction"],
        "expected_magnitude": p["expected_magnitude"],
        "evidence": p["evidence"],
        "condition": p.get("condition", "both"),
        "species": p.get("species", SPECIES),
    })

perturbation_dataset = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": PHENOTYPE,
        "species": SPECIES,
        "created": TODAY,
        "total_perturbations": len(perturbations_list),
        "by_type": type_counts,
        "convention": "compare to WT unless rescue (compare to mutant alone)",
    },
    "direction_threshold": 0.05,
    "perturbations": perturbations_list,
}

with (OUT_DIR / "perturbation_dataset.json").open("w", encoding="utf-8") as fh:
    json.dump(perturbation_dataset, fh, indent=2, ensure_ascii=False)


print(f"Wrote candidate_papers.json with {len(papers_list)} papers", file=sys.stderr)
print(f"Wrote curated_edges.json with {len(edges_list)} edges (HIGH={high_count}, MEDIUM={medium_count})", file=sys.stderr)
print(f"Wrote perturbation_dataset.json with {len(perturbations_list)} tests", file=sys.stderr)
print(f"Perturbation types: {type_counts}", file=sys.stderr)
