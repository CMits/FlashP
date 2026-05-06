"""
Schemas for merged network files.

- merge_log.json
- pleiotropic_perturbation_dataset.json
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import Direction, EvidenceEntry, FlashPMetadata, PerturbationType


# ============================================================================
# merge_log.json
# ============================================================================

class SourceNetworkEntry(BaseModel):
    name: str
    phenotype_node: str
    nodes: int
    edges: int
    tests: int


class MergeLogMetadata(FlashPMetadata):
    pass


class MergeLogFile(BaseModel):
    metadata: MergeLogMetadata
    source_networks: List[SourceNetworkEntry]
    normalization_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of source-specific node names to merged names"
    )
    merged_stats: Dict[str, Any] = Field(default_factory=dict)
    shared_nodes: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of node -> list of source networks containing it"
    )


# ============================================================================
# pleiotropic_perturbation_dataset.json
# ============================================================================

class ExpectedOutcome(BaseModel):
    phenotype_node: str
    expected_direction: Direction


class PleiotropicPerturbation(BaseModel):
    test_id: str = Field(description="PLEIO_001, PLEIO_002, ...")
    gene: str
    perturbation_type: PerturbationType
    description: str = ""
    gene_modifiers: Dict[str, float] = Field(default_factory=dict)
    exogenous_supply: Dict[str, float] = Field(default_factory=dict)
    expected_outcomes: List[ExpectedOutcome]
    evidence: List[EvidenceEntry] = Field(default_factory=list)
    source_network: str = Field(
        default="",
        description="Which individual network this perturbation originated from"
    )


class PleiotropicMetadata(FlashPMetadata):
    network_type: str = "merged_pleiotropic"
    description: str = ""
    total_pleiotropic_tests: int
    total_outcome_pairs: int


class PleiotropicPerturbationFile(BaseModel):
    metadata: PleiotropicMetadata
    pleiotropic_tests: List[PleiotropicPerturbation]
