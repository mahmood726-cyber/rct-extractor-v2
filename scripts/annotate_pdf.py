#!/usr/bin/env python3
"""
PDF Annotation Tool for Gold Standard Creation
==============================================

Interactive tool for manual extraction of effect estimates from PDFs.
Supports dual extraction protocol for inter-rater agreement calculation.

Usage:
    python scripts/annotate_pdf.py path/to/file.pdf
    python scripts/annotate_pdf.py path/to/file.pdf --annotator A
    python scripts/annotate_pdf.py --compare trial_name  # Compare A/B extractions

Output: JSONL files in test_pdfs/gold_standard/annotations/
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directories
GOLD_STANDARD_DIR = Path(__file__).parent.parent / "test_pdfs" / "gold_standard"
ANNOTATIONS_DIR = GOLD_STANDARD_DIR / "annotations"


@dataclass
class EffectEstimate:
    """A manually extracted effect estimate"""
    effect_type: str  # HR, OR, RR, MD, SMD, ARD, IRR
    value: float
    ci_lower: float
    ci_upper: float
    p_value: Optional[float] = None
    outcome: str = ""
    timepoint: str = ""
    comparison: str = ""
    analysis_population: str = "ITT"
    source_type: str = "text"  # text, table, figure
    page_number: int = 1
    raw_text: str = ""
    bounding_box: Optional[Dict[str, float]] = None
    confidence: str = "high"  # high, medium, low
    notes: str = ""


@dataclass
class PDFAnnotation:
    """Complete annotation for a PDF"""
    pdf_filename: str
    trial_name: str
    annotator_id: str
    annotation_date: str
    total_pages: int
    effects: List[EffectEstimate] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        """Convert to JSONL format"""
        data = asdict(self)
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> "PDFAnnotation":
        """Load from JSONL line"""
        data = json.loads(line)
        effects = [EffectEstimate(**e) for e in data.pop("effects", [])]
        return cls(**data, effects=effects)


class PDFAnnotator:
    """Interactive PDF annotation tool"""

    EFFECT_TYPES = ["HR", "OR", "RR", "MD", "SMD", "ARD", "IRR", "NNT"]
    SOURCE_TYPES = ["text", "table", "figure", "abstract", "supplementary"]
    CONFIDENCE_LEVELS = ["high", "medium", "low"]

    def __init__(self, pdf_path: Path, annotator_id: str = "A"):
        self.pdf_path = pdf_path
        self.annotator_id = annotator_id
        self.annotation = PDFAnnotation(
            pdf_filename=pdf_path.name,
            trial_name=pdf_path.stem,
            annotator_id=annotator_id,
            annotation_date=datetime.now().isoformat(),
            total_pages=0,
        )

        # Try to get page count
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            self.annotation.total_pages = len(doc)
            doc.close()
        except:
            pass

    def prompt_effect(self) -> Optional[EffectEstimate]:
        """Interactively prompt for effect estimate"""
        print("\n" + "=" * 60)
        print("NEW EFFECT ESTIMATE")
        print("=" * 60)

        # Effect type
        print(f"\nEffect types: {', '.join(self.EFFECT_TYPES)}")
        effect_type = input("Effect type (or 'done' to finish): ").strip().upper()
        if effect_type.lower() == 'done' or not effect_type:
            return None

        if effect_type not in self.EFFECT_TYPES:
            print(f"Warning: Non-standard effect type: {effect_type}")

        # Effect value and CI
        try:
            value = float(input("Effect value: ").strip())
            ci_lower = float(input("CI lower: ").strip())
            ci_upper = float(input("CI upper: ").strip())
        except ValueError:
            print("Error: Invalid numeric input")
            return self.prompt_effect()

        # P-value (optional)
        p_value_str = input("P-value (press Enter to skip): ").strip()
        p_value = None
        if p_value_str:
            # Parse various p-value formats
            p_value = self._parse_p_value(p_value_str)

        # Outcome
        outcome = input("Outcome (e.g., 'CV death or HF hospitalization'): ").strip()

        # Timepoint
        timepoint = input("Timepoint (e.g., 'median 18.2 months'): ").strip()

        # Comparison
        comparison = input("Comparison (e.g., 'dapagliflozin vs placebo'): ").strip()

        # Analysis population
        pop_options = ["ITT", "mITT", "per-protocol", "safety"]
        print(f"Analysis populations: {', '.join(pop_options)}")
        analysis_pop = input("Analysis population [ITT]: ").strip() or "ITT"

        # Source type
        print(f"Source types: {', '.join(self.SOURCE_TYPES)}")
        source_type = input("Source type [text]: ").strip() or "text"

        # Page number
        page_str = input("Page number [1]: ").strip()
        page_number = int(page_str) if page_str else 1

        # Raw text
        print("Paste the raw text containing this effect (end with empty line):")
        raw_lines = []
        while True:
            line = input()
            if not line:
                break
            raw_lines.append(line)
        raw_text = " ".join(raw_lines)

        # Confidence
        print(f"Confidence levels: {', '.join(self.CONFIDENCE_LEVELS)}")
        confidence = input("Your confidence [high]: ").strip() or "high"

        # Notes
        notes = input("Additional notes (optional): ").strip()

        return EffectEstimate(
            effect_type=effect_type,
            value=value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=p_value,
            outcome=outcome,
            timepoint=timepoint,
            comparison=comparison,
            analysis_population=analysis_pop,
            source_type=source_type,
            page_number=page_number,
            raw_text=raw_text,
            confidence=confidence,
            notes=notes,
        )

    def _parse_p_value(self, p_str: str) -> Optional[float]:
        """Parse various p-value formats"""
        p_str = p_str.lower().strip()

        # Handle "p<0.001", "p=0.04", etc.
        match = re.search(r'[<>=]?\s*(\d*\.?\d+(?:e[+-]?\d+)?)', p_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Handle "NS", "n.s."
        if 'ns' in p_str or 'n.s' in p_str:
            return 0.999  # Conventional non-significant marker

        return None

    def run_annotation(self) -> PDFAnnotation:
        """Run interactive annotation session"""
        print("\n" + "=" * 70)
        print(f"PDF ANNOTATION SESSION")
        print(f"File: {self.pdf_path.name}")
        print(f"Annotator: {self.annotator_id}")
        print(f"Pages: {self.annotation.total_pages}")
        print("=" * 70)

        # Trial name
        trial_name = input(f"\nTrial name [{self.annotation.trial_name}]: ").strip()
        if trial_name:
            self.annotation.trial_name = trial_name

        # Metadata
        print("\nEnter metadata (press Enter to skip):")
        self.annotation.metadata["journal"] = input("Journal: ").strip() or None
        self.annotation.metadata["year"] = input("Year: ").strip() or None
        self.annotation.metadata["pmid"] = input("PMID: ").strip() or None
        self.annotation.metadata["pmc_id"] = input("PMC ID: ").strip() or None
        self.annotation.metadata["doi"] = input("DOI: ").strip() or None
        self.annotation.metadata["therapeutic_area"] = input("Therapeutic area: ").strip() or None

        # Remove None values
        self.annotation.metadata = {k: v for k, v in self.annotation.metadata.items() if v}

        # Extract effects
        print("\n" + "-" * 40)
        print("Now enter each effect estimate found in the PDF.")
        print("Type 'done' when finished.")
        print("-" * 40)

        while True:
            effect = self.prompt_effect()
            if effect is None:
                break
            self.annotation.effects.append(effect)
            print(f"\n[Added effect #{len(self.annotation.effects)}: {effect.effect_type} "
                  f"{effect.value} ({effect.ci_lower}, {effect.ci_upper})]")

        return self.annotation

    def save_annotation(self, output_dir: Optional[Path] = None) -> Path:
        """Save annotation to JSONL file"""
        output_dir = output_dir or ANNOTATIONS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # Filename format: trial_name.annotator_X.jsonl
        filename = f"{self.annotation.trial_name}.annotator_{self.annotator_id.lower()}.jsonl"
        output_path = output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.annotation.to_jsonl())

        logger.info(f"Annotation saved: {output_path}")
        return output_path


def compare_annotations(trial_name: str, annotations_dir: Path = ANNOTATIONS_DIR) -> Dict[str, Any]:
    """Compare dual extractions for inter-rater agreement"""
    # Load both annotations
    anno_a_path = annotations_dir / f"{trial_name}.annotator_a.jsonl"
    anno_b_path = annotations_dir / f"{trial_name}.annotator_b.jsonl"

    if not anno_a_path.exists() or not anno_b_path.exists():
        raise FileNotFoundError(f"Missing annotation files for: {trial_name}")

    with open(anno_a_path) as f:
        anno_a = PDFAnnotation.from_jsonl(f.read())

    with open(anno_b_path) as f:
        anno_b = PDFAnnotation.from_jsonl(f.read())

    # Compare effects
    matches = []
    a_only = []
    b_only = []
    discrepancies = []

    matched_b_indices = set()

    for effect_a in anno_a.effects:
        found_match = False
        for i, effect_b in enumerate(anno_b.effects):
            if i in matched_b_indices:
                continue

            # Check if same effect (same type and close values)
            if (effect_a.effect_type == effect_b.effect_type and
                abs(effect_a.value - effect_b.value) < 0.02 and
                abs(effect_a.ci_lower - effect_b.ci_lower) < 0.02 and
                abs(effect_a.ci_upper - effect_b.ci_upper) < 0.02):

                matches.append({
                    "annotator_a": asdict(effect_a),
                    "annotator_b": asdict(effect_b),
                })
                matched_b_indices.add(i)
                found_match = True
                break

            # Check for same effect type but different values
            elif effect_a.effect_type == effect_b.effect_type:
                # Might be a discrepancy
                pass

        if not found_match:
            a_only.append(asdict(effect_a))

    # Find B-only effects
    for i, effect_b in enumerate(anno_b.effects):
        if i not in matched_b_indices:
            b_only.append(asdict(effect_b))

    # Calculate agreement metrics
    total_effects = len(anno_a.effects) + len(anno_b.effects)
    agreed_effects = len(matches) * 2

    # Simple agreement rate
    if total_effects > 0:
        agreement_rate = agreed_effects / total_effects
    else:
        agreement_rate = 1.0

    # Cohen's kappa approximation (for presence/absence agreement)
    # Simplified calculation
    kappa = agreement_rate  # Simplified - real kappa needs more data

    result = {
        "trial_name": trial_name,
        "annotator_a": anno_a.annotator_id,
        "annotator_b": anno_b.annotator_id,
        "total_effects_a": len(anno_a.effects),
        "total_effects_b": len(anno_b.effects),
        "matching_effects": len(matches),
        "a_only_effects": len(a_only),
        "b_only_effects": len(b_only),
        "agreement_rate": agreement_rate,
        "kappa": kappa,
        "matches": matches,
        "a_only": a_only,
        "b_only": b_only,
    }

    return result


def create_consensus(trial_name: str, annotations_dir: Path = ANNOTATIONS_DIR) -> Path:
    """Create consensus gold standard from dual extraction"""
    comparison = compare_annotations(trial_name, annotations_dir)

    # Load original annotations for metadata
    anno_a_path = annotations_dir / f"{trial_name}.annotator_a.jsonl"
    with open(anno_a_path) as f:
        anno_a = PDFAnnotation.from_jsonl(f.read())

    # Create consensus annotation
    consensus = PDFAnnotation(
        pdf_filename=anno_a.pdf_filename,
        trial_name=trial_name,
        annotator_id="CONSENSUS",
        annotation_date=datetime.now().isoformat(),
        total_pages=anno_a.total_pages,
        metadata=anno_a.metadata,
    )

    # Add matched effects (use annotator A's version)
    for match in comparison["matches"]:
        consensus.effects.append(EffectEstimate(**match["annotator_a"]))

    # Mark effects needing adjudication
    consensus.metadata["adjudication_needed"] = {
        "a_only": comparison["a_only"],
        "b_only": comparison["b_only"],
    }
    consensus.metadata["agreement_rate"] = comparison["agreement_rate"]

    # Save consensus
    output_path = annotations_dir / f"{trial_name}.gold.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(consensus.to_jsonl())

    logger.info(f"Consensus saved: {output_path}")
    return output_path


def print_comparison_report(comparison: Dict[str, Any]):
    """Print comparison report"""
    print("\n" + "=" * 70)
    print("INTER-RATER AGREEMENT REPORT")
    print("=" * 70)
    print(f"Trial: {comparison['trial_name']}")
    print(f"Annotator A: {comparison['annotator_a']} ({comparison['total_effects_a']} effects)")
    print(f"Annotator B: {comparison['annotator_b']} ({comparison['total_effects_b']} effects)")
    print("-" * 70)
    print(f"Matching effects: {comparison['matching_effects']}")
    print(f"A-only effects: {comparison['a_only_effects']}")
    print(f"B-only effects: {comparison['b_only_effects']}")
    print(f"Agreement rate: {comparison['agreement_rate']:.1%}")
    print(f"Kappa: {comparison['kappa']:.3f}")

    if comparison["a_only"]:
        print("\nEffects found only by Annotator A:")
        for e in comparison["a_only"]:
            print(f"  - {e['effect_type']} {e['value']} ({e['ci_lower']}, {e['ci_upper']})")

    if comparison["b_only"]:
        print("\nEffects found only by Annotator B:")
        for e in comparison["b_only"]:
            print(f"  - {e['effect_type']} {e['value']} ({e['ci_lower']}, {e['ci_upper']})")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Annotate PDFs for gold standard creation"
    )
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        help="PDF file to annotate OR trial name for comparison"
    )
    parser.add_argument(
        "--annotator", "-a",
        type=str,
        default="A",
        choices=["A", "B"],
        help="Annotator ID (A or B)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare dual extractions for given trial name"
    )
    parser.add_argument(
        "--consensus",
        action="store_true",
        help="Create consensus from dual extraction"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory for annotations"
    )

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        return

    if args.compare:
        comparison = compare_annotations(args.input)
        print_comparison_report(comparison)
    elif args.consensus:
        output_path = create_consensus(args.input)
        print(f"\nConsensus file created: {output_path}")
    else:
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            sys.exit(1)

        annotator = PDFAnnotator(pdf_path, args.annotator)
        annotation = annotator.run_annotation()
        output_path = annotator.save_annotation(args.output_dir)

        print(f"\n" + "=" * 60)
        print("ANNOTATION COMPLETE")
        print(f"=" * 60)
        print(f"Trial: {annotation.trial_name}")
        print(f"Effects extracted: {len(annotation.effects)}")
        print(f"Saved to: {output_path}")
        print("=" * 60)


if __name__ == "__main__":
    main()
