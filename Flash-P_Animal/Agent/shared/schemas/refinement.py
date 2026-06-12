"""
Schemas for Step 5 (REFINEMENT) output files.

- refinement_report.json
- iteration_N/fixes_applied.json
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import FlashPMetadata


class FixApplied(BaseModel):
    """One targeted fix applied during refinement."""
    iteration: int
    action: str = Field(
        description="edge_removal, edge_addition, perturbation_encoding, "
                    "test_exclusion, sign_change"
    )
    description: str
    reason: str
    biological_justification: str = ""
    source: str = Field(default="", description="Source node (for edge changes)")
    target: str = Field(default="", description="Target node (for edge changes)")
    sign: Optional[int] = None
    modifier_type: Optional[str] = None
    value: Optional[float] = None


class IterationRecord(BaseModel):
    """Summary of one refinement iteration."""
    iteration: int
    description: str = ""
    algebraic_accuracy: float
    ode_accuracy: float
    rwr_accuracy: float
    failures: List[str] = Field(default_factory=list)
    fixes_applied: int = 0
    edges_added: int = 0
    edges_removed: int = 0


class BestModel(BaseModel):
    location: str = ""
    algebraic_accuracy: float
    ode_accuracy: float
    rwr_accuracy: float
    total_nodes: int = 0
    total_edges: int = 0


class RefinementReportMetadata(FlashPMetadata):
    iterations_run: int
    best_iteration: int


class RefinementReportFile(BaseModel):
    metadata: RefinementReportMetadata
    iteration_history: List[IterationRecord]
    fixes_applied: List[FixApplied]
    best_model: BestModel


class IterationFixesFile(BaseModel):
    """Per-iteration fixes file (iteration_N/fixes_applied.json)."""
    iteration: int
    date: str
    fixes: List[FixApplied]
    results: Dict[str, Any] = Field(default_factory=dict)
