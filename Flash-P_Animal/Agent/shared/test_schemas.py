#!/usr/bin/env python3
"""
Unit tests for FLASH-P v1.0 Pydantic schemas.

Tests known-good and known-bad examples to ensure schemas enforce the rules.

Usage:
    python test_schemas.py
    python -m pytest test_schemas.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest
from pydantic import ValidationError

from schemas.common import Direction, EvidenceEntry, FlashPMetadata, NodeType
from schemas.perturbation import ReconciledPerturbation, ReconciledPerturbationFile
from schemas.network import NetworkFile, NetworkNode, NetworkEdge, NetworkMetadata
from schemas.validation import DetailedResult, ValidationResultsFile


# ============================================================================
# Common types
# ============================================================================

class TestDirection:
    def test_valid_directions(self):
        assert Direction("increased") == Direction.INCREASED
        assert Direction("decreased") == Direction.DECREASED
        assert Direction("unchanged") == Direction.UNCHANGED

    def test_invalid_direction(self):
        with pytest.raises(ValueError):
            Direction("up")


class TestNodeType:
    def test_all_types(self):
        for t in ["GENE", "HORMONE", "METABOLITE", "ENVIRONMENT",
                   "PROTEIN_COMPLEX", "REGULATORY_RNA", "PHENOTYPE", "PROCESS"]:
            assert NodeType(t).value == t

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            NodeType("UNKNOWN")


class TestEvidence:
    def test_valid_flat_evidence(self):
        ev = EvidenceEntry(
            doi="10.1234/test",
            title="Test paper",
            authors="Author A",
            year=2024,
            journal="Nature",
            evidence_sentence="The gene X increases Y.",
        )
        assert ev.doi == "10.1234/test"

    def test_minimal_evidence(self):
        ev = EvidenceEntry(doi="10.1234/test")
        assert ev.title == ""


# ============================================================================
# Reconciled perturbation — the most critical schema
# ============================================================================

class TestReconciledPerturbation:
    def test_valid_v2_perturbation(self):
        p = ReconciledPerturbation(
            test_id="T001",
            gene="MAX1",
            perturbation_type="knockout",
            expected_direction="increased",
            in_network=True,
            network_gene=["CCD7"],
            gene_modifiers={"CCD7": 0.0},
            exogenous_supply={},
            phenotype_node="Shoot_Branching",
        )
        assert p.network_gene == ["CCD7"]
        assert p.gene_modifiers == {"CCD7": 0.0}
        assert p.exogenous_supply == {}

    def test_network_gene_string_coerced_to_list(self):
        """v1.0 used bare strings — should auto-convert."""
        p = ReconciledPerturbation(
            test_id="T001", gene="PHYB", perturbation_type="knockout",
            expected_direction="increased", in_network=True,
            network_gene="PHYB",  # bare string — should become ["PHYB"]
            gene_modifiers={"PHYB": 0.0}, exogenous_supply={},
            phenotype_node="Hypocotyl_Length",
        )
        assert p.network_gene == ["PHYB"]

    def test_network_gene_none_coerced_to_empty_list(self):
        p = ReconciledPerturbation(
            test_id="T001", gene="X", perturbation_type="knockout",
            expected_direction="unchanged", in_network=False,
            network_gene=None,
            gene_modifiers={}, exogenous_supply={},
            phenotype_node="Test",
        )
        assert p.network_gene == []

    def test_gene_modifiers_scalar_rejected(self):
        """v1.0 used scalar gene_modifier — must be rejected."""
        with pytest.raises(ValidationError, match="gene_modifiers must be a dict"):
            ReconciledPerturbation(
                test_id="T001", gene="PHYB", perturbation_type="knockout",
                expected_direction="increased", in_network=True,
                network_gene=["PHYB"],
                gene_modifiers=0.0,  # WRONG — scalar
                exogenous_supply={},
                phenotype_node="Test",
            )

    def test_gene_modifiers_none_coerced_to_empty_dict(self):
        p = ReconciledPerturbation(
            test_id="T001", gene="X", perturbation_type="control",
            expected_direction="unchanged", in_network=False,
            network_gene=[], gene_modifiers=None,
            exogenous_supply={}, phenotype_node="Test",
        )
        assert p.gene_modifiers == {}

    def test_exogenous_nested_format_rejected(self):
        """v1.0 used nested {node, value} — must be rejected."""
        with pytest.raises(ValidationError, match="flat dict"):
            ReconciledPerturbation(
                test_id="T001", gene="GA", perturbation_type="treatment",
                expected_direction="decreased", in_network=True,
                network_gene=["Gibberellin"],
                gene_modifiers={},
                exogenous_supply={"node": "Gibberellin", "value": 1.0},  # WRONG
                phenotype_node="Test",
            )

    def test_exogenous_none_coerced_to_empty_dict(self):
        p = ReconciledPerturbation(
            test_id="T001", gene="X", perturbation_type="knockout",
            expected_direction="unchanged", in_network=False,
            network_gene=[], gene_modifiers={},
            exogenous_supply=None, phenotype_node="Test",
        )
        assert p.exogenous_supply == {}

    def test_missing_phenotype_node_rejected(self):
        with pytest.raises(ValidationError):
            ReconciledPerturbation(
                test_id="T001", gene="X", perturbation_type="knockout",
                expected_direction="unchanged", in_network=True,
                network_gene=["X"], gene_modifiers={"X": 0.0},
                exogenous_supply={},
                # phenotype_node missing!
            )


# ============================================================================
# Network
# ============================================================================

class TestNetworkFile:
    def test_valid_network(self):
        nf = NetworkFile(
            metadata=NetworkMetadata(
                flash_p_version="1.0", phenotype="test",
                species="Test species", created="2026-01-01",
                total_nodes=2, total_edges=1,
            ),
            nodes=[
                NetworkNode(id="A", type="GENE"),
                NetworkNode(id="B", type="PHENOTYPE"),
            ],
            edges=[
                NetworkEdge(source="A", target="B", sign=1),
            ],
        )
        assert len(nf.nodes) == 2
        assert nf.edges[0].sign == 1

    def test_invalid_sign(self):
        """sign must be int, not string."""
        with pytest.raises(ValidationError):
            NetworkEdge(source="A", target="B", sign="positive")


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    # Simple runner without pytest
    test_classes = [
        TestDirection, TestNodeType, TestEvidence,
        TestReconciledPerturbation, TestNetworkFile,
    ]

    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if not method_name.startswith("test_"):
                continue
            method = getattr(instance, method_name)
            try:
                method()
                passed += 1
                print(f"  PASS: {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                print(f"  FAIL: {cls.__name__}.{method_name}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
