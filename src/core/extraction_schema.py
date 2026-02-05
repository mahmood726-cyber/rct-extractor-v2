"""
Phase 0 Schema: Minimal, Unambiguous Extraction Schema

Based on Al-Fātiḥah Principle 1: "Start with intention"
Lock this schema early; everything else is "later".
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import hashlib


class ExtractionStatus(Enum):
    """Every field must have a status - never output without provenance."""
    CERTAIN = "certain"      # High confidence, validated
    UNCERTAIN = "uncertain"  # Extracted but conflicts or low confidence
    MISSING = "missing"      # Not found in document
    INVALID = "invalid"      # Found but failed validation


class OutcomeType(Enum):
    """Supported outcome types - start with common ones."""
    BINARY = "binary"           # events/total, OR, RR
    CONTINUOUS = "continuous"   # mean, SD, MD, SMD
    TIME_TO_EVENT = "tte"       # HR, survival
    RATE = "rate"               # IRR, person-years


@dataclass
class Provenance:
    """
    Every extracted value MUST have provenance.
    Principle 3: "Mercy = design for failure without lying"
    """
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    bbox: Optional[tuple] = None  # (x0, y0, x1, y1)
    source_text: str = ""
    source_section: str = ""  # abstract, methods, results, table, figure
    extraction_rule: str = ""  # which rule fired
    alternatives_found: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page": self.page_number,
            "line": self.line_number,
            "chars": (self.char_start, self.char_end) if self.char_start else None,
            "bbox": self.bbox,
            "text": self.source_text[:200] if self.source_text else None,
            "section": self.source_section,
            "rule": self.extraction_rule,
            "alternatives": self.alternatives_found[:3] if self.alternatives_found else None,
        }


@dataclass
class ExtractedValue:
    """
    Generic container for any extracted value with confidence and provenance.
    Principle 3: Never output a value without provenance.
    """
    value: Any
    confidence: float = 0.0  # 0.0-1.0
    status: ExtractionStatus = ExtractionStatus.UNCERTAIN
    provenance: Provenance = field(default_factory=Provenance)
    validation_messages: List[str] = field(default_factory=list)

    def is_usable(self) -> bool:
        """Can this value be used in analysis?"""
        return self.status in [ExtractionStatus.CERTAIN, ExtractionStatus.UNCERTAIN] and self.confidence >= 0.5

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "status": self.status.value,
            "provenance": self.provenance.to_dict(),
            "validation": self.validation_messages if self.validation_messages else None,
        }


@dataclass
class TrialArm:
    """Single trial arm with sample sizes."""
    name: ExtractedValue  # arm label
    n_randomized: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    n_analyzed: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    intervention_details: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name.to_dict(),
            "n_randomized": self.n_randomized.to_dict() if self.n_randomized.value else None,
            "n_analyzed": self.n_analyzed.to_dict() if self.n_analyzed.value else None,
            "intervention": self.intervention_details,
        }


@dataclass
class EffectInputs:
    """
    Complete effect data needed for meta-analysis.
    Addresses meta-analyst critique: "CIs alone cannot be pooled"
    """
    # Point estimate
    effect_type: str  # HR, OR, RR, MD, SMD, IRR, ARD
    point_estimate: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Confidence interval
    ci_lower: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    ci_upper: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    ci_level: float = 0.95

    # P-value
    p_value: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # For binary outcomes (needed for meta-analysis)
    events_treatment: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    events_control: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    n_treatment: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    n_control: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # For continuous outcomes
    mean_treatment: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    mean_control: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    sd_treatment: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    sd_control: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Standard error (calculated or reported)
    standard_error: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    se_method: str = ""  # "reported", "calculated_from_ci", "calculated_from_p"

    def has_complete_ci(self) -> bool:
        return (self.ci_lower.is_usable() and self.ci_upper.is_usable())

    def has_meta_analysis_inputs(self) -> bool:
        """Check if we have enough data for meta-analysis."""
        if self.effect_type in ["HR", "OR", "RR"]:
            # Need either events+n or CI
            has_counts = all([
                self.events_treatment.is_usable(),
                self.events_control.is_usable(),
                self.n_treatment.is_usable(),
                self.n_control.is_usable()
            ])
            return has_counts or (self.point_estimate.is_usable() and self.has_complete_ci())
        elif self.effect_type in ["MD", "SMD"]:
            # Need means, SDs, and Ns
            has_continuous = all([
                self.mean_treatment.is_usable(),
                self.mean_control.is_usable(),
                self.sd_treatment.is_usable(),
                self.sd_control.is_usable(),
                self.n_treatment.is_usable(),
                self.n_control.is_usable()
            ])
            return has_continuous or (self.point_estimate.is_usable() and self.standard_error.is_usable())
        return self.point_estimate.is_usable() and self.has_complete_ci()

    def to_dict(self) -> dict:
        result = {
            "effect_type": self.effect_type,
            "point_estimate": self.point_estimate.to_dict() if self.point_estimate.value else None,
            "ci_lower": self.ci_lower.to_dict() if self.ci_lower.value else None,
            "ci_upper": self.ci_upper.to_dict() if self.ci_upper.value else None,
            "ci_level": self.ci_level,
            "has_complete_ci": self.has_complete_ci(),
            "has_meta_inputs": self.has_meta_analysis_inputs(),
        }
        if self.p_value.value is not None:
            result["p_value"] = self.p_value.to_dict()
        if self.events_treatment.value is not None:
            result["events"] = {
                "treatment": self.events_treatment.to_dict(),
                "control": self.events_control.to_dict()
            }
        if self.n_treatment.value is not None:
            result["n"] = {
                "treatment": self.n_treatment.to_dict(),
                "control": self.n_control.to_dict()
            }
        if self.standard_error.value is not None:
            result["se"] = self.standard_error.to_dict()
            result["se_method"] = self.se_method
        return result


@dataclass
class Outcome:
    """
    Single outcome with context - addresses "CIs without knowing what it measures" critique.
    """
    name: ExtractedValue  # outcome name/description
    timepoint: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    outcome_type: OutcomeType = OutcomeType.BINARY
    is_primary: ExtractedValue = field(default_factory=lambda: ExtractedValue(False, status=ExtractionStatus.UNCERTAIN))
    effect: EffectInputs = field(default_factory=lambda: EffectInputs(effect_type="unknown"))

    def to_dict(self) -> dict:
        return {
            "name": self.name.to_dict(),
            "timepoint": self.timepoint.to_dict() if self.timepoint.value else None,
            "type": self.outcome_type.value,
            "is_primary": self.is_primary.to_dict(),
            "effect": self.effect.to_dict(),
        }


@dataclass
class RCTExtraction:
    """
    Complete RCT extraction with full provenance.
    Phase 0 schema - minimal and unambiguous.
    """
    # Document identification
    pdf_path: str
    pdf_hash: str  # SHA256 of PDF content for reproducibility
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    extractor_version: str = "4.3.5"

    # Trial identification
    trial_id: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    registry_id: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))  # NCT, ISRCTN, etc.
    title: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    journal: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    year: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Population
    condition: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    population_description: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Arms
    arms: List[TrialArm] = field(default_factory=list)
    n_randomized_total: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Outcomes
    outcomes: List[Outcome] = field(default_factory=list)

    # Risk of bias hints
    randomization_method: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))
    blinding: ExtractedValue = field(default_factory=lambda: ExtractedValue(None, status=ExtractionStatus.MISSING))

    # Validation summary
    validation_passed: bool = False
    validation_warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)

    # Extraction quality
    overall_confidence: float = 0.0
    overall_status: ExtractionStatus = ExtractionStatus.UNCERTAIN

    def calculate_overall_confidence(self):
        """Calculate overall extraction confidence."""
        confidences = []

        if self.trial_id.value:
            confidences.append(self.trial_id.confidence)
        if self.n_randomized_total.value:
            confidences.append(self.n_randomized_total.confidence)

        for arm in self.arms:
            if arm.n_randomized.value:
                confidences.append(arm.n_randomized.confidence)

        for outcome in self.outcomes:
            if outcome.effect.point_estimate.value:
                confidences.append(outcome.effect.point_estimate.confidence)
            if outcome.effect.has_complete_ci():
                confidences.append(min(outcome.effect.ci_lower.confidence, outcome.effect.ci_upper.confidence))

        self.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Set overall status
        if self.validation_errors:
            self.overall_status = ExtractionStatus.INVALID
        elif self.overall_confidence >= 0.8 and not self.validation_warnings:
            self.overall_status = ExtractionStatus.CERTAIN
        elif self.overall_confidence >= 0.5:
            self.overall_status = ExtractionStatus.UNCERTAIN
        else:
            self.overall_status = ExtractionStatus.MISSING

    def to_dict(self) -> dict:
        self.calculate_overall_confidence()
        return {
            "meta": {
                "pdf_path": self.pdf_path,
                "pdf_hash": self.pdf_hash,
                "extracted_at": self.extraction_timestamp,
                "extractor_version": self.extractor_version,
                "overall_confidence": round(self.overall_confidence, 3),
                "overall_status": self.overall_status.value,
                "validation_passed": self.validation_passed,
            },
            "trial": {
                "id": self.trial_id.to_dict() if self.trial_id.value else None,
                "registry_id": self.registry_id.to_dict() if self.registry_id.value else None,
                "title": self.title.to_dict() if self.title.value else None,
                "journal": self.journal.to_dict() if self.journal.value else None,
                "year": self.year.to_dict() if self.year.value else None,
            },
            "population": {
                "condition": self.condition.to_dict() if self.condition.value else None,
                "description": self.population_description.to_dict() if self.population_description.value else None,
            },
            "arms": [arm.to_dict() for arm in self.arms],
            "n_randomized_total": self.n_randomized_total.to_dict() if self.n_randomized_total.value else None,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "risk_of_bias": {
                "randomization": self.randomization_method.to_dict() if self.randomization_method.value else None,
                "blinding": self.blinding.to_dict() if self.blinding.value else None,
            },
            "validation": {
                "passed": self.validation_passed,
                "warnings": self.validation_warnings if self.validation_warnings else None,
                "errors": self.validation_errors if self.validation_errors else None,
            }
        }


def compute_pdf_hash(pdf_path: str) -> str:
    """Compute SHA256 hash of PDF for provenance tracking."""
    sha256 = hashlib.sha256()
    with open(pdf_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]  # First 16 chars for brevity
