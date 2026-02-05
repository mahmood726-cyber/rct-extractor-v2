#!/usr/bin/env python3
"""
CTG Cross-Validation Pipeline
Validates PDF extractions against ClinicalTrials.gov results.

Usage:
    python scripts/ctg_validator.py --ctg ctg_studies.json --pdfs test_pdfs/
    python scripts/ctg_validator.py --nct NCT02653482 --pdf study.pdf
"""

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.pdf.pdf_parser import PDFParser


@dataclass
class ValidationResult:
    """Result of validating a single effect estimate"""
    nct_id: str
    outcome: str
    expected_type: str
    expected_value: float
    expected_ci: Tuple[Optional[float], Optional[float]]
    extracted_type: Optional[str]
    extracted_value: Optional[float]
    extracted_ci: Tuple[Optional[float], Optional[float]]
    value_match: bool
    type_match: bool
    ci_match: bool
    overall_match: bool
    source: str  # 'ctg' or 'pdf'


@dataclass
class StudyValidation:
    """Validation results for a complete study"""
    nct_id: str
    title: str
    pdf_path: Optional[str]
    ctg_effects: int
    pdf_effects: int
    matched: int
    value_accuracy: float
    type_accuracy: float
    ci_accuracy: float
    results: List[ValidationResult]


class CTGValidator:
    """Cross-validator for CTG and PDF extractions"""

    def __init__(self, value_tolerance: float = 0.02, ci_tolerance: float = 0.05):
        """
        Initialize validator.

        Args:
            value_tolerance: Tolerance for value matching (default 0.02 = 2%)
            ci_tolerance: Tolerance for CI matching (default 0.05 = 5%)
        """
        self.value_tolerance = value_tolerance
        self.ci_tolerance = ci_tolerance
        self.extractor = EnhancedExtractor()
        self.parser = PDFParser()

    def validate_study(
        self,
        ctg_data: dict,
        pdf_path: Optional[str] = None,
        pdf_text: Optional[str] = None
    ) -> StudyValidation:
        """
        Validate a study's PDF extraction against CTG results.

        Args:
            ctg_data: CTG study data dict
            pdf_path: Path to PDF file
            pdf_text: Pre-extracted PDF text (optional)

        Returns:
            StudyValidation with results
        """
        nct_id = ctg_data.get("nct_id", "")
        title = ctg_data.get("title", "")
        ctg_effects = ctg_data.get("effect_estimates", [])

        # Extract from PDF if provided
        pdf_extractions = []
        if pdf_path:
            try:
                content = self.parser.parse(pdf_path)
                pdf_text = "\n".join(p.full_text for p in content.pages)
            except Exception as e:
                print(f"  Error parsing PDF: {e}")

        if pdf_text:
            pdf_extractions = self.extractor.extract(pdf_text)

        # Match CTG effects to PDF extractions
        results = []
        matched_count = 0

        for ctg_effect in ctg_effects:
            result = self._match_effect(ctg_effect, pdf_extractions, nct_id)
            results.append(result)
            if result.overall_match:
                matched_count += 1

        # Calculate accuracies
        n_ctg = len(ctg_effects)
        value_matches = sum(1 for r in results if r.value_match)
        type_matches = sum(1 for r in results if r.type_match)
        ci_matches = sum(1 for r in results if r.ci_match)

        return StudyValidation(
            nct_id=nct_id,
            title=title,
            pdf_path=pdf_path,
            ctg_effects=n_ctg,
            pdf_effects=len(pdf_extractions),
            matched=matched_count,
            value_accuracy=value_matches / n_ctg if n_ctg > 0 else 0,
            type_accuracy=type_matches / n_ctg if n_ctg > 0 else 0,
            ci_accuracy=ci_matches / n_ctg if n_ctg > 0 else 0,
            results=results
        )

    def _match_effect(
        self,
        ctg_effect: dict,
        pdf_extractions: list,
        nct_id: str
    ) -> ValidationResult:
        """Match a CTG effect to PDF extractions"""
        expected_type = ctg_effect.get("effect_type", "")
        expected_value = ctg_effect.get("value", 0)
        expected_ci = (
            ctg_effect.get("ci_lower"),
            ctg_effect.get("ci_upper")
        )
        outcome = ctg_effect.get("outcome_title", "")[:50]

        # Find best matching PDF extraction
        best_match = None
        best_score = 0

        for ext in pdf_extractions:
            score = self._match_score(ctg_effect, ext)
            if score > best_score:
                best_score = score
                best_match = ext

        # Determine match status
        if best_match:
            ext_type = best_match.effect_type.value if hasattr(best_match.effect_type, 'value') else str(best_match.effect_type)
            ext_value = best_match.point_estimate
            ext_ci = (
                best_match.ci.lower if best_match.ci else None,
                best_match.ci.upper if best_match.ci else None
            )

            value_match = self._values_match(expected_value, ext_value)
            type_match = expected_type.upper() == ext_type.upper()
            ci_match = self._cis_match(expected_ci, ext_ci)
            overall_match = value_match and type_match

        else:
            ext_type = None
            ext_value = None
            ext_ci = (None, None)
            value_match = False
            type_match = False
            ci_match = False
            overall_match = False

        return ValidationResult(
            nct_id=nct_id,
            outcome=outcome,
            expected_type=expected_type,
            expected_value=expected_value,
            expected_ci=expected_ci,
            extracted_type=ext_type,
            extracted_value=ext_value,
            extracted_ci=ext_ci,
            value_match=value_match,
            type_match=type_match,
            ci_match=ci_match,
            overall_match=overall_match,
            source="ctg"
        )

    def _match_score(self, ctg_effect: dict, pdf_extraction) -> float:
        """Calculate match score between CTG effect and PDF extraction"""
        score = 0.0

        # Type match
        ctg_type = ctg_effect.get("effect_type", "").upper()
        pdf_type = pdf_extraction.effect_type.value if hasattr(pdf_extraction.effect_type, 'value') else str(pdf_extraction.effect_type)

        if ctg_type == pdf_type.upper():
            score += 0.4

        # Value match
        ctg_value = ctg_effect.get("value", 0)
        pdf_value = pdf_extraction.point_estimate

        if self._values_match(ctg_value, pdf_value):
            score += 0.4

        # CI match
        ctg_ci = (ctg_effect.get("ci_lower"), ctg_effect.get("ci_upper"))
        pdf_ci = (
            pdf_extraction.ci.lower if pdf_extraction.ci else None,
            pdf_extraction.ci.upper if pdf_extraction.ci else None
        )

        if self._cis_match(ctg_ci, pdf_ci):
            score += 0.2

        return score

    def _values_match(self, v1: float, v2: float) -> bool:
        """Check if two values match within tolerance"""
        if v1 == 0 and v2 == 0:
            return True
        if v1 == 0 or v2 == 0:
            return False

        # Relative difference
        rel_diff = abs(v1 - v2) / max(abs(v1), abs(v2))
        return rel_diff <= self.value_tolerance

    def _cis_match(
        self,
        ci1: Tuple[Optional[float], Optional[float]],
        ci2: Tuple[Optional[float], Optional[float]]
    ) -> bool:
        """Check if two CIs match within tolerance"""
        if ci1[0] is None or ci1[1] is None:
            return True  # No expected CI to match
        if ci2[0] is None or ci2[1] is None:
            return False  # Expected CI but none extracted

        lower_match = self._values_match(ci1[0], ci2[0])
        upper_match = self._values_match(ci1[1], ci2[1])

        return lower_match and upper_match


def validate_batch(
    ctg_file: str,
    pdf_dir: Optional[str] = None,
    output_file: str = "validation_results.json"
):
    """
    Validate a batch of studies.

    Args:
        ctg_file: Path to CTG studies JSON
        pdf_dir: Directory containing PDFs (named by NCT ID)
        output_file: Output file for results
    """
    # Load CTG data
    with open(ctg_file) as f:
        data = json.load(f)

    studies = data.get("studies", [])
    print(f"Loaded {len(studies)} studies from CTG")

    validator = CTGValidator()
    results = []

    for i, study in enumerate(studies):
        nct_id = study.get("nct_id", "")
        print(f"[{i+1}/{len(studies)}] Validating {nct_id}...")

        # Find matching PDF
        pdf_path = None
        if pdf_dir:
            pdf_dir_path = Path(pdf_dir)
            # Try various naming conventions
            for pattern in [f"{nct_id}.pdf", f"{nct_id.lower()}.pdf", f"*{nct_id}*.pdf"]:
                matches = list(pdf_dir_path.glob(pattern))
                if matches:
                    pdf_path = str(matches[0])
                    break

        if study.get("effect_estimates"):
            validation = validator.validate_study(study, pdf_path)
            results.append(validation)

            print(f"  CTG effects: {validation.ctg_effects}")
            print(f"  PDF effects: {validation.pdf_effects}")
            print(f"  Matched: {validation.matched}")
            print(f"  Value accuracy: {validation.value_accuracy:.1%}")

    # Calculate overall metrics
    total_ctg = sum(r.ctg_effects for r in results)
    total_matched = sum(r.matched for r in results)
    total_value_match = sum(r.value_accuracy * r.ctg_effects for r in results)
    total_type_match = sum(r.type_accuracy * r.ctg_effects for r in results)
    total_ci_match = sum(r.ci_accuracy * r.ctg_effects for r in results)

    overall_accuracy = total_matched / total_ctg if total_ctg > 0 else 0
    overall_value = total_value_match / total_ctg if total_ctg > 0 else 0
    overall_type = total_type_match / total_ctg if total_ctg > 0 else 0
    overall_ci = total_ci_match / total_ctg if total_ctg > 0 else 0

    # Save results
    output = {
        "summary": {
            "studies_validated": len(results),
            "total_ctg_effects": total_ctg,
            "total_matched": total_matched,
            "overall_accuracy": round(overall_accuracy, 4),
            "value_accuracy": round(overall_value, 4),
            "type_accuracy": round(overall_type, 4),
            "ci_accuracy": round(overall_ci, 4)
        },
        "studies": [asdict(r) for r in results]
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n=== Overall Results ===")
    print(f"Studies validated: {len(results)}")
    print(f"CTG effects: {total_ctg}")
    print(f"Matched: {total_matched}")
    print(f"Overall accuracy: {overall_accuracy:.1%}")
    print(f"Value accuracy: {overall_value:.1%}")
    print(f"Type accuracy: {overall_type:.1%}")
    print(f"CI accuracy: {overall_ci:.1%}")
    print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="CTG Cross-Validation Pipeline")
    parser.add_argument("--ctg", type=str, required=True, help="CTG studies JSON file")
    parser.add_argument("--pdfs", type=str, help="Directory containing PDFs")
    parser.add_argument("--output", type=str, default="ctg_validation_results.json", help="Output file")

    args = parser.parse_args()

    validate_batch(args.ctg, args.pdfs, args.output)


if __name__ == "__main__":
    main()
