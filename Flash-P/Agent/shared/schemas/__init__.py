"""
FLASH-P v2.0 Pydantic Schemas

Strict type definitions for every JSON file in the pipeline.
Import from here for validation and type checking.
"""

from .common import (
    Confidence,
    Direction,
    EdgeEffect,
    EvidenceEntry,
    FlashPMetadata,
    NodeType,
    PerturbationType,
    ReconciliationType,
    Verification,
)
from .literature import (
    CandidatePaper,
    CandidatePapersFile,
    CuratedEdge,
    CuratedEdgesFile,
    PerturbationDatasetFile,
    RawPerturbation,
)
from .merged import (
    MergeLogFile,
    PleiotropicPerturbation,
    PleiotropicPerturbationFile,
)
from .network import (
    AlgebraicEquation,
    AlgebraicEquationsFile,
    NetworkEdge,
    NetworkFile,
    NetworkNode,
    NodeAnnotation,
    NodeAnnotationsFile,
    ODEEquationsFile,
)
from .perturbation import (
    PerturbationModification,
    ReconciledPerturbation,
    ReconciledPerturbationFile,
)
from .provenance import (
    FileRecord,
    PipelineManifest,
    StepRecord,
)
from .refinement import (
    FixApplied,
    IterationFixesFile,
    IterationRecord,
    RefinementReportFile,
)
from .validation import (
    AccuracyMetricsFile,
    DetailedResult,
    FailureAnalysisFile,
    FailureEntry,
    MethodComparisonFile,
    ODESensitivityFile,
    RWRSensitivityFile,
    ValidationMetrics,
    ValidationResultsFile,
)

__all__ = [
    # Common
    "Confidence", "Direction", "EdgeEffect", "EvidenceEntry",
    "FlashPMetadata", "NodeType", "PerturbationType",
    "ReconciliationType", "Verification",
    # Literature
    "CandidatePaper", "CandidatePapersFile",
    "CuratedEdge", "CuratedEdgesFile",
    "RawPerturbation", "PerturbationDatasetFile",
    # Network
    "NetworkNode", "NetworkEdge", "NetworkFile",
    "AlgebraicEquation", "AlgebraicEquationsFile",
    "ODEEquationsFile",
    "NodeAnnotation", "NodeAnnotationsFile",
    # Perturbation
    "PerturbationModification", "ReconciledPerturbation",
    "ReconciledPerturbationFile",
    # Validation
    "DetailedResult", "ValidationMetrics", "ValidationResultsFile",
    "AccuracyMetricsFile", "FailureEntry", "FailureAnalysisFile",
    "MethodComparisonFile", "ODESensitivityFile", "RWRSensitivityFile",
    # Provenance
    "FileRecord", "PipelineManifest", "StepRecord",
    # Refinement
    "FixApplied", "IterationRecord", "RefinementReportFile",
    "IterationFixesFile",
    # Merged
    "MergeLogFile", "PleiotropicPerturbation", "PleiotropicPerturbationFile",
]
