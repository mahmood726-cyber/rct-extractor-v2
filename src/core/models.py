"""
Core data models for RCT extraction with strict validation.
All extracted data must conform to these schemas.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal, Union
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS
# ============================================================

class EndpointType(str, Enum):
    BINARY = "binary"
    TIME_TO_EVENT = "tte"
    CONTINUOUS = "continuous"
    UNKNOWN = "unknown"


class AnalysisPopulation(str, Enum):
    ITT = "ITT"
    MODIFIED_ITT = "mITT"
    PER_PROTOCOL = "PP"
    SAFETY = "safety"
    UNCLEAR = "unclear"


class TableType(str, Enum):
    BASELINE = "baseline"
    OUTCOMES = "outcomes"
    SAFETY = "safety"
    SUBGROUP = "subgroup"
    FLOWCHART = "flowchart"
    OTHER = "other"


class ReviewSeverity(str, Enum):
    ERROR = "error"          # Must fix before use
    WARNING = "warning"      # Should review but may be usable
    INFO = "info"           # Minor issue, likely acceptable


class ExtractionConfidence(str, Enum):
    HIGH = "high"           # All validators pass, both passes agree
    MEDIUM = "medium"       # Minor flags, single pass confident
    LOW = "low"             # Significant uncertainty
    REVIEW_REQUIRED = "review_required"  # Cannot use without human review


# ============================================================
# PROVENANCE - Non-negotiable for every extracted value
# ============================================================

class BoundingBox(BaseModel):
    """Coordinates in PDF page space (points from bottom-left)"""
    x1: float
    y1: float
    x2: float
    y2: float

    @field_validator('x2')
    @classmethod
    def x2_greater_than_x1(cls, v, info):
        if 'x1' in info.data and v < info.data['x1']:
            raise ValueError('x2 must be >= x1')
        return v


class TextSpan(BaseModel):
    """Character offsets in extracted text"""
    start: int
    end: int
    text: str


class Provenance(BaseModel):
    """
    REQUIRED for every extracted datum.
    This is the 'receipt' - without it, data is not auditable.
    """
    pdf_file: str = Field(..., description="Source PDF filename")
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box on page")
    text_span: Optional[TextSpan] = Field(None, description="Text span offsets")
    raw_text: str = Field(..., min_length=1, description="Exact text containing value")
    image_crop_path: Optional[str] = Field(None, description="Path to cropped image for review")
    extraction_method: str = Field(..., description="Method used: 'pdfplumber'|'ocr'|'table_transformer'")
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# PAPER METADATA
# ============================================================

class PaperMetadata(BaseModel):
    """Trial identification metadata"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = Field(None, ge=1900, le=2100)
    doi: Optional[str] = None
    pmid: Optional[str] = None
    nct_id: Optional[str] = Field(None, pattern=r'^NCT\d{8}$')
    trial_name: Optional[str] = Field(None, description="e.g., 'DAPA-HF', 'PARADIGM-HF'")
    provenance: Optional[Provenance] = None


# ============================================================
# ARMS
# ============================================================

class Arm(BaseModel):
    """Treatment arm in the trial"""
    arm_id: str = Field(..., description="Internal identifier: 'treatment', 'control', 'arm_1'")
    arm_name: str = Field(..., description="Name as reported: 'Dapagliflozin 10mg'")
    arm_type: Literal["treatment", "control", "active_comparator", "placebo", "unknown"] = "unknown"
    n_randomized: Optional[int] = Field(None, ge=0)
    n_analyzed: Optional[int] = Field(None, ge=0)
    provenance: Optional[Provenance] = None

    @model_validator(mode='after')
    def analyzed_lte_randomized(self):
        if self.n_analyzed and self.n_randomized and self.n_analyzed > self.n_randomized:
            # Don't fail, but this should be flagged
            pass
        return self


# ============================================================
# EXTRACTED VALUES
# ============================================================

class BinaryOutcome(BaseModel):
    """Events / Total for binary endpoints"""
    arm_id: str
    events: int = Field(..., ge=0)
    n: int = Field(..., gt=0)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    provenance: Provenance

    @model_validator(mode='after')
    def events_lte_n(self):
        if self.events > self.n:
            raise ValueError(f'events ({self.events}) cannot exceed n ({self.n})')
        return self


class HazardRatioCI(BaseModel):
    """Hazard ratio with confidence interval"""
    hr: float = Field(..., gt=0, description="Hazard ratio must be positive")
    ci_low: float = Field(..., gt=0)
    ci_high: float = Field(..., gt=0)
    ci_level: float = Field(default=0.95, description="Usually 0.95 for 95% CI")
    p_value: Optional[float] = Field(None, ge=0, le=1)
    p_value_text: Optional[str] = Field(None, description="Raw p-value text like '<0.001'")
    provenance: Provenance

    @model_validator(mode='after')
    def validate_ci(self):
        if self.ci_low >= self.ci_high:
            raise ValueError(f'CI lower ({self.ci_low}) must be < upper ({self.ci_high})')
        if not (self.ci_low <= self.hr <= self.ci_high):
            raise ValueError(f'HR ({self.hr}) must be within CI [{self.ci_low}, {self.ci_high}]')
        return self


class OddsRatioCI(BaseModel):
    """Odds ratio with confidence interval"""
    or_value: float = Field(..., gt=0, alias="or")
    ci_low: float = Field(..., gt=0)
    ci_high: float = Field(..., gt=0)
    ci_level: float = Field(default=0.95)
    p_value: Optional[float] = Field(None, ge=0, le=1)
    provenance: Provenance

    @model_validator(mode='after')
    def validate_ci(self):
        if self.ci_low >= self.ci_high:
            raise ValueError(f'CI lower ({self.ci_low}) must be < upper ({self.ci_high})')
        return self


class RiskRatioCI(BaseModel):
    """Relative risk with confidence interval"""
    rr: float = Field(..., gt=0)
    ci_low: float = Field(..., gt=0)
    ci_high: float = Field(..., gt=0)
    ci_level: float = Field(default=0.95)
    p_value: Optional[float] = Field(None, ge=0, le=1)
    provenance: Provenance


class MeanDifference(BaseModel):
    """Mean difference for continuous outcomes"""
    md: float
    ci_low: float
    ci_high: float
    ci_level: float = Field(default=0.95)
    p_value: Optional[float] = Field(None, ge=0, le=1)
    provenance: Provenance


class ContinuousOutcome(BaseModel):
    """Continuous outcome per arm (mean, SD, n)"""
    arm_id: str
    mean: float
    sd: Optional[float] = Field(None, ge=0)
    se: Optional[float] = Field(None, ge=0)
    n: int = Field(..., gt=0)
    provenance: Provenance


# ============================================================
# TIMEPOINT
# ============================================================

class Timepoint(BaseModel):
    """Normalized timepoint"""
    raw_text: str = Field(..., description="As reported: '12 months', 'median 3.2 years'")
    normalized_days: Optional[int] = Field(None, ge=0, description="Normalized to days")
    normalized_label: Optional[str] = Field(None, description="'30d', '6m', '12m', '5y', 'median_fu'")
    is_primary: bool = Field(default=False, description="Is this the primary timepoint?")
    is_longest: bool = Field(default=False, description="Is this the longest follow-up?")
    provenance: Optional[Provenance] = None


# ============================================================
# EXTRACTION RECORD
# ============================================================

class ExtractionRecord(BaseModel):
    """Single extracted outcome with full provenance"""

    # Endpoint identification
    endpoint_canonical: str = Field(..., description="Canonical name from vocabulary")
    endpoint_raw: str = Field(..., description="Endpoint as written in source")
    endpoint_type: EndpointType

    # For composite endpoints
    is_composite: bool = Field(default=False)
    composite_definition: Optional[str] = Field(None, description="Definition text if composite")

    # Timepoint
    timepoint: Timepoint

    # Analysis type
    analysis_population: AnalysisPopulation = AnalysisPopulation.UNCLEAR
    is_adjusted: bool = Field(default=False)
    adjustment_note: Optional[str] = None

    # The actual data (one of these will be populated)
    binary_outcomes: Optional[List[BinaryOutcome]] = None
    effect_estimate: Optional[Union[HazardRatioCI, OddsRatioCI, RiskRatioCI, MeanDifference]] = None
    continuous_outcomes: Optional[List[ContinuousOutcome]] = None

    # Quality signals
    confidence: ExtractionConfidence = ExtractionConfidence.REVIEW_REQUIRED
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    flags: List[str] = Field(default_factory=list)

    # Cross-check results
    pass_a_value: Optional[str] = Field(None, description="Value from structure-first pass")
    pass_b_value: Optional[str] = Field(None, description="Value from semantic pass")
    passes_agree: Optional[bool] = None


# ============================================================
# REVIEW QUEUE ITEM
# ============================================================

class ReviewQueueItem(BaseModel):
    """Item flagged for human review"""
    record_id: str
    pdf_file: str
    page_number: int
    severity: ReviewSeverity
    reason_code: str = Field(..., description="Machine-readable: 'EVENTS_GT_N', 'PASS_DISAGREEMENT'")
    reason_text: str = Field(..., description="Human-readable explanation")
    extraction_attempt: Optional[ExtractionRecord] = None
    image_crop_path: Optional[str] = None
    suggested_action: str = Field(default="manual_review")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# FULL EXTRACTION OUTPUT
# ============================================================

class ExtractionOutput(BaseModel):
    """Complete extraction result for one PDF"""

    # Source
    source_pdf: str
    extraction_version: str = "2.0.0"
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    paper: PaperMetadata

    # Arms
    arms: List[Arm]

    # Extracted data
    extractions: List[ExtractionRecord]

    # Quality
    overall_confidence: ExtractionConfidence
    review_queue: List[ReviewQueueItem]

    # Stats
    pages_processed: int
    tables_found: int
    extraction_time_seconds: float


# ============================================================
# GOLD STANDARD FORMAT
# ============================================================

class GoldStandardRecord(BaseModel):
    """Ground truth for evaluation"""
    pdf_file: str
    endpoint_canonical: str
    endpoint_type: EndpointType
    timepoint_normalized: Optional[str] = None

    # For binary
    arm_values: Optional[List[dict]] = None  # [{"arm": "treatment", "events": 100, "n": 500}, ...]

    # For TTE
    hr: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None

    # Reference
    page_number: Optional[int] = None
    annotator: Optional[str] = None
    annotation_date: Optional[str] = None
    notes: Optional[str] = None
