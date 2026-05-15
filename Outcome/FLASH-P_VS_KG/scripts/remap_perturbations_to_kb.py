#!/usr/bin/env python3
"""
Remap v1.0 reconciled perturbations from Arabidopsis/<Phenotype>_network (FLASH-P)
onto the KB_Cleaned/<trait>_network node sets, so the same tests can be run by the
shared validators against the KB networks.

For each test:
  - Map each node in gene_modifiers and exogenous_supply to a KB node, trying:
      1. Exact match
      2. Case-insensitive match
      3. Alias lookup harvested from the archived KB's OLD reconciled file
         (e.g. "MAX3 = CCD7")
  - Keep surviving mods; drop unmappable ones.
  - in_network = true iff at least one modification survives.

Also copies the raw perturbation_dataset.json verbatim (needed for Table_S2).

Usage:
  python remap_perturbations_to_kb.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[2]  # FlashP_Repo/
FLASHP_DIR = ROOT / "Arabidopsis"
MERGED_FLASHP_DIR = ROOT / "merged_arabidopsis_network"
ARCHIVE_DIR = ROOT / "Knowledge_Base_Comparison_archived" / "KB_Cleaned"
RERUN_DIR = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20" / "KB_Cleaned"
ALIAS_DIR = ROOT / "Knowledge_Base_Comparison_rerun_2026-04-20" / "results" / "aliases"

TRAIT_MAP = {
    "shoot_branching":      ("Shoot_Branching_network",      "Shoot_Branching"),
    "flowering_time":       ("Flowering_Time_network",       "Flowering_Time"),
    "hypocotyl_length":     ("Hypocotyl_Length_network",     "Hypocotyl_Length"),
    "plant_height":         ("Plant_Height_network",         "Plant_Height"),
    "lateral_root_density": ("Lateral_Root_Density_network", "Lateral_Root_Density"),
    "seed_size":            ("Seed_Size_network",            "Seed_Size"),
}

ALIAS_RE = re.compile(r"^\s*([A-Za-z0-9/]+)\s*=\s*([A-Za-z0-9/]+)\s*$")


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def load_kb_nodes(kb_network_dir: Path):
    """Return (exact_set, ci_map) from KB network.json."""
    d = load_json(kb_network_dir / "network" / "network.json")
    exact = {n["id"] for n in d.get("nodes", [])}
    ci = {n.lower(): n for n in exact}
    return exact, ci


def load_expert_aliases(trait: str, kb_exact: set):
    """Load agent-produced aliases from results/aliases/<trait>.json.
    Returns (aliases_dict, type_overrides_dict).

    aliases_dict: {term -> kb_node}.
    type_overrides_dict: {term -> reconciliation_type} so we can report
    the specific v1.0 enum (family_member / composite_member / treatment_analog
    / mechanism_mapping) instead of a generic fallback.
    """
    aliases = {}
    type_overrides = {}
    p = ALIAS_DIR / f"{trait}.json"
    if not p.exists():
        return aliases, type_overrides
    try:
        d = load_json(p)
    except Exception:
        return aliases, type_overrides
    VALID = {"exact_match", "case_insensitive", "family_member",
             "composite_collapse", "composite_member", "treatment_analog",
             "mechanism_mapping", "not_in_network", "control"}
    NORMALIZE = {
        "exact": "exact_match",
        "family": "family_member",
        "composite": "composite_member",
        "treatment": "treatment_analog",
        "mechanism": "mechanism_mapping",
    }
    for entry in d.get("aliases", []):
        term = entry.get("term", "")
        kb_node = entry.get("kb_node", "")
        rtype = entry.get("reconciliation_type", "")
        rtype = NORMALIZE.get(rtype, rtype)
        if rtype not in VALID:
            rtype = "mechanism_mapping"
        if not term or not kb_node or rtype == "not_in_network":
            continue
        if kb_node not in kb_exact:
            # Invalid mapping — ignore
            continue
        aliases[term] = kb_node
        aliases[term.lower()] = kb_node
        if rtype:
            type_overrides[term] = rtype
            type_overrides[term.lower()] = rtype
    return aliases, type_overrides


def harvest_aliases(archive_reconciled_path: Path, kb_exact: set):
    """Parse "ALIAS = CANONICAL" lines from the archived KB reconciled file.
    Only keep aliases whose CANONICAL is a real KB node.
    """
    aliases = {}
    if not archive_reconciled_path.exists():
        return aliases
    try:
        d = load_json(archive_reconciled_path)
    except Exception:
        return aliases
    for t in d.get("perturbations", []):
        note = t.get("reconciliation_notes") or t.get("reconciliation_note") or ""
        if not note:
            continue
        m = ALIAS_RE.match(note)
        if not m:
            continue
        a, b = m.group(1), m.group(2)
        # Direction of alias: take whichever side is in KB as canonical
        if a in kb_exact and b not in kb_exact:
            aliases[b] = a
            aliases[b.lower()] = a
        elif b in kb_exact and a not in kb_exact:
            aliases[a] = b
            aliases[a.lower()] = b
    return aliases


def map_node(name: str, kb_exact: set, kb_ci: dict, aliases: dict,
             type_overrides: dict = None):
    """Return (kb_node_name, how) or (None, None).
    how is one of the v1.0 ReconciliationType enum values.
    """
    type_overrides = type_overrides or {}
    if name in kb_exact:
        return name, "exact_match"
    if name.lower() in kb_ci:
        return kb_ci[name.lower()], "case_insensitive"
    if name in aliases:
        return aliases[name], type_overrides.get(name, "mechanism_mapping")
    if name.lower() in aliases:
        return aliases[name.lower()], type_overrides.get(name.lower(), "mechanism_mapping")
    return None, None


def remap_test(t: dict, kb_exact: set, kb_ci: dict, aliases: dict,
               phenotype_node: str, type_overrides: dict = None):
    """Return a NEW test dict, remapped. Leaves original untouched."""
    type_overrides = type_overrides or {}
    t = deepcopy(t)

    new_gm = {}
    new_es = {}
    remap_types = []

    for node, val in (t.get("gene_modifiers") or {}).items():
        kb_node, how = map_node(node, kb_exact, kb_ci, aliases, type_overrides)
        if kb_node is not None:
            new_gm[kb_node] = float(val)
            remap_types.append(how)

    for node, val in (t.get("exogenous_supply") or {}).items():
        kb_node, how = map_node(node, kb_exact, kb_ci, aliases, type_overrides)
        if kb_node is not None:
            new_es[kb_node] = float(val)
            remap_types.append(how)

    in_net = bool(new_gm) or bool(new_es)

    perts = []
    for node, val in new_gm.items():
        perts.append({"node": node, "modifier_type": "gene_modifier", "value": float(val)})
    for node, val in new_es.items():
        perts.append({"node": node, "modifier_type": "exogenous_supply", "value": float(val)})

    # Determine reconciliation_type
    if not in_net:
        recon_type = "not_in_network"
    elif all(r == "exact_match" for r in remap_types):
        recon_type = "exact_match"
    elif any(r == "mechanism_mapping" for r in remap_types):
        recon_type = "mechanism_mapping"
    else:
        recon_type = "case_insensitive"

    t["gene_modifiers"] = new_gm
    t["exogenous_supply"] = new_es
    t["perturbations"] = perts
    t["network_gene"] = list(new_gm.keys()) if new_gm else []
    t["in_network"] = in_net
    t["phenotype_node"] = phenotype_node
    t["reconciliation_type"] = recon_type
    t["reconciliation_note"] = t.get("reconciliation_note", "") or ""
    return t


def remap_file(src_reconciled: Path, kb_network_dir: Path,
               archive_reconciled: Path, phenotype: str, phenotype_node: str,
               out_reconciled: Path, out_raw: Path = None, src_raw: Path = None):
    """Remap one perturbation dataset and write outputs."""
    kb_exact, kb_ci = load_kb_nodes(kb_network_dir)
    archive_aliases = harvest_aliases(archive_reconciled, kb_exact)
    expert_aliases, expert_types = load_expert_aliases(phenotype, kb_exact)
    # Expert aliases win over archive-derived aliases if both define a term.
    aliases = {**archive_aliases, **expert_aliases}

    d = load_json(src_reconciled)
    new_perts = [remap_test(t, kb_exact, kb_ci, aliases, phenotype_node,
                            type_overrides=expert_types)
                 for t in d.get("perturbations", [])]

    total = len(new_perts)
    in_net = sum(1 for t in new_perts if t["in_network"])
    not_in_net = total - in_net

    meta = deepcopy(d.get("metadata", {}))
    meta.update({
        "flash_p_version": "1.0",
        "phenotype": phenotype,
        "phenotype_node": phenotype_node,
        "species": meta.get("species", "Arabidopsis thaliana"),
        "source": "FLASH-P v1.0 tests remapped to KB_Cleaned nodes",
        "total_tests": total,
        "in_network": in_net,
        "not_in_network": not_in_net,
    })

    out = {
        "metadata": meta,
        "direction_threshold": d.get("direction_threshold", 0.05),
        "perturbations": new_perts,
    }
    save_json(out_reconciled, out)

    if src_raw is not None and out_raw is not None and src_raw.exists():
        shutil.copy2(src_raw, out_raw)

    pct = 100.0 * in_net / total if total else 0.0
    aliases_kept = sum(1 for t in new_perts if t["reconciliation_type"] == "mechanism_mapping")
    print(f"  {phenotype:<22}  tests={total:>4}  in_network={in_net:>4} "
          f"({pct:5.1f}%)  aliases_used={aliases_kept:>3}  KB_nodes={len(kb_exact)}")
    return total, in_net


def run_individual():
    print("Individual phenotype networks:")
    totals = {}
    for trait, (fp_dir, phenotype_node) in TRAIT_MAP.items():
        src_reconciled = FLASHP_DIR / fp_dir / "data" / "reconciled_perturbation_dataset.json"
        src_raw        = FLASHP_DIR / fp_dir / "data" / "perturbation_dataset.json"
        kb_dir         = RERUN_DIR / f"{trait}_network"
        archive_recon  = ARCHIVE_DIR / f"{trait}_network" / "data" / "reconciled_perturbation_dataset.json"
        out_reconciled = kb_dir / "data" / "reconciled_perturbation_dataset.json"
        out_raw        = kb_dir / "data" / "perturbation_dataset.json"
        n_total, n_in = remap_file(
            src_reconciled=src_reconciled, kb_network_dir=kb_dir,
            archive_reconciled=archive_recon, phenotype=trait,
            phenotype_node=phenotype_node, out_reconciled=out_reconciled,
            out_raw=out_raw, src_raw=src_raw)
        totals[trait] = (n_total, n_in)
    return totals


def run_merged():
    print("\nMerged network:")
    trait = "merged"
    phenotype_node = "Shoot_Branching"  # placeholder; merged tests have their own per-test phenotype_node
    src_reconciled = MERGED_FLASHP_DIR / "data" / "reconciled_perturbation_dataset.json"
    src_raw_alt    = MERGED_FLASHP_DIR / "data" / "perturbation_dataset.json"
    kb_dir         = RERUN_DIR / "merged_arabidopsis_network"
    archive_recon  = ARCHIVE_DIR / "merged_arabidopsis_network" / "data" / "reconciled_perturbation_dataset.json"
    out_reconciled = kb_dir / "data" / "reconciled_perturbation_dataset.json"
    out_raw        = kb_dir / "data" / "perturbation_dataset.json"

    kb_exact, kb_ci = load_kb_nodes(kb_dir)
    archive_aliases = harvest_aliases(archive_recon, kb_exact)
    expert_aliases, expert_types = load_expert_aliases("merged", kb_exact)
    aliases = {**archive_aliases, **expert_aliases}
    d = load_json(src_reconciled)
    new_perts = []
    for t in d.get("perturbations", []):
        # Each merged test already carries its own phenotype_node — keep it iff in KB
        per_test_phen = t.get("phenotype_node", "")
        if per_test_phen not in kb_exact:
            # mark as not_in_network due to missing phenotype node
            tt = deepcopy(t)
            tt["in_network"] = False
            tt["gene_modifiers"] = {}
            tt["exogenous_supply"] = {}
            tt["perturbations"] = []
            tt["network_gene"] = []
            tt["reconciliation_type"] = "not_in_network"
            tt["reconciliation_note"] = f"phenotype_node '{per_test_phen}' missing in KB merged graph"
            new_perts.append(tt)
            continue
        new_perts.append(remap_test(t, kb_exact, kb_ci, aliases, per_test_phen,
                                    type_overrides=expert_types))

    total = len(new_perts)
    in_net = sum(1 for t in new_perts if t["in_network"])
    not_in_net = total - in_net

    meta = deepcopy(d.get("metadata", {}))
    meta.update({
        "flash_p_version": "1.0",
        "phenotype": "merged",
        "phenotype_node": meta.get("phenotype_node", ""),
        "species": meta.get("species", "Arabidopsis thaliana"),
        "source": "FLASH-P v1.0 merged tests remapped to KB merged nodes",
        "total_tests": total,
        "in_network": in_net,
        "not_in_network": not_in_net,
    })
    out = {
        "metadata": meta,
        "direction_threshold": d.get("direction_threshold", 0.05),
        "perturbations": new_perts,
    }
    save_json(out_reconciled, out)
    if src_raw_alt.exists():
        shutil.copy2(src_raw_alt, out_raw)
    pct = 100.0 * in_net / total if total else 0.0
    print(f"  {'merged':<22}  tests={total:>4}  in_network={in_net:>4} "
          f"({pct:5.1f}%)  KB_nodes={len(kb_exact)}")
    return total, in_net


def run_merged_pleiotropic():
    print("\nMerged pleiotropic:")
    kb_dir = RERUN_DIR / "merged_arabidopsis_network"
    src = MERGED_FLASHP_DIR / "data" / "pleiotropic_perturbation_dataset.json"
    if not src.exists():
        print("  (no pleiotropic source found — skipping)")
        return
    kb_exact, kb_ci = load_kb_nodes(kb_dir)
    archive_recon = ARCHIVE_DIR / "merged_arabidopsis_network" / "data" / "reconciled_perturbation_dataset.json"
    archive_aliases = harvest_aliases(archive_recon, kb_exact)
    expert_aliases, expert_types = load_expert_aliases("merged", kb_exact)
    aliases = {**archive_aliases, **expert_aliases}

    d = load_json(src)
    new_tests = []
    dropped = 0
    for t in d.get("pleiotropic_tests", []):
        tt = deepcopy(t)
        new_gm, new_es = {}, {}
        for node, val in (t.get("gene_modifiers") or {}).items():
            kb_node, _ = map_node(node, kb_exact, kb_ci, aliases, expert_types)
            if kb_node is not None:
                new_gm[kb_node] = float(val)
        for node, val in (t.get("exogenous_supply") or {}).items():
            kb_node, _ = map_node(node, kb_exact, kb_ci, aliases, expert_types)
            if kb_node is not None:
                new_es[kb_node] = float(val)
        # Filter expected_outcomes to phenotype nodes that exist
        new_outcomes = [oc for oc in (t.get("expected_outcomes") or [])
                        if oc.get("phenotype_node") in kb_exact]
        if not (new_gm or new_es) or not new_outcomes:
            dropped += 1
            continue
        tt["gene_modifiers"] = new_gm
        tt["exogenous_supply"] = new_es
        tt["expected_outcomes"] = new_outcomes
        new_tests.append(tt)

    meta = deepcopy(d.get("metadata", {}))
    meta.update({
        "flash_p_version": "1.0",
        "source": "FLASH-P v1.0 pleiotropic tests remapped to KB merged nodes",
        "total_tests": len(new_tests),
    })
    out = {"metadata": meta, "pleiotropic_tests": new_tests}
    save_json(kb_dir / "data" / "pleiotropic_perturbation_dataset.json", out)
    print(f"  pleiotropic tests: kept={len(new_tests)}  dropped={dropped}")


def main():
    if not RERUN_DIR.exists():
        print(f"ERROR: rerun dir missing: {RERUN_DIR}", file=sys.stderr)
        sys.exit(1)
    run_individual()
    run_merged()
    run_merged_pleiotropic()


if __name__ == "__main__":
    main()
