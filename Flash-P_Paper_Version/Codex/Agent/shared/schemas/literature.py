"""
Schemas for Step 1 (LITERATURE REVIEW) output files.

- candidate_papers.json
- curated_edges.json
- perturbation_dataset.json
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .common import (
    Confidence, Direction, EdgeEffect, EvidenceEntry, FlashPMetadata,
    NodeType, PerturbationType,
)


# ============================================================================
# candidate_papers.json
# ============================================================================

class CandidatePaper(BaseModel):
    doi: str
    title: str
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    status: str = Field(default="read", description="read | skipped | paywalled")
    pmc_id: Optional[str] = None


class CandidatePapersMetadata(FlashPMetadata):
    total_papers: int


class CandidatePapersFile(BaseModel):
    metadata: CandidatePapersMetadata
    papers: List[CandidatePaper]


# ============================================================================
# curated_edges.json
# ============================================================================

class CuratedEdge(BaseModel):
    edge_id: str = Field(description="Unique edge identifier, e.g. E001")
    source: str
    target: str
    source_type: NodeType
    target_type: NodeType
    sign: int = Field(description="1 = activation, -1 = inhibition")
    effect: EdgeEffect
    edge_type: str = Field(
        default="",
        description="transcriptional, post-translational, transport, etc."
    )
    confidence: Confidence = Confidence.MEDIUM
    mechanism: str = ""
    in_model: bool = Field(
        default=True,
        description="Whether this edge was selected for the network model"
    )
    evidence: List[EvidenceEntry] = Field(min_length=1)


class CuratedEdgesMetadata(FlashPMetadata):
    total_edges: int
    high_confidence: Optional[int] = None
    medium_confidence: Optional[int] = None


class CuratedEdgesFile(BaseModel):
    metadata: CuratedEdgesMetadata
    edges: List[CuratedEdge]


# ============================================================================
# perturbation_dataset.json (raw, before reconciliation)
# ============================================================================

class RawPerturbation(BaseModel):
    test_id: str = Field(description="Sequential ID: T001, T002, ...")
    gene: str
    perturbation_type: PerturbationType
    expected_direction: Direction
    expected_magnitude: str = Field(
        default="",
        description="strong, moderate, slight, or empty"
    )
    evidence: List[EvidenceEntry] = Field(min_length=1)
    condition: str = Field(default="both", description="LD, SD, both, normal")
    species: str = Field(default="")


class PerturbationDatasetMetadata(FlashPMetadata):
    total_perturbations: int
    by_type: Optional[Dict[str, int]] = None
    convention: Optional[str] = None


class PerturbationDatasetFile(BaseModel):
    metadata: PerturbationDatasetMetadata
    direction_threshold: float = 0.05
    perturbations: List[RawPerturbation]
