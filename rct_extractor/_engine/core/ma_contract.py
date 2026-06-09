"""Meta-analysis output contract for real-RCT PDF extraction."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RATIO_EFFECT_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFFERENCE_EFFECT_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}
SUPPORTED_EFFECT_TYPES = sorted(RATIO_EFFECT_TYPES | DIFFERENCE_EFFECT_TYPES)


class MAProvenance(BaseModel):
    """Minimum provenance needed for auditability and reproducibility."""

    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1, description="Snippet supporting the extracted value.")
    page_number: int = Field(ge=0, description="0-based PDF page index.")
    source_type: Literal["text", "table", "figure", "ocr", "computed", "unknown"] = "unknown"
    char_start: Optional[int] = Field(default=None, ge=0)
    char_end: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_char_offsets(self) -> "MAProvenance":
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("char_start and char_end must both be set or both be null.")
        if self.char_start is not None and self.char_end is not None and self.char_end < self.char_start:
            raise ValueError("char_end cannot be less than char_start.")
        return self


class MAExtractionRecord(BaseModel):
    """Contract for one extraction record that can enter a meta-analysis workflow."""

    model_config = ConfigDict(extra="forbid")

    study_id: str = Field(min_length=1)
    outcome_name: str = Field(min_length=1)
    effect_type: Literal[
        "HR",
        "OR",
        "RR",
        "IRR",
        "GMR",
        "NNT",
        "NNH",
        "MD",
        "SMD",
        "ARD",
        "ARR",
        "RRR",
        "RD",
        "WMD",
    ]
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    standard_error: Optional[float] = Field(default=None, ge=0)
    p_value: Optional[float] = Field(default=None, ge=0, le=1)

    timepoint: Optional[str] = None
    is_primary: Optional[bool] = None
    is_subgroup: bool = False
    computation_origin: Literal["reported", "computed"] = "reported"
    provenance: MAProvenance

    @model_validator(mode="after")
    def validate_meta_analysis_fields(self) -> "MAExtractionRecord":
        has_ci_lower = self.ci_lower is not None
        has_ci_upper = self.ci_upper is not None
        has_complete_ci = has_ci_lower and has_ci_upper

        if has_ci_lower != has_ci_upper:
            raise ValueError("ci_lower and ci_upper must both be set or both be null.")
        if not has_complete_ci and self.standard_error is None:
            raise ValueError("Record is not meta-analysis-ready: provide CI or standard_error.")

        if has_complete_ci:
            if self.ci_lower > self.ci_upper:
                raise ValueError("CI bounds are reversed (ci_lower > ci_upper).")
            if not (self.ci_lower <= self.point_estimate <= self.ci_upper):
                raise ValueError("Point estimate must lie within CI bounds.")

        if self.effect_type in RATIO_EFFECT_TYPES:
            if self.point_estimate <= 0:
                raise ValueError(f"{self.effect_type} point_estimate must be > 0.")
            if has_complete_ci and (self.ci_lower <= 0 or self.ci_upper <= 0):
                raise ValueError(f"{self.effect_type} CI bounds must be > 0.")

        return self

    @property
    def has_complete_ci(self) -> bool:
        return self.ci_lower is not None and self.ci_upper is not None

    @property
    def is_meta_analysis_ready(self) -> bool:
        return self.has_complete_ci or self.standard_error is not None


def is_meta_analysis_ready(record: Mapping[str, Any]) -> bool:
    """Return True if record validates against the MA output contract."""
    try:
        MAExtractionRecord.model_validate(record)
        return True
    except ValidationError:
        return False


def validate_ma_records(
    records: Iterable[Mapping[str, Any]],
) -> Tuple[List[MAExtractionRecord], List[str]]:
    """Validate multiple records and return parsed models plus human-readable errors."""
    validated: List[MAExtractionRecord] = []
    errors: List[str] = []

    for idx, record in enumerate(records):
        try:
            validated.append(MAExtractionRecord.model_validate(record))
        except ValidationError as exc:
            errors.append(f"Record {idx}: {exc}")

    return validated, errors


def contract_summary() -> Dict[str, Any]:
    """Expose lightweight contract metadata for tooling and docs."""
    return {
        "supported_effect_types": SUPPORTED_EFFECT_TYPES,
        "ratio_effect_types": sorted(RATIO_EFFECT_TYPES),
        "difference_effect_types": sorted(DIFFERENCE_EFFECT_TYPES),
        "required_for_ma_ready": "CI bounds or standard_error",
    }


__all__ = [
    "DIFFERENCE_EFFECT_TYPES",
    "MAExtractionRecord",
    "MAProvenance",
    "RATIO_EFFECT_TYPES",
    "SUPPORTED_EFFECT_TYPES",
    "contract_summary",
    "is_meta_analysis_ready",
    "validate_ma_records",
]
