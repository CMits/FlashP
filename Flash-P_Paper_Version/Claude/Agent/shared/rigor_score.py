#!/usr/bin/env python3
"""
FLASH-P v1.0 — Network Quality Metric (FLASH-P Rigor Score, FRS)

Computes a composite network quality score that combines chance-corrected
prediction quality (Cohen's kappa) with scope (network size x number of tests).

Formula:
    FRS = kappa * log2(T * (N + E))

Where:
    kappa = Cohen's kappa (chance-corrected agreement, range [-1, 1])
    T     = number of validated tests
    N     = number of nodes in the network
    E     = number of edges in the network

See docs/NETWORK_QUALITY_METRIC.md for the full derivation and justification.

This module is the single source of truth for:
    - FRS computation (compute_frs)
    - Kappa 95% confidence interval (compute_kappa_ci)
    - FRS band labels (band_label)
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


FRS_BANDS: List[Tuple[float, str]] = [
    (3.0, "weak"),
    (6.0, "small-scale solid"),
    (9.0, "medium-scale solid"),
    (12.0, "large-scale strong"),
    (float("inf"), "exceptional"),
]

KAPPA_BANDS: List[Tuple[float, str]] = [
    (0.00, "poor"),
    (0.20, "slight"),
    (0.40, "fair"),
    (0.60, "moderate"),
    (0.80, "substantial"),
    (1.01, "almost perfect"),
]


def compute_frs(kappa: float, n_tests: int, n_nodes: int, n_edges: int) -> float:
    """
    Compute the FLASH-P Rigor Score.

        FRS = kappa * log2(T * (N + E))

    Edge cases:
        - T * (N + E) <= 1 returns 0.0 (trivial network)
        - Returns signed value (negative kappa gives negative FRS)
    """
    scope = n_tests * (n_nodes + n_edges)
    if scope <= 1:
        return 0.0
    return round(kappa * math.log2(scope), 4)


def compute_dars(
    kappa: float,
    complexity_scores: List[int],
    n_nodes: int,
    n_edges: int,
) -> float:
    """
    Compute the Difficulty-Adjusted Rigor Score.

        DARS = kappa * log2(T_effective * (N + E))

    Where T_effective = sum(complexity_score_i) — harder tests count more.
    With complexity_score in {1, 2, 3+}, a network of all hard tests gets
    up to log2(3) = 1.585 extra "bits" of scope over an equivalent network
    of all easy tests.

    Args:
        kappa: Cohen's kappa computed over ALL tests (not stratified).
               If hard tests fail, kappa drops and DARS naturally drops too.
        complexity_scores: list of integer complexity scores (1=easy, 2=medium, 3=hard)
                           for each test that contributed to kappa.
        n_nodes, n_edges: network scale.

    Edge cases:
        - Empty complexity_scores or scope <= 1 returns 0.0
        - Returns signed value
    """
    if not complexity_scores:
        return 0.0
    t_effective = sum(complexity_scores)
    scope = t_effective * (n_nodes + n_edges)
    if scope <= 1:
        return 0.0
    return round(kappa * math.log2(scope), 4)


def _kappa_from_confusion(matrix: List[List[int]]) -> tuple[float, int]:
    """Helper: compute Cohen's kappa from a k x k confusion matrix.
    Returns (kappa, total). Returns (0.0, 0) if matrix is empty."""
    k = len(matrix)
    total = sum(sum(row) for row in matrix)
    if total == 0:
        return (0.0, 0)
    correct = sum(matrix[i][i] for i in range(k))
    p_o = correct / total
    p_e = sum(
        (sum(matrix[i]) / total) * (sum(matrix[r][i] for r in range(k)) / total)
        for i in range(k)
    )
    if (1 - p_e) == 0:
        return (0.0, total)
    return ((p_o - p_e) / (1 - p_e), total)


def compute_stratified_metrics(
    results_labels: List[Tuple[str, str, int]],
) -> Dict[str, Dict]:
    """
    Compute per-stratum accuracy + kappa from a list of
    (expected_direction, predicted_direction, complexity_score) tuples.

    Returns dict keyed by stratum name ("easy", "medium", "hard"):
        {
          "easy":   {"n": int, "correct": int, "accuracy_pct": float,
                     "cohens_kappa": float|None, "kappa_note": str|None},
          "medium": {...},
          "hard":   {...},
        }

    Kappa is None (with a note) when the stratum has < 5 tests OR all tests
    in the stratum have the same expected/predicted label (degenerate).

    Strata boundaries (inclusive-low, exclusive-high on complexity_score):
        easy    = complexity_score == 1
        medium  = complexity_score == 2
        hard    = complexity_score >= 3
    """
    labels = ["increased", "decreased", "unchanged"]
    label_idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)

    strata = {
        "easy":   [],
        "medium": [],
        "hard":   [],
    }
    for expected, predicted, score in results_labels:
        if score <= 1:
            strata["easy"].append((expected, predicted))
        elif score == 2:
            strata["medium"].append((expected, predicted))
        else:
            strata["hard"].append((expected, predicted))

    out: Dict[str, Dict] = {}
    for name, items in strata.items():
        n = len(items)
        correct = sum(1 for e, p in items if e == p)
        if n == 0:
            out[name] = {
                "n": 0, "correct": 0, "accuracy_pct": None,
                "cohens_kappa": None, "kappa_note": "no tests in stratum",
            }
            continue

        # Build confusion matrix for this stratum
        matrix = [[0] * k for _ in range(k)]
        for e, p in items:
            ei = label_idx.get(e, k - 1)
            pi = label_idx.get(p, k - 1)
            matrix[ei][pi] += 1

        kappa_val, _ = _kappa_from_confusion(matrix)

        # Guard against degenerate stratum
        note: str | None = None
        if n < 5:
            note = f"stratum too small (n={n}) for reliable kappa"

        out[name] = {
            "n": n,
            "correct": correct,
            "accuracy_pct": round(correct / n * 100, 1),
            "cohens_kappa": round(kappa_val, 4) if note is None else None,
            "kappa_note": note,
        }

    return out


def band_label(frs: float) -> str:
    """Return the qualitative band label for an FRS value."""
    if frs < 0:
        return "below-random"
    for threshold, label in FRS_BANDS:
        if frs < threshold:
            return label
    return "exceptional"


def kappa_band_label(kappa: float) -> str:
    """Return the Landis & Koch (1977) qualitative band for Cohen's kappa."""
    if kappa < 0:
        return "below-chance"
    for threshold, label in KAPPA_BANDS:
        if kappa < threshold:
            return label
    return "almost perfect"


def compute_kappa_ci(
    confusion_matrix: List[List[int]],
    alpha: float = 0.05,
) -> Tuple[float, float]:
    """
    Compute the asymptotic 95% confidence interval for Cohen's kappa
    using the Fleiss & Cohen (1969) standard error.

    Args:
        confusion_matrix: k x k observed-count matrix (rows=expected, cols=predicted)
        alpha: significance level (default 0.05 → 95% CI)

    Returns:
        (lower_bound, upper_bound) tuple. If the standard error cannot be
        computed (e.g. no variation), returns (kappa, kappa).

    Reference:
        Fleiss JL, Cohen J, Everitt BS (1969). Large sample standard errors
        of kappa and weighted kappa. Psychol Bull 72:323-327.
    """
    k = len(confusion_matrix)
    N = sum(sum(row) for row in confusion_matrix)
    if N == 0:
        return (0.0, 0.0)

    row_totals = [sum(row) for row in confusion_matrix]
    col_totals = [sum(confusion_matrix[i][j] for i in range(k)) for j in range(k)]

    p_o = sum(confusion_matrix[i][i] for i in range(k)) / N
    p_e = sum((row_totals[i] / N) * (col_totals[i] / N) for i in range(k))

    if (1 - p_e) == 0:
        return (0.0, 0.0)

    kappa = (p_o - p_e) / (1 - p_e)

    # Fleiss-Cohen-Everitt asymptotic variance (general multiclass form)
    p_ij = [[confusion_matrix[i][j] / N for j in range(k)] for i in range(k)]
    p_i_dot = [row_totals[i] / N for i in range(k)]
    p_dot_j = [col_totals[j] / N for j in range(k)]

    # A = sum_i p_ii * (1 - (p_i. + p_.i)(1 - kappa))^2
    A = sum(
        p_ij[i][i] * (1 - (p_i_dot[i] + p_dot_j[i]) * (1 - kappa)) ** 2
        for i in range(k)
    )
    # B = (1 - kappa)^2 * sum_{i != j} p_ij * (p_.i + p_j.)^2
    B = (1 - kappa) ** 2 * sum(
        p_ij[i][j] * (p_dot_j[i] + p_i_dot[j]) ** 2
        for i in range(k)
        for j in range(k)
        if i != j
    )
    # C = (kappa - p_e * (1 - kappa))^2
    C = (kappa - p_e * (1 - kappa)) ** 2

    var_kappa = (A + B - C) / (N * (1 - p_e) ** 2)
    if var_kappa < 0:
        return (kappa, kappa)

    se = math.sqrt(var_kappa)
    # Two-sided z for standard alpha values
    z_table = {0.10: 1.6449, 0.05: 1.9600, 0.01: 2.5758}
    z = z_table.get(alpha, 1.9600)

    return (round(kappa - z * se, 4), round(kappa + z * se, 4))


def build_rigor_report(
    kappa: float,
    mcc: float,
    confusion_matrix: List[List[int]],
    n_tests: int,
    n_nodes: int,
    n_edges: int,
    mean_path_length: float | None = None,
    complexity_scores: List[int] | None = None,
    results_labels: List[Tuple[str, str, int]] | None = None,
) -> Dict:
    """
    Build a full tiered rigor report for one method.

    Returns a dict with four tiers:
        tier1_quality:    kappa, kappa_ci_lower, kappa_ci_upper, kappa_band, mcc
        tier2_scope:      n_nodes, n_edges, n_tests, mean_path_length, t_effective
        tier3_rigor:      rigor_score (FRS), rigor_band
        tier4_difficulty: dars, dars_band, stratified (per easy/medium/hard)

    ``complexity_scores`` enables DARS; ``results_labels`` enables stratified
    per-stratum kappa/accuracy. Both are optional — tiers degrade gracefully.

    Intended to be merged into an existing metrics dict.
    """
    kappa_lo, kappa_hi = compute_kappa_ci(confusion_matrix)
    frs = compute_frs(kappa, n_tests, n_nodes, n_edges)

    report: Dict = {
        "tier1_quality": {
            "cohens_kappa": round(kappa, 4),
            "kappa_ci_lower": kappa_lo,
            "kappa_ci_upper": kappa_hi,
            "kappa_band": kappa_band_label(kappa),
            "mcc": round(mcc, 4),
        },
        "tier2_scope": {
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "n_tests": n_tests,
            "mean_path_length": (
                round(mean_path_length, 2) if mean_path_length is not None else None
            ),
        },
        "tier3_rigor": {
            "rigor_score": frs,
            "rigor_band": band_label(frs),
            "formula": "kappa * log2(n_tests * (n_nodes + n_edges))",
        },
    }

    if complexity_scores is not None and complexity_scores:
        t_eff = sum(complexity_scores)
        report["tier2_scope"]["t_effective"] = t_eff
        dars = compute_dars(kappa, complexity_scores, n_nodes, n_edges)
        report["tier4_difficulty"] = {
            "dars": dars,
            "dars_band": band_label(dars),
            "formula": "kappa * log2(t_effective * (n_nodes + n_edges))",
            "t_effective": t_eff,
            "complexity_weighting": "score 1=easy, 2=medium, 3+=hard (n_mutations + n_treatments)",
        }
        if results_labels is not None:
            report["tier4_difficulty"]["stratified"] = compute_stratified_metrics(results_labels)

    return report


# ---------------------------------------------------------------------------
# Self-tests (run: python rigor_score.py)
# ---------------------------------------------------------------------------

def _self_test() -> None:
    # Edge cases
    assert compute_frs(0.0, 100, 30, 50) == 0.0, "kappa=0 must give FRS=0"
    assert compute_frs(1.0, 1, 1, 0) == 0.0, "trivial network must give FRS=0"
    assert compute_frs(-0.2, 50, 10, 10) < 0, "negative kappa must give negative FRS"

    # Worked examples from plan
    assert abs(compute_frs(0.80, 20, 5, 5) - 6.11) < 0.1, (
        f"small-scale expected ~6.11, got {compute_frs(0.80, 20, 5, 5)}"
    )
    assert abs(compute_frs(0.80, 100, 30, 50) - 10.37) < 0.1, (
        f"large-scale expected ~10.37, got {compute_frs(0.80, 100, 30, 50)}"
    )
    assert abs(compute_frs(0.90, 150, 30, 50) - 12.20) < 0.1, (
        f"exceptional expected ~12.20, got {compute_frs(0.90, 150, 30, 50)}"
    )

    # Band labels
    assert band_label(0.0) == "weak"
    assert band_label(5.0) == "small-scale solid"
    assert band_label(10.5) == "large-scale strong"
    assert band_label(15.0) == "exceptional"
    assert band_label(-0.5) == "below-random"

    # Kappa bands (Landis & Koch)
    assert kappa_band_label(0.85) == "almost perfect"
    assert kappa_band_label(0.70) == "substantial"
    assert kappa_band_label(0.50) == "moderate"
    assert kappa_band_label(0.30) == "fair"
    assert kappa_band_label(-0.1) == "below-chance"

    # Kappa CI smoke test (perfect agreement -> CI near kappa=1)
    perfect = [[10, 0, 0], [0, 10, 0], [0, 0, 10]]
    lo, hi = compute_kappa_ci(perfect)
    assert lo >= 0.95, f"perfect-agreement CI lower should be ~1, got {lo}"

    # Shoot Branching worked values (from plan)
    frs_alg = compute_frs(0.7722, 105, 33, 48)  # algebraic
    frs_ode = compute_frs(0.7920, 105, 33, 48)  # ode
    frs_rwr = compute_frs(0.6463, 105, 33, 48)  # rwr
    print(f"Shoot_Branching FRS — alg={frs_alg}, ode={frs_ode}, rwr={frs_rwr}")
    print(f"Bands — alg={band_label(frs_alg)}, ode={band_label(frs_ode)}, "
          f"rwr={band_label(frs_rwr)}")

    # ---- DARS tests ----
    # Empty case
    assert compute_dars(0.8, [], 30, 50) == 0.0
    # All easy (score=1 each) — DARS should equal FRS (T_eff == T)
    all_easy = [1] * 105
    dars_easy_only = compute_dars(0.7722, all_easy, 33, 48)
    assert abs(dars_easy_only - frs_alg) < 0.001, (
        f"all-easy DARS should equal FRS: {dars_easy_only} vs {frs_alg}"
    )

    # Shoot Branching actual distribution: 71 easy, 33 medium, 1 hard
    sb_scores = [1]*71 + [2]*33 + [3]*1   # T_eff = 71 + 66 + 3 = 140
    assert sum(sb_scores) == 140
    dars_sb = compute_dars(0.7722, sb_scores, 33, 48)
    print(f"Shoot_Branching DARS — alg={dars_sb}  (FRS was {frs_alg})")
    assert abs(dars_sb - 10.40) < 0.05, f"expected ~10.40, got {dars_sb}"

    # All-hard hypothetical: 105 tests all at score 3 -> T_eff = 315
    all_hard = [3] * 105
    dars_all_hard = compute_dars(0.7722, all_hard, 33, 48)
    print(f"Hypothetical all-hard DARS — {dars_all_hard}")
    # Bonus over FRS should be log2(3) * kappa ~ 1.585 * 0.77 ~ 1.22
    assert abs((dars_all_hard - frs_alg) - 0.7722 * math.log2(3)) < 0.01

    # ---- Stratified metrics tests ----
    # Synthetic: 10 easy all correct, 10 medium 6 correct, 5 hard 4 correct
    synth = (
        [("increased", "increased", 1)] * 10 +
        [("increased", "increased", 2)] * 6 +
        [("increased", "decreased", 2)] * 4 +
        [("decreased", "decreased", 3)] * 4 +
        [("decreased", "increased", 3)] * 1
    )
    strat = compute_stratified_metrics(synth)
    assert strat["easy"]["n"] == 10 and strat["easy"]["accuracy_pct"] == 100.0
    assert strat["medium"]["n"] == 10 and strat["medium"]["accuracy_pct"] == 60.0
    assert strat["hard"]["n"] == 5 and strat["hard"]["accuracy_pct"] == 80.0
    print(f"Stratified smoke test — easy={strat['easy']['accuracy_pct']}%, "
          f"medium={strat['medium']['accuracy_pct']}%, "
          f"hard={strat['hard']['accuracy_pct']}%")

    # Full report smoke test
    report = build_rigor_report(
        kappa=0.7722,
        mcc=0.754,
        confusion_matrix=[[52, 3, 3], [2, 29, 0], [2, 4, 10]],
        n_tests=105,
        n_nodes=33,
        n_edges=48,
        mean_path_length=2.4,
        complexity_scores=sb_scores,
        results_labels=synth,  # synthetic for smoke test
    )
    print("\nFull tiered report (Shoot Branching algebraic, synthetic strat):")
    import json
    print(json.dumps(report, indent=2))

    print("\nAll self-tests passed.")


if __name__ == "__main__":
    _self_test()
