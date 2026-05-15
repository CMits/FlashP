"""
Schemas for Step 3 (PERTURBATION RECONCILIATION) output files.

- reconciled_perturbation_dataset.json

THIS IS THE MOST CRITICAL SCHEMA — it caused the most inconsistencies in v1.0.
Rules enforced here:
  - network_gene: ALWAYS List[str], never a bare string
  - gene_modifiers: ALWAYS Dict[str, float], never a scalar, never None
  - exogenous_supply: ALWAYS Dict[str, float], never nested {node, value}, never None
  - test_id: sequential format T001, T002, ...
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .common import (
    Direction, EvidenceEntry, FlashPMetadata, PerturbationType,
    ReconciliationType,
)


class PerturbationModification(BaseModel):
    """One atomic modification in a perturbation experiment."""
    node: str = Field(description="Network node being modified")
    modifier_type: Literal["gene_modifier", "exogenous_supply"]
    value: float = Field(description="0.0=KO, 0.5=KD, 1.0=WT, 2.0=OE for gene_modifier; 1.0 for exogenous")


class ReconciledPerturbation(BaseModel):
    """
    A single perturbation test mapped to network nodes.

    STRICT RULES (v1.0):
    - network_gene must be List[str], e.g. ["PHYB"] not "PHYB"
    - gene_modifiers must be Dict[str, float], e.g. {"PHYB": 0.0} not 0.0
    - exogenous_supply must be Dict[str, float], e.g. {"ABI5": 1.0} not {"node": "ABI5", "value": 1.0}
    """
    test_id: str = Field(description="Sequential ID: T001, T002, ...")
    gene: str = Field(description="Original gene name from literature")
    perturbation_type: PerturbationType
    expected_direction: Direction
    in_network: bool = Field(
        description="Whether the gene maps to a node in the network"
    )
    # THE CRITICAL FIELDS — must be these exact types
    network_gene: List[str] = Field(
        default_factory=list,
        description="Network node(s) actually perturbed. ALWAYS a list."
    )
    gene_modifiers: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of network node -> modifier value. ALWAYS a dict."
    )
    exogenous_supply: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of network node -> supply value. ALWAYS a flat dict."
    )
    perturbations: List[PerturbationModification] = Field(
        default_factory=list,
        description="Detailed list of all modifications applied"
    )
    notes: str = Field(
        default="",
        description="Reconciliation notes, composite handling explanation"
    )
    evidence: List[EvidenceEntry] = Field(default_factory=list)
    phenotype_node: str = Field(description="Target phenotype node in the network")
    comparison_baseline: str = Field(
        default="WT",
        description="WT for most tests, mutant_alone for rescue experiments"
    )
    condition: str = Field(default="both", description="LD, SD, both, normal")
    reconciliation_type: Optional[ReconciliationType] = None
    reconciliation_note: str = Field(default="")
    expected_magnitude: str = Field(default="")
    species: str = Field(default="")

    @field_validator("network_gene", mode="before")
    @classmethod
    def coerce_network_gene_to_list(cls, v):
        """Ensure network_gene is always a list, even if given as string."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("gene_modifiers", mode="before")
    @classmethod
    def coerce_gene_modifiers_to_dict(cls, v):
        """Reject scalar gene_modifier; must be a dict."""
        if v is None:
            return {}
        if isinstance(v, (int, float)):
            raise ValueError(
                f"gene_modifiers must be a dict, got scalar {v}. "
                f"Use {{'NODE_NAME': {v}}} instead."
            )
        return v

    @field_validator("exogenous_supply", mode="before")
    @classmethod
    def coerce_exogenous_supply(cls, v):
        """Reject nested {node, value} format; must be flat dict."""
        if v is None:
            return {}
        if isinstance(v, dict) and "node" in v:
            raise ValueError(
                f"exogenous_supply must be a flat dict like {{'ABI5': 1.0}}, "
                f"not nested {v}"
            )
        return v


class ReconciledPerturbationMetadata(FlashPMetadata):
    total_tests: int
    in_network: int = Field(description="Number of tests with in_network=true")
    not_in_network: int = Field(description="Number of tests with in_network=false")
    phenotype_node: str = Field(default="")
    convention: Optional[str] = None


class ReconciledPerturbationFile(BaseModel):
    metadata: ReconciledPerturbationMetadata
    direction_threshold: float = 0.05
    perturbations: List[ReconciledPerturbation]
