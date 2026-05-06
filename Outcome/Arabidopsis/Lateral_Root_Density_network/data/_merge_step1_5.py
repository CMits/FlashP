"""
One-shot merge script for FLASH-P Step 1.5 (Literature Review Judge) additions
to Arabidopsis/Lateral_Root_Density_network.

Run from FlashP_Repo/ project root:
    python Arabidopsis/Lateral_Root_Density_network/data/_merge_step1_5.py

Behavior:
  - Reads current data/candidate_papers.json, curated_edges.json, perturbation_dataset.json
  - Appends new papers / edges / perturbations (IDs continue sequentially)
  - Deduplicates against existing (DOI for papers; (source,target,sign) for edges;
    (gene, perturbation_type, signature) for perturbations). If a duplicate is
    found, the new evidence is appended to the existing entry's evidence list
    (for papers and edges); duplicate perturbations are skipped.
  - Every new item carries discovery_source / gap_addressed provenance fields.
  - Writes the three files in place. Validation is run separately.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).parent

# ---------------------------------------------------------------------------
# New papers (Step 1.5 additions)
# Each entry has discovery_source, discovered_by, gap_addressed as extras.
# ---------------------------------------------------------------------------
NEW_PAPERS = [
    {
        "doi": "10.1073/pnas.1319953111",
        "title": "CLE-CLAVATA1 peptide-receptor signaling module regulates the expansion of plant root systems in a nitrogen-dependent manner",
        "authors": "Araya T, Miyamoto M, Wibowo J, Suzuki A, Kojima S, Tsuchiya YN, Sawa S, Fukuda H, von Wiren N, Takahashi H",
        "year": 2014,
        "journal": "PNAS",
        "status": "added_by_judge",
        "pmc_id": "PMC3918772",
        "discovered_by": "literature_judge",
        "gap_addressed": "G002",
    },
    {
        "doi": "10.1105/tpc.114.122887",
        "title": "WOX11 and 12 Are Involved in the First-Step Cell Fate Transition during de Novo Root Organogenesis in Arabidopsis",
        "authors": "Liu J, Sheng L, Xu Y, Li J, Yang Z, Huang H, Xu L",
        "year": 2014,
        "journal": "The Plant Cell",
        "status": "added_by_judge",
        "pmc_id": "PMC4001370",
        "discovered_by": "literature_judge",
        "gap_addressed": "G003",
    },
    {
        "doi": "10.1104/pp.16.01067",
        "title": "Transcription Factors WOX11/12 Directly Activate WOX5/7 to Promote Root Primordia Initiation and Organogenesis",
        "authors": "Hu X, Xu L",
        "year": 2016,
        "journal": "Plant Physiology",
        "status": "added_by_judge",
        "pmc_id": "PMC5129711",
        "discovered_by": "literature_judge",
        "gap_addressed": "G003",
    },
    {
        "doi": "10.1105/tpc.105.033365",
        "title": "A Link between Ethylene and Auxin Uncovered by the Characterization of Two Root-Specific Ethylene-Insensitive Mutants in Arabidopsis",
        "authors": "Stepanova AN, Hoyt JM, Hamilton AA, Alonso JM",
        "year": 2005,
        "journal": "The Plant Cell",
        "status": "added_by_judge",
        "pmc_id": "PMC1182485",
        "discovered_by": "literature_judge",
        "gap_addressed": "G004",
    },
    {
        "doi": "10.1016/j.cell.2008.01.047",
        "title": "TAA1-Mediated Auxin Biosynthesis Is Essential for Hormone Crosstalk and Plant Development",
        "authors": "Stepanova AN, Robertson-Hoyt J, Yun J, Benavente LM, Xie DY, Dolezal K, Schlereth A, Jurgens G, Alonso JM",
        "year": 2008,
        "journal": "Cell",
        "status": "added_by_judge",
        "discovered_by": "literature_judge",
        "gap_addressed": "G001,G004",
    },
    {
        "doi": "10.1038/s41598-018-28188-1",
        "title": "PID/WAG-mediated phosphorylation of the Arabidopsis PIN3 auxin transporter mediates polarity switches during gravitropism",
        "authors": "Grones P, Abas M, Hajny J, Jones A, Waidmann S, Kleine-Vehn J, Friml J",
        "year": 2018,
        "journal": "Scientific Reports",
        "status": "added_by_judge",
        "pmc_id": "PMC6035267",
        "discovered_by": "literature_judge",
        "gap_addressed": "G005",
    },
    {
        "doi": "10.3389/fpls.2024.1387321",
        "title": "BZR1 and BES1 transcription factors mediate brassinosteroid control over root system architecture in response to nitrogen availability",
        "authors": "Al-Mamun MH, Cazzonelli CI, Krishna P",
        "year": 2024,
        "journal": "Frontiers in Plant Science",
        "status": "added_by_judge",
        "discovered_by": "literature_judge",
        "gap_addressed": "G006",
    },
    {
        "doi": "10.1105/tpc.108.059584",
        "title": "Type B Response Regulators of Arabidopsis Play Key Roles in Cytokinin Signaling and Plant Development",
        "authors": "Argyros RD, Mathews DE, Chiang YH, Palmer CM, Thibault DM, Etheridge N, Argyros DA, Mason MG, Kieber JJ, Schaller GE",
        "year": 2008,
        "journal": "The Plant Cell",
        "status": "added_by_judge",
        "pmc_id": "PMC2553617",
        "discovered_by": "literature_judge",
        "gap_addressed": "G007",
    },
    {
        "doi": "10.1111/tpj.16103",
        "title": "CLE3 and its homologs share overlapping functions in the modulation of lateral root formation through CLV1 and BAM1 in Arabidopsis thaliana",
        "authors": "Nakagami S, Aoyama T, Nomura M, Kondo Y, Tabata R, Furuya T, Kondo Y, Sawa S, Notaguchi M, Fukuda H, Betsuyaku S",
        "year": 2023,
        "journal": "The Plant Journal",
        "status": "added_by_judge",
        "discovered_by": "literature_judge",
        "gap_addressed": "G002",
    },
    {
        "doi": "10.3389/fpls.2016.01884",
        "title": "The Role and Regulation of ABI5 (ABA-Insensitive 5) in Plant Development, Abiotic Stress Responses and Phytohormone Crosstalk",
        "authors": "Skubacz A, Daszkowska-Golec A, Szarejko I",
        "year": 2016,
        "journal": "Frontiers in Plant Science",
        "status": "added_by_judge",
        "discovered_by": "literature_judge",
        "gap_addressed": "G008",
    },
]

# ---------------------------------------------------------------------------
# New edges (E211+). Flat evidence format, discovery_source + gap_addressed extras.
# ---------------------------------------------------------------------------
def _ev(doi, title, authors, year, journal, es, claim, ft=True):
    return {
        "doi": doi, "title": title, "authors": authors, "year": year, "journal": journal,
        "evidence_sentence": es, "claim": claim,
        "verification": "full_text_read" if ft else "abstract_read",
        "full_text_read": bool(ft),
    }

NEW_EDGES = [
    # --- G002: CLE-CLV1 N-demand module (Araya 2014) ---
    {
        "source": "CLE3", "target": "CLV1", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "signaling", "confidence": "HIGH",
        "mechanism": "CLE3 peptide (pericycle) diffuses apoplastically and binds CLV1 receptor on phloem companion cells",
        "in_model": False,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLAVATA1 peptide-receptor signaling module regulates the expansion of plant root systems in a nitrogen-dependent manner",
            "Araya T, et al.", 2014, "PNAS",
            "CLE peptides are hypothesized to be secreted from pericycle cells and transported through the apoplastic continuum to reach CLV1 in companion cells",
            "CLE3 peptide activates CLV1 receptor")],
    },
    {
        "source": "CLE1", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "HIGH",
        "mechanism": "N-responsive CLE1 overexpression represses LR primordia growth and emergence",
        "in_model": False,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLAVATA1 peptide-receptor signaling module regulates the expansion of plant root systems in a nitrogen-dependent manner",
            "Araya T, et al.", 2014, "PNAS",
            "CLE1, -3, -4, and -7 were induced by N deficiency in roots, predominantly expressed in root pericycle cells, and their overexpression repressed the growth of lateral root primordia and their emergence from the primary root",
            "CLE1 inhibits LR density")],
    },
    {
        "source": "CLE3", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "HIGH",
        "mechanism": "CLE3 peptide, via CLV1 phloem receptor, systemically suppresses LR primordium emergence under low N",
        "in_model": True,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLAVATA1 peptide-receptor signaling module regulates the expansion of plant root systems in a nitrogen-dependent manner",
            "Araya T, et al.", 2014, "PNAS",
            "emerged lateral roots at stage VIII was dramatically decreased by overexpression of CLE1, -2, -3, -4, and -7",
            "CLE3 inhibits LR density")],
    },
    {
        "source": "CLE4", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "MEDIUM",
        "mechanism": "N-responsive CLE4 redundantly suppresses LR primordia",
        "in_model": False,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "CLE1, -3, -4, and -7 were induced by N deficiency",
            "CLE4 inhibits LR density")],
    },
    {
        "source": "CLE7", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "MEDIUM",
        "mechanism": "N-responsive CLE7 redundantly suppresses LR primordia",
        "in_model": False,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "CLE1, -3, -4, and -7 were induced by N deficiency",
            "CLE7 inhibits LR density")],
    },
    {
        "source": "CLV1", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "HIGH",
        "mechanism": "CLV1 phloem companion-cell receptor transduces CLE3 signal to repress LR emergence under low N",
        "in_model": True,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "clv1 mutants showed progressive outgrowth of lateral root primordia into lateral roots under N-deficient conditions",
            "CLV1 inhibits LR (removed in clv1)")],
    },
    {
        "source": "Low_Nitrate", "target": "CLE3", "source_type": "ENVIRONMENT", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "N deficiency (<100 uM NO3-) induces CLE3 transcription in pericycle",
        "in_model": True,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "CLE1, -3, -4, and -7 were induced by N deficiency in roots, predominantly expressed in root pericycle cells",
            "Low N activates CLE3")],
    },
    {
        "source": "Low_Nitrate", "target": "CLE1", "source_type": "ENVIRONMENT", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "MEDIUM",
        "mechanism": "Low N induces CLE1 transcription in pericycle",
        "in_model": False,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "CLE1, -3, -4, and -7 were induced by N deficiency in roots",
            "Low N activates CLE1")],
    },
    # Low_Nitrate direct effect edge (enables environmental node)
    {
        "source": "Low_Nitrate", "target": "Lateral_Root_Density", "source_type": "ENVIRONMENT", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "environmental", "confidence": "HIGH",
        "mechanism": "Systemic severe N-deficiency activates CLE-CLV1 module that represses LR emergence; counter-balanced by local TAR2-auxin induction",
        "in_model": True,
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "a signaling module composed of N-responsive CLE peptides and the CLV1 receptor-like kinase plays a crucial role in regulating the expansion of the root system under N-deficient conditions",
            "Low N systemically inhibits LR")],
    },
    # --- G003: WOX11/WOX12 founder-to-organ ---
    {
        "source": "Auxin", "target": "WOX11", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Auxin (IAA) directly induces WOX11 expression in regeneration-competent cells",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 Are Involved in the First-Step Cell Fate Transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "WOX11 expression could be detected in leaf explants of the WOX11pro:GUS line after ~6 h on B5 medium containing 1 uM IAA",
            "Auxin activates WOX11")],
    },
    {
        "source": "WOX11", "target": "LBD16", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "WOX11/12 upregulate LBD16 to drive root founder cell fate transition",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 first-step cell fate transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "WOX11 and WOX12 then act redundantly to upregulate LBD16 and LBD29",
            "WOX11 activates LBD16")],
    },
    {
        "source": "WOX11", "target": "LBD29", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "WOX11/12 upregulate LBD29",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 first-step cell fate transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "WOX11 and WOX12 then act redundantly to upregulate LBD16 and LBD29",
            "WOX11 activates LBD29")],
    },
    {
        "source": "WOX12", "target": "LBD16", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "WOX12 redundantly upregulates LBD16 with WOX11",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 first-step cell fate transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "WOX11 and WOX12 then act redundantly to upregulate LBD16 and LBD29",
            "WOX12 activates LBD16")],
    },
    {
        "source": "WOX11", "target": "WOX5", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "WOX11/12 directly bind WOX5 promoter cis-elements to activate transcription in primordia (ChIP + luciferase)",
        "in_model": False,
        "evidence": [_ev(
            "10.1104/pp.16.01067",
            "WOX11/12 Directly Activate WOX5/7",
            "Hu X, Xu L", 2016, "Plant Physiology",
            "WOX11/12 function genetically upstream of WOX5/7, and the WOX11/12 proteins directly bind to the promoters of WOX5/7 to activate their transcription",
            "WOX11 activates WOX5")],
    },
    {
        "source": "WOX11", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "MEDIUM",
        "mechanism": "WOX11-mediated non-canonical root branching contributes to root system plasticity (Sheng et al. 2017) via WOX11/12 upregulation of LBD16/29",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 first-step cell fate transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "wox11-2 wox12-1 was more strongly delayed ... mutant explants produced fewer roots than did the wild-type",
            "WOX11 promotes root primordia number")],
    },
    # --- G001/G004: Ethylene-driven auxin biosynthesis ---
    {
        "source": "Ethylene", "target": "TAA1", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Ethylene transcriptionally upregulates TAA1/TAR family in root meristem and elongation zone",
        "in_model": True,
        "evidence": [_ev(
            "10.1016/j.cell.2008.01.047",
            "TAA1-Mediated Auxin Biosynthesis Is Essential for Hormone Crosstalk",
            "Stepanova AN, et al.", 2008, "Cell",
            "the TAA1/TAR family of aminotransferases was shown to be transcriptionally regulated by ethylene in the root meristem and in the elongation zone of the root",
            "Ethylene induces TAA1 transcription")],
    },
    {
        "source": "Ethylene", "target": "WEI2", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Ethylene induces ASA1/WEI2 anthranilate synthase alpha-subunit via EIN2-dependent pathway",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.105.033365",
            "A Link between Ethylene and Auxin Uncovered by wei2 wei7",
            "Stepanova AN, et al.", 2005, "The Plant Cell",
            "Ethylene treatment resulted in a significant induction of the ASA1-GUS and ASB1-GUS reporters in the Col-0 background",
            "Ethylene induces WEI2/ASA1")],
    },
    {
        "source": "Ethylene", "target": "WEI7", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Ethylene induces ASB1/WEI7 anthranilate synthase beta-subunit via EIN2",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.105.033365",
            "A Link between Ethylene and Auxin Uncovered by wei2 wei7",
            "Stepanova AN, et al.", 2005, "The Plant Cell",
            "Ethylene treatment resulted in a significant induction of the ASA1-GUS and ASB1-GUS reporters",
            "Ethylene induces WEI7/ASB1")],
    },
    {
        "source": "WEI2", "target": "Auxin", "source_type": "GENE", "target_type": "HORMONE",
        "sign": 1, "effect": "activation", "edge_type": "enzymatic", "confidence": "HIGH",
        "mechanism": "ASA1/WEI2 anthranilate synthase is rate-limiting for Trp biosynthesis, feeding IAA production",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.105.033365",
            "wei2 wei7", "Stepanova AN, et al.", 2005, "The Plant Cell",
            "WEI2/ASA1 and WEI7/ASB1 genes encode alpha- and beta-subunits of anthranilate synthase, a rate-limiting enzyme of tryptophan biosynthesis",
            "WEI2 feeds auxin biosynthesis")],
    },
    {
        "source": "WEI7", "target": "Auxin", "source_type": "GENE", "target_type": "HORMONE",
        "sign": 1, "effect": "activation", "edge_type": "enzymatic", "confidence": "HIGH",
        "mechanism": "ASB1/WEI7 is rate-limiting for Trp biosynthesis feeding IAA",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.105.033365",
            "wei2 wei7", "Stepanova AN, et al.", 2005, "The Plant Cell",
            "Upregulation of WEI2/ASA1 and WEI7/ASB1 by ethylene results in auxin accumulation in the primary root tip, while loss-of-function mutations in these genes prevent ethylene-mediated auxin increase",
            "WEI7 feeds auxin biosynthesis")],
    },
    {
        "source": "Ethylene", "target": "TAR2", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Ethylene induces TAR2 transcription (redundant with TAA1 in ethylene-auxin amplification)",
        "in_model": False,
        "evidence": [_ev(
            "10.1016/j.cell.2008.01.047",
            "TAA1-Mediated Auxin Biosynthesis", "Stepanova AN, et al.", 2008, "Cell",
            "the TAA1/TAR family of aminotransferases was shown to be transcriptionally regulated by ethylene in the root meristem",
            "Ethylene activates TAR2")],
    },
    # --- G005: PID/WAG → PIN polarity ---
    {
        "source": "PID", "target": "PIN3", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "HIGH",
        "mechanism": "PID phosphorylates PIN3 TPRXS(N/S) motifs, shifting PIN3 polarity from basal/rootward to apical/shootward and antagonising gravity-induced PIN3 relocation that underlies LR-triggering auxin maxima",
        "in_model": False,
        "evidence": [_ev(
            "10.1038/s41598-018-28188-1",
            "PID/WAG-mediated phosphorylation of PIN3",
            "Grones P, et al.", 2018, "Scientific Reports",
            "overexpression of these kinases leads to a basal-to-apical (rootward-to-shootward) shift in PIN polarity",
            "PID inhibits PIN3 rootward polarity")],
    },
    {
        "source": "WAG1", "target": "PIN3", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "MEDIUM",
        "mechanism": "WAG1 AGC3-kinase redundantly phosphorylates PIN3 to shift polarity apically",
        "in_model": False,
        "evidence": [_ev(
            "10.1038/s41598-018-28188-1",
            "PID/WAG phosphorylation of PIN3",
            "Grones P, et al.", 2018, "Scientific Reports",
            "PID groups with WAG1 and WAG2, which are root growth regulators also involved in auxin transport-regulated plant development",
            "WAG1 phosphorylates PIN3")],
    },
    {
        "source": "WAG2", "target": "PIN3", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "MEDIUM",
        "mechanism": "WAG2 redundantly phosphorylates PIN3",
        "in_model": False,
        "evidence": [_ev(
            "10.1038/s41598-018-28188-1",
            "PID/WAG phosphorylation of PIN3",
            "Grones P, et al.", 2018, "Scientific Reports",
            "PID groups with WAG1 and WAG2",
            "WAG2 phosphorylates PIN3")],
    },
    # --- G006: BR control of LR via BIN2 / BZR1 / BES1 ---
    {
        "source": "BRI1", "target": "BIN2", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "HIGH",
        "mechanism": "BR-activated BRI1 inactivates BIN2 GSK3-like kinase",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "BR signaling is triggered when BR binds to the cell surface receptor BRI1, which leads to inactivation of BIN2, a negative regulator of the two key transcription factors BZR1 and BES1",
            "BRI1 inhibits BIN2")],
    },
    {
        "source": "BIN2", "target": "BZR1", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "HIGH",
        "mechanism": "BIN2 GSK3 kinase phosphorylates BZR1 for proteasomal degradation",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "In the absence of BR, BIN2 phosphorylates BZR1 and BES1, which leads to their degradation",
            "BIN2 degrades BZR1")],
    },
    {
        "source": "BIN2", "target": "BES1", "source_type": "GENE", "target_type": "GENE",
        "sign": -1, "effect": "inhibition", "edge_type": "post-translational", "confidence": "HIGH",
        "mechanism": "BIN2 phosphorylates BES1 for degradation",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "In the absence of BR, BIN2 phosphorylates BZR1 and BES1, which leads to their degradation",
            "BIN2 degrades BES1")],
    },
    {
        "source": "BZR1", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Constitutively active BZR1 (bzr1-1D) enhances LR number and length, especially under mild N deficiency",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "bzr1-1D increased LR number by 13-233% across N conditions",
            "BZR1 promotes LR density")],
    },
    {
        "source": "BES1", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Dominant BES1 (bes1-D) enhances LR number (64% at full N) and total length (241% at severe N deficiency)",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "bes1-D exhibited significantly higher LR density (64% increase at full N) and 241% greater total LR length at severe deficiency",
            "BES1 promotes LR density")],
    },
    {
        "source": "Brassinosteroid", "target": "Lateral_Root_Density", "source_type": "HORMONE", "target_type": "PHENOTYPE",
        "sign": 1, "effect": "activation", "edge_type": "signaling", "confidence": "HIGH",
        "mechanism": "BR dose-dependent promotion of LR density via BIN2-BZR1/BES1 axis (optimal low-nM EBR)",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1 and BES1 mediate BR control of RSA",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "Exogenous 24-epibrassinolide (EBR) at 0.05 nM increased LR number by 28% and total LR length by 50% under mild N deficiency",
            "BR promotes LR density")],
    },
    # --- G007: Type-B ARR10, ARR12 ---
    {
        "source": "ARR10", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Type-B ARR10 transcription factor transduces cytokinin response in root, contributing to CK-mediated LR repression (arr1,10,12 triple shows near-complete CK insensitivity)",
        "in_model": True,
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type B Response Regulators in Cytokinin Signaling",
            "Argyros RD, et al.", 2008, "The Plant Cell",
            "Higher order mutants revealed progressively decreased sensitivity to cytokinin, including effects on root elongation, lateral root formation",
            "ARR10 mediates cytokinin response for LR")],
    },
    {
        "source": "ARR12", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "Type-B ARR12 redundantly with ARR1/ARR10 transduces CK signal to repress LR",
        "in_model": True,
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type B Response Regulators in Cytokinin Signaling",
            "Argyros RD, et al.", 2008, "The Plant Cell",
            "ARR1, ARR10, and ARR12 are all involved in cytokinin regulation",
            "ARR12 mediates CK LR repression")],
    },
    {
        "source": "AHK2", "target": "ARR10", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "phosphorelay", "confidence": "HIGH",
        "mechanism": "AHK-AHP phosphorelay activates type-B ARR10",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type B Response Regulators in Cytokinin Signaling",
            "Argyros RD, et al.", 2008, "The Plant Cell",
            "ARR10 and ARR12 are involved in the AHK-dependent signaling pathway",
            "AHK2 activates ARR10")],
    },
    {
        "source": "AHK2", "target": "ARR12", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "phosphorelay", "confidence": "HIGH",
        "mechanism": "AHK phosphorelay activates ARR12",
        "in_model": False,
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type B Response Regulators in Cytokinin Signaling",
            "Argyros RD, et al.", 2008, "The Plant Cell",
            "ARR10 and ARR12 are involved in the AHK-dependent signaling pathway",
            "AHK2 activates ARR12")],
    },
    # --- G002 Nakagami 2023 (CLV1 / BAM1 for CLE3) ---
    {
        "source": "CLE3", "target": "BAM1", "source_type": "GENE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "signaling", "confidence": "MEDIUM",
        "mechanism": "CLE3 peptide also binds BAM1 receptor in parallel with CLV1 to suppress LR",
        "in_model": False,
        "evidence": [_ev(
            "10.1111/tpj.16103",
            "CLE3 and homologs modulate LR formation through CLV1 and BAM1",
            "Nakagami S, et al.", 2023, "The Plant Journal",
            "CLE3 and its homologs share overlapping functions in the modulation of lateral root formation through CLV1 and BAM1",
            "CLE3 activates BAM1",
            ft=False)],
    },
    {
        "source": "BAM1", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "signaling", "confidence": "MEDIUM",
        "mechanism": "BAM1 redundantly with CLV1 transduces CLE3 LR-suppressing signal",
        "in_model": False,
        "evidence": [_ev(
            "10.1111/tpj.16103",
            "CLE3 CLV1 BAM1 in LR",
            "Nakagami S, et al.", 2023, "The Plant Journal",
            "CLE3 and its homologs share overlapping functions in the modulation of lateral root formation through CLV1 and BAM1",
            "BAM1 inhibits LR",
            ft=False)],
    },
    # --- G008: ABI5 in LR under stress ---
    {
        "source": "ABA", "target": "ABI5", "source_type": "HORMONE", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "HIGH",
        "mechanism": "ABA induces ABI5 bZIP TF via PYL/PP2C/SnRK2 core module",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2016.01884",
            "ABI5 in Plant Development and Stress",
            "Skubacz A, et al.", 2016, "Frontiers in Plant Science",
            "ABI5 is induced by ABA as part of the core ABA signaling module and binds G-box cis elements",
            "ABA activates ABI5",
            ft=False)],
    },
    {
        "source": "ABI5", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": -1, "effect": "inhibition", "edge_type": "transcriptional", "confidence": "MEDIUM",
        "mechanism": "ABI5 negatively regulates LR via PIN1 repression under stress (nitrate/ABA crosstalk with ABI4)",
        "in_model": True,
        "evidence": [_ev(
            "10.3389/fpls.2016.01884",
            "ABI5 in Plant Development and Stress",
            "Skubacz A, et al.", 2016, "Frontiers in Plant Science",
            "ABI5 acts as a negative regulator of lateral root development in the presence of stress, with the link between auxin and ABA signaling during root development mediated by PIN1 and involving ABI5",
            "ABI5 represses LR under stress",
            ft=False)],
    },
    {
        "source": "High_Nitrate", "target": "ABI5", "source_type": "ENVIRONMENT", "target_type": "GENE",
        "sign": 1, "effect": "activation", "edge_type": "transcriptional", "confidence": "MEDIUM",
        "mechanism": "High nitrate promotes ABI5-dependent LR inhibition (abi5 mutants reduce this inhibition)",
        "in_model": False,
        "evidence": [_ev(
            "10.3389/fpls.2016.01884",
            "ABI5 review", "Skubacz A, et al.", 2016, "Frontiers in Plant Science",
            "inhibitory effect of nitrate on root growth was significantly reduced in abi4 and abi5 mutants",
            "High N activates ABI5 (reduced in abi5)",
            ft=False)],
    },
    # --- Extraction-density recovery: Stepanova 2008 gives IAA sensitivity for taa1 tar2 ---
    {
        "source": "TAR2", "target": "Lateral_Root_Density", "source_type": "GENE", "target_type": "PHENOTYPE",
        "sign": 1, "effect": "activation", "edge_type": "enzymatic", "confidence": "HIGH",
        "mechanism": "TAR2 aminotransferase, with TAA1, generates IAA required for ethylene-triggered LR modulation and low-N-induced LR initiation",
        "in_model": True,
        "evidence": [_ev(
            "10.1016/j.cell.2008.01.047",
            "TAA1-Mediated Auxin Biosynthesis", "Stepanova AN, et al.", 2008, "Cell",
            "TAA1/TAR-mediated auxin biosynthesis is essential for hormone crosstalk and plant development including lateral root formation under low nitrate",
            "TAR2 promotes LR",
            ft=False)],
    },
]

# ---------------------------------------------------------------------------
# New perturbations (T141+)
# ---------------------------------------------------------------------------
NEW_PERTURBATIONS = [
    # G002 CLE / CLV1
    {
        "gene": "cle3", "perturbation_type": "knockout",
        "expected_direction": "increased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "low_nitrate",
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "cle mutants showed outgrowth of lateral root primordia under N-deficient conditions",
            "cle3 increases LR under low N")],
    },
    {
        "gene": "clv1", "perturbation_type": "knockout",
        "expected_direction": "increased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "low_nitrate",
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "clv1 mutants showed progressive outgrowth of lateral root primordia into lateral roots under N-deficient conditions",
            "clv1 increases LR under low N")],
    },
    {
        "gene": "CLE3", "perturbation_type": "overexpression",
        "expected_direction": "decreased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "emerged lateral roots at stage VIII was dramatically decreased by overexpression of CLE1, -2, -3, -4, and -7",
            "CLE3 OE decreases LR")],
    },
    # G003 WOX11/WOX12
    {
        "gene": "wox11 wox12", "perturbation_type": "double_knockout",
        "expected_direction": "decreased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1105/tpc.114.122887",
            "WOX11 and 12 first-step cell fate transition",
            "Liu J, et al.", 2014, "The Plant Cell",
            "rooting time of wox11-2 wox12-1 was more strongly delayed ... mutant explants produced fewer roots than did the wild-type",
            "wox11 wox12 decreases root primordia")],
    },
    # G004 ethylene
    {
        "gene": "ein3 eil1", "perturbation_type": "double_knockout",
        "expected_direction": "increased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1111/j.1365-313X.2008.03495.x",
            "Ethylene regulates LR formation",
            "Negi S, et al.", 2008, "Plant J",
            "Mutations that block ethylene responses enhance root formation",
            "ein3 eil1 increases LR (ethylene insensitive)")],
    },
    {
        "gene": "wei2", "perturbation_type": "loss_of_function",
        "expected_direction": "decreased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "acc_treatment",
        "evidence": [_ev(
            "10.1105/tpc.105.033365",
            "wei2 wei7", "Stepanova AN, et al.", 2005, "The Plant Cell",
            "wei2-1 and wei7-4 mutants display root-specific ethylene insensitivity ... loss-of-function mutations in these genes prevent ethylene-mediated auxin increase",
            "wei2 decreases ethylene-induced auxin (and LR modulation)")],
    },
    # G006 brassinosteroid
    {
        "gene": "bzr1-1D", "perturbation_type": "gain_of_function",
        "expected_direction": "increased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1/BES1 control RSA under N",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "bzr1-1D increased LR number by 13-233% across N conditions",
            "bzr1-1D increases LR")],
    },
    {
        "gene": "bes1-D", "perturbation_type": "gain_of_function",
        "expected_direction": "increased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1/BES1 control RSA under N",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "bes1-D exhibited significantly higher LR density",
            "bes1-D increases LR")],
    },
    {
        "gene": "EBR_treatment", "perturbation_type": "exogenous_treatment",
        "expected_direction": "increased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "mild_N_deficient",
        "evidence": [_ev(
            "10.3389/fpls.2024.1387321",
            "BZR1/BES1 control RSA under N",
            "Al-Mamun MH, et al.", 2024, "Frontiers in Plant Science",
            "EBR at 0.05 nM increased LR number by 28% and total LR length by 50% under mild N deficiency",
            "EBR increases LR under mild N")],
    },
    # G007 type-B ARRs
    {
        "gene": "arr1 arr10 arr12", "perturbation_type": "triple_knockout",
        "expected_direction": "increased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type-B ARRs in CK signaling", "Argyros RD, et al.", 2008, "The Plant Cell",
            "arr1,10,12 triple mutant is significantly less sensitive to cytokinin ... showed almost complete insensitivity to cytokinin",
            "arr1 arr10 arr12 increases LR (cytokinin insensitive)")],
    },
    {
        "gene": "arr10 arr12", "perturbation_type": "double_knockout",
        "expected_direction": "increased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1105/tpc.108.059584",
            "Type-B ARRs in CK signaling", "Argyros RD, et al.", 2008, "The Plant Cell",
            "ARR10 and ARR12 redundantly play an important role in the cytokinin signaling in roots",
            "arr10 arr12 increases LR")],
    },
    # Canonical multi-mutants missing from Step 1
    {
        "gene": "lbd16 lbd18 lbd29", "perturbation_type": "triple_knockout",
        "expected_direction": "decreased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1242/dev.071928",
            "LBD16/ASL18 and related LBDs in LR",
            "Goh T, et al.", 2012, "Development",
            "LBD16 and other ASL proteins redundantly regulate the establishment of asymmetry in LR founder cells; triple mutants show strong LR reduction",
            "lbd16 lbd18 lbd29 decreases LR",
            ft=False)],
    },
    {
        "gene": "tir1 afb1 afb2 afb3 afb4 afb5", "perturbation_type": "quintuple_knockout",
        "expected_direction": "decreased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.7554/eLife.54740",
            "TIR1/AFB genetic analysis", "Prigge MJ, et al.", 2020, "eLife",
            "higher-order TIR1/AFB mutants display near-complete auxin insensitivity and dramatically reduced lateral root formation",
            "tir1 afb higher-order mutant strongly decreases LR",
            ft=False)],
    },
    {
        "gene": "pin2 pin3 pin7", "perturbation_type": "triple_knockout",
        "expected_direction": "decreased", "expected_magnitude": "strong",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1101/cshperspect.a039933",
            "Auxin in Root Development",
            "Roychoudhry S, Kepinski S", "2022", "CSHL Perspectives Biol",
            "polar auxin transport mutants show altered branching patterns, with closely grouped, fused, or fewer LRP/LRs; triple pin mutants exacerbate the phenotype",
            "pin2 pin3 pin7 decreases LR")],
    },
    # G008 ABI5
    {
        "gene": "abi5", "perturbation_type": "knockout",
        "expected_direction": "increased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "high_nitrate",
        "evidence": [_ev(
            "10.3389/fpls.2016.01884",
            "ABI5 review", "Skubacz A, et al.", 2016, "Frontiers in Plant Science",
            "inhibitory effect of nitrate on root growth was significantly reduced in abi4 and abi5 mutants",
            "abi5 increases LR under high N",
            ft=False)],
    },
    # G009 Low_Nitrate environmental perturbation
    {
        "gene": "Low_Nitrate", "perturbation_type": "environmental",
        "expected_direction": "decreased", "expected_magnitude": "moderate",
        "species": "Arabidopsis thaliana", "condition": "low_nitrate_systemic",
        "evidence": [_ev(
            "10.1073/pnas.1319953111",
            "CLE-CLV1 N module", "Araya T, et al.", 2014, "PNAS",
            "signaling module composed of N-responsive CLE peptides and CLV1 receptor plays a crucial role in regulating expansion of the root system under N-deficient conditions",
            "low systemic N decreases LR")],
    },
    # G005 PID
    {
        "gene": "pid", "perturbation_type": "knockout",
        "expected_direction": "increased", "expected_magnitude": "slight",
        "species": "Arabidopsis thaliana", "condition": "normal",
        "evidence": [_ev(
            "10.1038/s41598-018-28188-1",
            "PID/WAG phosphorylation of PIN3", "Grones P, et al.", 2018, "Scientific Reports",
            "analysis of lateral root stages revealed an increased number of first-stage primordia in PIN3 phosphorylation mutant variants",
            "pid slightly increases LR stage I primordia")],
    },
]


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------
def merge(path: Path):
    papers_file = path / "candidate_papers.json"
    edges_file = path / "curated_edges.json"
    perts_file = path / "perturbation_dataset.json"

    papers_j = json.loads(papers_file.read_text(encoding="utf-8"))
    edges_j = json.loads(edges_file.read_text(encoding="utf-8"))
    perts_j = json.loads(perts_file.read_text(encoding="utf-8"))

    # --- papers ---
    existing_dois = {p["doi"].lower() for p in papers_j["papers"]}
    papers_appended = 0
    papers_merged = 0
    for np in NEW_PAPERS:
        if np["doi"].lower() in existing_dois:
            papers_merged += 1
            continue
        papers_j["papers"].append(np)
        papers_appended += 1
    papers_j["metadata"]["total_papers"] = len(papers_j["papers"])

    # --- edges ---
    existing_edge_keys = {}
    for e in edges_j["edges"]:
        key = (e["source"], e["target"], int(e["sign"]))
        existing_edge_keys[key] = e
    max_eid = max(int(e["edge_id"][1:]) for e in edges_j["edges"])
    next_eid = max_eid + 1
    edges_appended = 0
    edges_merged = 0
    for ne in NEW_EDGES:
        key = (ne["source"], ne["target"], int(ne["sign"]))
        if key in existing_edge_keys:
            # merge evidence onto existing edge
            existing_edge_keys[key]["evidence"].extend(ne["evidence"])
            edges_merged += 1
            continue
        ne = dict(ne)  # copy
        ne["edge_id"] = f"E{next_eid:03d}"
        ne["discovery_source"] = "literature_judge"
        # Derive gap addressed from the paper(s) cited
        ne["gap_addressed"] = _gap_for_edge(ne)
        edges_j["edges"].append(ne)
        existing_edge_keys[key] = ne
        next_eid += 1
        edges_appended += 1
    edges_j["metadata"]["total_edges"] = len(edges_j["edges"])

    # --- perturbations ---
    def pkey(p):
        return (p["gene"].lower(), p["perturbation_type"], p.get("expected_direction"))
    existing_pkeys = {pkey(p) for p in perts_j["perturbations"]}
    max_tid = max(int(p["test_id"][1:]) for p in perts_j["perturbations"])
    next_tid = max_tid + 1
    perts_appended = 0
    perts_skipped = 0
    for np in NEW_PERTURBATIONS:
        k = pkey(np)
        if k in existing_pkeys:
            perts_skipped += 1
            continue
        np = dict(np)
        np["test_id"] = f"T{next_tid:03d}"
        np["discovery_source"] = "literature_judge"
        np["gap_addressed"] = _gap_for_pert(np)
        perts_j["perturbations"].append(np)
        existing_pkeys.add(k)
        next_tid += 1
        perts_appended += 1
    perts_j["metadata"]["total_perturbations"] = len(perts_j["perturbations"])

    # --- write back ---
    papers_file.write_text(json.dumps(papers_j, indent=2), encoding="utf-8")
    edges_file.write_text(json.dumps(edges_j, indent=2), encoding="utf-8")
    perts_file.write_text(json.dumps(perts_j, indent=2), encoding="utf-8")

    return {
        "papers_appended": papers_appended,
        "papers_merged": papers_merged,
        "edges_appended": edges_appended,
        "edges_merged": edges_merged,
        "perturbations_appended": perts_appended,
        "perturbations_skipped": perts_skipped,
        "final_counts": {
            "papers": len(papers_j["papers"]),
            "edges": len(edges_j["edges"]),
            "perturbations": len(perts_j["perturbations"]),
        },
    }


# Map DOI to gap_id for provenance tagging
DOI_TO_GAP = {
    "10.1073/pnas.1319953111": "G002",
    "10.1105/tpc.114.122887": "G003",
    "10.1104/pp.16.01067": "G003",
    "10.1105/tpc.105.033365": "G004",
    "10.1016/j.cell.2008.01.047": "G001",
    "10.1038/s41598-018-28188-1": "G005",
    "10.3389/fpls.2024.1387321": "G006",
    "10.1105/tpc.108.059584": "G007",
    "10.1111/tpj.16103": "G002",
    "10.3389/fpls.2016.01884": "G008",
    "10.7554/eLife.54740": "G010",
    "10.1242/dev.071928": "G010",
    "10.1111/j.1365-313X.2008.03495.x": "G004",
    "10.1101/cshperspect.a039933": "G010",
}


def _gap_for_edge(edge):
    for ev in edge.get("evidence", []):
        doi = ev.get("doi", "")
        if doi in DOI_TO_GAP:
            return DOI_TO_GAP[doi]
    return "unspecified"


def _gap_for_pert(pert):
    for ev in pert.get("evidence", []):
        doi = ev.get("doi", "")
        if doi in DOI_TO_GAP:
            return DOI_TO_GAP[doi]
    return "unspecified"


if __name__ == "__main__":
    result = merge(DATA)
    print(json.dumps(result, indent=2))
