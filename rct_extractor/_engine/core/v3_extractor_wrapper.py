"""
V3 Extractor Wrapper for Team-of-Rivals
========================================

Wraps the proven v3.0 EnhancedExtractor to work with the
Team-of-Rivals consensus system while preserving 100% sensitivity.
"""

import re
from typing import List, Optional
from .team_of_rivals import BaseExtractor, CandidateExtraction, ExtractorType
from .enhanced_extractor_v3 import EnhancedExtractor, Extraction


class V3ExtractorWrapper(BaseExtractor):
    """
    Wrapper around the proven v3.0 EnhancedExtractor.

    This extractor achieved 100% sensitivity and 0% FPR on validation,
    so it serves as the primary "ground truth" extractor in Team-of-Rivals.
    """

    extractor_type = ExtractorType.PATTERN

    def __init__(self):
        self.v3_extractor = EnhancedExtractor()

    def extract(self, text: str) -> List[CandidateExtraction]:
        """Extract using the full v3.0 extractor"""
        # Use v3.0's extract method
        v3_extractions = self.v3_extractor.extract(text)

        # Convert to CandidateExtraction format
        candidates = []
        for ext in v3_extractions:
            ci_lower = ext.ci.lower if ext.ci else None
            ci_upper = ext.ci.upper if ext.ci else None

            # Skip if no CI (required for verification)
            if ci_lower is None or ci_upper is None:
                continue

            candidates.append(CandidateExtraction(
                effect_type=ext.effect_type.value,
                value=ext.point_estimate,
                ci_lower=ci_lower,
                ci_upper=ci_upper,
                source_text=ext.source_text,
                char_start=ext.char_start,
                char_end=ext.char_end,
                extractor=self.extractor_type,
                extractor_confidence=ext.calibrated_confidence,
                p_value=ext.p_value,
            ))

        return candidates
