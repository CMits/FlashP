"""One-shot script to build reconciled_perturbation_dataset.json for Poplar Lignin S/G."""

import json
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "perturbation_dataset.json"
OUT = HERE / "reconciled_perturbation_dataset.json"

with open(RAW) as f:
    raw = json.load(f)

raw_by_id = {p["test_id"]: p for p in raw["perturbations"]}


def _pm(node, mtype, value):
    return {"node": node, "modifier_type": mtype, "value": value}


def _rec(tid, src_id, gene, ptype, direction, magnitude, species,
         network_gene, gene_modifiers, exogenous_supply, perturbations,
         recon_type, recon_note, notes, in_network=True,
         baseline="WT", evidence=None, condition=None):
    src = raw_by_id.get(src_id, {}) if src_id else {}
    ev = evidence if evidence is not None else src.get("evidence", [])
    cond = condition if condition is not None else src.get("condition", "normal")
    return {
        "test_id": tid,
        "gene": gene,
        "perturbation_type": ptype,
        "expected_direction": direction,
        "in_network": in_network,
        "network_gene": network_gene,
        "gene_modifiers": gene_modifiers,
        "exogenous_supply": exogenous_supply,
        "perturbations": perturbations,
        "notes": notes,
        "evidence": ev,
        "phenotype_node": "Lignin_SG_Ratio",
        "comparison_baseline": baseline,
        "condition": cond,
        "reconciliation_type": recon_type,
        "reconciliation_note": recon_note,
        "expected_magnitude": magnitude,
        "species": species,
    }


# Standard modifier conventions for poplar lignin per task instructions:
#   OE -> gm=2.0
#   KD / RNAi / antisense -> gm=0.1
#   KO / CRISPR KO / dominant-repression (LoF) -> gm=0.0
#   Single paralog of collapsed composite -> gm=0.997

tests = []

# --- F5H1 OE cluster (4 tests) ---
for tid in ["T001", "T002", "T003", "T004"]:
    src = raw_by_id[tid]
    tests.append(_rec(
        tid=tid, src_id=tid, gene="F5H1",
        ptype="overexpression", direction="increased", magnitude=src["expected_magnitude"],
        species=src["species"],
        network_gene=["F5H1"],
        gene_modifiers={"F5H1": 2.0},
        exogenous_supply={},
        perturbations=[_pm("F5H1", "gene_modifier", 2.0)],
        recon_type="exact_match",
        recon_note="F5H1 OE (C4H::F5H or 35S::F5H) -> network node F5H1 gm=2.0",
        notes="Canonical positive-control S/G OE experiment in poplar (Meyermans 2000; Huntley 2003; Stewart 2009; Skyba 2013)",
    ))

# --- COMT1 KD / KD ---
for tid in ["T005", "T006"]:
    src = raw_by_id[tid]
    tests.append(_rec(
        tid=tid, src_id=tid, gene="COMT1",
        ptype="knockdown", direction="decreased", magnitude=src["expected_magnitude"],
        species=src["species"],
        network_gene=["COMT1"],
        gene_modifiers={"COMT1": 0.1},
        exogenous_supply={},
        perturbations=[_pm("COMT1", "gene_modifier", 0.1)],
        recon_type="exact_match",
        recon_note="COMT1 RNAi/antisense -> network node COMT1 gm=0.1",
        notes="COMT1 is the syringyl-specific methylation step; silencing -> loss of S units",
    ))

# --- CCoAOMT1 KD ---
tests.append(_rec(
    tid="T007", src_id="T007", gene="CCoAOMT1",
    ptype="knockdown", direction="unchanged", magnitude="slight",
    species=raw_by_id["T007"]["species"],
    network_gene=["CCOAOMT1"],
    gene_modifiers={"CCOAOMT1": 0.1},
    exogenous_supply={},
    perturbations=[_pm("CCOAOMT1", "gene_modifier", 0.1)],
    recon_type="case_insensitive",
    recon_note="CCoAOMT1 -> CCOAOMT1 (case difference only)",
    notes="CCoAOMT1 KD reduces total lignin but leaves S/G ratio largely unchanged",
))

# --- CCR2 KD / KO ---
src = raw_by_id["T008"]
tests.append(_rec(
    tid="T008", src_id="T008", gene="CCR2",
    ptype="knockdown", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["CCR2"],
    gene_modifiers={"CCR2": 0.1},
    exogenous_supply={},
    perturbations=[_pm("CCR2", "gene_modifier", 0.1)],
    recon_type="exact_match",
    recon_note="CCR2 RNAi -> CCR2 gm=0.1",
    notes="CCR RNAi preferentially lowers S units in poplar (Leple 2007)",
))

src = raw_by_id["T009"]
tests.append(_rec(
    tid="T009", src_id="T009", gene="CCR2",
    ptype="knockout", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["CCR2"],
    gene_modifiers={"CCR2": 0.0},
    exogenous_supply={},
    perturbations=[_pm("CCR2", "gene_modifier", 0.0)],
    recon_type="exact_match",
    recon_note="CCR2 null allele -> CCR2 gm=0.0",
    notes="Null CCR2 allele + haploinsufficient allele (De Meester 2020)",
))

# --- CAD1 KD ---
src = raw_by_id["T010"]
tests.append(_rec(
    tid="T010", src_id="T010", gene="CAD1",
    ptype="knockdown", direction="unchanged", magnitude="slight",
    species=src["species"],
    network_gene=["CAD1"],
    gene_modifiers={"CAD1": 0.1},
    exogenous_supply={},
    perturbations=[_pm("CAD1", "gene_modifier", 0.1)],
    recon_type="exact_match",
    recon_note="CAD1 antisense -> CAD1 gm=0.1",
    notes="CAD acts on both coniferaldehyde and sinapaldehyde; KD does not shift S/G ratio",
))

# --- C3H1 KD (3 conflicting tests) ---
for tid, direction, magnitude in [
    ("T011", "increased", "strong"),
    ("T012", "increased", "strong"),
    ("T013", "decreased", "moderate"),
]:
    src = raw_by_id[tid]
    tests.append(_rec(
        tid=tid, src_id=tid, gene="C3H1",
        ptype="knockdown", direction=direction, magnitude=magnitude,
        species=src["species"],
        network_gene=["C3H1"],
        gene_modifiers={"C3H1": 0.1},
        exogenous_supply={},
        perturbations=[_pm("C3H1", "gene_modifier", 0.1)],
        recon_type="exact_match",
        recon_note="C3H1 RNAi -> C3H1 gm=0.1",
        notes="C3H KD redirects flux to H; G reduced preferentially, S maintained (Coleman 2008; Ralph 2012). Opposing result in P. alba x glandulosa (Peng 2021) reflects genetic-background variation.",
    ))

# --- 4CL1 / 4CL5 (Pt4CL aliases) ---
src = raw_by_id["T014"]
tests.append(_rec(
    tid="T014", src_id="T014", gene="4CL1",
    ptype="knockdown", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["PT4CL1"],
    gene_modifiers={"PT4CL1": 0.1},
    exogenous_supply={},
    perturbations=[_pm("PT4CL1", "gene_modifier", 0.1)],
    recon_type="case_insensitive",
    recon_note="4CL1 -> PT4CL1 (Pt species prefix)",
    notes="4CL antisense lowers total lignin and S/G",
))

src = raw_by_id["T015"]
tests.append(_rec(
    tid="T015", src_id="T015", gene="4CL1",
    ptype="knockout_CRISPR", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["PT4CL1"],
    gene_modifiers={"PT4CL1": 0.0},
    exogenous_supply={},
    perturbations=[_pm("PT4CL1", "gene_modifier", 0.0)],
    recon_type="case_insensitive",
    recon_note="4CL1 -> PT4CL1 (Pt species prefix)",
    notes="4CL1 CRISPR KO preferentially reduces S relative to G (Wang 2020)",
))

src = raw_by_id["T016"]
tests.append(_rec(
    tid="T016", src_id="T016", gene="4CL5",
    ptype="knockout_CRISPR", direction="unchanged", magnitude="slight",
    species=src["species"],
    network_gene=["PT4CL5"],
    gene_modifiers={"PT4CL5": 0.0},
    exogenous_supply={},
    perturbations=[_pm("PT4CL5", "gene_modifier", 0.0)],
    recon_type="case_insensitive",
    recon_note="4CL5 -> PT4CL5 (Pt species prefix)",
    notes="4CL5 CRISPR KO does not change S/G (4CL5 is not the lignin-dedicated paralog)",
))

# --- CSE1 KD ---
src = raw_by_id["T017"]
tests.append(_rec(
    tid="T017", src_id="T017", gene="CSE1",
    ptype="knockdown", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["CSE1"],
    gene_modifiers={"CSE1": 0.1},
    exogenous_supply={},
    perturbations=[_pm("CSE1", "gene_modifier", 0.1)],
    recon_type="exact_match",
    recon_note="CSE1 RNAi -> CSE1 gm=0.1",
    notes="CSE1 RNAi modestly reduces S/G (Saleme 2017)",
))

# --- CSE1;CSE2 double KO (CSE2 not in network; CSE1 subsumes both paralogs) ---
src = raw_by_id["T018"]
tests.append(_rec(
    tid="T018", src_id="T018", gene="CSE1;CSE2",
    ptype="double_knockout", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["CSE1"],
    gene_modifiers={"CSE1": 0.0},
    exogenous_supply={},
    perturbations=[_pm("CSE1", "gene_modifier", 0.0)],
    recon_type="composite_collapse",
    recon_note="CSE2 not separately represented; CSE1 node represents the CSE family",
    notes="Both paralogs CRISPR-edited (de Vries 2021); effective full KO of CSE function",
))

# --- SND1 OE ---
src = raw_by_id["T019"]
tests.append(_rec(
    tid="T019", src_id="T019", gene="SND1",
    ptype="overexpression", direction="increased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["SND1"],
    gene_modifiers={"SND1": 2.0},
    exogenous_supply={},
    perturbations=[_pm("SND1", "gene_modifier", 2.0)],
    recon_type="exact_match",
    recon_note="SND1/WND OE -> SND1 gm=2.0",
    notes="SND1 OE activates secondary wall program; modest S/G increase via MYB/F5H1 route",
))

# --- SND1 dominant-repression (PtrWND2B SRDX) ---
src = raw_by_id["T020"]
tests.append(_rec(
    tid="T020", src_id="T020", gene="SND1",
    ptype="loss_of_function", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["SND1"],
    gene_modifiers={"SND1": 0.0},
    exogenous_supply={},
    perturbations=[_pm("SND1", "gene_modifier", 0.0)],
    recon_type="exact_match",
    recon_note="PtrWND2B SRDX dominant-repression acts as family-level LoF -> SND1 gm=0.0",
    notes="Dominant repression creates a chimeric repressor on SND1-family targets; treated as composite KO",
))

# --- MYB3 / MYB21 dominant-repression ---
src = raw_by_id["T021"]
tests.append(_rec(
    tid="T021", src_id="T021", gene="MYB3",
    ptype="loss_of_function", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["MYB3"],
    gene_modifiers={"MYB3": 0.0},
    exogenous_supply={},
    perturbations=[_pm("MYB3", "gene_modifier", 0.0)],
    recon_type="exact_match",
    recon_note="PtrMYB3 SRDX dominant-repression -> MYB3 gm=0.0",
    notes="Master-switch MYB dominant-repression: 60-70% wall-thickness reduction",
))

src = raw_by_id["T022"]
tests.append(_rec(
    tid="T022", src_id="T022", gene="MYB21",
    ptype="loss_of_function", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["MYB21"],
    gene_modifiers={"MYB21": 0.0},
    exogenous_supply={},
    perturbations=[_pm("MYB21", "gene_modifier", 0.0)],
    recon_type="exact_match",
    recon_note="PtrMYB21 SRDX dominant-repression -> MYB21 gm=0.0",
    notes="Master-switch MYB dominant-repression: strong secondary-wall alteration",
))

# --- MYB152 / MYB156 / MYB221 OE ---
for tid, gene, direction, magnitude, node in [
    ("T023", "MYB152", "increased", "moderate", "MYB152"),
    ("T024", "MYB156", "decreased", "strong", "MYB156"),
    ("T025", "MYB221", "decreased", "moderate", "MYB221"),
]:
    src = raw_by_id[tid]
    tests.append(_rec(
        tid=tid, src_id=tid, gene=gene,
        ptype="overexpression", direction=direction, magnitude=magnitude,
        species=src["species"],
        network_gene=[node],
        gene_modifiers={node: 2.0},
        exogenous_supply={},
        perturbations=[_pm(node, "gene_modifier", 2.0)],
        recon_type="exact_match",
        recon_note=f"{gene} OE -> {node} gm=2.0",
        notes=f"{gene} OE (Populus TF expressed in Arabidopsis or Populus)",
    ))

# --- KNAT7 OE and KD ---
src = raw_by_id["T026"]
tests.append(_rec(
    tid="T026", src_id="T026", gene="KNAT7",
    ptype="overexpression", direction="increased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["KNAT7"],
    gene_modifiers={"KNAT7": 2.0},
    exogenous_supply={},
    perturbations=[_pm("KNAT7", "gene_modifier", 2.0)],
    recon_type="exact_match",
    recon_note="KNAT7 OE -> KNAT7 gm=2.0",
    notes="KNAT7 OE: slight S/G increase (Ahlawat 2021)",
))

src = raw_by_id["T027"]
tests.append(_rec(
    tid="T027", src_id="T027", gene="KNAT7",
    ptype="knockdown", direction="increased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["KNAT7"],
    gene_modifiers={"KNAT7": 0.1},
    exogenous_supply={},
    perturbations=[_pm("KNAT7", "gene_modifier", 0.1)],
    recon_type="exact_match",
    recon_note="KNAT7 antisense -> KNAT7 gm=0.1",
    notes="KNAT7 antisense also gives slight S/G increase (KNAT7 is a modulatory brake; both OE and KD shift composition slightly)",
))

# --- LTF1 phospho-dead mutant (NOT IN NETWORK) ---
src = raw_by_id["T028"]
tests.append(_rec(
    tid="T028", src_id="T028", gene="LTF1",
    ptype="phospho_dead_mutant", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=[],
    gene_modifiers={},
    exogenous_supply={},
    perturbations=[],
    recon_type="not_in_network",
    recon_note="LTF1 (MYB lignin repressor; Gui 2019) is not represented in the current network",
    notes="LTF1 is a poplar MYB repressor regulated by phosphorylation; no direct ortholog node in the network",
    in_network=False,
))

# --- NF_YA11 OE / CRISPR KO ---
src = raw_by_id["T029"]
tests.append(_rec(
    tid="T029", src_id="T029", gene="NF_YA11",
    ptype="overexpression", direction="increased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["NF_YA11"],
    gene_modifiers={"NF_YA11": 2.0},
    exogenous_supply={},
    perturbations=[_pm("NF_YA11", "gene_modifier", 2.0)],
    recon_type="exact_match",
    recon_note="NF-YA11 OE -> NF_YA11 gm=2.0",
    notes="NF-YA11 activates F5H; OE raises S/G (Wei 2024)",
))

src = raw_by_id["T030"]
tests.append(_rec(
    tid="T030", src_id="T030", gene="NF_YA11",
    ptype="knockout_CRISPR", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["NF_YA11"],
    gene_modifiers={"NF_YA11": 0.0},
    exogenous_supply={},
    perturbations=[_pm("NF_YA11", "gene_modifier", 0.0)],
    recon_type="exact_match",
    recon_note="NF-YA11 CRISPR KO -> NF_YA11 gm=0.0",
    notes="nf-ya11 poplars show reduced S-lignin and S/G ratio (Wei 2024)",
))

# --- miR397a OE (NOT IN NETWORK; laccases/miR nodes absent) ---
src = raw_by_id["T031"]
tests.append(_rec(
    tid="T031", src_id="T031", gene="miR397a",
    ptype="overexpression", direction="unchanged", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=[],
    gene_modifiers={},
    exogenous_supply={},
    perturbations=[],
    recon_type="not_in_network",
    recon_note="miR397a targets laccase genes; neither miR397a nor laccase nodes are in the network",
    notes="Ptr-miR397a OE lowers total lignin via laccase suppression; S/G unchanged (Lu 2013)",
    in_network=False,
))

# --- SND1_B dominant-repression (PtrWND6B SRDX) -> composite-family LoF on SND1 ---
src = raw_by_id["T032"]
tests.append(_rec(
    tid="T032", src_id="T032", gene="SND1_B",
    ptype="loss_of_function", direction="decreased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["SND1"],
    gene_modifiers={"SND1": 0.0},
    exogenous_supply={},
    perturbations=[_pm("SND1", "gene_modifier", 0.0)],
    recon_type="composite_collapse",
    recon_note="PtrWND6B is an SND1 paralog; SND1 node represents the family. Dominant-repression acts on family targets -> gm=0.0.",
    notes="SND1-B (WND6B) DR gave 68% wall reduction; collapsed to SND1 composite",
))

# --- HCT1 KD ---
src = raw_by_id["T033"]
tests.append(_rec(
    tid="T033", src_id="T033", gene="HCT1",
    ptype="knockdown", direction="unchanged", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["HCT1"],
    gene_modifiers={"HCT1": 0.1},
    exogenous_supply={},
    perturbations=[_pm("HCT1", "gene_modifier", 0.1)],
    recon_type="exact_match",
    recon_note="HCT1 RNAi -> HCT1 gm=0.1",
    notes="HCT RNAi lowers total lignin without shifting S/G (Peng 2014; Zhou 2018)",
))

# --- Tension_Wood environmental treatment ---
src = raw_by_id["T034"]
tests.append(_rec(
    tid="T034", src_id="T034", gene="Tension_Wood",
    ptype="treatment", direction="increased", magnitude=src["expected_magnitude"],
    species=src["species"],
    network_gene=["Tension_Wood"],
    gene_modifiers={},
    exogenous_supply={"Tension_Wood": 1.0},
    perturbations=[_pm("Tension_Wood", "exogenous_supply", 1.0)],
    recon_type="exact_match",
    recon_note="Tension wood induction encoded as Tension_Wood source node with exogenous_supply=1.0",
    notes="Tension-wood lignin is S-enriched relative to normal/opposite wood (Al-Haddad 2013)",
    condition="tension_wood_induction",
))

# --- Controls (one per major species background) ---
wt_control_evidence = [{
    "doi": "10.1104/pp.123.4.1363",
    "title": "Lignification in Transgenic Poplars with Extremely Reduced Caffeic Acid O-Methyltransferase Activity (WT control)",
    "authors": "Jouanin L et al.",
    "year": 2000,
    "journal": "Plant Physiology",
    "evidence_sentence": "Wild-type Populus tremula x alba stem xylem: ~33-34% G, 64-67% S; S/G ratio ~2.0",
    "claim": "WT baseline S/G ratio in P. tremula x alba stem xylem",
}]

tests.append(_rec(
    tid="T035", src_id=None, gene="WT_control",
    ptype="control", direction="unchanged", magnitude="",
    species="Populus tremula x alba",
    network_gene=[],
    gene_modifiers={},
    exogenous_supply={},
    perturbations=[],
    recon_type="control",
    recon_note="WT (no perturbation) - P. tremula x alba baseline",
    notes="Negative control: no modifications, expected=unchanged",
    evidence=wt_control_evidence,
    condition="normal",
))

wt_tricho_evidence = [{
    "doi": "10.1073/pnas.1308936110",
    "title": "Ptr-miR397a is a negative regulator of laccase genes affecting lignin content in Populus trichocarpa (WT control)",
    "authors": "Lu S et al.",
    "year": 2013,
    "journal": "PNAS",
    "evidence_sentence": "S/G ratio of 2.1 in WT Populus trichocarpa stem xylem",
    "claim": "WT baseline S/G in P. trichocarpa ~2.0-3.0",
}]

tests.append(_rec(
    tid="T036", src_id=None, gene="WT_control",
    ptype="control", direction="unchanged", magnitude="",
    species="Populus trichocarpa",
    network_gene=[],
    gene_modifiers={},
    exogenous_supply={},
    perturbations=[],
    recon_type="control",
    recon_note="WT (no perturbation) - P. trichocarpa reference species baseline",
    notes="Negative control for the reference species",
    evidence=wt_tricho_evidence,
    condition="normal",
))

wt_arab_evidence = [{
    "doi": "10.1038/srep05054",
    "title": "Regulation of secondary cell wall biosynthesis by poplar R2R3 MYB transcription factor PtrMYB152 in Arabidopsis (WT control)",
    "authors": "Wang S et al.",
    "year": 2014,
    "journal": "Scientific Reports",
    "evidence_sentence": "Arabidopsis wild-type controls showed S/G 0.31 vs 0.37-0.42 in 35S:PtrMYB152 lines",
    "claim": "Arabidopsis WT baseline for heterologous expression assays",
}]

tests.append(_rec(
    tid="T037", src_id=None, gene="WT_control",
    ptype="control", direction="unchanged", magnitude="",
    species="Arabidopsis thaliana",
    network_gene=[],
    gene_modifiers={},
    exogenous_supply={},
    perturbations=[],
    recon_type="control",
    recon_note="WT (no perturbation) - Arabidopsis heterologous-expression host baseline",
    notes="Negative control for heterologous Arabidopsis assays (MYB152/MYB221 OE)",
    evidence=wt_arab_evidence,
    condition="normal",
))


# --- Metadata ---
in_network_count = sum(1 for t in tests if t["in_network"])
not_in_network_count = sum(1 for t in tests if not t["in_network"])

metadata = {
    "flash_p_version": "2.0",
    "phenotype": "Lignin_SG_Ratio",
    "species": "Populus trichocarpa",
    "created": "2026-04-20",
    "total_tests": len(tests),
    "in_network": in_network_count,
    "not_in_network": not_in_network_count,
    "phenotype_node": "Lignin_SG_Ratio",
    "convention": "Higher S/G (more syringyl, less guaiacyl) = increased; lower = decreased. WT Populus trichocarpa stem xylem S/G ~2-3.",
}

output = {
    "metadata": metadata,
    "direction_threshold": 0.05,
    "perturbations": tests,
}

with open(OUT, "w") as f:
    json.dump(output, f, indent=2)

# Reporting
print(f"Wrote {OUT}")
print(f"Total tests: {len(tests)}")
print(f"In-network: {in_network_count}")
print(f"Not-in-network: {not_in_network_count}")
print()

from collections import Counter
by_recon = Counter(t["reconciliation_type"] for t in tests)
print("By reconciliation_type:")
for k, v in sorted(by_recon.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()

by_ptype = Counter(t["perturbation_type"] for t in tests)
print("By perturbation_type:")
for k, v in sorted(by_ptype.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()

by_species = Counter(t["species"] for t in tests)
print("By species background:")
for k, v in sorted(by_species.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

controls = [t for t in tests if t["reconciliation_type"] == "control"]
print(f"\nControls: {len(controls)}")
for t in controls:
    print(f"  {t['test_id']} - {t['species']}")
