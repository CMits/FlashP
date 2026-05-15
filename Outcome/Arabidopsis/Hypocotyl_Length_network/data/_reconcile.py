"""
Step 3 (PERTURBATION) reconciliation for Hypocotyl_Length network.

Maps the 160 raw perturbation tests in perturbation_dataset.json to the 54-node
network (network/network.json) using the priority table from PERTURBATION_AGENT.md
plus the hypocotyl-specific notes from the Step 3 prompt.

Mapping rules per the priority table:
  1 exact_match            (same node id)
  2 case_insensitive       (e.g. phyB -> PHYB)
  3 family_member          (e.g. BES1 -> BZR1, ARF7 -> ARF6)
  4 composite_collapse     (multi-paralog KO collapsed to a composite node, gm=0.0)
  5 composite_member       (single paralog KO of a collapsed composite, gm=0.997)
  6 treatment_analog       (e.g. NAA -> Auxin exogenous=1.0)
  7 mechanism_mapping      (e.g. NPA -> Auxin gm=0.1; ETR1-1 -> CTR1 gm=2.0)
  8 not_in_network         (in_network=false)
  9 control                (WT, expected=unchanged)
"""

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "perturbation_dataset.json"
OUT = ROOT / "reconciled_perturbation_dataset.json"
NET = ROOT.parent / "network" / "network.json"

# ---------------------------------------------------------------------------
# Per-test reconciliation table.
# Each entry: {test_id: (network_genes, gene_modifiers, exogenous_supply,
#                        reconciliation_type, baseline, note)}
# - network_genes: list[str] (always a list)
# - gene_modifiers: dict[str, float] (always a dict; {} if empty)
# - exogenous_supply: dict[str, float] (always flat dict; {} if empty)
# - reconciliation_type: string from the enum
# - baseline: "WT" or "mutant"
# - note: human reconciliation_note
# Use None for IN_NETWORK=False (then network_genes=[], modifiers={}, supply={}).
# ---------------------------------------------------------------------------

NIN = ("not_in_network", "WT")  # shorthand for not_in_network entries


def nin(reason: str):
    return ([], {}, {}, "not_in_network", "WT", reason)


# Convenience constants for hypocotyl encoding
TABLE = {
    "T001": nin("14-3-3 lambda/kappa scaffold proteins not modeled"),
    "T002": (["Ethylene"], {}, {"Ethylene": 1.0}, "treatment_analog", "WT",
             "ACC = ethylene precursor; exogenous Ethylene=1.0 on source node"),
    "T003": (["Ethylene"], {}, {"Ethylene": 1.0}, "treatment_analog", "WT",
             "ACC at 28C: same encoding; framework cannot capture warm-temperature ethylene insensitivity"),
    "T004": (["TIR1", "Auxin"], {"TIR1": 0.997}, {"Auxin": 1.0}, "composite_member", "WT",
             "AFB5 KO + picloram (auxin analog); single AFB paralog -> TIR1 composite gm=0.997 + exogenous Auxin"),
    "T005": nin("AHA2 plasma-membrane H+-ATPase not modeled"),
    "T006": (["ARF6"], {"ARF6": 0.0}, {}, "exact_match", "WT", "ARF6 KO"),
    "T007": (["ARF6"], {"ARF6": 0.0}, {}, "composite_collapse", "WT",
             "arf6 arf7 arf8 triple: only ARF6 in network; ARF7/ARF8 collapsed to ARF6 composite"),
    "T008": (["ARF6"], {"ARF6": 0.0}, {}, "composite_collapse", "WT",
             "arf6 arf8 double: ARF8 collapsed to ARF6 composite"),
    "T009": (["ARF6"], {"ARF6": 0.997}, {}, "family_member", "WT",
             "ARF7 mapped to ARF6 (closest paralog) with single-member modifier 0.997"),
    "T010": (["ARF6"], {"ARF6": 0.997}, {}, "family_member", "WT",
             "ARF8 mapped to ARF6 (closest paralog) with single-member modifier 0.997"),
    "T011": nin("ARP6 (SWR1 complex) not modeled"),
    "T012": (["AUX_IAA"], {"AUX_IAA": 2.0}, {}, "composite_member", "WT",
             "axr2/IAA7 dominant gain-of-function = stabilized AUX/IAA -> AUX_IAA gm=2.0"),
    "T013": (["AUX_IAA"], {"AUX_IAA": 0.0}, {}, "composite_collapse", "WT",
             "iaa7 iaa17 (AXR2 AXR3) double LOF -> AUX_IAA composite KO. NOTE: dataset labels this 'double_knockout'; encoding follows that"),
    "T014": (["TIR1"], {"TIR1": 0.1}, {}, "mechanism_mapping", "WT",
             "Auxinole = TIR1/AFB antagonist -> TIR1 gm=0.1 (KD)"),
    "T015": (["BAK1"], {"BAK1": 0.0}, {}, "exact_match", "WT", "BAK1 KO"),
    "T016": nin("BBX18 not in network"),
    "T017": (["BBX21"], {"BBX21": 0.0}, {}, "exact_match", "WT", "BBX21 KO"),
    "T018": (["BBX21"], {"BBX21": 2.0}, {}, "exact_match", "WT", "BBX21 OE"),
    "T019": nin("BBX22 not in network"),
    "T020": nin("BBX24 not in network"),
    "T021": (["BZR1"], {"BZR1": 2.0}, {}, "family_member", "WT",
             "BES1 = BZR1 paralog (BES1/BZR2); gain-of-function -> BZR1 gm=2.0"),
    "T022": (["BIN2"], {"BIN2": 2.0}, {}, "exact_match", "WT",
             "bin2-1 = constitutively active kinase -> BIN2 gm=2.0; in dark, more BIN2 -> stronger BR signaling block? Per literature bin2-1 in dark = increased hypocotyl"),
    "T023": (["BIN2"], {"BIN2": 2.0}, {}, "exact_match", "WT",
             "bin2-1 in light = decreased (BR-deficient phenotype)"),
    "T024": (["BR"], {}, {"BR": 1.0}, "treatment_analog", "WT",
             "BL (brassinolide) = exogenous BR on hormone node"),
    "T025": (["BRI1"], {"BRI1": 0.0}, {}, "exact_match", "WT", "BRI1 KO (BR receptor null)"),
    "T026": (["BR"], {}, {"BR": 1.0}, "treatment_analog", "WT",
             "Exogenous BR (24-epi-BL) on BR hormone node"),
    "T027": (["BZR1"], {"BZR1": 2.0}, {}, "exact_match", "WT",
             "bzr1-1D dominant gain-of-function -> BZR1 gm=2.0"),
    "T028": (["DET2"], {"DET2": 0.1}, {}, "mechanism_mapping", "WT",
             "Brassinazole (Brz) blocks BR biosynthesis -> DET2 gm=0.1 (KD)"),
    "T029": nin("CCA1/LHY morning-loop clock genes not modeled (only ELF3_EC and TOC1 represented)"),
    "T030": nin("COG1 (Dof TF) not in network"),
    "T031": (["COP1"], {"COP1": 0.0}, {}, "exact_match", "WT", "COP1 KO"),
    "T032": (["COP1"], {"COP1": 0.0}, {}, "exact_match", "WT", "COP1 KO in white light"),
    "T033": (["CRY1"], {"CRY1": 0.0}, {}, "exact_match", "WT", "CRY1 KO under blue light"),
    "T034": (["CRY1"], {"CRY1": 2.0}, {}, "exact_match", "WT", "CRY1 OE"),
    "T035": (["CRY1", "CRY2"], {"CRY1": 0.0, "CRY2": 0.0}, {}, "exact_match", "WT",
             "cry1 cry2 double KO"),
    "T036": (["CRY2"], {"CRY2": 0.0}, {}, "exact_match", "WT", "CRY2 KO"),
    "T037": (["CRY2"], {"CRY2": 2.0}, {}, "exact_match", "WT", "CRY2 OE"),
    "T038": (["CTR1"], {"CTR1": 0.0}, {}, "exact_match", "WT",
             "ctr1 = constitutive ethylene response (loss of negative regulator)"),
    "T039": (["DELLA"], {"DELLA": 0.0}, {}, "composite_collapse", "WT",
             "DELLA quintuple (gai rga rgl1 rgl2 rgl3) -> DELLA composite KO"),
    "T040": (["DELLA"], {"DELLA": 0.0}, {}, "composite_collapse", "WT",
             "Pentuple DELLA loss -> DELLA composite KO"),
    "T041": (["DET1"], {"DET1": 0.0}, {}, "exact_match", "WT", "DET1 KO"),
    "T042": (["DET2"], {"DET2": 0.0}, {}, "exact_match", "WT", "DET2 KO (BR biosynthesis null)"),
    "T043": (["DWF4"], {"DWF4": 0.0}, {}, "exact_match", "WT", "DWF4 KO (BR biosynthesis null)"),
    "T044": nin("EBF1 (E3 ligase for EIN3) not modeled"),
    "T045": nin("EBF1/EBF2 not modeled"),
    "T046": (["EIN2", "Ethylene"], {"EIN2": 0.0}, {"Ethylene": 1.0}, "exact_match", "WT",
             "EIN2 KO + ACC (ethylene precursor); insensitive to ethylene -> increased vs WT+ACC"),
    "T047": (["EIN3", "Ethylene"], {"EIN3": 0.0}, {"Ethylene": 1.0}, "exact_match", "WT",
             "EIN3 KO + ACC; insensitive to ethylene"),
    "T048": (["EIN3"], {"EIN3": 2.0}, {}, "exact_match", "WT", "EIN3 OE"),
    "T049": (["EIN3", "Ethylene"], {"EIN3": 0.0}, {"Ethylene": 1.0}, "composite_collapse", "WT",
             "ein3 eil1 double + ACC; EIL1 collapsed to EIN3 composite"),
    "T050": (["ELF3_EC"], {"ELF3_EC": 0.0}, {}, "composite_member", "WT",
             "ELF3 single KO disrupts evening complex -> ELF3_EC composite gm=0.0 (single component is essential for EC)"),
    "T051": (["ELF3_EC"], {"ELF3_EC": 0.0}, {}, "composite_member", "WT",
             "ELF3 KO at 22C -> ELF3_EC disrupted"),
    "T052": (["ELF3_EC", "PIF4", "PIF5"],
             {"ELF3_EC": 0.0, "PIF4": 0.0, "PIF5": 0.0}, {}, "composite_collapse", "WT",
             "elf3 pif4 pif5 triple: PIFs gone trumps ELF3 effect -> decreased"),
    "T053": (["ELF3_EC"], {"ELF3_EC": 0.5}, {}, "composite_member", "WT",
             "ELF4 KO disrupts EC; modeled as partial loss of ELF3_EC composite (gm=0.5)"),
    "T054": (["CTR1"], {"CTR1": 2.0}, {}, "mechanism_mapping", "WT",
             "etr1-1 dominant ethylene-insensitive: signals 'no ethylene' -> CTR1 stays active -> CTR1 gm=2.0"),
    "T055": (["GA20OX1"], {"GA20OX1": 0.0}, {}, "mechanism_mapping", "WT",
             "GA1 (CPS) is upstream GA biosynthesis; mapped to closest in-network biosynthesis enzyme GA20OX1 KO"),
    "T056": (["GA20OX1"], {"GA20OX1": 0.0}, {}, "exact_match", "WT", "GA20ox1 KO"),
    "T057": (["GA4"], {}, {"GA4": 1.0}, "treatment_analog", "WT",
             "GA3 treatment -> exogenous GA on GA4 metabolite node"),
    "T058": (["GA3OX1"], {"GA3OX1": 0.0}, {}, "exact_match", "WT", "GA3ox1 KO"),
    "T059": (["DELLA"], {"DELLA": 2.0}, {}, "composite_member", "WT",
             "gai-1 dominant gain-of-function (DELLA-deletion stabilized) -> DELLA gm=2.0"),
    "T060": (["GI"], {"GI": 0.0}, {}, "exact_match", "WT", "GI KO at 27C"),
    "T061": (["GI"], {"GI": 2.0}, {}, "exact_match", "WT", "GI OE at 27C"),
    "T062": (["GID1"], {"GID1": 0.0}, {}, "composite_collapse", "WT",
             "gid1a gid1b gid1c triple -> GID1 composite KO"),
    "T063": nin("GRF4 (growth-regulating factor) not in network"),
    "T064": nin("GRF4 OE not in network"),
    "T065": nin("HBI1 (bHLH) not in network"),
    "T066": (["HFR1"], {"HFR1": 0.0}, {}, "exact_match", "WT", "HFR1 KO under shade/FR"),
    "T067": nin("HMR/PAP5 (plastid-nuclear) not in network"),
    "T068": (["HSFA1D"], {"HSFA1D": 0.0}, {}, "composite_collapse", "WT",
             "hsfa1a hsfa1b hsfa1d triple: A/B collapsed to HSFA1D composite"),
    "T069": (["HSFA1D"], {"HSFA1D": 2.0}, {}, "exact_match", "WT", "HSFA1D OE"),
    "T070": (["HY5"], {"HY5": 0.0}, {}, "exact_match", "WT", "HY5 KO"),
    "T071": (["HY5", "HYH"], {"HY5": 0.0, "HYH": 0.0}, {}, "exact_match", "WT",
             "hy5 hyh double KO"),
    "T072": (["HYH"], {"HYH": 0.0}, {}, "exact_match", "WT", "HYH KO"),
    "T073": nin("IBH1 (atypical bHLH) not in network"),
    "T074": (["ELF3_EC"], {"ELF3_EC": 0.5}, {}, "composite_member", "WT",
             "LUX KO disrupts evening complex; partial loss of ELF3_EC (gm=0.5)"),
    "T075": nin("MPK3 MAP-kinase not in network"),
    "T076": nin("MPK6 MAP-kinase not in network"),
    "T077": (["Auxin"], {}, {"Auxin": 1.0}, "treatment_analog", "WT",
             "NAA = synthetic auxin -> exogenous Auxin=1.0"),
    "T078": (["Auxin"], {"Auxin": 0.1}, {}, "mechanism_mapping", "WT",
             "NPA blocks auxin transport (PIN); PIN not in network -> proxy as Auxin gm=0.1"),
    "T079": nin("PAR1 not in network"),
    "T080": nin("PAR1 OE not in network"),
    "T081": (["PHYA"], {"PHYA": 0.0}, {}, "exact_match", "WT", "PHYA KO under FRc"),
    "T082": (["PHYA", "PHYB"], {"PHYA": 0.0, "PHYB": 0.0}, {}, "exact_match", "WT",
             "phyA phyB double KO"),
    "T083": (["PHYB"], {"PHYB": 0.0}, {}, "exact_match", "WT", "PHYB KO under Rc"),
    "T084": (["PHYB"], {"PHYB": 0.0}, {}, "exact_match", "WT", "PHYB KO in white light"),
    "T085": (["PHYB"], {"PHYB": 2.0}, {}, "exact_match", "WT", "PHYB OE"),
    "T086": (["PHYB"], {"PHYB": 2.0}, {}, "exact_match", "WT",
             "PHYB-G111D dominant active variant -> PHYB gm=2.0"),
    "T087": (["PIF3"], {"PIF3": 0.997}, {}, "family_member", "WT",
             "PIF1 not in network; mapped to PIF3 (closest skotomorphogenesis-active PIF) with single-member modifier"),
    "T088": (["PIF3", "PIF4", "PIF5"],
             {"PIF3": 0.0, "PIF4": 0.0, "PIF5": 0.0}, {}, "composite_collapse", "WT",
             "pifQ (pif1 pif3 pif4 pif5); PIF1 omitted (not in network); other three KO"),
    "T089": (["PIF3"], {"PIF3": 0.0}, {}, "exact_match", "WT", "PIF3 KO under Rc"),
    "T090": (["PIF3"], {"PIF3": 2.0}, {}, "exact_match", "WT", "PIF3 OE in white light"),
    "T091": (["PIF4"], {"PIF4": 0.0}, {}, "exact_match", "WT", "PIF4 KO at warm temperature"),
    "T092": (["PIF4"], {"PIF4": 0.0}, {}, "exact_match", "WT", "PIF4 KO under Rc/white"),
    "T093": (["PIF4"], {"PIF4": 2.0}, {}, "exact_match", "WT", "PIF4 OE"),
    "T094": (["PIF4", "PIF5", "PIF7"],
             {"PIF4": 0.0, "PIF5": 0.0, "PIF7": 0.0}, {}, "exact_match", "WT",
             "pif4 pif5 pif7 triple KO under shade+warm"),
    "T095": (["PIF5"], {"PIF5": 0.0}, {}, "exact_match", "WT", "PIF5 KO under Rc"),
    "T096": (["PIF5"], {"PIF5": 2.0}, {}, "exact_match", "WT", "PIF5 OE"),
    "T097": (["PIF7"], {"PIF7": 0.0}, {}, "exact_match", "WT", "PIF7 KO under Rc"),
    "T098": (["PIF7"], {"PIF7": 0.0}, {}, "exact_match", "WT", "PIF7 KO under shade"),
    "T099": (["PIF7"], {"PIF7": 2.0}, {}, "exact_match", "WT",
             "PIF7 phospho-dead = constitutively nuclear/active -> PIF7 gm=2.0"),
    "T100": nin("PRE1 (PRE family bHLH) not in network"),
    "T101": nin("PRE1/PRE2/PRE5/PRE6 not in network"),
    "T102": nin("PRR5/7/9 morning clock genes not in network"),
    "T103": (["GA3OX1"], {"GA3OX1": 0.1}, {}, "mechanism_mapping", "WT",
             "Paclobutrazol (PAC) inhibits GA biosynthesis -> GA3OX1 gm=0.1 (KD)"),
    "T104": (["Auxin"], {}, {"Auxin": 1.0}, "treatment_analog", "WT",
             "Picloram = synthetic auxin -> exogenous Auxin=1.0"),
    "T105": nin("RCB (chloroplast biogenesis) not in network"),
    "T106": (["DELLA"], {"DELLA": 0.997}, {}, "composite_member", "WT",
             "RGA single KO -> DELLA composite gm=0.997 (1 of 5 paralogs)"),
    "T107": (["DELLA"], {"DELLA": 0.5}, {}, "composite_member", "WT",
             "rga gai double KO -> DELLA composite gm=0.5 (2 of 5 paralogs lost)"),
    "T108": nin("SAUR19 (auxin-induced effector) not in network"),
    "T109": (["AUX_IAA"], {"AUX_IAA": 2.0}, {}, "composite_member", "WT",
             "shy2/IAA3 dominant gain-of-function -> AUX_IAA gm=2.0"),
    "T110": nin("SLY1 (F-box for DELLA) not in network"),
    "T111": (["SPA1"], {"SPA1": 0.0}, {}, "composite_collapse", "WT",
             "spa1 spa2 spa3 spa4 quadruple: SPA2-4 collapsed to SPA1 composite"),
    "T112": (["TIR1", "Auxin"], {"TIR1": 0.0}, {"Auxin": 1.0}, "exact_match", "WT",
             "TIR1 KO + auxin treatment"),
    "T113": (["TIR1"], {"TIR1": 0.0}, {}, "composite_collapse", "WT",
             "tir1 afb1 afb2 afb3 quadruple: AFBs collapsed to TIR1 composite"),
    "T114": (["TOC1"], {"TOC1": 0.0}, {}, "exact_match", "WT", "TOC1 KO 27C SD"),
    "T115": (["TOC1"], {"TOC1": 2.0}, {}, "exact_match", "WT", "TOC1 OE LD"),
    "T116": (["TOC1"], {"TOC1": 2.0}, {}, "exact_match", "WT", "TOC1 OE in light"),
    "T117": (["UVR8"], {"UVR8": 0.0}, {}, "exact_match", "WT", "UVR8 KO under UV-B"),
    "T118": (["UVR8"], {"UVR8": 2.0}, {}, "exact_match", "WT", "UVR8 OE under UV-B"),
    "T119": nin("XBAT31 (E3 ligase) not in network"),
    "T120": nin("XBAT31 OE not in network"),
    "T121": (["YUC8"], {"YUC8": 0.0}, {}, "composite_collapse", "WT",
             "yuc2 yuc5 yuc8 yuc9 quadruple: YUC2/5/9 collapsed to YUC8 composite"),
    "T122": (["YUC8"], {"YUC8": 0.0}, {}, "exact_match", "WT", "YUC8 KO under shade/warm"),
    "T123": (["PHYB"], {"PHYB": 0.0}, {}, "case_insensitive", "WT",
             "phyB-9 = PHYB null allele -> PHYB gm=0.0"),
    "T124": nin("RUP1/RUP2 (UV-B negative regulators) not in network"),
    "T125": nin("RUP2 OE not in network"),
    "T126": nin("RUP2 KO not in network"),
    "T127": (["GID1"], {"GID1": 0.5}, {}, "composite_member", "WT",
             "gid1a gid1c double KO -> GID1 composite gm=0.5 (2/3 paralogs lost)"),
    "T128": (["GID1"], {"GID1": 0.5}, {}, "composite_member", "WT",
             "gid1a gid1b double KO -> GID1 composite gm=0.5"),
    "T129": (["GID1"], {"GID1": 0.5}, {}, "composite_member", "WT",
             "gid1b gid1c double KO -> GID1 composite gm=0.5"),
    "T130": nin("TCP5/TCP13/TCP17 (TCP TFs) not in network"),
    "T131": nin("TCP17 OE not in network"),
    "T132": nin("TCP5 OE not in network"),
    "T133": nin("TCP13 OE not in network"),
    "T134": nin("TCP17 KO not in network"),
    "T135": (["BAS1"], {"BAS1": 0.0}, {}, "exact_match", "WT", "BAS1 KO (BR catabolic enzyme)"),
    "T136": (["SOB7"], {"SOB7": 0.0}, {}, "exact_match", "WT", "SOB7 KO (BR catabolic enzyme)"),
    "T137": (["BAS1", "SOB7"], {"BAS1": 0.0, "SOB7": 0.0}, {}, "exact_match", "WT",
             "bas1 sob7 double KO"),
    "T138": (["BAS1"], {"BAS1": 2.0}, {}, "exact_match", "WT", "BAS1 OE"),
    "T139": (["BBX11"], {"BBX11": 0.0}, {}, "exact_match", "WT", "BBX11 KO"),
    "T140": (["BBX11"], {"BBX11": 2.0}, {}, "exact_match", "WT", "BBX11 OE"),
    "T141": (["BBX11", "BBX21"], {"BBX11": 0.0, "BBX21": 0.0}, {}, "exact_match", "WT",
             "bbx11 bbx21 double KO"),
    "T142": nin("ATHB2/HAT4 (HD-ZIP II) not in network"),
    "T143": nin("ATHB2 OE not in network"),
    "T144": nin("ATHB4 OE not in network"),
    "T145": nin("HAT3/ATHB4 not in network"),
    "T146": (["Auxin"], {"Auxin": 0.1}, {}, "mechanism_mapping", "WT",
             "pin3 pin4 pin7 triple: PIN auxin-efflux carriers not in network -> Auxin gm=0.1 proxy"),
    "T147": (["FHY1"], {"FHY1": 0.0}, {}, "exact_match", "WT", "FHY1 KO under FRc"),
    "T148": (["FHY1"], {"FHY1": 0.0}, {}, "composite_collapse", "WT",
             "fhy1 fhl double: FHL collapsed to FHY1 composite"),
    "T149": nin("FHY3 (FAR-RED ELONGATED HYPOCOTYL 3) not in network"),
    "T150": nin("FAR1 (FHY3 homolog) not in network"),
    "T151": (["HFR1"], {"HFR1": 0.0}, {}, "exact_match", "WT", "HFR1 KO under FRc/shade"),
    "T152": nin("LAF1 (R2R3-MYB) not in network"),
    "T153": (["BBX25"], {"BBX25": 0.0}, {}, "exact_match", "WT", "BBX25 KO"),
    "T154": (["BBX25"], {"BBX25": 2.0}, {}, "exact_match", "WT", "BBX25 OE"),
    "T155": (["BBX25"], {"BBX25": 0.0}, {}, "composite_collapse", "WT",
             "bbx24 bbx25 double: BBX24 collapsed to BBX25 composite"),
    "T156": (["ABA"], {}, {"ABA": 1.0}, "treatment_analog", "WT",
             "ABA treatment -> exogenous ABA=1.0 on source node"),
    "T157": (["PIF3", "PIF4", "PIF5"],
             {"PIF3": 0.0, "PIF4": 0.0, "PIF5": 0.0}, {}, "composite_collapse", "WT",
             "pifQ in darkness; PIF1 omitted (not in network)"),
    "T158": nin("PHOT1/PHOT2 phototropins not in network"),
    "T159": nin("MG132 proteasome inhibitor: no proteasome node in network"),
    "T160": (["Ethylene"], {"Ethylene": 0.1}, {}, "mechanism_mapping", "WT",
             "AVG inhibits ethylene biosynthesis -> Ethylene (source) gm=0.1 (endogenous KD)"),
}


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    net = json.loads(NET.read_text(encoding="utf-8"))
    valid_nodes = {n["id"] for n in net["nodes"]}
    phenotype_node = net["metadata"]["phenotype_node"]

    out_perts = []
    in_count = 0
    out_count = 0
    by_type = {}
    by_condition = {}

    for entry in raw["perturbations"]:
        tid = entry["test_id"]
        if tid not in TABLE:
            raise SystemExit(f"Missing reconciliation entry for {tid}")
        net_genes, gms, exo, rtype, baseline, note = TABLE[tid]

        # Sanity-check that every referenced node exists in the network
        for n in net_genes:
            if n not in valid_nodes:
                raise SystemExit(f"{tid}: node {n!r} not in network")
        for n in gms:
            if n not in valid_nodes:
                raise SystemExit(f"{tid}: gene_modifier node {n!r} not in network")
        for n in exo:
            if n not in valid_nodes:
                raise SystemExit(f"{tid}: exogenous_supply node {n!r} not in network")

        in_network = rtype != "not_in_network"
        if in_network:
            in_count += 1
        else:
            out_count += 1
        by_type[rtype] = by_type.get(rtype, 0) + 1
        cond = entry.get("condition", "")
        by_condition[cond] = by_condition.get(cond, 0) + 1

        # Build the explicit perturbations list
        modlist = []
        for node, val in gms.items():
            modlist.append({"node": node, "modifier_type": "gene_modifier", "value": val})
        for node, val in exo.items():
            modlist.append({"node": node, "modifier_type": "exogenous_supply", "value": val})

        rec = {
            "test_id": tid,
            "gene": entry["gene"],
            "perturbation_type": entry["perturbation_type"],
            "expected_direction": entry["expected_direction"],
            "in_network": in_network,
            "network_gene": net_genes,
            "gene_modifiers": gms,
            "exogenous_supply": exo,
            "perturbations": modlist,
            "notes": note,
            "evidence": deepcopy(entry.get("evidence", [])),
            "phenotype_node": phenotype_node,
            "comparison_baseline": baseline,
            "condition": cond,
            "reconciliation_type": rtype,
            "reconciliation_note": note,
            "expected_magnitude": entry.get("expected_magnitude", ""),
            "species": entry.get("species", "Arabidopsis thaliana"),
        }
        out_perts.append(rec)

    # Append a WT negative control test (T161)
    control_id = f"T{len(out_perts) + 1:03d}"
    out_perts.append({
        "test_id": control_id,
        "gene": "WT",
        "perturbation_type": "control",
        "expected_direction": "unchanged",
        "in_network": True,
        "network_gene": [],
        "gene_modifiers": {},
        "exogenous_supply": {},
        "perturbations": [],
        "notes": "Negative control: WT vs WT, expected unchanged",
        "evidence": [],
        "phenotype_node": phenotype_node,
        "comparison_baseline": "WT",
        "condition": "any",
        "reconciliation_type": "control",
        "reconciliation_note": "WT baseline self-comparison; expected unchanged by definition",
        "expected_magnitude": "minimal",
        "species": "Arabidopsis thaliana",
    })
    in_count += 1
    by_type["control"] = by_type.get("control", 0) + 1
    by_condition["any"] = by_condition.get("any", 0) + 1

    out = {
        "metadata": {
            "flash_p_version": "1.0",
            "phenotype": "Hypocotyl_Length",
            "species": "Arabidopsis thaliana",
            "created": "2026-04-19",
            "total_tests": len(out_perts),
            "in_network": in_count,
            "not_in_network": out_count,
            "phenotype_node": phenotype_node,
            "convention": "compare to WT unless rescue (compare to mutant alone); see reconciliation_note for hypocotyl-specific encodings",
        },
        "direction_threshold": raw.get("direction_threshold", 0.05),
        "perturbations": out_perts,
    }

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"Total: {len(out_perts)}  in_network: {in_count}  not_in_network: {out_count}")
    print()
    print("Breakdown by reconciliation_type:")
    for k in sorted(by_type):
        print(f"  {k:<22} {by_type[k]}")
    print()
    print("Breakdown by condition (top):")
    for k in sorted(by_condition, key=lambda x: -by_condition[x]):
        print(f"  {k:<35} {by_condition[k]}")


if __name__ == "__main__":
    main()
