"""
PERTURBATION Step 3 - reconciliation.

Maps every entry in data/perturbation_dataset.json to network nodes in
network/network.json and emits reconciled_perturbation_dataset.json per
ReconciledPerturbationFile schema.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "perturbation_dataset.json"
NET = ROOT / "network" / "network.json"
OUT = ROOT / "data" / "reconciled_perturbation_dataset.json"

raw = json.load(open(RAW, encoding="utf-8"))
net = json.load(open(NET, encoding="utf-8"))
network_nodes = {n["id"] for n in net["nodes"]}

# ---------------------------------------------------------------------------
# Mapping table: gene_name -> (network_node, reconciliation_type, note)
# ---------------------------------------------------------------------------
# Reconciliation types: exact_match, case_insensitive, family_member,
#   composite_collapse, composite_member, treatment_analog, mechanism_mapping,
#   not_in_network, control
GENE_MAP = {
    # --- Exact matches ---
    "SPL9": ("SPL9", "exact_match", ""),
    "miR156": ("miR156", "exact_match", ""),
    "miR172": ("miR172", "exact_match", ""),
    "SPY": ("SPY", "exact_match", ""),
    "SLY1": ("SLY1", "exact_match", ""),
    "BRI1": ("BRI1", "exact_match", ""),
    "BIN2": ("BIN2", "exact_match", ""),
    "CO": ("CO", "exact_match", ""),
    "FT": ("FT", "exact_match", ""),
    "GI": ("GI", "exact_match", ""),
    "FKF1": ("FKF1", "exact_match", ""),
    "ZTL": ("ZTL", "exact_match", ""),
    "CDF1": ("CDF1", "exact_match", ""),
    "SVP": ("SVP", "exact_match", ""),
    "FLM": ("FLM", "exact_match", ""),
    "FRI": ("FRI", "exact_match", ""),
    "FLC": ("FLC", "exact_match", ""),
    "VIN3": ("VIN3", "exact_match", ""),
    "Temperature": ("Temperature", "exact_match", ""),
    "Auxin": ("Auxin", "exact_match", ""),
    "HY5": ("HY5", "exact_match", ""),
    "COP1": ("COP1", "exact_match", ""),
    "TPS1": ("TPS1", "exact_match", ""),
    "MAX2": ("MAX2", "exact_match", ""),
    "CKX3": ("CKX3", "exact_match", ""),
    "ARR1": ("ARR1", "exact_match", ""),
    "Cytokinin": ("Cytokinin", "exact_match", ""),
    "CTR1": ("CTR1", "exact_match", ""),
    "EIN2": ("EIN2", "exact_match", ""),
    "EIN3": ("EIN3", "exact_match", ""),
    "ETR1": ("ETR1", "exact_match", ""),
    "Ethylene": ("Ethylene", "exact_match", ""),
    "D14": ("D14", "exact_match", ""),
    "Strigolactone": ("Strigolactone", "exact_match", ""),
    "ABA": ("ABA", "exact_match", ""),
    "ABI5": ("ABI5", "exact_match", ""),
    "ABI1": ("ABI1", "exact_match", ""),
    "PYL": ("PYL", "exact_match", ""),
    "HFR1": ("HFR1", "exact_match", ""),
    "PAR1": ("PAR1", "exact_match", ""),
    "LDL1": ("LDL1", "exact_match", ""),
    "Gibberellin": ("Gibberellin", "exact_match", ""),
    "Brassinosteroid": ("Brassinosteroid", "exact_match", ""),

    # --- Case-insensitive (renamed in Builder) ---
    "phyB": ("PHYB", "case_insensitive",
             "phyB lowercase gene name renamed to PHYB in network (GENE regex compliance)."),
    "phyA": ("PHYA", "case_insensitive",
             "phyA lowercase gene name renamed to PHYA in network."),

    # --- Composite members (paralog collapse) ---
    "PIF4": ("PIF4_5_7", "composite_member",
             "PIF4 is one of PIF4/PIF5/PIF7 in composite PIF4_5_7."),
    "PIF3": ("PIF4_5_7", "family_member",
             "PIF3 is not in the PIF4_5_7 composite but shares TF activity; mapped as family."),
    "TOE1": ("AP2_TOE", "composite_member",
             "TOE1 is one of AP2/TOE1/TOE2/SMZ in composite AP2_TOE."),
    "SMZ": ("AP2_TOE", "composite_member", "SMZ in AP2_TOE composite."),
    "FCA": ("AUT_SYN", "composite_member",
             "FCA in AUT_SYN composite (FCA/FPA/FLD/FVE/LD/FY/LDL1 autonomous pathway)."),
    "FPA": ("AUT_SYN", "composite_member", "FPA in AUT_SYN composite."),
    "FLD": ("AUT_SYN", "composite_member", "FLD in AUT_SYN composite."),
    "FVE": ("AUT_SYN", "composite_member", "FVE in AUT_SYN composite."),
    "FY": ("AUT_SYN", "composite_member", "FY in AUT_SYN composite."),
    "VRN2": ("PRC2", "composite_member",
             "VRN2 in PRC2 composite (VRN2/CLF/SWN/FIE)."),
    "GA20ox1": ("GA20OX", "composite_member",
                 "GA20ox1 in GA20OX composite (GA20ox1/2/3)."),
    "GA3ox1": ("GA3OX", "composite_member",
                "GA3ox1 in GA3OX composite (GA3ox1/2)."),
    "GA2ox": ("GA2OX", "composite_member",
              "GA2ox in GA2OX composite (GA2ox1/2)."),
    "GID1A": ("GID1", "composite_member",
              "GID1A in GID1 composite (A/B/C)."),
    "GAI": ("DELLA", "composite_member",
             "GAI in DELLA composite (RGA/GAI/RGL1/RGL2)."),
    "RGA": ("DELLA", "composite_member", "RGA in DELLA composite."),
    "DELLA": ("DELLA", "composite_collapse",
              "DELLA whole-composite collapse."),
    "BZR1": ("BZR_BES", "composite_member",
             "BZR1 in BZR_BES composite (BZR1/BES1)."),
    "BES1": ("BZR_BES", "composite_member", "BES1 in BZR_BES composite."),
    "DWF4": ("BR_SYN", "composite_member",
             "DWF4 in BR_SYN composite (DWF4/DET2/CPD/CYP85A1)."),
    "DET2": ("BR_SYN", "composite_member", "DET2 in BR_SYN composite."),
    "CPD":  ("BR_SYN", "composite_member", "CPD in BR_SYN composite."),
    "YUC8": ("YUC_TAA", "composite_member",
             "YUC8 in YUC_TAA composite (YUC8/TAA1)."),
    "ARF6": ("ARF6_7_8", "composite_member",
             "ARF6 in ARF6_7_8 composite."),
    "IPT3": ("IPT", "composite_member",
             "IPT3 in IPT composite (IPT3/5/7)."),
    "MAX1": ("SL_SYN", "composite_member",
             "MAX1 in SL_SYN composite (D27/MAX1/MAX3/MAX4)."),
    "MAX3": ("SL_SYN", "composite_member", "MAX3 in SL_SYN composite."),
    "MAX4": ("SL_SYN", "composite_member", "MAX4 in SL_SYN composite."),
    "ELF3": ("EC", "composite_member",
             "ELF3 in Evening Complex composite (ELF3/ELF4/LUX)."),
    "ELF4": ("EC", "composite_member", "ELF4 in EC composite."),
    "LUX":  ("EC", "composite_member", "LUX in EC composite."),
    "SOC1": ("FLOWER_INT", "composite_member",
             "SOC1 in FLOWER_INT composite (SOC1/LFY/AP1)."),
    "LFY":  ("FLOWER_INT", "composite_member", "LFY in FLOWER_INT composite."),
    "AP1":  ("FLOWER_INT", "composite_member", "AP1 in FLOWER_INT composite."),

    # --- Family members (non-composite) ---
    "AHK2": ("AHK3", "family_member",
             "AHK2 not in network; mapped to AHK3 (representative CK receptor in AHK2/3/4 family)."),
    "SPL2": ("SPL9", "family_member",
             "SPL2 is a miR156 target; network SPL9 represents SPL family effects."),

    # --- Treatment analogs ---
    "Vernalization": ("Cold_Vernalization", "treatment_analog",
                       "Vernalization treatment maps to Cold_Vernalization env node."),

    # --- Mechanism mappings ---
    "CPS": ("GA20OX", "mechanism_mapping",
            "CPS is the most upstream GA biosynthesis enzyme (ent-CDP synthase; ga1 mutant); effect proxied via GA20OX KO."),
    "KS":  ("GA20OX", "mechanism_mapping",
            "KS (ent-kaurene synthase; ga2 mutant); proxied via GA20OX KO."),
    "KO":  ("GA20OX", "mechanism_mapping",
            "KO (ent-kaurene oxidase; ga3 mutant); proxied via GA20OX KO."),

    # --- Not in network ---
    "TEM1": ("not_in_network", "not_in_network",
             "TEMPRANILLO 1 AP2/ERF FT repressor; not added to the network (LOW-priority S205 deferred)."),
    "ARP6": ("not_in_network", "not_in_network",
             "ARP6/SEF chromatin remodeler upstream of H2A_Z; not in network."),
    "KIB1": ("not_in_network", "not_in_network",
             "KIB1 BIN2 E3 ligase; not in network."),
    "BKI1": ("not_in_network", "not_in_network",
             "BKI1 BRI1 kinase inhibitor; not in network."),
    "CRY1": ("not_in_network", "not_in_network",
             "Cryptochrome 1 blue-light receptor; not in network (LOW priority)."),
    "CCA1": ("not_in_network", "not_in_network",
             "CCA1 morning clock component; not in network (LOW priority; distinct from Evening Complex)."),
    "EBF1": ("not_in_network", "not_in_network",
             "EBF1 EIN3-degrading F-box; not in network."),
    "SMXL6": ("not_in_network", "not_in_network",
              "SMXL6_7_8 composite not in the height network; documented as literature_gap S201."),
    "BP":  ("not_in_network", "not_in_network",
            "BP/KNAT1 meristem-identity gene; not in network (S106/S204 deferred)."),
    "STM": ("not_in_network", "not_in_network",
            "STM meristem-identity gene; not in network."),
    "FD":  ("not_in_network", "not_in_network",
            "FD FT-partner bZIP; not in network (FLOWER_INT composite captures FD-FT target effect)."),
    "PIN1": ("not_in_network", "not_in_network",
             "PIN1 auxin transporter; not in network."),
    "PIN3": ("not_in_network", "not_in_network",
             "PIN3 auxin transporter; not in network."),
    "Auxin_Transport": ("not_in_network", "not_in_network",
                         "Auxin_Transport PROCESS node not in network."),

    # --- Empty gene (Sucrose treatment per evidence) ---
    "": ("Sucrose", "treatment_analog",
         "Perturbation entry had empty gene field; evidence describes Sucrose treatment."),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
HORMONES_METABOLITES_ENVS = {
    "Gibberellin", "Brassinosteroid", "Auxin", "Cytokinin", "Ethylene",
    "ABA", "Strigolactone",
    "Sucrose", "T6P",
    "Light", "Temperature", "Cold_Vernalization",
}

# Multi-gene KO keywords
MULTI_KO_TYPES = {
    "double_knockout", "triple_knockout", "quadruple_knockout",
    "quintuple_knockout",
}


def get_gene_modifier(ptype, rec_type):
    """Return the gene_modifier float for a given perturbation_type."""
    if ptype in ("knockout", "loss_of_function"):
        if rec_type == "composite_member":
            return 0.99
        return 0.0
    if ptype in ("knockdown",):
        return 0.5
    if ptype in ("overexpression",):
        return 2.0
    if ptype in MULTI_KO_TYPES:
        # Multi-gene KOs: assume covering multiple paralogs in the composite
        # or a true double-KO of non-composite genes. Treat as full KO.
        return 0.0
    if ptype in ("gain_of_function",):
        # DELLA gai-1 stabilised → composite modifier OE-like
        return 2.0
    if ptype in ("knockout_arp6",):
        return 0.0
    if ptype in ("inhibitor_PBZ",):
        return 0.1  # GA biosynthesis KD proxy
    return 1.0  # default WT baseline


def build_perturbations_list(gene_mods, exo_supply):
    """Flatten gene_modifiers + exogenous_supply into the per-test
    perturbations array."""
    out = []
    for node, val in gene_mods.items():
        out.append({"node": node, "modifier_type": "gene_modifier", "value": val})
    for node, val in exo_supply.items():
        out.append({"node": node, "modifier_type": "exogenous_supply", "value": val})
    return out


def reconcile(p, idx):
    """Return a reconciled perturbation dict for a single raw entry."""
    tid = f"T{idx:03d}"
    gene = p.get("gene", "")
    ptype = p.get("perturbation_type", "")
    expected = p.get("expected_direction", "unchanged")
    magnitude = p.get("expected_magnitude", "")
    evidence = p.get("evidence", [])
    condition = p.get("condition", "both")
    species = p.get("species", "Arabidopsis thaliana")

    # Lookup
    if gene in GENE_MAP:
        mapped_node, rec_type, note = GENE_MAP[gene]
    else:
        # Try case-insensitive
        low = {k.lower(): (v, t, n) for k, (v, t, n) in GENE_MAP.items()}
        if gene.lower() in low:
            mapped_node, rec_type, note = low[gene.lower()]
            rec_type = "case_insensitive"
        else:
            mapped_node, rec_type, note = "not_in_network", "not_in_network", \
                f"Gene '{gene}' has no mapping entry."

    in_network = (mapped_node != "not_in_network")

    gene_modifiers = {}
    exogenous_supply = {}
    comparison_baseline = "WT"

    if not in_network:
        # No modification; flagged for VALIDATOR to skip
        pass
    else:
        # Determine modifier encoding based on perturbation type
        if ptype in ("exogenous_treatment", "chemical_treatment"):
            # Hormone or metabolite treatment: WT baseline + exogenous supply
            if mapped_node in HORMONES_METABOLITES_ENVS or mapped_node == "Cold_Vernalization":
                exogenous_supply = {mapped_node: 1.0}
            else:
                # Fall back to setting gene_modifier = 2.0 (treatment-as-OE proxy)
                gene_modifiers = {mapped_node: 2.0}

        elif ptype == "environmental":
            # Vernalization or Temperature
            exogenous_supply = {mapped_node: 1.0}

        elif ptype == "knockout_plus_treatment":
            # Mutant + treatment (signalling mutant context, see Trap 5)
            gene_modifiers = {mapped_node: 0.0 if rec_type != "composite_member" else 0.99}
            # Identify the treatment from evidence or default to matching hormone
            treatment_node = None
            claim = (evidence[0].get("claim", "") if evidence else "").lower()
            ev = (evidence[0].get("evidence_sentence", "") if evidence else "").lower()
            text = claim + " " + ev
            if "ga" in text or "gibberell" in text:
                treatment_node = "Gibberellin"
            elif "bl" in text or "brassinosteroid" in text or "brassinolide" in text:
                treatment_node = "Brassinosteroid"
            elif "27" in text or "warm" in text or "temperature" in text:
                treatment_node = "Temperature"
            elif "r:fr" in text or "shade" in text or "light" in text:
                treatment_node = "Light"
            if treatment_node and treatment_node in network_nodes:
                exogenous_supply[treatment_node] = 1.0
            # Comparison baseline: rescue means compared to mutant alone or WT
            comparison_baseline = "mutant"

        elif ptype in ("rescue_experiment",):
            # Similar to knockout_plus_treatment
            gene_modifiers = {mapped_node: 0.0 if rec_type != "composite_member" else 0.99}
            claim = (evidence[0].get("claim", "") if evidence else "").lower()
            if "bl" in claim or "brassinosteroid" in claim or "brassinolide" in claim:
                exogenous_supply["Brassinosteroid"] = 1.0
            elif "ga" in claim:
                exogenous_supply["Gibberellin"] = 1.0
            comparison_baseline = "mutant"

        elif ptype == "gain_of_function_plus_treatment":
            # gai-1 (stabilised DELLA) + GA — no rescue
            gene_modifiers = {mapped_node: 2.0}
            exogenous_supply["Gibberellin"] = 1.0
            comparison_baseline = "mutant"

        elif ptype == "inhibitor_PBZ":
            # Paclobutrazol inhibits GA biosynthesis
            gene_modifiers = {"GA20OX": 0.1, "GA3OX": 0.1}

        else:
            # Standard KO / OE / knockdown / multi-gene KO
            gm = get_gene_modifier(ptype, rec_type)
            gene_modifiers = {mapped_node: gm}

    perturbations_list = build_perturbations_list(gene_modifiers, exogenous_supply)

    # Clean evidence -- flat structure
    clean_ev = []
    for ev in evidence:
        clean_ev.append({
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

    return {
        "test_id": tid,
        "gene": gene,
        "perturbation_type": ptype,
        "expected_direction": expected,
        "in_network": in_network,
        "network_gene": [mapped_node] if in_network else [],
        "gene_modifiers": gene_modifiers,
        "exogenous_supply": exogenous_supply,
        "perturbations": perturbations_list,
        "notes": note,
        "evidence": clean_ev,
        "phenotype_node": "Plant_Height",
        "comparison_baseline": comparison_baseline,
        "condition": condition,
        "reconciliation_type": rec_type,
        "reconciliation_note": note,
        "expected_magnitude": magnitude,
        "species": species,
    }


# ---------------------------------------------------------------------------
# Reconcile every test
# ---------------------------------------------------------------------------
reconciled = []
for i, p in enumerate(raw["perturbations"], start=1):
    reconciled.append(reconcile(p, i))

# Add a WT negative control (per quality checklist)
control_test = {
    "test_id": f"T{len(reconciled)+1:03d}",
    "gene": "WT",
    "perturbation_type": "control",
    "expected_direction": "unchanged",
    "in_network": True,
    "network_gene": ["Plant_Height"],
    "gene_modifiers": {},
    "exogenous_supply": {},
    "perturbations": [],
    "notes": "Wild-type control; no perturbation applied. All gene_modifiers at default 1.0.",
    "evidence": [{
        "doi": "10.0/wt-control",
        "title": "Wild-type negative control",
        "authors": "FLASH-P v2.0",
        "year": 2026,
        "journal": "(internal)",
        "evidence_sentence": "WT Col-0 plants at normal conditions show standard plant height baseline.",
        "claim": "Baseline WT condition; expected value = 1.0 for all nodes.",
    }],
    "phenotype_node": "Plant_Height",
    "comparison_baseline": "WT",
    "condition": "both",
    "reconciliation_type": "control",
    "reconciliation_note": "Synthetic WT control ensuring VALIDATOR has at least one unchanged benchmark.",
    "expected_magnitude": "none",
    "species": "Arabidopsis thaliana",
}
reconciled.append(control_test)

# ---------------------------------------------------------------------------
# Emit output
# ---------------------------------------------------------------------------
in_net_count = sum(1 for r in reconciled if r["in_network"])
not_in_net_count = len(reconciled) - in_net_count

out = {
    "metadata": {
        "flash_p_version": "2.0",
        "phenotype": "Plant_Height",
        "species": "Arabidopsis thaliana",
        "created": "2026-04-19",
        "total_tests": len(reconciled),
        "in_network": in_net_count,
        "not_in_network": not_in_net_count,
        "phenotype_node": "Plant_Height",
        "convention": "expected_direction compares perturbation to WT baseline (or mutant alone for rescues); direction_threshold 0.05",
    },
    "direction_threshold": 0.05,
    "perturbations": reconciled,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
from collections import Counter
rc_counter = Counter(r["reconciliation_type"] for r in reconciled)
print(f"Reconciled {len(reconciled)} tests "
      f"({in_net_count} in network, {not_in_net_count} not_in_network)")
print(f"Wrote {OUT}")
print("\nBreakdown by reconciliation_type:")
for rc, n in rc_counter.most_common():
    print(f"  {rc:25s} {n}")

# Control check
ctrl = [r for r in reconciled if r["reconciliation_type"] == "control"]
print(f"\nControls: {len(ctrl)}")

# Sanity: show 3 not_in_network
print("\nSample not_in_network tests:")
for r in reconciled:
    if not r["in_network"]:
        print(f"  {r['test_id']}  {r['gene']:20s} -> {r['reconciliation_note']}")
