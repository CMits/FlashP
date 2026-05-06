"""
Paired McNemar's test: single-trait vs merged Arabidopsis network.

For each of the three validation methods (Algebraic, ODE, RWR), pair every
merged-network test to its single-trait counterpart by test_id and run
McNemar's test on the 2x2 correct/incorrect contingency.

Outputs:
  - CSV : one row per method (for supplementary Table S10)
  - JSON: full contingency + per-test pairing detail (for downstream reuse)

Paper-scoped artifact: lives with the merged network's other figure-3 outputs.
Re-run after any re-merge or re-validation.

Usage (from repo root or this script's directory):
    python merged_arabidopsis_network/scripts/mcnemar_paired.py
    python merged_arabidopsis_network/scripts/mcnemar_paired.py --help
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from scipy.stats import binom, chi2
except ImportError:
    print("ERROR: scipy is required. pip install scipy", file=sys.stderr)
    sys.exit(2)

METHODS = {
    "Algebraic": "script_validation_results.json",
    "ODE": "ode_validation_results.json",
    "RWR": "rwr_validation_results.json",
}

DEFAULT_TRAIT_MAP = {
    "FT": "Flowering_Time",
    "HL": "Hypocotyl_Length",
    "LR": "Lateral_Root_Density",
    "PH": "Plant_Height",
    "SS": "Seed_Size",
    "SB": "Shoot_Branching",
}

COVERAGE_FLOOR = 0.95


@dataclass
class McNemarResult:
    method: str
    n_paired: int
    a_both_correct: int
    b_single_only: int
    c_merged_only: int
    d_both_wrong: int
    single_accuracy: float
    merged_accuracy: float
    delta_pct_pts: float
    statistic: float
    p_value: float
    test_type: str
    direction: str


def mcnemar(b: int, c: int) -> tuple[float, float, str]:
    n = b + c
    if n == 0:
        return 0.0, 1.0, "no_discordance"
    if n >= 25:
        stat = (abs(b - c) - 1) ** 2 / n
        p = 1 - chi2.cdf(stat, df=1)
        return stat, p, "chi2_continuity"
    k = min(b, c)
    p = 2 * binom.cdf(k, n, 0.5)
    p = min(p, 1.0)
    return float(k), p, "exact_binomial"


def load_detailed(path: Path) -> list[dict]:
    with path.open() as f:
        data = json.load(f)
    det = data.get("detailed_results")
    if det is None:
        raise ValueError(f"{path}: missing 'detailed_results'")
    return det


def strip_prefix(test_id: str, trait_map: dict[str, str]) -> tuple[str, str] | None:
    if "_" not in test_id:
        return None
    prefix, rest = test_id.split("_", 1)
    trait = trait_map.get(prefix)
    if trait is None:
        return None
    return trait, rest


def pair_method(
    method: str,
    merged_dir: Path,
    single_dir: Path,
    trait_map: dict[str, str],
) -> tuple[McNemarResult, list[dict]]:
    merged_file = merged_dir / "validation" / METHODS[method]
    merged = load_detailed(merged_file)

    single_cache: dict[str, dict[str, dict]] = {}
    for trait in trait_map.values():
        sf = single_dir / f"{trait}_network" / "validation" / METHODS[method]
        if not sf.exists():
            print(f"WARN: missing {sf}", file=sys.stderr)
            single_cache[trait] = {}
            continue
        det = load_detailed(sf)
        single_cache[trait] = {r["test_id"]: r for r in det}

    a = b = c = d = 0
    pair_rows: list[dict] = []
    unmatched = 0

    for m_row in merged:
        mid = m_row["test_id"]
        parsed = strip_prefix(mid, trait_map)
        if parsed is None:
            unmatched += 1
            continue
        trait, single_id = parsed
        s_row = single_cache.get(trait, {}).get(single_id)
        if s_row is None or s_row.get("correct") is None or m_row.get("correct") is None:
            unmatched += 1
            continue
        s_ok = bool(s_row["correct"])
        m_ok = bool(m_row["correct"])
        if s_ok and m_ok:
            cell = "a_both_correct"
            a += 1
        elif s_ok and not m_ok:
            cell = "b_single_only"
            b += 1
        elif not s_ok and m_ok:
            cell = "c_merged_only"
            c += 1
        else:
            cell = "d_both_wrong"
            d += 1
        pair_rows.append(
            {
                "method": method,
                "merged_test_id": mid,
                "single_test_id": single_id,
                "trait": trait,
                "single_correct": s_ok,
                "merged_correct": m_ok,
                "cell": cell,
            }
        )

    n_paired = a + b + c + d
    coverage = n_paired / len(merged) if merged else 0
    if coverage < COVERAGE_FLOOR:
        raise RuntimeError(
            f"{method}: paired coverage {coverage:.1%} < {COVERAGE_FLOOR:.0%} "
            f"(unmatched={unmatched} / merged={len(merged)}). "
            "Check trait_map prefixes or single-trait validation files."
        )

    single_acc = 100 * (a + b) / n_paired
    merged_acc = 100 * (a + c) / n_paired
    stat, p, test_type = mcnemar(b, c)
    if p >= 0.05:
        direction = "ns"
    elif c > b:
        direction = "merged_better"
    else:
        direction = "single_better"

    return (
        McNemarResult(
            method=method,
            n_paired=n_paired,
            a_both_correct=a,
            b_single_only=b,
            c_merged_only=c,
            d_both_wrong=d,
            single_accuracy=round(single_acc, 2),
            merged_accuracy=round(merged_acc, 2),
            delta_pct_pts=round(merged_acc - single_acc, 2),
            statistic=round(stat, 4),
            p_value=round(p, 6),
            test_type=test_type,
            direction=direction,
        ),
        pair_rows,
    )


def write_csv(path: Path, results: list[McNemarResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        w.writeheader()
        for r in results:
            w.writerow(asdict(r))


def write_json(path: Path, results: list[McNemarResult], pair_rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "test": "paired McNemar's test, single-trait vs merged",
        "comparison": "within-trait (not pleiotropic)",
        "alpha": 0.05,
        "methods": {r.method: asdict(r) for r in results},
        "pairs": pair_rows,
    }
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    here = Path(__file__).resolve().parent
    merged_root = here.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merged-dir", type=Path, default=merged_root,
                    help="merged network root (default: parent of this script)")
    ap.add_argument("--single-dir", type=Path, default=merged_root.parent / "Arabidopsis",
                    help="parent directory of the six *_network single-trait folders")
    ap.add_argument("--out-csv", type=Path, default=merged_root / "supplementary" / "Table_S11_mcnemar.csv")
    ap.add_argument("--out-json", type=Path, default=merged_root / "validation" / "mcnemar_results.json")
    ap.add_argument("--trait-map", type=Path, default=None,
                    help="optional JSON with {prefix: trait_folder_name}")
    args = ap.parse_args()

    trait_map = DEFAULT_TRAIT_MAP
    if args.trait_map:
        trait_map = json.loads(args.trait_map.read_text())

    results: list[McNemarResult] = []
    all_pairs: list[dict] = []
    for method in METHODS:
        res, pairs = pair_method(method, args.merged_dir, args.single_dir, trait_map)
        results.append(res)
        all_pairs.extend(pairs)

    write_csv(args.out_csv, results)
    write_json(args.out_json, results, all_pairs)

    print(f"{'method':10s} {'n':>4} {'single%':>8} {'merged%':>8} {'b':>4} {'c':>4} "
          f"{'stat':>8} {'p':>10} {'type':>18} {'dir':>14}")
    for r in results:
        print(f"{r.method:10s} {r.n_paired:>4} {r.single_accuracy:>8.2f} {r.merged_accuracy:>8.2f} "
              f"{r.b_single_only:>4} {r.c_merged_only:>4} {r.statistic:>8.3f} {r.p_value:>10.6f} "
              f"{r.test_type:>18s} {r.direction:>14s}")

    print(f"\nCSV : {args.out_csv}")
    print(f"JSON: {args.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
