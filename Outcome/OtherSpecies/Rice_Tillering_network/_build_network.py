"""
Rice Tillering network builder (Step 2).

Reads curated_edges.json (merged Step 1 + 1.5), selects the edges to include
in the model, renames nodes to satisfy the GENE naming regex
(^[A-Z][A-Z0-9_]*$ — so Os* prefixes are dropped and '.' -> '_'), writes the
four BUILDER outputs.

Biology notes:
- Strigolactone Perception Gate: SL -> D14 ONLY. D14 and D3 are co-inhibitors
  of D53. D3 is a source (constitutive F-box). No SL bypass edges to OsTB1/
  IPA1/Tiller_Number (prompt mandate for d14+GR24, d3+GR24 tests).
- D53 double-brake: D53 -| IPA1, -| TB1 (via IPA1), -| MOC1, -| CKX9.
- Coherent feed-forward: high SL -> D53 degraded -> IPA1 up -> TB1 up AND
  CKX9 up -> Cytokinin down.
- CK Biosynthesis/Degradation Balance: IPT + LOG (synthesis) vs CKX2 + CKX9
  (degradation).
- GA/DELLA: SLR1 -| (degraded by) GA; SLR1 stabilises MOC1 and NGR5.
- NGR5/N: N + Sucrose + NRT1_1B activate NGR5 which PRC2-represses TB1 and
  IPA1; GA degrades NGR5. Multi-output scaffold.
- Clock: Light -> CCA1; CCA1 -| PRR1; PRR1 -| CCA1 (Motif 7 mutual inhibition).
- Dropped nodes documented as literature_gap-style residuals in build log.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
NET = HERE / "network"
NET.mkdir(exist_ok=True, parents=True)

# ----------------------------------------------------------------------------
# Rename: drop "Os" prefix and replace '.' with '_' so all GENE ids pass
# ^[A-Z][A-Z0-9_]*$
# ----------------------------------------------------------------------------
RENAME = {
    "OsTB1": "TB1",
    "OsCKX2": "CKX2",
    "OsCKX9": "CKX9",
    "OsCKX4": "CKX4",
    "OsCKX11": "CKX11",
    "OsIPT": "IPT",
    "OsLOG": "LOG",
    "OsHK4": "HK4",
    "OsHK3": "HK3",
    "OsAHP": "AHP",
    "OsRR21": "RR21",
    "OsRR_typeA": "RR_TYPEA",
    "OsPIN1a": "PIN1A",
    "OsPIN1b": "PIN1B",
    "OsPIN2": "PIN2",
    "OsPIN9": "PIN9",
    "OsTAR2": "TAR2",
    "OsYUCCA": "YUCCA",
    "OsTIR1": "TIR1",
    "OsIAA": "IAA",
    "OsARF": "ARF",
    "OsARF12": "ARF12",
    "OsCDKF_2": "CDKF2",
    "OsMADS57": "MADS57",
    "OsCCA1": "CCA1",
    "OsPRR1": "PRR1",
    "OsTCP19": "TCP19",
    "OsLBD37": "LBD37",
    "OsGATA8": "GATA8",
    "OsBZR1": "BZR1",
    "OsVIL2": "VIL2",
    "OsSHI1": "SHI1",
    "OsGA20ox2": "GA20OX2",
    "OsMAX1": "MAX1",
    "OsNLP4": "NLP4",
    "OsNiR": "NIR",
    "OsAMT3.2": "AMT3_2",
    "OsDEP1": "DEP1",
    "OsLAX1": "LAX1",
    "OsHOX12": "HOX12",
    "OsDRM1": "DRM1",
    "Os1900": "MAX1_1900",
    "NRT1.1B": "NRT1_1B",
    # TAB1 (axillary meristem Tillers Absent 1) is the OsWUS ortholog, same
    # gene as MOC3 in the more recent literature — collapse the aliases.
    "TAB1": "MOC3",
}


def ren(x):
    return RENAME.get(x, x)


# ----------------------------------------------------------------------------
# Selected edges (whitelist — by curated edge_id)
# ----------------------------------------------------------------------------
# Rationale for key exclusions:
#   E009 IPA1->OsDEP1         : panicle, floating for tillering
#   E012 IPA1->OsHK4          : would close CK positive-feedback loop (Trap 1)
#   E014 miR529-|IPA1         : redundant w/ miR156
#   E024 OsTB1->D14           : E025/E122 cover MADS57-D14 axis
#   E028 MOC1->OSH1           : OSH1 has no path to phenotype
#   E038 NRT1.1B->Nitrogen    : backward (Nitrogen is source)
#   E044 OsCKX4-|Cytokinin    : CKX family reps already covered by CKX2/CKX9
#   E046 OsCKX11-|Cytokinin   : ditto
#   E056 SL->OsCKX9           : violates SL perception-gate purity; routed via D53
#   E057 OsPIN1a-|Tiller      : kept PIN1B as representative
#   E059 OsPIN2->Tiller       : minor
#   E063-E065 Auxin/TIR/IAA/ARF: no ARF->target edges in curation, arm floats
#   E073 Sucrose->Tiller      : summary edge; detailed paths preserved
#   E079 TAB1->Tiller         : TAB1 collapsed to MOC3 (aliases)
#   E080 TAB1->OSH1           : TAB1/OSH1 replaced by MOC3 path
#   E086 SL-|OsBZR1           : SL perception-gate purity
#   E087-E088 OsTB2           : natural variation; minor
#   E089-E091 GT1/NCED1       : ABA path simplified (ABA modelled as source)
#   E094-E096 NLP4/NIR        : simplification
#   E100 SL->Tiller (summary) : detailed cascade preserved
#   E101 IPA1->Tiller (sum)   : detailed cascade preserved
#   E102-E104 NPF7.7/AAP5/GS1 : minor N-->CK feeders
#   E105-E106 SLR1/GA->Tiller : summary
#   E107 ARF12->CDKF2         : floating
#   E108 SL-|PIN1             : SL perception-gate purity
#   E110-E112 Auxin/SL->TB1   : summary edges
#   E113 N-|TB1               : redundant w/ NGR5 path
#   E114 N-|TCP19             : redundant w/ LBD37 path
#   E122 TB1->MADS57          : sign=0 post-translational; MADS57 path via E025+E026
#   E124 SL->AM_Fungi         : out of scope
#   E125-E130 summary edges   : detailed paths preserved
#   E131 OsLAX1=LAX1 alias    : no separate node
#   E135-E136 GID1-|SLR1/NGR5 : GA effect encoded as direct E032/E033
#   E140-E141 D53->TPL->IPA1  : redundant w/ direct D53-|IPA1 (E004)
#   E143 D14->D3              : D3 is source in the Perception Gate motif
#   E149 OsGATA8-|OsAMT3.2    : AMT3.2 has no path to phenotype
#   E150 OsGATA8->Tiller (sum): detailed path via TCP19-DLT preserved
#   E154 MOC3->Tiller (sum)   : detailed FON1 path preserved
#   E156-E159 T20/HOX12/ABA   : ABA modelled as source; mini-cascade skipped
#   E160-E161 HK3             : HK4 is the canonical CK receptor for tillering
#   E162-E163 TB1->DRM1       : dormancy marker; simplification
#   E164 MAX1<->1900 alias    : kept both nodes separately

INCLUDE_EDGES = {
    # Decapitation/auxin
    "E109",  # Decapitation -| Auxin
    "E120",  # TAR2 -> Auxin
    "E121",  # YUCCA -> Auxin

    # Auxin targets (including apical-dominance mechanisms)
    "E021",  # Auxin -> D10
    "E022",  # Auxin -> D17
    "E050",  # Auxin -| IPT
    "E062",  # Auxin -> TB1

    # SL biosynthesis
    "E017",  # D27 -> SL
    "E018",  # D10 -> SL
    "E019",  # D17 -> SL
    "E020",  # MAX1 -> SL
    "E151",  # MAX1_1900 -> SL
    "E155",  # T20 -> SL

    # Inputs to SL biosynthesis
    "E097",  # Phosphate -| D27
    "E098",  # Phosphate -| D10
    "E099",  # Phosphate -| D17
    "E115",  # N -| D10
    "E116",  # N -| D17
    "E117",  # N -| D27
    "E152",  # N -> MAX1_1900

    # SL perception gate
    "E001",  # SL -> D14
    "E002",  # D14 -| D53
    "E003",  # D3 -| D53
    "E067",  # CCA1 -> D14
    "E068",  # CCA1 -> D10
    "E036",  # NGR5 -| D14
    "E025",  # MADS57 -| D14

    # D53 regulation and outputs
    "E004",  # D53 -| IPA1
    "E005",  # D53 -| MOC1
    "E006",  # D53 -| CKX9
    "E008",  # IPA1 -> D53 (negative feedback with E004 — stabilising)
    "E072",  # Sucrose -> D53

    # IPA1 regulation
    "E013",  # miR156 -| IPA1
    "E015",  # IPI1 -| IPA1
    "E016",  # SHI1 -| IPA1
    "E055",  # RR21 -> IPA1
    "E069",  # CCA1 -> IPA1
    "E144",  # NGR5 -| IPA1

    # IPA1 outputs
    "E007",  # IPA1 -> TB1
    # E010 (IPA1 -> LOG) DROPPED — would close a 6-step positive-feedback loop
    # IPA1 -> LOG -> Cytokinin -> HK4 -> AHP -> RR21 -> IPA1 (Trap 1).
    "E011",  # IPA1 -> PIN1B

    # TB1 regulation and output
    "E023",  # TB1 -| Tiller_Number
    "E035",  # NGR5 -| TB1
    "E048",  # Cytokinin -| TB1
    "E066",  # CCA1 -> TB1
    "E084",  # BZR1 -| TB1
    "E133",  # T6P -| TB1
    "E147",  # VIL2 -| TB1

    # MADS57 axis (miR444 test)
    "E026",  # miR444 -| MADS57

    # MOC1 axis
    "E027",  # MOC1 -> Tiller_Number
    "E029",  # TAD1 -| MOC1
    "E030",  # TE -| MOC1
    "E031",  # SLR1 -> MOC1
    "E123",  # MOC1 -> LAX1
    "E153",  # MOC1 -> MOC3

    # MOC3/FON axis
    "E081",  # FON2 -| MOC3     (TAB1 renamed to MOC3)
    "E082",  # MOC3 -> FON1
    "E083",  # FON1 -> Tiller_Number

    # LAX axis
    "E076",  # LAX1 -> Tiller_Number

    # Cytokinin biosynthesis/degradation balance
    "E049",  # IPT -> Cytokinin
    "E051",  # LOG -> Cytokinin
    "E043",  # CKX2 -| Cytokinin
    "E045",  # CKX9 -| Cytokinin
    "E139",  # RR_TYPEA -| Cytokinin (CK negative feedback)
    "E093",  # DST -> CKX2
    # E047 (Cytokinin -> Tiller_Number) DROPPED — would put the phenotype
    # above the §10 hard cap of 5 activators. CK effect still cascades via
    # Cytokinin -| TB1 -| Tiller_Number.

    # CK signalling chain (one-way — E012 dropped to break +feedback)
    "E052",  # Cytokinin -> HK4
    "E053",  # HK4 -> AHP
    "E054",  # AHP -> RR21
    "E138",  # Cytokinin -> RR_TYPEA

    # PIN transporters
    "E058",  # PIN1B -| Tiller_Number
    "E060",  # PIN9 -> Tiller_Number
    "E061",  # Ammonium -> PIN9

    # GA/DELLA/NGR5
    "E032",  # GA -| SLR1
    "E033",  # GA -| NGR5
    "E034",  # SLR1 -> NGR5
    "E137",  # GA20OX2 -> Gibberellin
    "E037",  # Nitrogen -> NGR5
    "E134",  # NRT1_1B -> NGR5
    "E145",  # Sucrose -> NGR5

    # N-TCP19-DLT arm
    "E039",  # TCP19 -| DLT
    "E040",  # DLT -> Tiller_Number
    "E041",  # LBD37 -| TCP19
    "E042",  # N -> LBD37
    "E148",  # GATA8 -| TCP19

    # BR arm
    "E085",  # BR -> BZR1
    "E142",  # BR -> DLT

    # Sugar/T6P
    "E075",  # MOC2 -> Sucrose
    "E132",  # Sucrose -> T6P
    "E146",  # DTN1 -> Sucrose

    # Clock
    "E070",  # PRR1 -| CCA1
    "E071",  # CCA1 -| PRR1
    "E074",  # Sucrose -| CCA1
    "E118",  # Light -> CCA1
    "E119",  # Photoperiod -> PRR1

    # ABA output
    "E092",  # ABA -| Tiller_Number
}


# ----------------------------------------------------------------------------
# Node metadata: full_name, description, type, is_source (derived from edges)
# ----------------------------------------------------------------------------
NODE_META = {
    # Environment
    "Nitrogen":        ("ENVIRONMENT", "Soil nitrogen supply",
                        "Nitrate + ammonium pool; activates NGR5 (NRT1.1B -> PRC2) and LBD37 arms, represses SL biosynthesis genes."),
    "Ammonium":        ("ENVIRONMENT", "Ammonium form of N",
                        "Ammonium-specific N species; activates PIN9 auxin efflux carrier."),
    "Phosphate":       ("ENVIRONMENT", "Soil phosphate",
                        "P sufficiency represses SL biosynthesis; P starvation elevates D27/D10/D17 and SL."),
    "Light":           ("ENVIRONMENT", "Light (photosynthetic + signalling)",
                        "Entrains circadian CCA1 expression."),
    "Photoperiod":     ("ENVIRONMENT", "Photoperiod length",
                        "Regulates PRR1 evening peak in rice clock."),
    "Decapitation":    ("ENVIRONMENT", "Shoot apex removal",
                        "Removes polar auxin source; releases axillary buds."),
    # Hormones
    "Strigolactone":   ("HORMONE", "Strigolactone (orobanchol, 4-deoxyorobanchol)",
                        "Branching-suppressing hormone synthesised via D27/D17/D10/MAX1 pathway; perceived by D14."),
    "Cytokinin":       ("HORMONE", "Cytokinin (iP, tZ)",
                        "Promotes tiller bud outgrowth; balance of IPT/LOG synthesis vs CKX degradation."),
    "Auxin":           ("HORMONE", "Indole-3-acetic acid",
                        "Apical auxin maintains bud dormancy via IPT repression + SL-biosynthesis activation + TB1 activation."),
    "Gibberellin":     ("HORMONE", "Active GAs (GA1, GA4)",
                        "Degrades SLR1 and NGR5 via GID1; net GA effect is anti-tillering."),
    "Brassinosteroid": ("HORMONE", "Castasterone / brassinolide",
                        "Stabilises BZR1 (which complexes with D53 on TB1 promoter) and activates DLT."),
    "ABA":             ("HORMONE", "Abscisic acid",
                        "Promotes bud dormancy; treatment reduces tillering."),
    # Metabolites
    "Sucrose":         ("METABOLITE", "Sucrose",
                        "Photosynthetic sugar; stabilises D53, activates NGR5, represses CCA1, produces T6P."),
    "T6P":             ("METABOLITE", "Trehalose-6-phosphate",
                        "Sugar-status signal that represses TB1 in buds."),
    # Regulatory RNAs
    "miR156":          ("REGULATORY_RNA", "microRNA 156",
                        "Cleaves IPA1/OsSPL14 mRNA; juvenile-phase high expression."),
    "miR444":          ("REGULATORY_RNA", "microRNA 444a",
                        "Cleaves OsMADS57 mRNA; miR444 OE reduces tillers via MADS57 loss."),
    # SL biosynthesis
    "T20":             ("GENE", "T20 (Z-ISO, rice zeta-carotene isomerase)",
                        "Upstream of D27 in carotenoid pathway; supplies precursors for both SL and ABA."),
    "D27":             ("GENE", "DWARF27 (iron-containing beta-carotene isomerase)",
                        "First committed step of SL biosynthesis; converts all-trans to 9-cis beta-carotene."),
    "D10":             ("GENE", "DWARF10 / CCD8",
                        "Carotenoid cleavage dioxygenase 8; converts 9-cis-beta-apo-10'-carotenal to carlactone."),
    "D17":             ("GENE", "DWARF17 / HTD1 / CCD7",
                        "CCD7; cleaves 9-cis-beta-carotene upstream of D10."),
    "MAX1":            ("GENE", "OsMAX1 family (Os900/Os1400/Os1500/Os5100)",
                        "Generic collapsed MAX1 paralog family; converts carlactone to canonical SLs."),
    "MAX1_1900":       ("GENE", "OsMAX1 paralog Os1900 (N-responsive)",
                        "N-fertilisation-inducible MAX1-like; promoter mutations increase tillers under low N."),
    # SL signalling
    "D14":             ("GENE", "DWARF14 (alpha/beta hydrolase SL receptor)",
                        "SL receptor; binds GR24/endogenous SL, then co-inhibits D53 with D3."),
    "D3":              ("GENE", "DWARF3 (F-box subunit of SCF^D3)",
                        "Constitutive F-box; co-inhibitor of D53 together with ligand-bound D14."),
    # D53 and hubs
    "D53":             ("PROTEIN_COMPLEX", "DWARF53 (SMXL ortholog / EAR-motif repressor)",
                        "Double-brake repressor of IPA1 and MOC1; SL-induced ubiquitin-proteasome turnover."),
    # IPA1 / TB1 axis
    "IPA1":            ("GENE", "IDEAL PLANT ARCHITECTURE1 / OsSPL14 / WFP",
                        "SBP-box TF; activates TB1/LOG/PIN1b; repressed by D53, miR156, IPI1, SHI1, NGR5."),
    "TB1":             ("GENE", "OsTB1 / FC1 (TEOSINTE BRANCHED1 / FINE CULM1)",
                        "TCP family branching-repressor TF; integrates IPA1, CK, Auxin, NGR5, T6P signals."),
    "IPI1":            ("GENE", "IPA1-INTERACTING PROTEIN 1",
                        "RING-type E3 ubiquitin ligase; ubiquitinates IPA1 (K48 chains in panicles)."),
    "SHI1":            ("GENE", "OsSHI1",
                        "Physically binds IPA1 and represses its transcriptional activation."),
    "VIL2":            ("GENE", "OsVIL2",
                        "Chromatin-interacting factor; binds and represses OsTB1 promoter (Yoon 2019)."),
    "MADS57":          ("GENE", "OsMADS57",
                        "MADS-box TF; binds CArG motif in D14 promoter and represses D14 transcription."),
    # MOC family
    "MOC1":            ("GENE", "MONOCULM 1 (GRAS TF)",
                        "Master activator of axillary meristem initiation; stabilised by SLR1; degraded by TAD1/TE APC/C."),
    "MOC3":            ("GENE", "MOC3 / OsWUS / TAB1",
                        "WUSCHEL homolog required for AM initiation; cooperates with MOC1 to activate FON1."),
    "FON1":            ("GENE", "FLORAL ORGAN NUMBER 1",
                        "CLAVATA1-like kinase; specifically required for tiller bud elongation (fon1 forms buds but fails to elongate)."),
    "FON2":            ("GENE", "FLORAL ORGAN NUMBER 2",
                        "CLV3-like peptide; restricts TAB1/MOC3 expression domain."),
    "LAX1":            ("GENE", "LAX PANICLE1",
                        "bHLH TF essential for AM initiation; lax1 + downstream axillary meristem loss."),
    # APC/C
    "TAD1":            ("GENE", "TILLERING AND DWARF 1 (CDH1-type APC/C co-activator)",
                        "Recruits MOC1 to APC/C for cell-cycle-dependent proteasomal degradation."),
    "TE":              ("GENE", "TILLER ENHANCER (CDC20-type APC/C co-activator)",
                        "APC/C co-activator that targets MOC1 for ubiquitin-proteasome degradation."),
    # CK
    "IPT":             ("GENE", "OsIPT family (adenylate isopentenyltransferase)",
                        "Rate-limiting CK biosynthesis enzymes (OsIPT4/OsIPT7 dominant in shoots)."),
    "LOG":             ("GENE", "LONELY GUY / OsLOG family",
                        "Converts CK nucleotides to active free bases."),
    "CKX2":            ("GENE", "OsCKX2 / Gn1a (cytokinin oxidase/dehydrogenase 2)",
                        "Primary CK-degrading enzyme; gn1a LOF accumulates CK and increases tillers."),
    "CKX9":            ("GENE", "OsCKX9",
                        "CK oxidase; SL-responsive via D53 de-repression; couples SL -> CK depletion."),
    "DST":             ("GENE", "DROUGHT AND SALT TOLERANCE (zinc-finger TF)",
                        "Binds DBS motif in CKX2 promoter and activates its transcription."),
    "HK4":             ("GENE", "OsHK4 (CK histidine kinase receptor)",
                        "Primary CK receptor for tillering; phosphorylates AHP."),
    "AHP":             ("GENE", "OsAHP1/2 (histidine phosphotransfer)",
                        "Relays phosphate signal from HK4 to type-B RR21."),
    "RR21":            ("GENE", "OsRR21 (type-B CK response regulator)",
                        "DNA-binding TF; binds CK-response elements in IPA1 promoter."),
    "RR_TYPEA":        ("GENE", "type-A OsRRs (primary CK-response genes)",
                        "CK-induced negative feedback regulators that dampen CK signalling."),
    # PIN
    "PIN1B":           ("GENE", "OsPIN1b (auxin efflux carrier)",
                        "PIN1 paralog; KO increases tillers; IPA1-activated."),
    "PIN9":            ("GENE", "OsPIN9 (ammonium-induced auxin efflux carrier)",
                        "Ammonium-specifically-induced PIN; OE increases tillers."),
    # Auxin biosynthesis
    "TAR2":            ("GENE", "OsTAR2 (TAA1/TAR family aminotransferase)",
                        "First step of tryptophan-dependent IAA biosynthesis."),
    "YUCCA":           ("GENE", "OsYUCCA family (flavin monooxygenase)",
                        "Rate-limiting step of IAA biosynthesis (IPA -> IAA)."),
    # GA/DELLA
    "SLR1":            ("GENE", "SLENDER RICE 1 (rice DELLA)",
                        "Growth-repressing DELLA; stabilises MOC1 and NGR5; degraded upon GA-GID1 perception."),
    "GA20OX2":         ("GENE", "OsGA20ox2 (SD1)",
                        "GA biosynthesis enzyme; sd1 (null) is the Green Revolution allele; reduced GA -> increased tillers."),
    # N / NGR5 arm
    "NGR5":            ("GENE", "NITROGEN-MEDIATED TILLER GROWTH RESPONSE 5 (AP2-TF)",
                        "Recruits PRC2 to TB1 and IPA1 promoters for H3K27me3 repression; N- and sucrose-activated, GA-degraded."),
    "NRT1_1B":         ("GENE", "NRT1.1B (nitrate transceptor)",
                        "Indica/japonica natural variation in N-responsive phosphorylation of NGR5."),
    "TCP19":           ("GENE", "OsTCP19",
                        "N-responsive TCP TF; represses DLT; N -> LBD37 -| TCP19 relieves DLT repression."),
    "LBD37":           ("GENE", "OsLBD37 (lateral organ boundaries)",
                        "N-induced TF that directly represses OsTCP19."),
    "GATA8":           ("GENE", "OsGATA8 (elite haplotype OsGATA8-H)",
                        "Zn-finger GATA TF; represses OsTCP19 (relieves DLT) and balances N-uptake with tiller productivity."),
    "DLT":             ("GENE", "DWARF AND LOW TILLERING (GRAS TF)",
                        "Positive regulator of tillering; BR-activated; repressed by TCP19."),
    # BR
    "BZR1":            ("GENE", "OsBZR1",
                        "BR-stabilised TF; recruits D53 to TB1 promoter for additional repression."),
    # Clock
    "CCA1":            ("GENE", "OsCCA1 / OsLHY (MYB-like clock TF)",
                        "Morning-peak clock component; activates TB1/D14/D10/IPA1; mutually inhibits PRR1."),
    "PRR1":            ("GENE", "OsPRR1 / OsTOC1 (pseudo-response regulator)",
                        "Evening-peak clock component; mutually inhibits CCA1."),
    # Sucrose biosynthesis
    "DTN1":            ("GENE", "Decreased Tiller Number 1 (FBP aldolase)",
                        "Required for photosynthesis-derived sucrose accumulation in shoot base; sucrose -> NGR5."),
    "MOC2":            ("GENE", "MOC2 (fructose-1,6-bisphosphatase 1)",
                        "Sucrose biosynthesis; moc2 shows monoculm-like tillering defect."),
    # Phenotype
    "Tiller_Number":   ("PHENOTYPE", "Tiller number",
                        "Final phenotype: number of rice tillers produced (per plant, per unit area)."),
}


# ----------------------------------------------------------------------------
# Read curated edges and build network.json
# ----------------------------------------------------------------------------
with open(DATA / "curated_edges.json", "r", encoding="utf-8") as f:
    curated = json.load(f)

filtered = [e for e in curated["edges"] if e["edge_id"] in INCLUDE_EDGES]
missing = INCLUDE_EDGES - {e["edge_id"] for e in filtered}
assert not missing, f"Missing edge ids: {missing}"

# Build node set and remap
node_ids = set()
edges_out = []
for i, e in enumerate(filtered, 1):
    src = ren(e["source"])
    tgt = ren(e["target"])
    node_ids.add(src)
    node_ids.add(tgt)
    # Normalise evidence (each entry flat; authors as string)
    evs = []
    for ev in e.get("evidence", []):
        a = ev.get("authors", "")
        if isinstance(a, list):
            a = ", ".join(a)
        evs.append({
            "doi": ev.get("doi", ""),
            "title": ev.get("title", ""),
            "authors": a,
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
        "sign": int(e["sign"]) if e["sign"] != 0 else 1,
        "edge_id": f"N{i:03d}",
        "effect": e.get("effect", "activation"),
        "mechanism": e.get("mechanism", ""),
        "evidence": evs,
    })

# is_source: true iff no incoming edges
incoming = {n: 0 for n in node_ids}
for e in edges_out:
    incoming[e["target"]] = incoming.get(e["target"], 0) + 1

nodes_out = []
for nid in sorted(node_ids):
    if nid not in NODE_META:
        raise ValueError(f"Missing NODE_META for {nid}")
    ntype, full_name, desc = NODE_META[nid]
    is_source = incoming.get(nid, 0) == 0
    nodes_out.append({
        "id": nid,
        "type": ntype,
        "full_name": full_name,
        "description": desc,
        "is_source": is_source,
    })

source_count = sum(1 for n in nodes_out if n["is_source"])
source_pct = round(source_count / len(nodes_out) * 100, 1) if nodes_out else 0.0

network = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Tillering",
        "phenotype_node": "Tiller_Number",
        "species": "Oryza sativa",
        "created": "2026-04-20",
        "total_nodes": len(nodes_out),
        "total_edges": len(edges_out),
        "source_nodes": source_count,
        "source_percentage": source_pct,
    },
    "nodes": nodes_out,
    "edges": edges_out,
}

with open(NET / "network.json", "w", encoding="utf-8") as f:
    json.dump(network, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# Build algebraic_equations.json
# ----------------------------------------------------------------------------
# For each node, collect activators (sign=+1) and inhibitors (sign=-1)
activators = {n["id"]: [] for n in nodes_out}
inhibitors = {n["id"]: [] for n in nodes_out}
for e in edges_out:
    if e["sign"] == 1:
        activators[e["target"]].append(e["source"])
    else:
        inhibitors[e["target"]].append(e["source"])

# Assert no node exceeds 7 activators or inhibitors (per BUILDER §10)
for nid in activators:
    if len(activators[nid]) > 7:
        print(f"WARNING: {nid} has {len(activators[nid])} activators")
    if len(inhibitors[nid]) > 7:
        print(f"WARNING: {nid} has {len(inhibitors[nid])} inhibitors")


def algebraic_formula(node, acts, inhs, is_source):
    if is_source:
        return f"{node} = gene_modifier + exogenous_supply"
    parts = []
    if acts:
        inner = " * ".join([f"max({a}, 0.01)" for a in acts])
        parts.append(f"({inner})^(1/{len(acts)})")
    if inhs:
        inner_i = " * ".join(inhs) if len(inhs) > 1 else inhs[0]
        parts.append(f"min(1/max({inner_i}, 0.1), 10.0)")
    body = " * ".join(parts) if parts else "1.0"
    return f"{node} = {body} * gene_modifier + exogenous_supply"


eqs = []
for n in nodes_out:
    nid = n["id"]
    acts = activators[nid]
    inhs = inhibitors[nid]
    eqs.append({
        "node": nid,
        "type": n["type"],
        "is_source": n["is_source"],
        "activators": acts,
        "inhibitors": inhs,
        "formula": algebraic_formula(nid, acts, inhs, n["is_source"]),
    })

alg = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Tillering",
        "species": "Oryza sativa",
        "created": "2026-04-20",
        "total_equations": len(eqs),
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
    "equations": eqs,
}

with open(NET / "algebraic_equations.json", "w", encoding="utf-8") as f:
    json.dump(alg, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# Build ode_equations.json (default K=1.0, n=2)
# ----------------------------------------------------------------------------
def ode_formula(node, acts, inhs, is_source):
    if is_source:
        return f"{node} = gene_modifier + exogenous_supply"
    pieces = []
    for a in acts:
        pieces.append(f"f({a})")
    for i in inhs:
        pieces.append(f"g({i})")
    body = " * ".join(pieces) if pieces else "1.0"
    return f"{node} = {body} * gene_modifier + exogenous_supply"


ode_eqs = []
for n in nodes_out:
    nid = n["id"]
    ode_eqs.append({
        "node": nid,
        "activators": activators[nid],
        "inhibitors": inhibitors[nid],
        "formula": ode_formula(nid, activators[nid], inhibitors[nid], n["is_source"]),
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

with open(NET / "ode_equations.json", "w", encoding="utf-8") as f:
    json.dump(ode, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------
# Build node_annotations.json
# ----------------------------------------------------------------------------
out_deg = {n["id"]: 0 for n in nodes_out}
for e in edges_out:
    out_deg[e["source"]] = out_deg.get(e["source"], 0) + 1

annotations = []
for n in nodes_out:
    nid = n["id"]
    inc = incoming.get(nid, 0)
    outd = out_deg.get(nid, 0)
    annotations.append({
        "node": nid,
        "full_name": n.get("full_name", ""),
        "type": n["type"],
        "description": n.get("description", ""),
        "in_degree": inc,
        "out_degree": outd,
        "total_degree": inc + outd,
        "is_source": bool(n["is_source"]),
        "n_activators": len(activators[nid]),
        "n_inhibitors": len(inhibitors[nid]),
    })

na = {
    "metadata": {
        "flash_p_version": "1.0",
        "phenotype": "Tillering",
        "species": "Oryza sativa",
        "created": "2026-04-20",
        "total_nodes": len(annotations),
    },
    "annotations": annotations,
}

with open(NET / "node_annotations.json", "w", encoding="utf-8") as f:
    json.dump(na, f, indent=2, ensure_ascii=False)


print(f"Nodes: {len(nodes_out)}  Edges: {len(edges_out)}")
print(f"Sources: {source_count} ({source_pct}%)")
print("Wrote network.json, algebraic_equations.json, ode_equations.json, node_annotations.json")
