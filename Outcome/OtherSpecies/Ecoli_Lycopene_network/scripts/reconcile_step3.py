"""
FLASH-P Step 3 reconciler for E. coli Lycopene Titer network.

Maps raw perturbation_dataset.json entries to network nodes following the
priority table in PERTURBATION_AGENT.md + the task-specific encoding rules
listed in the Step 3 prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

NETWORK_DIR = Path(__file__).resolve().parent.parent
RAW = NETWORK_DIR / "data" / "perturbation_dataset.json"
NET = NETWORK_DIR / "network" / "network.json"
OUT = NETWORK_DIR / "data" / "reconciled_perturbation_dataset.json"

PHENO = "Lycopene_Titer"

# ---------------------------------------------------------------------------
# Per-test reconciliation specification
# ---------------------------------------------------------------------------
# Each entry: test_id -> {
#   "in_network": bool,
#   "network_gene": [str, ...],
#   "gene_modifiers": {node: val, ...},
#   "exogenous_supply": {node: val, ...},
#   "baseline": "WT" | "mutant",
#   "rtype": reconciliation_type enum string,
#   "note": short explanation,
# }
# ---------------------------------------------------------------------------

SPEC = {
    # --- MEP pathway & terminal crt cassette ---
    "T001": {"gm": {"DXS": 2.0}, "rtype": "case_insensitive",
             "note": "Dxs -> DXS (case)"},
    "T002": {"gm": {"IDI": 2.0}, "rtype": "case_insensitive",
             "note": "Idi -> IDI"},
    "T003": {"gm": {"DXS": 2.0, "IDI": 2.0}, "rtype": "case_insensitive",
             "note": "dxs+idi combined OE"},
    "T004": {"gm": {"DXS": 2.0, "DXR": 2.0}, "rtype": "case_insensitive",
             "note": "dxs+dxr combined OE"},
    "T005": {"gm": {"DXS": 2.0, "IDI": 2.0}, "rtype": "composite_collapse",
             "note": "ispD/ispF not explicit nodes; kept dxs+idi OE"},
    "T006": {"gm": {"ISPA": 2.0}, "rtype": "case_insensitive",
             "note": "IspA -> ISPA OE"},
    "T007": {"gm": {"ISPB": 0.1}, "rtype": "case_insensitive",
             "note": "IspB RBS-down / antisense KD (essential gene cannot be fully KO'd)"},
    "T008": {"gm": {"CRTE": 2.0}, "rtype": "case_insensitive",
             "note": "CrtE -> CRTE OE"},
    "T009": {"gm": {"CRTB": 2.0}, "rtype": "case_insensitive",
             "note": "CrtB -> CRTB OE"},
    "T010": {"gm": {"CRTI": 2.0}, "rtype": "case_insensitive",
             "note": "CrtI -> CRTI OE"},
    "T011": {"gm": {"CRTE": 2.0, "CRTB": 2.0, "CRTI": 2.0},
             "rtype": "case_insensitive",
             "note": "crtEBI cassette co-OE"},
    "T012": {"gm": {"CRTE": 0.0}, "rtype": "case_insensitive",
             "note": "CrtE KO"},
    "T013": {"gm": {"CRTB": 0.0}, "rtype": "case_insensitive",
             "note": "CrtB KO"},
    "T014": {"gm": {"CRTI": 0.0}, "rtype": "case_insensitive",
             "note": "CrtI KO"},
    # --- MVA cassette (PMK is NOT a node; encode remaining 5 enzymes) ---
    "T015": {"gm": {"ATOB": 2.0, "HMGS": 2.0, "HMGR": 2.0, "MVK": 2.0, "MVD": 2.0},
             "rtype": "composite_collapse",
             "note": "Full MVA upper+lower cassette OE; PMK not in network so omitted"},
    "T016": {"gm": {"ATOB": 2.0}, "rtype": "case_insensitive",
             "note": "AtoB -> ATOB OE"},
    "T017": {"gm": {"HMGS": 2.0}, "rtype": "case_insensitive",
             "note": "HMGS OE"},
    "T018": {"gm": {"HMGR": 2.0}, "rtype": "case_insensitive",
             "note": "HMGR OE (maps to tHMGR engineered variant too)"},
    "T019": {"gm": {"MVK": 2.0}, "rtype": "case_insensitive",
             "note": "MVK OE"},
    "T020": {"in_network": False, "rtype": "not_in_network",
             "note": "PMK (phosphomevalonate kinase) not a node in this network"},
    "T021": {"gm": {"MVD": 2.0}, "rtype": "case_insensitive",
             "note": "MVD OE"},
    "T022": {"gm": {"DXS": 0.0}, "rtype": "case_insensitive",
             "note": "Dxs KO"},
    "T023": {"gm": {"ISPA": 0.0}, "rtype": "case_insensitive",
             "note": "IspA KO (encoded as full KO of node)"},
    # --- Central carbon metabolism redirection ---
    "T024": {"gm": {"PGI": 0.0}, "rtype": "case_insensitive",
             "note": "Pgi KO (redirects flux to PPP)"},
    "T025": {"gm": {"ZWF": 0.0}, "rtype": "case_insensitive",
             "note": "Zwf KO (removes PPP entry)"},
    "T026": {"gm": {"PGI": 0.0, "ZWF": 0.0}, "rtype": "case_insensitive",
             "note": "Pgi+Zwf double KO (Alper 2005 classic)"},
    "T027": {"gm": {"PPS": 2.0}, "rtype": "family_member",
             "note": "PpsA = PPS (phosphoenolpyruvate synthase)"},
    "T028": {"gm": {"PYKA": 0.0, "PYKF": 0.0}, "rtype": "case_insensitive",
             "note": "PykA+PykF double KO"},
    "T029": {"gm": {"ACEE": 0.0, "GDHA": 0.0}, "rtype": "case_insensitive",
             "note": "AceE+GdhA double KO"},
    "T030": {"gm": {"GDHA": 0.0, "ACEE": 0.0}, "rtype": "composite_collapse",
             "note": "GdhA+AceE+FdhF triple KO; FdhF not in network, encoded 2/3"},
    "T031": {"gm": {"GDHA": 0.0, "ACEE": 0.0}, "rtype": "composite_collapse",
             "note": "GdhA+AceE+YjiD triple KO; YjiD not in network, encoded 2/3"},
    "T032": {"gm": {"GDHA": 0.0, "ACEE": 0.0}, "rtype": "composite_collapse",
             "note": "GdhA/AceE KO + FdhF/YjiD/YcgW not in network; "
                     "encoded the two modelled deletions"},
    "T033": {"gm": {"GDHA": 0.0, "ACEE": 0.0, "PGI": 0.0, "ZWF": 0.0},
             "rtype": "composite_collapse",
             "note": "Alper 2005 8.5x combinatorial strain: encoded the 4 dominant "
                     "in-network deletions (gdhA/aceE/pgi/zwf) that characterise the winner"},
    # --- Regulators & stress response ---
    "T034": {"in_network": False, "rtype": "not_in_network",
             "note": "CRP (cAMP receptor protein) not in network"},
    "T035": {"gm": {"RPOS": 0.0}, "rtype": "case_insensitive",
             "note": "RpoS KO"},
    "T036": {"gm": {"DXS": 2.0}, "rtype": "composite_collapse",
             "note": "AppY+Dxs co-OE: AppY not in network, encoded DXS OE alone"},
    "T037": {"gm": {"DXS": 2.0, "CRL": 2.0, "RPOS": 2.0},
             "rtype": "composite_collapse",
             "note": "AppY+Crl+RpoS+Dxs: AppY not in network, others encoded"},
    "T038": {"gm": {"HNR": 0.0}, "rtype": "composite_collapse",
             "note": "Hnr+YliE double KO: YliE not in network, encoded HNR only"},
    "T039": {"gm": {"PPC": 2.0}, "rtype": "composite_collapse",
             "note": "Ppc+Pck combined OE: Pck not in network, encoded PPC OE"},
    # --- Membrane / envelope engineering via composite source nodes ---
    "T040": {"gm": {"MEMBRANE_STORAGE": 2.0}, "rtype": "mechanism_mapping",
             "note": "PlsB/PlsC/Almgs phospholipid-biosynthesis OE boosts membrane storage capacity for carotenoids"},
    "T041": {"gm": {"ENVELOPE_STRESS": 0.0}, "rtype": "mechanism_mapping",
             "note": "WaaC KO (deep-rough LPS) reduces envelope barrier -> ENVELOPE_STRESS composite goes to 0"},
    "T042": {"gm": {"ENVELOPE_STRESS": 0.0}, "rtype": "mechanism_mapping",
             "note": "WaaF KO (LPS outer-core defect) reduces envelope barrier"},
    "T043": {"gm": {"ENVELOPE_STRESS": 0.0}, "rtype": "mechanism_mapping",
             "note": "Lpp/NlpI/MlaE/TolA quadruple KO destabilises envelope -> reduced stress composite"},
    "T044": {"in_network": False, "rtype": "not_in_network",
             "note": "alphaKGDH + SDH + TalB engineering (NADPH/ATP rewiring) - none are explicit nodes"},
    "T045": {"gm": {"GDHA": 0.0, "MEMBRANE_STORAGE": 2.0},
             "rtype": "composite_collapse",
             "note": "GdhA/EutD KO + TpiA/OmpE/OmpN OE: GDHA modelled as KO, OmpE/OmpN -> MEMBRANE_STORAGE OE; EutD/TpiA not in network"},
    # --- Chassis strain comparisons (no Chassis_Strain source node) ---
    "T046": {"in_network": False, "rtype": "not_in_network",
             "note": "MG1655 chassis reference; no Chassis_Strain node"},
    "T047": {"in_network": False, "rtype": "not_in_network",
             "note": "BL21 chassis; no Chassis_Strain node"},
    "T048": {"in_network": False, "rtype": "not_in_network",
             "note": "W3110 chassis; no Chassis_Strain node"},
    "T049": {"in_network": False, "rtype": "not_in_network",
             "note": "DH5alpha chassis; no Chassis_Strain node"},
    "T050": {"in_network": False, "rtype": "not_in_network",
             "note": "SURE chassis; no Chassis_Strain node"},
    # --- Engineering inputs (exogenous supply on source nodes) ---
    "T051": {"ex": {"IPTG": 1.0}, "rtype": "treatment_analog",
             "note": "IPTG high (1 mM) -> IPTG exogenous_supply=1.0"},
    "T052": {"ex": {"IPTG": 0.0}, "rtype": "treatment_analog",
             "note": "IPTG absent (no induction) -> IPTG exogenous_supply=0.0"},
    "T053": {"ex": {"Arabinose": 1.0}, "rtype": "treatment_analog",
             "note": "Arabinose 1% -> Arabinose exogenous_supply=1.0"},
    "T054": {"ex": {"Arabinose": 0.0}, "rtype": "treatment_analog",
             "note": "Arabinose absent -> Arabinose exogenous_supply=0.0"},
    "T055": {"ex": {"Glucose": 1.0}, "rtype": "treatment_analog",
             "note": "Glucose as sole C source (baseline) -> Glucose exogenous_supply=1.0"},
    "T056": {"ex": {"Glycerol": 1.0, "Glucose": 0.0}, "rtype": "treatment_analog",
             "note": "Glycerol carbon source -> Glycerol=1.0, Glucose=0.0"},
    "T057": {"ex": {"Xylose": 1.0, "Glucose": 0.0}, "rtype": "treatment_analog",
             "note": "Xylose carbon source -> Xylose=1.0, Glucose=0.0"},
    "T058": {"ex": {"Temperature": 1.0}, "rtype": "treatment_analog",
             "note": "37 C growth -> Temperature exogenous_supply=1.0"},
    "T059": {"ex": {"Temperature": 0.0}, "rtype": "treatment_analog",
             "note": "28 C growth -> Temperature exogenous_supply=0.0"},
    "T060": {"ex": {"Temperature": 0.0}, "rtype": "treatment_analog",
             "note": "37->25 C shift encoded at low-temperature state"},
    "T061": {"ex": {"Oxygen_Level": 1.0}, "rtype": "treatment_analog",
             "note": "High aeration -> Oxygen_Level exogenous_supply=1.0"},
    "T062": {"ex": {"Oxygen_Level": 0.3}, "rtype": "treatment_analog",
             "note": "Microaerobic -> Oxygen_Level exogenous_supply=0.3"},
    "T063": {"gm": {"ROS": 2.0}, "rtype": "mechanism_mapping",
             "note": "Menadione = superoxide generator -> ROS composite gm=2.0"},
    "T064": {"gm": {"RPOS": 0.0, "KATE": 2.0}, "rtype": "composite_collapse",
             "note": "KatE OE in rpoS-KO background"},
    "T065": {"gm": {"SOXR": 0.0}, "rtype": "case_insensitive",
             "note": "SoxR KO"},
    "T066": {"gm": {"SOXS": 0.0}, "rtype": "case_insensitive",
             "note": "SoxS KO"},
    "T067": {"in_network": False, "rtype": "not_in_network",
             "note": "OxyR not in network"},
    "T068": {"gm": {"FNR": 0.0}, "rtype": "case_insensitive",
             "note": "FNR KO"},
    "T069": {"gm": {"ARCA": 0.0}, "rtype": "case_insensitive",
             "note": "ArcA KO"},
    "T070": {"gm": {"CRA": 0.0}, "rtype": "case_insensitive",
             "note": "Cra KO"},
    "T071": {"gm": {"CRL": 0.0}, "rtype": "case_insensitive",
             "note": "Crl KO"},
    "T072": {"gm": {"HNR": 0.0}, "rtype": "case_insensitive",
             "note": "Hnr KO"},
    "T073": {"in_network": False, "rtype": "not_in_network",
             "note": "YliE not in network"},
    "T074": {"in_network": False, "rtype": "not_in_network",
             "note": "YtjC not in network"},
    "T075": {"in_network": False, "rtype": "not_in_network",
             "note": "YjiD not in network"},
    "T076": {"gm": {"ATOB": 2.0, "HMGS": 2.0, "HMGR": 2.0},
             "rtype": "composite_collapse",
             "note": "MVA upper (mvaE=AtoB+HMGR; mvaS=HMGS) cassette OE"},
    "T077": {"gm": {"MVK": 2.0, "MVD": 2.0},
             "rtype": "composite_collapse",
             "note": "MVA lower (MVK, PMK, MVD) + exogenous mevalonate feed; PMK not in network, mevalonate not a source so feed not encoded"},
    "T078": {"gm": {"ATOB": 2.0, "HMGS": 2.0, "HMGR": 2.0, "MVK": 2.0, "MVD": 2.0, "IDI": 2.0},
             "rtype": "composite_collapse",
             "note": "MVA cassette + Type-II IDI OE (PMK not in network)"},
    "T079": {"ex": {"Glucose": 1.0}, "rtype": "treatment_analog",
             "note": "Fed-batch glucose -> sustained Glucose=1.0 (process encoded as standard C supply)"},
    "T080": {"in_network": False, "rtype": "not_in_network",
             "note": "Fructose auxiliary C source; no Fructose node"},
    "T081": {"in_network": False, "rtype": "not_in_network",
             "note": "mRNA SSS optimisation -- process, not a gene modifier"},
    "T082": {"in_network": False, "rtype": "not_in_network",
             "note": "Chromosomal integration -- delivery method, not a gene modifier"},
    "T083": {"in_network": False, "rtype": "not_in_network",
             "note": "MAGE (Wang 2009) RBS optimisation across 20 loci -- process"},
    "T084": {"in_network": False, "rtype": "not_in_network",
             "note": "Golden Gate / SSA combinatorial assembly -- process, not a gene modifier"},
    "T085": {"gm": {"CRTE": 2.0}, "rtype": "composite_collapse",
             "note": "CrtE ortholog P.agglomerans vs P.ananatis -- encoded as CrtE OE (ortholog identity not captured)"},
    "T086": {"ex": {"Plasmid_Copy_Number": 1.0}, "rtype": "treatment_analog",
             "note": "High-copy plasmid -> Plasmid_Copy_Number exogenous_supply=1.0"},
    "T087": {"gm": {"IDI": 2.0, "DXS": 2.0, "CRTE": 2.0, "CRTB": 2.0, "CRTI": 2.0},
             "rtype": "composite_collapse",
             "note": "RBS-tuned idi+dxs+crtEBI OE"},
    "T088": {"gm": {"CRTE": 2.0}, "ex": {"IPTG": 0.0},
             "rtype": "composite_collapse",
             "note": "CrtE (P.agglomerans) OE under constitutive (non-IPTG) promoter"},
    "T089": {"gm": {}, "ex": {}, "rtype": "control",
             "note": "MG1655 + crtEBI wild-type baseline, no auxiliary interventions",
             "baseline": "WT"},
    "T090": {"in_network": False, "rtype": "not_in_network",
             "note": "TalB (transaldolase B) not in network"},
    "T091": {"gm": {"DXS": 2.0, "DXR": 2.0, "ISPA": 2.0, "IDI": 2.0},
             "rtype": "composite_collapse",
             "note": "dxs+dxr+ispA+idi MEP cassette OE"},
    "T092": {"gm": {"GDHA": 0.0}, "rtype": "case_insensitive",
             "note": "GdhA KO"},
    "T093": {"gm": {"EDD": 2.0}, "rtype": "case_insensitive",
             "note": "Edd OE"},
    "T094": {"gm": {"EDA": 2.0}, "rtype": "case_insensitive",
             "note": "Eda OE"},
    "T095": {"in_network": False, "rtype": "not_in_network",
             "note": "PfkA not in network (mechanism similar to Pgi KO but not encoded to avoid false analog)"},
    "T096": {"in_network": False, "rtype": "not_in_network",
             "note": "PfkA+PfkB double KO -- neither in network"},
    "T097": {"in_network": False, "rtype": "not_in_network",
             "note": "Gnd (6-phosphogluconate dehydrogenase) not in network"},
    "T098": {"gm": {"PGI": 0.0, "ZWF": 2.0, "EDA": 2.0, "EDD": 0.0},
             "rtype": "composite_collapse",
             "note": "Engineered ED-pathway strain: Δpgi + ZWF OE + EDA OE + EDD deletion (final strain 3.6x). PfkA/PfkB contributions not in network."},
    "T099": {"gm": {"MVK": 2.0}, "rtype": "mechanism_mapping",
             "note": "MVK V13D/S148I/V301E triple point mutant (higher specific activity) -> encoded as MVK OE"},
    "T100": {"gm": {"KATE": 2.0}, "rtype": "case_insensitive",
             "note": "KatE OE"},
    "T101": {"gm": {"KATE": 2.0, "ROS": 2.0}, "rtype": "composite_collapse",
             "note": "KatE OE under menadione oxidative stress; baseline = menadione treatment alone",
             "baseline": "mutant"},
    "T102": {"gm": {"MEMBRANE_STORAGE": 2.0}, "rtype": "mechanism_mapping",
             "note": "Almgs+PlsB+PlsC membrane engineering -> MEMBRANE_STORAGE OE"},
    "T103": {"gm": {"MEMBRANE_STORAGE": 2.0}, "rtype": "mechanism_mapping",
             "note": "PlsB+PlsC+DgkA membrane engineering -> MEMBRANE_STORAGE OE"},
    "T104": {"gm": {"MVK": 2.0, "MVD": 2.0, "IDI": 2.0},
             "rtype": "composite_collapse",
             "note": "LM22 downstream MVA RBS-tuned: MVK+PMK+MVD+IDI; PMK not in network"},
    "T105": {"gm": {"MVK": 2.0, "MVD": 2.0, "HMGS": 2.0, "HMGR": 2.0},
             "rtype": "composite_collapse",
             "note": "MVA midstream T7-strong OE; known framework limitation (plasmid burden not modelled, so prediction will not capture the decreased outcome)"},
    "T106": {"gm": {"ATOB": 2.0, "HMGS": 2.0, "HMGR": 2.0, "MVK": 2.0, "MVD": 2.0},
             "rtype": "composite_collapse",
             "note": "E.saccharolyticus+S.cerevisiae MVA cassette (pSCS3); ortholog identity not captured; PMK not in network"},
    "T107": {"gm": {"ATOB": 2.0, "HMGS": 2.0, "HMGR": 2.0, "MVK": 2.0, "MVD": 2.0},
             "rtype": "composite_collapse",
             "note": "E.faecalis+S.pneumoniae MVA cassette (pSNA); same encoding as T106"},
    "T108": {"gm": {"PPC": 0.0}, "rtype": "case_insensitive",
             "note": "Ppc KO"},
}


def build_entry(raw, spec):
    """Convert a raw perturbation + spec into a ReconciledPerturbation dict."""
    gm = spec.get("gm", {})
    ex = spec.get("ex", {})
    in_network = spec.get("in_network", True) and (bool(gm) or bool(ex) or spec["rtype"] == "control")

    network_genes = sorted(set(list(gm.keys()) + list(ex.keys())))

    perts = []
    for node, val in gm.items():
        perts.append({"node": node, "modifier_type": "gene_modifier", "value": float(val)})
    for node, val in ex.items():
        perts.append({"node": node, "modifier_type": "exogenous_supply", "value": float(val)})

    evidence = raw.get("evidence", [])
    # authors field must be a string per EvidenceEntry
    ev_out = []
    for e in evidence:
        authors = e.get("authors", "")
        if isinstance(authors, list):
            authors = ", ".join(authors)
        ev_out.append({
            "doi": e.get("doi", ""),
            "title": e.get("title", ""),
            "authors": authors,
            "year": e.get("year"),
            "journal": e.get("journal", ""),
            "evidence_sentence": e.get("evidence_sentence", ""),
            "claim": e.get("claim", ""),
            "verification": e.get("verification"),
            "full_text_read": e.get("full_text_read"),
        })

    return {
        "test_id": raw["test_id"],
        "gene": raw["gene"],
        "perturbation_type": raw["perturbation_type"],
        "expected_direction": raw["expected_direction"],
        "in_network": bool(in_network),
        "network_gene": network_genes,
        "gene_modifiers": {k: float(v) for k, v in gm.items()},
        "exogenous_supply": {k: float(v) for k, v in ex.items()},
        "perturbations": perts,
        "notes": spec["note"],
        "evidence": ev_out,
        "phenotype_node": PHENO,
        "comparison_baseline": spec.get("baseline", "WT"),
        "condition": raw.get("condition", "normal"),
        "reconciliation_type": spec["rtype"],
        "reconciliation_note": spec["note"],
        "expected_magnitude": raw.get("expected_magnitude", ""),
        "species": raw.get("species", "Escherichia coli"),
    }


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    net = json.loads(NET.read_text(encoding="utf-8"))
    node_ids = {n["id"] for n in net["nodes"]}

    out_perts = []
    missing_spec = []
    for p in raw["perturbations"]:
        tid = p["test_id"]
        if tid not in SPEC:
            missing_spec.append(tid)
            continue
        entry = build_entry(p, SPEC[tid])
        # Verify every referenced node is in the network
        for n in entry["network_gene"]:
            assert n in node_ids, f"{tid}: node {n!r} not in network"
        out_perts.append(entry)

    if missing_spec:
        raise RuntimeError(f"Missing spec entries for: {missing_spec}")

    in_network_count = sum(1 for e in out_perts if e["in_network"])

    out = {
        "metadata": {
            "flash_p_version": "2.0",
            "phenotype": "Lycopene_Titer",
            "species": "Escherichia coli",
            "created": "2026-04-21",
            "total_tests": len(out_perts),
            "in_network": in_network_count,
            "not_in_network": len(out_perts) - in_network_count,
            "phenotype_node": PHENO,
            "convention": raw["metadata"].get("convention", ""),
        },
        "direction_threshold": raw.get("direction_threshold", 0.05),
        "perturbations": out_perts,
    }

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"total={len(out_perts)} in_network={in_network_count} "
          f"not_in_network={len(out_perts) - in_network_count}")


if __name__ == "__main__":
    main()
