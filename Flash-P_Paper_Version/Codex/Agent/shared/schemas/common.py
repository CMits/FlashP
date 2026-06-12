"""
Common types shared across all FLASH-P v1.0 schemas.

Every JSON file in the pipeline uses these base types to ensure
consistency across all 12+ networks and all pipeline steps.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums — strict allowed values
# ============================================================================

class NodeType(str, Enum):
    GENE = "GENE"
    HORMONE = "HORMONE"
    METABOLITE = "METABOLITE"
    ENVIRONMENT = "ENVIRONMENT"
    PROTEIN_COMPLEX = "PROTEIN_COMPLEX"
    REGULATORY_RNA = "REGULATORY_RNA"
    PHENOTYPE = "PHENOTYPE"
    PROCESS = "PROCESS"


class Direction(str, Enum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"


class PerturbationType(str, Enum):
    KNOCKOUT = "knockout"
    OVEREXPRESSION = "overexpression"
    KNOCKDOWN = "knockdown"
    GAIN_OF_FUNCTION = "gain_of_function"
    LOSS_OF_FUNCTION = "loss_of_function"
    HETEROZYGOUS = "heterozygous"
    KNOCKOUT_CRISPR = "knockout_CRISPR"
    PHOSPHO_DEAD_MUTANT = "phospho_dead_mutant"
    KNOCKOUT_ARP6 = "knockout_arp6"
    # Multi-gene
    DOUBLE_KNOCKOUT = "double_knockout"
    DOUBLE_MUTANT = "double_mutant"
    TRIPLE_KNOCKOUT = "triple_knockout"
    QUADRUPLE_KNOCKOUT = "quadruple_knockout"
    QUINTUPLE_KNOCKOUT = "quintuple_knockout"
    # Gene + treatment combos
    KNOCKOUT_PLUS_TREATMENT = "knockout_plus_treatment"
    KNOCKOUT_PLUS_GR24 = "knockout_plus_GR24"
    GAIN_OF_FUNCTION_PLUS_TREATMENT = "gain_of_function_plus_treatment"
    GAIN_OF_FUNCTION_PLUS_GR24 = "gain_of_function_plus_GR24"
    LOSS_OF_FUNCTION_PLUS_GR24 = "loss_of_function_plus_GR24"
    MIR156_OE_PLUS_GR24 = "miR156_OE_plus_GR24"
    # Rescue
    RESCUE = "rescue"
    RESCUE_EXPERIMENT = "rescue_experiment"
    # Background epistasis
    KNOCKDOWN_IN_D3_BACKGROUND = "knockdown_in_d3_background"
    KNOCKDOWN_IN_D14_BACKGROUND = "knockdown_in_d14_background"
    FC1_OE_IN_D3_BACKGROUND = "FC1_OE_in_d3_background"
    # Combined / epistasis
    COMBINED = "combined"
    COMBINED_TRANSGENIC = "combined_transgenic"
    EPISTASIS = "epistasis"
    # Pure treatments (WT + something)
    TREATMENT = "treatment"
    EXOGENOUS_TREATMENT = "exogenous_treatment"
    EXOGENOUS_SL = "exogenous_SL"
    CHEMICAL_TREATMENT = "chemical_treatment"
    ACC_TREATMENT = "acc_treatment"
    HIGH_NITRATE_TREATMENT = "high_nitrate_treatment"
    DROUGHT_STRESS = "drought_stress"
    INHIBITOR_PBZ = "inhibitor_PBZ"
    ENVIRONMENTAL = "environmental"
    # Controls
    CONTROL = "control"
    NEGATIVE_CONTROL = "negative_control"


class EdgeEffect(str, Enum):
    ACTIVATION = "activation"
    INHIBITION = "inhibition"
    REPRESSION = "repression"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Verification(str, Enum):
    FULL_TEXT_READ = "full_text_read"
    ABSTRACT_READ = "abstract_read"
    PUBMED_CROSSCHECKED = "pubmed_crosschecked"


class ReconciliationType(str, Enum):
    EXACT_MATCH = "exact_match"
    CASE_INSENSITIVE = "case_insensitive"
    FAMILY_MEMBER = "family_member"
    COMPOSITE_COLLAPSE = "composite_collapse"
    COMPOSITE_MEMBER = "composite_member"
    TREATMENT_ANALOG = "treatment_analog"
    MECHANISM_MAPPING = "mechanism_mapping"
    NOT_IN_NETWORK = "not_in_network"
    CONTROL = "control"


# ============================================================================
# Shared models
# ============================================================================

class FlashPMetadata(BaseModel):
    """Metadata block present in every pipeline output file."""
    flash_p_version: str = Field(description="Pipeline version, e.g. '1.0'")
    phenotype: str = Field(description="Target phenotype, e.g. 'flowering_time'")
    species: str = Field(description="Species name, e.g. 'Arabidopsis thaliana'")
    created: str = Field(description="Creation date YYYY-MM-DD")


class EvidenceEntry(BaseModel):
    """
    Flat evidence structure — used everywhere.
    NEVER nested (no 'source' sub-object).
    """
    doi: str = Field(description="DOI of the source paper")
    title: str = Field(default="", description="Paper title")
    authors: str = Field(default="", description="Author list")
    year: Optional[int] = Field(default=None, description="Publication year")
    journal: str = Field(default="", description="Journal name")
    evidence_sentence: str = Field(
        default="",
        description="Exact quote from paper supporting this claim"
    )
    claim: str = Field(default="", description="What this evidence supports")
    verification: Optional[Verification] = Field(
        default=None,
        description="How the paper was read"
    )
    full_text_read: Optional[bool] = Field(
        default=None,
        description="Whether full text was read"
    )
