#!/usr/bin/env python3
"""Post-extraction cleanup: fix Unicode artifacts in DOIs that Gemma occasionally
emits (e.g. '10.104\\ub3c4/...' should be '10.1104/...'). Also validates DOI
format and reports unfixable cases."""
import json, re, sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DOI_RE = re.compile(r"^10\.\d{4,9}/[\S]+$")

# Common publisher prefixes — used to repair Unicode noise inside the prefix
KNOWN_PREFIXES = [
    "10.1104/",  # Plant Physiology
    "10.1105/",  # Plant Cell
    "10.1126/",  # Science
    "10.1038/",  # Nature
    "10.1093/",  # Oxford UP (JXB, PCP)
    "10.1111/",  # Wiley (New Phyt, Plant J)
    "10.1016/",  # Elsevier (Cell, Trends)
    "10.1242/",  # Development
    "10.3389/",  # Frontiers
    "10.1073/",  # PNAS
    "10.1101/",  # bioRxiv
    "10.1186/",  # BMC
    "10.7554/",  # eLife
    "10.1021/",  # ACS
    "10.1007/",  # Springer
    "10.1002/",  # Wiley general
    "10.1371/",  # PLoS
    "10.4161/",  # Plant Signaling & Behavior
    "10.1089/",
    "10.1146/",
]


def repair(doi: str) -> str:
    if not doi:
        return doi
    # strip non-ASCII characters from inside the prefix portion
    fixed = "".join(c if ord(c) < 128 else "" for c in doi)
    if DOI_RE.match(fixed):
        return fixed
    # Try to align garbled prefix to a known one
    if "/" in fixed:
        suffix = fixed.split("/", 1)[1]
        for kp in KNOWN_PREFIXES:
            # if suffix matches a typical pattern for the publisher, try that prefix
            if kp == "10.1104/" and re.match(r"^pp\.\d", suffix): return kp + suffix
            if kp == "10.1105/" and re.match(r"^tpc\.\d", suffix): return kp + suffix
            if kp == "10.1093/" and re.match(r"^(pcp|jxb)/", suffix): return kp + suffix
            if kp == "10.1111/" and re.match(r"^(nph|tpj)\.", suffix): return kp + suffix
    return doi  # give up, keep original


def update_evidence(evidence, fix_map):
    if not isinstance(evidence, dict):
        return 0
    cnt = 0
    if evidence.get("doi") in fix_map:
        evidence["doi"] = fix_map[evidence["doi"]]
        cnt += 1
    return cnt


def main():
    p = json.load((DATA / "candidate_papers.json").open())
    e = json.load((DATA / "curated_edges.json").open())
    pt = json.load((DATA / "perturbation_dataset.json").open())

    fix_map = {}
    bad = []
    for pp in p["papers"]:
        original = pp.get("doi")
        if not original:
            bad.append((pp.get("paper_id"), original, "missing"))
            continue
        if DOI_RE.match(original):
            continue
        fixed = repair(original)
        if DOI_RE.match(fixed):
            fix_map[original] = fixed
            pp["doi"] = fixed
        else:
            bad.append((pp.get("paper_id"), original, "unrepairable"))

    # propagate fixes to edges and perturbations
    e_fixed = sum(update_evidence(ed.get("evidence"), fix_map) for ed in e["edges"])
    pt_fixed = sum(update_evidence(t.get("evidence"), fix_map) for t in pt["perturbations"])

    json.dump(p, (DATA / "candidate_papers.json").open("w"), indent=2, ensure_ascii=False)
    json.dump(e, (DATA / "curated_edges.json").open("w"), indent=2, ensure_ascii=False)
    json.dump(pt, (DATA / "perturbation_dataset.json").open("w"), indent=2, ensure_ascii=False)

    print(f"DOIs repaired in papers: {len(fix_map)}")
    if fix_map:
        for o, f in list(fix_map.items())[:10]:
            print(f"  {o!r:50s}  -->  {f!r}")
    print(f"evidence entries updated: {e_fixed} edges, {pt_fixed} perturbations")
    print(f"unrepairable / missing: {len(bad)}")
    for pid, doi, why in bad:
        print(f"  - {pid}: {why} ({doi!r})")


if __name__ == "__main__":
    main()
