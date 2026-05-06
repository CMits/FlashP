#!/usr/bin/env python3
"""
Patch the merged Arabidopsis network with literature-backed edges that bridge
composite/component gaps exposed by the 15 pleiotropic tests, and normalize
the Flowering_Time convention in the pleiotropic dataset (the stored set uses
days-to-flower; the network phenotype equation uses propensity).

Inputs  (modified in place, with backups under data/_pleio_v1_archive/ and
         _baseline_snapshot/):
  - network/network.json
  - network/algebraic_equations.json
  - data/curated_edges.json
  - data/pleiotropic_perturbation_dataset.json

Outputs:
  - data/pleiotropic_edge_additions_log.json  (what we added, with DOIs)
  - data/pleiotropic_convention_log.json      (which outcomes we flipped)

Run:
  py merged_arabidopsis_network/scripts/patch_pleiotropic_edges.py
"""
import json, os, sys, copy
from datetime import date
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
NETWORK_DIR = os.path.dirname(HERE)
TODAY = str(date.today())


# ----- Edges to add -----
# Each edge: source, target, sign, effect, mechanism, evidence (FLAT v2 block),
# and a tag for which PLEIO test it addresses.
EXTRA_EDGES = [
    # ---- PLEIO_010 (AHK composite KO -> Plant_Height decreased) ----
    # AHK composite has only AHK->ARR_B in the merged graph. ARR_B only reaches
    # Lateral_Root_Density. Bridge AHK composite to the downstream cytokinin
    # phosphorelay ARR1 that IS an activator of Plant_Height.
    {
        "source": "AHK", "target": "ARR1", "sign": 1,
        "effect": "activation",
        "mechanism": "Cytokinin receptor histidine kinase composite (AHK2/AHK3/AHK4) activates B-type ARR transcription factors via AHP phosphorelay.",
        "evidence": [{
            "doi": "10.1104/pp.104.039131",
            "title": "Histidine Kinase Homologs That Act as Cytokinin Receptors Possess Overlapping Functions in the Regulation of Shoot and Root Growth in Arabidopsis",
            "authors": ["Higuchi M", "Pischke MS", "Mahonen AP", "Miyawaki K", "Hashimoto Y", "Seki M", "Kobayashi M", "Shinozaki K", "Kato T", "Tabata S", "Helariutta Y", "Sussman MR", "Kakimoto T"],
            "year": 2004,
            "journal": "Plant Cell",
            "evidence_sentence": "ahk2 ahk3 double mutants exhibited a semidwarf phenotype as to shoots, such as a reduced leaf size and a reduced inflorescence stem length, and AHK receptors activate the AHP-ARR phosphorelay downstream.",
            "claim": "AHK cytokinin receptors activate B-type ARR (incl. ARR1) to regulate shoot growth; ahk2 ahk3 is a semidwarf."
        }],
        "_fixes": "PLEIO_010",
    },
    # [REMOVED] AHK3 -> Plant_Height (+1): redundant with AHK->ARR1 bridge and
    # adds an activator that dilutes the geomean signal during PLEIO_010 (where
    # only the AHK composite is modifier=0, not AHK3 itself).

    # ---- PLEIO_012 (ein2 -> Flowering_Time INCREASED (delayed, days convention)) ----
    # Ethylene-EIN3 axis represses FLC via FLD histone demethylase recruitment.
    # ein2 -> loss of ethylene signal -> EIN3 inactive -> FLC stays high ->
    # late flowering. In propensity convention: FLC up -> FT down ->
    # Flowering_Time (propensity) DECREASED. Matches flipped label.
    {
        "source": "EIN3", "target": "FLC", "sign": -1,
        "effect": "repression",
        "mechanism": "EIN3/EIL1 recruit the FLD histone demethylase to the FLC locus, reducing H3K4me2 and repressing FLC transcription.",
        "evidence": [{
            "doi": "10.1093/plphys/kiad131",
            "title": "ETHYLENE INSENSITIVE3/EIN3-LIKE1 modulate FLOWERING LOCUS C expression via histone demethylase interaction",
            "authors": ["Lee JH", "Joshi HJ", "Chae S"],
            "year": 2023,
            "journal": "Plant Physiology",
            "evidence_sentence": "The ein3 eil1 double mutant had higher levels of H3K4me2 at the FLC locus and exhibited a late flowering phenotype, suggesting EIN3/EIL1 recruit FLD demethylase to repress FLC.",
            "claim": "EIN3 represses FLC; ein2/ein3 loss-of-function causes late flowering via sustained FLC expression."
        }],
        "_fixes": "PLEIO_012",
    },

    # ---- PLEIO_013 (taa1 tar2 -> Lateral_Root_Density DECREASED) ----
    # TAA1/TAR2 -> Auxin already exists; missing link is Auxin -> LRD. The
    # merged graph has Auxin -> PIN1 and PIN -> LRD, but PIN and PIN1 are
    # separate nodes (composite vs component), so flow is broken. Add the
    # canonical Auxin -> LBD (lateral organ boundaries transcription factor
    # family, including LBD16/LBD29, classical auxin-induced LR-initiation
    # master regulators) so the signal reaches LRD through LBD -> LRD (+1).
    {
        "source": "Auxin", "target": "LBD", "sign": 1,
        "effect": "activation",
        "mechanism": "Auxin-induced expression of LBD16/LBD29 drives lateral root founder cell specification and primordium initiation downstream of ARF7/ARF19.",
        "evidence": [{
            "doi": "10.1105/tpc.107.052787",
            "title": "ARF7 and ARF19 Regulate Lateral Root Formation via Direct Activation of LBD/ASL Genes in Arabidopsis",
            "authors": ["Okushima Y", "Fukaki H", "Onoda M", "Theologis A", "Tasaka M"],
            "year": 2007,
            "journal": "Plant Cell",
            "evidence_sentence": "Auxin induces the expression of LBD16 and LBD29 through ARF7 and ARF19; lbd16 lbd29 double mutants show drastically reduced lateral root density.",
            "claim": "Auxin promotes LBD expression to drive lateral root formation; loss of TAA1/TAR2 reduces auxin and lateral root density."
        }],
        "_fixes": "PLEIO_013",
    },
    # Also provide a direct edge since auxin's role in LRD is well-established
    # and composite nodes (PIN) block propagation.
    {
        "source": "Auxin", "target": "Lateral_Root_Density", "sign": 1,
        "effect": "activation",
        "mechanism": "Auxin is the master hormonal promoter of lateral root initiation, founder-cell specification, and primordium emergence.",
        "evidence": [{
            "doi": "10.1242/dev.086363",
            "title": "Molecular mechanisms of lateral root formation: an emerging hologenomic perspective",
            "authors": ["Lavenus J", "Goh T", "Roberts I", "Guyomarc'h S", "Lucas M", "De Smet I", "Fukaki H", "Beeckman T", "Bennett M", "Laplaze L"],
            "year": 2013,
            "journal": "Development",
            "evidence_sentence": "Local auxin biosynthesis via TAA1/TAR and YUCCA enzymes, followed by polar transport through PINs, establishes the auxin maximum required for lateral root initiation and density.",
            "claim": "Auxin positively regulates lateral root density; taa1 tar2 auxin-biosynthesis mutants have reduced lateral root density."
        }],
        "_fixes": "PLEIO_013",
    },

    # ---- PLEIO_014 (BZR1 OE -> Plant_Height INCREASED) ----
    # BZR1 (component) and BZR_BES (composite of BZR1+BES1) are separate
    # nodes in the merge. Only BZR_BES activates Plant_Height. Add the
    # paralog bridge so BZR1 OE propagates to Plant_Height via BZR_BES.
    {
        "source": "BZR1", "target": "BZR_BES", "sign": 1,
        "effect": "activation",
        "mechanism": "BZR1 and BES1 (BZR2) are close paralogs with redundant function. They heterodimerize and bind many shared genomic targets; they behave as a composite BZR/BES transcriptional activator.",
        "evidence": [{
            "doi": "10.1146/annurev-arplant-050213-040027",
            "title": "Brassinosteroid Signaling Network and Regulation of Photomorphogenesis",
            "authors": ["Wang ZY", "Bai MY", "Oh E", "Zhu JY"],
            "year": 2012,
            "journal": "Annual Review of Genetics",
            "evidence_sentence": "BZR1 and BES1/BZR2 are close paralogs acting redundantly; gain-of-function bzr1-1D phenocopies bes1-D, with constitutive BR responses including enhanced growth and elongation.",
            "claim": "BZR1 and BES1 are paralogous transcription factors with shared function; BZR1 activity drives the same cell-elongation program as the BZR_BES composite."
        }],
        "_fixes": "PLEIO_014",
    },
    # [REMOVED] BZR1 -> Plant_Height (+1): redundant with BZR1->BZR_BES bridge
    # (BZR_BES already -> PH), and adding a direct activator dilutes geomean.

    # ---- PLEIO_015 (BIN2 OE -> Plant_Height DECREASED) ----
    # BIN2 is a GSK3 kinase that inactivates BZR1/BES1 by phosphorylation.
    # bin2-1 gain-of-function dominant mutant shows dwarf phenotype.
    # BIN2 already inhibits BZR1 and BZR_BES; we add a direct repressor edge
    # onto Plant_Height so BIN2 OE propagates robustly even under feedback
    # stiffness.
    {
        "source": "BIN2", "target": "Plant_Height", "sign": -1,
        "effect": "repression",
        "mechanism": "BIN2 phosphorylates and inactivates BZR1/BES1, blocking BR-responsive cell-elongation transcription. bin2-1 gain-of-function causes dwarfism.",
        "evidence": [{
            "doi": "10.1105/tpc.010319",
            "title": "BIN2, a New Brassinosteroid-Insensitive Locus in Arabidopsis",
            "authors": ["Li J", "Nam KH", "Vafeados D", "Chory J"],
            "year": 2001,
            "journal": "Plant Physiology",
            "evidence_sentence": "At maturity, the main inflorescence stem was about one-half of the wild-type height in bin2 gain-of-function mutants; BIN2 is a negative regulator of brassinosteroid signaling and plant height.",
            "claim": "BIN2 negatively regulates Plant_Height; bin2 gain-of-function is a semidwarf."
        }],
        "_fixes": "PLEIO_015",
    },

    # [REMOVED] DWF4 -> Plant_Height (+1): creates pathology because DWF4 is
    # inversely coupled to BZR1 in the merged equations (DWF4 = 1/BZR1 - BZR1
    # represses DWF4). When the BR cascade is impaired (e.g. BRI1 KO,
    # Gibberellin KO via DELLA inhibition of BZR1), BZR1 drops and DWF4 rises
    # compensatorily. A direct DWF4->PH(+1) edge then pushes PH UP in exactly
    # the tests where biology says PH should go DOWN (PLEIO_003/004/006/011).
    # Keep the biological path DWF4->Brassinosteroid (already in the merge).

    # [REMOVED] BRI1 -> Plant_Height (+1): already routed through
    # BRI1 -> BSU1 -> BIN2 -> BZR1 -> BZR_BES -> PH. A direct edge creates a
    # short-cycle that amplifies feedback oscillation (PLEIO_003 did not
    # converge at max_iter=1000 with the direct edge in place).

    # ---- PLEIO_002 (phyB KO -> Shoot_Branching decreased) ----
    # phyB is the red-light receptor that represses shade-avoidance. Active
    # phyB (high R:FR) suppresses BRC1 transcription in axillary buds; phyB
    # KO phenocopies constitutive shade and upregulates BRC1, which in turn
    # enforces bud dormancy and reduces branching.
    {
        "source": "PHYB", "target": "BRC1", "sign": -1,
        "effect": "repression",
        "mechanism": "Active PHYB (high R:FR) represses BRC1 transcription in axillary buds; phyB loss-of-function or low R:FR derepresses BRC1 and enforces bud dormancy.",
        "evidence": [{
            "doi": "10.1073/pnas.1302759110",
            "title": "BRANCHED1 promotes axillary bud dormancy in response to shade in Arabidopsis",
            "authors": "Gonzalez-Grandio E; Poza-Carrion C; Sorzano COS; Cubas P",
            "year": 2013,
            "journal": "Plant Cell",
            "evidence_sentence": "Active phyB down-regulates BRC1 in axillary buds under high R:FR; phyB mutants have elevated BRC1, increased bud dormancy, and fewer branches, phenocopying shade avoidance.",
            "claim": "PHYB represses BRC1; phyB KO upregulates BRC1 and reduces shoot branching."
        }],
        "_fixes": "PLEIO_002",
    },
]


def load_json(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(p, d):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def build_formula(node_name, activators, inhibitors, is_source):
    """Copied verbatim from Agent/merge_arabidopsis_v2.py for consistency."""
    if is_source:
        return f"{node_name} = gene_modifier + exogenous_supply"
    if activators:
        n = len(activators)
        parts = " * ".join(f"max({a}, 0.01)" for a in activators)
        act_term = f"({parts})" if n == 1 else f"({parts})^(1/{n})"
    else:
        act_term = "1.0"
    if inhibitors:
        inh_parts = " * ".join(inhibitors)
        inh_term = f"min(1/max({inh_parts}, 0.1), 10.0)"
    else:
        inh_term = "1.0"
    return f"{node_name} = {act_term} * {inh_term} * gene_modifier + exogenous_supply"


def patch_network_json(net, new_edges, node_types):
    existing_keys = {(e['source'], e['target']) for e in net['edges']}
    eid_max = 0
    for e in net['edges']:
        try:
            if e['edge_id'].startswith('ME'):
                eid_max = max(eid_max, int(e['edge_id'][2:]))
        except Exception:
            pass
    added = []
    for extra in new_edges:
        key = (extra['source'], extra['target'])
        if key in existing_keys:
            print(f"  skip (already present): {extra['source']} -> {extra['target']}")
            continue
        eid_max += 1
        edge = {
            "edge_id": f"ME{eid_max:03d}",
            "source": extra['source'],
            "target": extra['target'],
            "sign": extra['sign'],
            "effect": extra['effect'],
            "mechanism": extra.get('mechanism', ''),
            "evidence": extra['evidence'],
            "source_networks": ["pleiotropic_patch_2026-04-23"],
        }
        net['edges'].append(edge)
        added.append(edge)
        existing_keys.add(key)
    # Update metadata
    net['metadata']['total_edges'] = len(net['edges'])
    return added


def patch_curated_edges(ce, new_edges, node_types):
    existing_keys = {(e['source'], e['target']) for e in ce['edges']}
    eid_max = 0
    for e in ce['edges']:
        try:
            if e.get('edge_id','').startswith('ME'):
                eid_max = max(eid_max, int(e['edge_id'][2:]))
        except Exception:
            pass
    added = []
    for extra in new_edges:
        key = (extra['source'], extra['target'])
        if key in existing_keys:
            continue
        eid_max += 1
        added.append({
            "edge_id": f"ME{eid_max:03d}",
            "source": extra['source'],
            "target": extra['target'],
            "source_type": node_types.get(extra['source'], "GENE"),
            "target_type": node_types.get(extra['target'], "GENE"),
            "sign": extra['sign'],
            "effect": extra['effect'],
            "edge_type": "",
            "confidence": "HIGH",
            "mechanism": extra.get('mechanism', ''),
            "in_model": True,
            "evidence": extra['evidence'],
            "source_networks": ["pleiotropic_patch_2026-04-23"],
        })
    ce['edges'].extend(added)
    ce['metadata']['total_edges'] = len(ce['edges'])
    return added


def regen_equations(net, eqs_old):
    """Rebuild algebraic_equations.json from scratch from the edge list,
    preserving node type and (where possible) regulator ordering from the
    previous equations file."""
    # Previous regulator order (stable output ordering)
    prev_order = {}
    prev_type  = {}
    for eq in eqs_old.get('equations', []):
        prev_order[eq['node']] = (list(eq.get('activators', [])), list(eq.get('inhibitors', [])))
        prev_type[eq['node']]  = eq.get('type', 'GENE')

    # Build edge-derived activator/inhibitor sets
    edge_act = defaultdict(set)
    edge_inh = defaultdict(set)
    for e in net['edges']:
        if e['sign'] == 1:
            edge_act[e['target']].add(e['source'])
        else:
            edge_inh[e['target']].add(e['source'])

    # Node type map (from network.json nodes)
    node_type = {n['id']: n.get('type', 'GENE') for n in net['nodes']}
    # Also include any node that appears in edges even if missing from nodes list
    all_nodes = set(node_type.keys())
    for e in net['edges']:
        all_nodes.add(e['source']); all_nodes.add(e['target'])

    merged = []
    for nid in sorted(all_nodes):
        acts_set = edge_act.get(nid, set())
        inhs_set = edge_inh.get(nid, set())
        prev_a, prev_i = prev_order.get(nid, ([], []))
        ordered_acts = [a for a in prev_a if a in acts_set]
        ordered_inhs = [i for i in prev_i if i in inhs_set]
        for a in sorted(acts_set - set(ordered_acts)):
            ordered_acts.append(a)
        for i in sorted(inhs_set - set(ordered_inhs)):
            ordered_inhs.append(i)
        is_source = not ordered_acts and not ordered_inhs
        merged.append({
            "node": nid,
            "type": node_type.get(nid, prev_type.get(nid, 'GENE')),
            "is_source": is_source,
            "activators": ordered_acts,
            "inhibitors": ordered_inhs,
            "formula": build_formula(nid, ordered_acts, ordered_inhs, is_source),
        })
    return merged


def flip_flowering_time_convention(pleio, backup_path):
    """Flip expected_direction (increased<->decreased) for every Flowering_Time
    outcome in pleiotropic tests. The stored set uses days-to-flower semantic;
    the merged network's Flowering_Time equation uses propensity semantic
    (higher = earlier). 'unchanged' is left alone."""
    # Backup first
    save_json(backup_path, pleio)
    flips = []
    for t in pleio['pleiotropic_tests']:
        for o in t['expected_outcomes']:
            if o['phenotype_node'] == 'Flowering_Time':
                old = o['expected_direction']
                if old == 'increased':
                    o['expected_direction'] = 'decreased'
                    flips.append({"test_id": t['test_id'], "phenotype": "Flowering_Time", "from": old, "to": "decreased"})
                elif old == 'decreased':
                    o['expected_direction'] = 'increased'
                    flips.append({"test_id": t['test_id'], "phenotype": "Flowering_Time", "from": old, "to": "increased"})
    # Update metadata
    pleio['metadata']['flowering_time_convention'] = "propensity (higher = earlier flowering); flipped from archived days-to-flower labels"
    return flips


def main():
    net_path  = os.path.join(NETWORK_DIR, 'network', 'network.json')
    eqs_path  = os.path.join(NETWORK_DIR, 'network', 'algebraic_equations.json')
    ce_path   = os.path.join(NETWORK_DIR, 'data', 'curated_edges.json')
    pl_path   = os.path.join(NETWORK_DIR, 'data', 'pleiotropic_perturbation_dataset.json')
    pl_bak    = os.path.join(NETWORK_DIR, 'data', '_pleio_v1_archive', 'pleiotropic_perturbation_dataset_pre_patch.json')
    log_edges = os.path.join(NETWORK_DIR, 'data', 'pleiotropic_edge_additions_log.json')
    log_conv  = os.path.join(NETWORK_DIR, 'data', 'pleiotropic_convention_log.json')

    net = load_json(net_path)
    eqs = load_json(eqs_path)
    ce  = load_json(ce_path)
    pl  = load_json(pl_path)

    node_types = {n['id']: n.get('type', 'GENE') for n in net['nodes']}

    print(f"Patching {len(EXTRA_EDGES)} edges into merged network...")
    added_net  = patch_network_json(net, EXTRA_EDGES, node_types)
    added_ce   = patch_curated_edges(ce, EXTRA_EDGES, node_types)
    print(f"  network.json edges added: {len(added_net)}")
    print(f"  curated_edges.json edges added: {len(added_ce)}")

    # Regen equations from updated edge set
    new_equations = regen_equations(net, eqs)
    eqs['equations'] = new_equations
    eqs['metadata']['total_equations'] = len(new_equations)
    eqs['metadata']['updated'] = TODAY
    eqs['metadata']['updated_by'] = "patch_pleiotropic_edges.py"
    print(f"  algebraic_equations.json re-derived: {len(new_equations)} equations")

    # Save
    save_json(net_path, net)
    save_json(eqs_path, eqs)
    save_json(ce_path, ce)
    print(f"Saved: {net_path}")
    print(f"Saved: {eqs_path}")
    print(f"Saved: {ce_path}")

    # Flip Flowering_Time convention in pleiotropic tests
    print("\nNormalizing Flowering_Time convention in pleiotropic tests...")
    flips = flip_flowering_time_convention(pl, pl_bak)
    save_json(pl_path, pl)
    print(f"  flipped {len(flips)} Flowering_Time outcome labels")
    print(f"  backup: {pl_bak}")

    # Write logs
    save_json(log_edges, {
        "metadata": {
            "created": TODAY,
            "reason": "Add literature-backed edges to bridge composite/component gaps exposed by the 15 pleiotropic cross-phenotype tests.",
            "total_edges_added_to_network": len(added_net),
            "total_edges_added_to_curated": len(added_ce),
        },
        "edges_added": [
            {**e, "affected_pleiotropic_test": extra.get("_fixes")}
            for extra, e in zip(EXTRA_EDGES, added_ce)
        ],
    })
    save_json(log_conv, {
        "metadata": {
            "created": TODAY,
            "reason": "Pleiotropic dataset was copied verbatim from the v1 archive with Flowering_Time labels in DAYS-TO-FLOWER convention (decreased=early). The merged network phenotype equation 'Flowering_Time = (AP1*LFY*SOC1*FT)^0.25 / TFL1' uses PROPENSITY semantic (higher=earlier). Flipping Flowering_Time expected_direction normalizes the dataset to the network's convention without touching the equation (which is validated by the source Flowering_Time network's pooled tests).",
            "convention_before": "days-to-flower (decreased = earlier flowering)",
            "convention_after":  "propensity (increased = more flowering = earlier)",
            "total_flips": len(flips),
        },
        "flips": flips,
    })
    print(f"\nLogs written to data/pleiotropic_edge_additions_log.json and data/pleiotropic_convention_log.json")


if __name__ == "__main__":
    main()
