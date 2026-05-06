"""
Schemas for Step 2 (BUILDER) output files.

- network.json
- algebraic_equations.json
- ode_equations.json
- node_annotations.json
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .common import EvidenceEntry, FlashPMetadata, NodeType


# ============================================================================
# network.json
# ============================================================================

class NetworkNode(BaseModel):
    id: str = Field(description="Node identifier, e.g. FLC, Auxin, Flowering_Time")
    type: NodeType
    full_name: str = Field(default="", description="Full descriptive name")
    description: str = Field(default="", description="Biological description")
    is_source: Optional[bool] = Field(
        default=None,
        description="True for nodes with no regulators (environment, constitutive)"
    )


class NetworkEdge(BaseModel):
    source: str
    target: str
    sign: int = Field(description="1 = activation, -1 = inhibition")
    edge_id: str = Field(default="", description="Edge identifier, e.g. N001")
    effect: str = Field(default="", description="activation, repression, inhibition")
    mechanism: str = Field(default="", description="Biological mechanism")
    evidence: Optional[List[EvidenceEntry]] = None


class NetworkMetadata(FlashPMetadata):
    total_nodes: int
    total_edges: int
    source_nodes: Optional[int] = None
    source_percentage: Optional[float] = None


class NetworkFile(BaseModel):
    metadata: NetworkMetadata
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]


# ============================================================================
# algebraic_equations.json
# ============================================================================

class AlgebraicParameters(BaseModel):
    epsilon: float = 0.1
    K: float = 10.0
    activator_floor: float = 0.01
    damping: float = 0.7
    direction_threshold: float = 0.05
    max_iterations: int = 100
    convergence_tolerance: float = 0.0001


class AlgebraicEquation(BaseModel):
    node: str
    type: NodeType
    is_source: bool = False
    activators: List[str] = Field(default_factory=list)
    inhibitors: List[str] = Field(default_factory=list)
    formula: str = Field(description="The algebraic equation formula string")


class AlgebraicEquationsMetadata(FlashPMetadata):
    total_equations: int


class AlgebraicEquationsFile(BaseModel):
    metadata: AlgebraicEquationsMetadata
    parameters: AlgebraicParameters
    equations: List[AlgebraicEquation]


# ============================================================================
# ode_equations.json
# ============================================================================

class ODEEquation(BaseModel):
    node: str
    activators: List[str] = Field(default_factory=list)
    inhibitors: List[str] = Field(default_factory=list)
    formula: str = Field(description="ODE Hill function formula string")


class ODEEquationsMetadata(BaseModel):
    method: str = "ODE (Hill Functions)"
    K: float = 1.0
    n: int = 2
    accuracy: Optional[float] = None
    hill_activation_formula: str = ""
    hill_inhibition_formula: str = ""
    dt: float = 0.01
    max_time: float = 50.0
    convergence_tolerance: float = 0.001
    direction_threshold: float = 0.05
    activator_floor: float = 0.01


class ODEEquationsFile(BaseModel):
    metadata: ODEEquationsMetadata
    equations: List[ODEEquation]


# ============================================================================
# node_annotations.json
# ============================================================================

class NodeAnnotation(BaseModel):
    node: str
    full_name: str = ""
    type: NodeType
    description: str = ""
    in_degree: int = 0
    out_degree: int = 0
    total_degree: int = 0
    is_source: bool = False
    n_activators: int = 0
    n_inhibitors: int = 0


class NodeAnnotationsMetadata(FlashPMetadata):
    total_nodes: int


class NodeAnnotationsFile(BaseModel):
    metadata: NodeAnnotationsMetadata
    annotations: List[NodeAnnotation]
