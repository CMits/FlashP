"""
Step 3 reconciliation builder for Lateral_Root_Density.
Produces reconciled_perturbation_dataset.json by mapping the 157 raw tests
to the 55-node LR network using the priority table in PERTURBATION_AGENT.md
and the LR-specific rules in the user prompt.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "perturbation_dataset.json"
NET_PATH = ROOT.parent / "network" / "network.json"
OUT_PATH = ROOT / "reconciled_perturbation_dataset.json"

with open(RAW_PATH, "r", encoding="utf-8") as fh:
    raw = json.load(fh)
with open(NET_PATH, "r", encoding="utf-8") as fh:
    net = json.load(fh)

NET_NODES = {n.get("id") or n.get("name") for n in net["nodes"]}
PHENOTYPE_NODE = "Lateral_Root_Density"

# ---------------------------------------------------------------------------
# Mapping table:
#   keyed by raw test_id -> dict with the reconciliation information.
#   keys:
#     nog           : network_gene list
#     gm            : gene_modifiers dict
#     exo           : exogenous_supply dict
#     rtype         : reconciliation_type (enum)
#     rnote         : reconciliation_note
#     notes         : free-form notes
#     baseline      : 'WT' or 'mutant'   (default 'WT')
#     expected      : OVERRIDE expected_direction if set  (else use raw)
#     in_network    : False for not_in_network
# ---------------------------------------------------------------------------

M = {}

def add(tid, nog, gm, exo, rtype, rnote, notes="", baseline="WT",
        expected=None, in_network=True):
    M[tid] = dict(nog=nog, gm=gm, exo=exo, rtype=rtype, rnote=rnote,
                  notes=notes, baseline=baseline, expected=expected,
                  in_network=in_network)

def nin(tid, rnote, notes=""):
    """Flag not_in_network."""
    M[tid] = dict(nog=[], gm={}, exo={}, rtype="not_in_network",
                  rnote=rnote, notes=notes, baseline="WT",
                  expected=None, in_network=False)

# ---- TIR1/AFB family (T001-T006, T044, T045, T153) -----------------------
add("T001", ["TIR1"], {"TIR1": 0.0}, {}, "exact_match",
    "tir1 KO -> TIR1 node")
add("T002", ["TIR1"], {"TIR1": 0.997}, {}, "family_member",
    "AFB1 is a TIR1/AFB-family paralog; mapped to TIR1 composite representative (single-paralog redundancy gm=0.997)")
add("T003", ["TIR1"], {"TIR1": 0.997}, {}, "family_member",
    "AFB2 -> TIR1 family (single-paralog redundancy)")
add("T004", ["TIR1"], {"TIR1": 0.5}, {}, "family_member",
    "tir1 afb2 double -> partial TIR1/AFB family loss (2 of 6 paralogs collapsed into TIR1 node)")
add("T005", ["TIR1"], {"TIR1": 0.0}, {}, "family_member",
    "tir1 afb2 afb3 triple -> the three main root auxin receptors -> full TIR1 perception loss in network")
add("T006", ["TIR1"], {"TIR1": 0.8}, {}, "family_member",
    "afb4 afb5 double -> partial TIR1 family loss (AFB4/5 are a distinct clade, residual TIR1/AFB1/2/3 intact)")
add("T044", ["TIR1"], {"TIR1": 0.997}, {}, "family_member",
    "afb3 single -> TIR1 family paralog")
add("T045", ["TIR1"], {"TIR1": 2.0}, {}, "family_member",
    "AFB3 OE -> TIR1 family OE")
add("T153", ["TIR1"], {"TIR1": 0.0}, {}, "family_member",
    "tir1 afb1-5 sextuple -> complete TIR1/AFB loss")

# ---- Aux/IAA family (T007-T010) ------------------------------------------
add("T007", ["IAA14"], {"IAA14": 2.0}, {}, "exact_match",
    "slr-1 is a stabilised dominant IAA14; gm=2.0 encodes super-active repressor (see §Dominant-negative Aux/IAA rule)")
add("T008", ["IAA28"], {"IAA28": 2.0}, {}, "exact_match",
    "iaa28-1 stabilised dominant allele; gm=2.0")
nin("T009",
    "IAA12 (bdl) partners with ARF5 (MP); neither IAA12 nor ARF5 is in the LR network",
    "Dominant bdl stabilised allele; ARF5 pathway not captured")
add("T010", ["IAA14"], {"IAA14": 2.0}, {}, "family_member",
    "shy2 (iaa3) stabilised dominant allele; IAA3 is the nearest LR-functional Aux/IAA paralog to the in-network IAA14 node; gm=2.0")

# ---- ARFs (T011-T014) ----------------------------------------------------
add("T011", ["ARF7"], {"ARF7": 0.0}, {}, "exact_match",
    "arf7 KO")
add("T012", ["ARF19"], {"ARF19": 0.0}, {}, "exact_match",
    "arf19 KO")
add("T013", ["ARF7", "ARF19"], {"ARF7": 0.0, "ARF19": 0.0}, {},
    "exact_match", "arf7 arf19 double KO")
nin("T014",
    "ARF5 (MP) not in LR network",
    "ARF5 governs embryonic patterning, not modelled here")

# ---- LBD family (T015-T020, T143 OE) -------------------------------------
add("T015", ["LBD"], {"LBD": 0.997}, {}, "composite_member",
    "LBD16 is one of several LR LBDs collapsed into the LBD composite; single-paralog gm=0.997")
add("T016", ["LBD"], {"LBD": 2.0}, {}, "composite_member",
    "LBD16 OE -> LBD composite OE")
add("T017", ["LBD"], {"LBD": 2.0}, {}, "composite_member",
    "LBD29 OE -> LBD composite OE")
add("T018", ["LBD"], {"LBD": 0.8}, {}, "composite_member",
    "LBD16 knockdown -> mild reduction in LBD composite")
add("T019", ["LBD"], {"LBD": 0.997}, {}, "composite_member",
    "LBD18 single KO")
add("T020", ["LBD"], {"LBD": 0.997}, {}, "composite_member",
    "LBD29 single KO")
add("T152", ["LBD"], {"LBD": 0.0}, {}, "composite_collapse",
    "lbd16 lbd18 lbd29 triple -> all three main LR LBDs lost -> LBD composite gm=0")

# ---- GATA23, PUCHI (T021-T023) -------------------------------------------
add("T021", ["GATA23"], {"GATA23": 0.0}, {}, "exact_match",
    "gata23 LOF")
add("T022", ["GATA23"], {"GATA23": 2.0}, {}, "exact_match",
    "GATA23 OE")
nin("T023", "PUCHI not in LR network",
    "PUCHI is a lateral-root AP2 TF; not modelled")

# ---- PLT triple (T024) ---------------------------------------------------
add("T024", ["PLT"], {"PLT": 0.0}, {}, "composite_collapse",
    "plt3 plt5 plt7 triple -> full PLT composite KO")

# ---- PIN family (T025-T031, T071, T154) ----------------------------------
add("T025", ["AUX1"], {"AUX1": 0.0}, {}, "exact_match",
    "aux1 KO")
add("T026", ["LAX3"], {"LAX3": 0.0}, {}, "exact_match",
    "lax3 KO")
add("T027", ["PIN"], {"PIN": 0.997}, {}, "composite_member",
    "pin2 -> PIN composite single-paralog")
add("T028", ["PIN"], {"PIN": 0.997}, {}, "composite_member",
    "pin3 -> PIN composite single-paralog")
add("T029", ["PIN"], {"PIN": 0.9}, {}, "composite_member",
    "pin3 pin7 double -> partial PIN composite loss (~2 of ~8 PINs)")
add("T030", ["PIN"], {"PIN": 0.997}, {}, "composite_member",
    "pin8 -> PIN composite single-paralog")
nin("T031", "ABCB19 (efflux carrier, distinct family) not in network",
    "ABCB/PGP efflux transporter, separate from PIN family")
add("T032", ["PIN"], {"PIN": 0.1}, {}, "mechanism_mapping",
    "GNOM controls PIN membrane trafficking; LOF collapses PIN polarity -> modelled as strong PIN KD gm=0.1")
add("T071", ["PIN"], {"PIN": 0.997}, {}, "composite_member",
    "pin3 (independent replicate) -> PIN composite single-paralog")
add("T154", ["PIN"], {"PIN": 0.5}, {}, "composite_member",
    "pin2 pin3 pin7 triple -> substantial PIN composite loss (~3 of ~8 PINs)")

# ---- Auxin biosynthesis (T033-T035) --------------------------------------
add("T033", ["TAA1", "TAR2"], {"TAA1": 0.0, "TAR2": 0.0}, {},
    "exact_match", "taa1 tar2 double KO")
add("T034", ["TAR2"], {"TAR2": 0.0}, {}, "exact_match",
    "tar2 KO")
add("T035", ["YUC4"], {"YUC4": 0.0}, {}, "family_member",
    "yuc quadruple (yuc1/2/4/6) -> only YUC4 represented in network; gm=0 models strong YUC-family auxin biosynthesis loss")

# ---- Cytokinin receptors & biosynthesis (T036-T040) ---------------------
add("T036", ["AHK"], {"AHK": 0.3}, {}, "composite_member",
    "ahk2 ahk3 double -> two of three AHK paralogs lost in the AHK composite -> gm=0.3")
add("T037", ["AHK"], {"AHK": 0.7}, {}, "composite_member",
    "ahk4 (cre1) single -> one of three AHK paralogs lost; gm=0.7 reflects moderate CK-insensitivity phenotype")
add("T038", ["CKX2"], {"CKX2": 2.0}, {}, "family_member",
    "CKX1 OE -> CKX2 node represents the CKX family; OE gm=2.0")
add("T039", ["IPT5"], {"IPT5": 2.0}, {}, "family_member",
    "IPT OE (e.g., IPT3/5/7) -> IPT5 node represents the IPT family; gm=2.0")
nin("T040", "AHP6 not in network",
    "AHP6 is a pseudo-His phosphotransferase that blocks CK signalling in LR founders; not modelled")

# ---- Nitrate transporters / response (T041-T043) -------------------------
add("T041", ["CHL1"], {"CHL1": 0.0}, {}, "exact_match",
    "nrt1.1 (chl1) KO -> CHL1")
nin("T042", "NRT2.1 not in network",
    "NRT2.1 is the high-affinity nitrate transporter, separate from the CHL1/NRT1.1 transceptor; not modelled")
add("T043", ["ANR1"], {"ANR1": 0.5}, {}, "exact_match",
    "ANR1 knockdown -> gm=0.5")

# ---- Lateral-root TFs not in network (T046-T048) -------------------------
nin("T046", "NAC4 not in network",
    "NAC4 downstream of ARF7; not modelled")
nin("T047", "STOP1 not in network",
    "STOP1 is a low-pH/Al TF; not modelled")
nin("T048", "ALMT1 not in network",
    "ALMT1 malate transporter; not modelled")
nin("T049", "LPR1/LPR2 not in network",
    "Low-phosphate response ferroxidases; not modelled directly")

# ---- Ethylene axis (T050-T053, T073, T074, T094, T145) -------------------
add("T050", ["EIN2"], {"EIN2": 0.0}, {}, "exact_match",
    "ein2 KO")
add("T051", ["EIN2"], {"EIN2": 0.0}, {}, "mechanism_mapping",
    "etr1 ethylene-insensitive allele blocks ethylene signalling upstream of CTR1/EIN2; encoded as EIN2 gm=0 to match ein2-like phenotype (expected increased LR)")
add("T052", ["CTR1"], {"CTR1": 0.0}, {}, "exact_match",
    "ctr1 LOF -> constitutive ethylene signalling -> EIN2 up -> LR down")
add("T053", ["ACS"], {"ACS": 2.0}, {}, "mechanism_mapping",
    "eto1 LOF stabilises ACS5 -> excess ethylene biosynthesis; encoded as ACS gm=2.0 (OE)")
add("T073", ["Ethylene"], {}, {"Ethylene": 1.0}, "treatment_analog",
    "ACC -> ethylene biosynthesis precursor -> Ethylene exogenous supply")
add("T074", ["EIN2"], {"EIN2": 0.0}, {}, "mechanism_mapping",
    "AgNO3 blocks ethylene receptors -> phenotypic ethylene-insensitivity -> EIN2 gm=0 (same encoding as etr1)")
add("T094", ["ACS"], {"ACS": 0.1}, {}, "mechanism_mapping",
    "AVG inhibits ACS (ACC synthase) -> ethylene biosynthesis block")
add("T145", ["EIN2"], {"EIN2": 0.0}, {}, "mechanism_mapping",
    "ein3 eil1 double are the main ethylene-response TFs downstream of EIN2; encoded as EIN2 gm=0 because EIN3/EIL1 are not separate nodes")

# ---- ABA axis (T054-T060, T077, T098) -----------------------------------
add("T054", ["ABI4_5"], {"ABI4_5": 0.5}, {}, "composite_member",
    "abi4 single KO -> ABI4_5 composite (ABI4+ABI5 collapsed); partial loss gm=0.5")
add("T055", ["ABI4_5"], {"ABI4_5": 2.0}, {}, "composite_member",
    "ABI4 OE -> ABI4_5 composite OE")
add("T056", ["PYL8"], {"PYL8": 0.0}, {}, "exact_match",
    "pyl8 KO")
nin("T057", "MYB77 not in network",
    "MYB77 auxin-responsive TF; not modelled")
add("T058", ["ABI1"], {"ABI1": 2.0}, {}, "exact_match",
    "abi1-1 dominant gof PP2C -> ABA-insensitive (ABI1 super-active at inhibiting SnRK2); gm=2.0 reflects the dominant gain-of-inhibition")
add("T059", ["SNRK2"], {"SNRK2": 0.0}, {}, "composite_collapse",
    "snrk2.2/2.3/2.6 triple -> full SNRK2 composite loss")
add("T060", ["PYL8"], {"PYL8": 0.0}, {}, "family_member",
    "pyr1 pyl1 pyl2 pyl4 quadruple -> broad ABA-receptor loss; PYL8 node represents the PYR/PYL/RCAR family, encoded as gm=0 to model ABA perception block")
add("T077", ["ABA"], {}, {"ABA": 1.0}, "treatment_analog",
    "exogenous ABA -> ABA supply")

# ---- Strigolactone axis (T061-T066, T081, T104, T122, T123) -------------
add("T061", ["MAX2"], {"MAX2": 0.0}, {}, "exact_match",
    "max2 KO")
add("T062", ["D14"], {"D14": 0.0}, {}, "exact_match",
    "d14 KO")
nin("T063", "KAI2 not in network",
    "KAI2 is the karrikin receptor, functionally distinct from D14; mapping to D14 would invert the expected direction (D14 KO increases LR whereas KAI2 KO decreases)")
add("T064", ["MAX3"], {"MAX3": 0.0}, {}, "exact_match",
    "max3 KO")
add("T065", ["MAX4"], {"MAX4": 0.0}, {}, "exact_match",
    "max4 KO")
add("T066", ["MAX1"], {"MAX1": 0.0}, {}, "exact_match",
    "max1 KO")
add("T081", ["Strigolactone"], {}, {"Strigolactone": 1.0}, "treatment_analog",
    "GR24 synthetic SL -> Strigolactone supply")
nin("T104", "LBO (LATERAL BRANCHING OXIDOREDUCTASE) not in network",
    "LBO catalyses the final SL-biosynthesis step; not modelled as a separate node")

# ---- Light/phy axis (T067-T070, T086) ------------------------------------
add("T067", ["HY5"], {"HY5": 0.0}, {}, "exact_match",
    "hy5 KO")
add("T068", ["HY5"], {"HY5": 0.0}, {}, "family_member",
    "hy5 hyh double -> HYH maps to HY5 paralog; double gm=0")
add("T069", ["PHYB"], {"PHYB": 0.0}, {}, "exact_match",
    "phyB KO")
add("T070", ["PHYB"], {"PHYB": 0.0}, {}, "family_member",
    "phyA -> PHYB node represents the phytochrome family in this network")
add("T072", ["LAX3"], {"LAX3": 0.0}, {}, "exact_match",
    "lax3 (independent replicate)")
add("T086", ["PHYB"], {"PHYB": 0.1}, {}, "mechanism_mapping",
    "Far-Red light inactivates PHYB (shade avoidance) -> PHYB gm=0.1")

# ---- Auxin treatments & inhibitors (T075, T076, T079, T080, T092, T093, T111, T137) --
add("T075", ["Auxin"], {}, {"Auxin": 1.0}, "treatment_analog",
    "IAA treatment -> Auxin supply")
add("T076", ["Auxin"], {}, {"Auxin": 1.0}, "treatment_analog",
    "NAA -> Auxin supply (synthetic auxin)")
add("T079", ["PIN"], {"PIN": 0.1}, {}, "mechanism_mapping",
    "TIBA blocks polar auxin transport -> PIN KD")
add("T080", ["PIN"], {"PIN": 0.1}, {}, "mechanism_mapping",
    "NPA blocks polar auxin transport -> PIN KD")
add("T092", ["ARF7", "ARF19"], {"ARF7": 0.1, "ARF19": 0.1}, {},
    "mechanism_mapping",
    "PCIB antagonises auxin-responsive ARFs -> ARF7/19 KD")
add("T093", ["TIR1"], {"TIR1": 0.1}, {}, "mechanism_mapping",
    "auxinole is a TIR1/AFB antagonist -> TIR1 KD")
add("T111", ["Auxin"], {}, {"Auxin": 1.0}, "mechanism_mapping",
    "alf1/sur dominant mutant -> constitutive auxin accumulation -> Auxin exogenous=1.0")
add("T137", ["TIR1"], {"TIR1": 0.1}, {}, "mechanism_mapping",
    "miR393 targets TIR1/AFB transcripts -> TIR1 KD")

# ---- Cytokinin treatments (T078, T095) ----------------------------------
add("T078", ["Cytokinin"], {}, {"Cytokinin": 1.0}, "treatment_analog",
    "Zeatin -> Cytokinin supply")
add("T095", ["Cytokinin"], {}, {"Cytokinin": 1.0}, "treatment_analog",
    "kinetin -> Cytokinin supply")

# ---- Nitrate conditions (T082-T084, T141, T142, T155, T156) --------------
add("T082", ["Low_Nitrate"], {"Low_Nitrate": 0.0}, {}, "mechanism_mapping",
    "10 mM KNO3 high-N -> Low_Nitrate turned off (gm=0)")
add("T083", ["ANR1"], {"ANR1": 2.0}, {}, "mechanism_mapping",
    "localised KNO3 patch -> local N-foraging response via ANR1 induction (OE-like)")
add("T084", ["NLP7"], {"NLP7": 2.0}, {}, "mechanism_mapping",
    "glutamate -> activates N-signalling TF NLP7 (surrogate for amino-acid N sensing)")
add("T141", ["CLE"], {"CLE": 0.997},
    {"Low_Nitrate": 1.0}, "composite_member",
    "cle3 single KO under low N -> CLE composite single-paralog; low-N condition Low_Nitrate exogenous=1",
    baseline="WT")
add("T142", ["CLV1"], {"CLV1": 0.0},
    {"Low_Nitrate": 1.0}, "exact_match",
    "clv1 KO under low N",
    baseline="WT")
add("T155", ["ABI4_5", "Low_Nitrate"], {"ABI4_5": 0.5, "Low_Nitrate": 0.0},
    {}, "composite_member",
    "abi5 single KO under high-N; abi5 maps to ABI4_5 composite (gm=0.5 partial), Low_Nitrate gm=0 marks high-N",
    baseline="WT")
add("T156", ["Low_Nitrate"], {}, {"Low_Nitrate": 1.0}, "exact_match",
    "systemic low-N environment -> Low_Nitrate supply",
    baseline="WT")

# ---- Phosphate conditions (T085, T119) -----------------------------------
add("T085", ["Low_Phosphate"], {}, {"Low_Phosphate": 1.0}, "exact_match",
    "low-Pi environment -> Low_Phosphate supply")
add("T119", ["Low_Phosphate"], {}, {"Low_Phosphate": 1.0}, "mechanism_mapping",
    "low-Pi with Fe omission; Fe node not in network so encoding reduces to Low_Phosphate supply; biology caveat noted",
    notes="Fe-omission cancels low-P LR response in biology; network cannot distinguish")

# ---- Environmental stresses not in network -------------------------------
nin("T087", "UV_B stress not modelled")
nin("T088", "Salt stress not modelled")
nin("T089", "Hypoxia not modelled")
nin("T090", "Low_Potassium not modelled")
nin("T091", "High_Water regime not modelled")
nin("T117", "Almt1 malate rescue not modelled (ALMT1 absent)")
nin("T118", "SHAM/mitochondrial respiration axis not modelled")
nin("T120", "PDR2 P5-type ATPase not in network")
nin("T121", "NAC1 not in network")
nin("T124", "KAI2 not in network -> KAI2 + GR24 not encodable")
nin("T125", "RALF4 not in network")
nin("T126", "QSK1 IMK2 receptor-like kinases not in network")
nin("T127", "ORE1 NAC TF not in network")
nin("T132", "TOR kinase axis not in network")
nin("T135", "PAX kinase not in network")
nin("T136", "BRX membrane protein not in network")
nin("T140", "Fe-patch local response not modelled")
nin("T157", "PID kinase (PIN polarity regulator) not in network")
nin("T105", "DAO2 maps to DAO1 as paralog, but DAO1 is already a source node with default gm=1.0 so dao1 dao2 double would require DAO1 gm=0",
    "Actually encodeable via family: DAO1 gm=0.0. Reassigning below.")
# Reassign T105 as family_member (dao1 dao2 double -> DAO1 node as family representative)
add("T105", ["DAO1"], {"DAO1": 0.0}, {}, "family_member",
    "dao1 dao2 double -> DAO1 node represents the DAO IAA-oxidase family")

nin("T106", "ARF3/ETT not in network")
nin("T107", "IBR1/3/10 IBA->IAA conversion genes not in network")
nin("T108", "ACR4 receptor-like kinase not in network")
nin("T109", "RALF34 peptide not in network")
nin("T110", "CEP5/CEPR peptide-receptor pair not in network")
nin("T112", "BBX16 B-box TF not in network")
nin("T113", "AGL21 MADS TF not in network")

# ---- CLE family (T114, T143) ---------------------------------------------
add("T114", ["CLE"], {"CLE": 2.0}, {}, "composite_member",
    "CLE-peptide OE (general) -> CLE composite OE")
add("T143", ["CLE"], {"CLE": 2.0}, {}, "composite_member",
    "CLE3 OE -> CLE composite OE")

# ---- NRT1.1 phospho variants (T115, T116) --------------------------------
add("T115", ["CHL1"], {"CHL1": 2.0}, {}, "mechanism_mapping",
    "T101A NRT1.1 prevents phosphorylation -> locked low-affinity mode -> enhanced N-uptake signalling (encoded as CHL1 gm=2.0)")
add("T116", ["CHL1"], {"CHL1": 0.5}, {}, "mechanism_mapping",
    "T101D phospho-mimic locks NRT1.1 in high-affinity/low-signal mode -> CHL1 functional reduction gm=0.5")

# ---- Gain-of-function + treatment (T096, T097) ---------------------------
add("T096", ["IAA28", "Auxin"], {"IAA28": 2.0}, {"Auxin": 1.0},
    "mechanism_mapping",
    "iaa28-1 gof + NAA -> stabilised IAA28 cannot be degraded even with excess auxin; combined treatment compared to WT")
add("T097", ["IAA14", "Auxin"], {"IAA14": 2.0}, {"Auxin": 1.0},
    "mechanism_mapping",
    "slr-1 (IAA14 stabilised) + NAA vs WT -> stabilised IAA14 resists auxin-dependent degradation")
add("T098", ["ABI4_5", "Auxin"], {"ABI4_5": 0.5}, {"Auxin": 1.0},
    "composite_member",
    "abi4 + IAA combined vs WT -> abi4 partial (ABI4_5 composite) plus auxin supply")

# ---- Rescue experiments (T099-T103, T122, T123, T146) -------------------
add("T099", ["PYL8", "Auxin"], {"PYL8": 0.0}, {"Auxin": 1.0},
    "mechanism_mapping",
    "pyl8 + IAA rescue; baseline = pyl8 alone",
    baseline="mutant")
add("T100", ["ARF7", "ARF19"], {"ARF7": 2.0, "ARF19": 0.0}, {},
    "mechanism_mapping",
    "arf7 arf19 + ARF7-GR (dex induced) rescue; ARF7 forced active on top of arf19 loss; baseline = arf7 arf19 double",
    baseline="mutant")
add("T101", ["ARF7", "ARF19", "LBD"], {"ARF7": 0.0, "ARF19": 0.0, "LBD": 2.0},
    {}, "mechanism_mapping",
    "arf7 arf19 + LBD16 OE rescue; LBD forced downstream of the ARF block",
    baseline="mutant")
add("T102", ["PLT"], {"PLT": 2.0}, {}, "mechanism_mapping",
    "plt3 plt5 plt7 + PLT1 OE rescue -> PLT composite forced back on (gm=2.0)",
    baseline="mutant")
add("T103", ["PLT", "PIN"], {"PLT": 0.0, "PIN": 2.0}, {},
    "mechanism_mapping",
    "plt3 plt5 plt7 + PIN1 OE rescue -> PIN forced high but PLT block remains; expected unchanged vs plt3/5/7 mutant",
    baseline="mutant")
add("T122", ["MAX2", "Strigolactone"], {"MAX2": 0.0}, {"Strigolactone": 1.0},
    "mechanism_mapping",
    "max2 + GR24: signalling-mutant rescue (Trap 5) -> expected unchanged vs max2 alone",
    baseline="mutant")
add("T123", ["D14", "Strigolactone"], {"D14": 0.0}, {"Strigolactone": 1.0},
    "mechanism_mapping",
    "d14 + GR24: signalling-mutant rescue (Trap 5) -> expected unchanged vs d14 alone",
    baseline="mutant")
add("T146", ["TAA1", "Ethylene"], {"TAA1": 0.5}, {"Ethylene": 1.0},
    "mechanism_mapping",
    "wei2 (ASA1) under ACC; wei2 reduces Trp->IAA precursor pool. Encoded as TAA1 partial KD + ethylene supply")

# ---- GA axis (T128-T131) -------------------------------------------------
add("T128", ["GA"], {}, {"GA": 1.0}, "treatment_analog",
    "GA3 -> GA supply")
add("T129", ["GA"], {"GA": 0.1}, {}, "mechanism_mapping",
    "PAC (paclobutrazol) inhibits GA biosynthesis -> GA gm=0.1")
add("T130", ["GA"], {"GA": 0.1}, {}, "mechanism_mapping",
    "ga1 KO blocks GA biosynthesis; GA1 (CPS) not a separate node -> encode as GA gm=0.1")
add("T131", ["DELLA"], {"DELLA": 0.0}, {}, "composite_collapse",
    "della quadruple KO -> DELLA composite fully lost")

# ---- BR axis (T133, T134, T147-T149) -------------------------------------
add("T133", ["Brassinosteroid"], {}, {"Brassinosteroid": 1.0},
    "treatment_analog",
    "BR brassinolide -> Brassinosteroid supply")
add("T134", ["BRI1"], {"BRI1": 0.0}, {}, "exact_match",
    "bri1 KO")
add("T147", ["BZR"], {"BZR": 2.0}, {}, "composite_member",
    "bzr1-1D dominant gof -> BZR composite hyper-active; gm=2.0")
add("T148", ["BZR"], {"BZR": 2.0}, {}, "composite_member",
    "bes1-D (BZR2-D) dominant gof -> BZR composite hyper-active")
add("T149", ["Brassinosteroid", "Low_Nitrate"], {},
    {"Brassinosteroid": 1.0, "Low_Nitrate": 1.0}, "treatment_analog",
    "EBR (epi-brassinolide) under mild N-deficiency -> BR + low-N dual supply")

# ---- Cytokinin response TFs (T150, T151) ---------------------------------
add("T150", ["ARR_B"], {"ARR_B": 0.0}, {}, "composite_collapse",
    "arr1 arr10 arr12 triple -> full type-B ARR composite KO")
add("T151", ["ARR_B"], {"ARR_B": 0.5}, {}, "composite_member",
    "arr10 arr12 double -> partial type-B ARR composite loss")

# ---- Bending / drought (T138, T139) --------------------------------------
add("T138", ["PIN"], {"PIN": 2.0}, {}, "mechanism_mapping",
    "48-h root bending induces local auxin maxima via PIN3 repolarisation -> PIN gm=2.0 surrogate")
add("T139", ["ABA"], {}, {"ABA": 1.0}, "mechanism_mapping",
    "drought stress activates ABA biosynthesis -> ABA exogenous=1.0 surrogate")

# ---- WOX family (T144) ---------------------------------------------------
add("T144", ["WOX11"], {"WOX11": 0.0}, {}, "family_member",
    "wox11 wox12 double -> WOX12 maps to WOX11 paralog; double gm=0")

# ---------------------------------------------------------------------------
# Build final dataset
# ---------------------------------------------------------------------------
recs = []
for p in raw["perturbations"]:
    tid = p["test_id"]
    if tid not in M:
        raise RuntimeError(f"Missing mapping for {tid}: {p.get('gene')}")
    m = M[tid]
    in_net = m["in_network"]
    perturbations_list = []
    for node, val in m["gm"].items():
        perturbations_list.append({
            "node": node,
            "modifier_type": "gene_modifier",
            "value": float(val),
        })
    for node, val in m["exo"].items():
        perturbations_list.append({
            "node": node,
            "modifier_type": "exogenous_supply",
            "value": float(val),
        })
    # Carry evidence through (trim verification keys to flat format)
    evid_list = []
    for e in p.get("evidence", []):
        authors = e.get("authors", "")
        if isinstance(authors, list):
            authors = ", ".join(authors)
        flat = {
            "doi": e.get("doi", ""),
            "title": e.get("title", ""),
            "authors": authors,
            "year": e.get("year"),
            "journal": e.get("journal", ""),
            "evidence_sentence": e.get("evidence_sentence", ""),
            "claim": e.get("claim", ""),
        }
        evid_list.append(flat)
    expected = m["expected"] if m["expected"] else p.get("expected_direction")
    entry = {
        "test_id": tid,
        "gene": p.get("gene", ""),
        "perturbation_type": p.get("perturbation_type", ""),
        "expected_direction": expected,
        "in_network": in_net,
        "network_gene": m["nog"],
        "gene_modifiers": m["gm"],
        "exogenous_supply": m["exo"],
        "perturbations": perturbations_list,
        "notes": m["notes"] or m["rnote"],
        "evidence": evid_list,
        "phenotype_node": PHENOTYPE_NODE,
        "comparison_baseline": m["baseline"],
        "condition": p.get("condition", "normal"),
        "reconciliation_type": m["rtype"],
        "reconciliation_note": m["rnote"],
    }
    recs.append(entry)

# Append WT negative control (T158)
recs.append({
    "test_id": "T158",
    "gene": "WT",
    "perturbation_type": "control",
    "expected_direction": "unchanged",
    "in_network": True,
    "network_gene": [],
    "gene_modifiers": {},
    "exogenous_supply": {},
    "perturbations": [],
    "notes": "WT negative control: no perturbation; expected LR density = baseline.",
    "evidence": [{
        "doi": "control",
        "title": "WT control -- no perturbation",
        "authors": "FLASH-P",
        "year": 2026,
        "journal": "N/A",
        "evidence_sentence": "Untreated wild-type Col-0 baseline used as reference for all perturbation comparisons.",
        "claim": "WT baseline is unchanged relative to itself"
    }],
    "phenotype_node": PHENOTYPE_NODE,
    "comparison_baseline": "WT",
    "condition": "normal",
    "reconciliation_type": "control",
    "reconciliation_note": "Internal reference run (no node perturbed)",
})

in_ct = sum(1 for r in recs if r["in_network"])
nin_ct = sum(1 for r in recs if not r["in_network"])

output = {
    "metadata": {
        "flash_p_version": "2.0",
        "phenotype": "Lateral_Root_Density",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
        "total_tests": len(recs),
        "in_network": in_ct,
        "not_in_network": nin_ct,
        "phenotype_node": PHENOTYPE_NODE,
    },
    "direction_threshold": 0.05,
    "perturbations": recs,
}

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(output, fh, indent=2)

# Summary
from collections import Counter
by_rtype = Counter(r["reconciliation_type"] for r in recs)
by_cond = Counter(r["condition"] for r in recs)
ctrl_ct = sum(1 for r in recs if r["reconciliation_type"] == "control")

print(f"Wrote {OUT_PATH}")
print(f"Total tests: {len(recs)}")
print(f"In-network: {in_ct}")
print(f"Not-in-network: {nin_ct}")
print(f"Control tests: {ctrl_ct}")
print("\nBy reconciliation_type:")
for k, v in sorted(by_rtype.items(), key=lambda x: -x[1]):
    print(f"  {k:22s} {v}")
print("\nBy condition:")
for k, v in sorted(by_cond.items(), key=lambda x: -x[1]):
    print(f"  {k:30s} {v}")
