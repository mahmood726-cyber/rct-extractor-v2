"""
Primary Outcome Detector
==========================

Heuristic scoring to identify which extracted effect estimate
corresponds to the primary outcome of a clinical trial.

Scoring weights:
- Abstract presence (weight 5): Effect appears in abstract section
- "Primary endpoint/outcome" label nearby (weight 4)
- First effect in results section (weight 3)
- Table row labeled "Primary" (weight 2)
- Has p-value reported (weight 1)

Output: Each Extraction gets is_primary: bool + primary_score: float
"""

import re
from typing import List, Optional


# Patterns indicating primary outcome context
PRIMARY_LABEL_PATTERNS = [
    (r'primary\s+(?:end\s*point|outcome|efficacy\s+(?:end\s*point|outcome))', 4),
    (r'primary\s+composite\s+(?:end\s*point|outcome)', 4),
    (r'primary\s+analysis', 3),
    (r'primary\s+objective', 3),
    (r'co-?primary\s+(?:end\s*point|outcome)', 3),
    (r'principal\s+(?:end\s*point|outcome)', 3),
]

# Patterns indicating secondary outcome
SECONDARY_PATTERNS = [
    r'secondary\s+(?:end\s*point|outcome)',
    r'exploratory\s+(?:end\s*point|outcome|analysis)',
    r'post[- ]?hoc\s+analysis',
    r'subgroup\s+analysis',
    r'safety\s+(?:end\s*point|outcome)',
    r'adverse\s+event',
]


class PrimaryOutcomeDetector:
    """
    Detect which extraction is the primary outcome using heuristic scoring.
    """

    def __init__(self):
        self._primary_patterns = [
            (re.compile(p, re.IGNORECASE), w)
            for p, w in PRIMARY_LABEL_PATTERNS
        ]
        self._secondary_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in SECONDARY_PATTERNS
        ]

    def score_extractions(
        self,
        extractions: List,
        full_text: str,
    ) -> List:
        """
        Score each extraction for primary outcome likelihood.

        Modifies extractions in-place: sets is_primary and primary_score.
        The highest-scoring extraction gets is_primary=True.
        If tied, the earliest extraction (by char_start) wins.

        Args:
            extractions: List of Extraction objects
            full_text: Full text of the document

        Returns:
            The same list of extractions (modified in-place)
        """
        if not extractions:
            return extractions

        # Detect abstract boundary
        abstract_end = self._find_abstract_end(full_text)

        # Detect results section
        results_start = self._find_results_start(full_text)

        # Score each extraction
        scores = []
        for ext in extractions:
            score = self._score_extraction(ext, full_text, abstract_end, results_start)
            ext.primary_score = score
            scores.append(score)

        # Find max score
        max_score = max(scores) if scores else 0
        if max_score <= 0:
            return extractions

        # Count how many have max score
        max_count = sum(1 for s in scores if s == max_score)

        # Only mark primary if there's a unique winner
        if max_count == 1:
            for ext, score in zip(extractions, scores):
                ext.is_primary = (score == max_score)
        elif max_count > 1:
            # v5.2: Tiebreak by earliest char_start (first in document wins)
            # char_start=0 is the default for table extractions — sort last
            tied_indices = [i for i, s in enumerate(scores) if s == max_score]
            def tiebreak_key(i):
                cs = extractions[i].char_start
                return cs if cs > 0 else float('inf')
            earliest_idx = min(tied_indices, key=tiebreak_key)
            extractions[earliest_idx].is_primary = True

        return extractions

    def _score_extraction(
        self,
        extraction,
        full_text: str,
        abstract_end: int,
        results_start: int,
    ) -> float:
        """Score a single extraction for primary outcome likelihood."""
        score = 0.0
        char_start = extraction.char_start
        source_text = extraction.source_text

        # 1. Abstract presence (weight 5)
        if abstract_end > 0 and char_start < abstract_end:
            score += 5.0

        # 2. "Primary endpoint/outcome" label nearby (weight 4)
        # Check 500 chars before the extraction
        context_start = max(0, char_start - 500)
        context = full_text[context_start:char_start + len(source_text) + 100]

        for pattern, weight in self._primary_patterns:
            if pattern.search(context):
                score += weight
                break  # Only count once

        # 2b. Penalty for secondary/exploratory context
        for pattern in self._secondary_patterns:
            if pattern.search(context):
                score -= 2.0
                break

        # 3. First effect in results section (weight 3)
        if results_start > 0 and char_start > 0:
            # Check if this is the first extraction in the results section
            if char_start >= results_start:
                # Distance from results start — closer = more likely primary
                distance = char_start - results_start
                if distance < 500:
                    score += 3.0
                elif distance < 1500:
                    score += 1.5

        # 4. Table row labeled "Primary" (weight 2)
        if "[table]" in source_text.lower():
            if re.search(r'primary', source_text, re.IGNORECASE):
                score += 2.0

        # 5. Has p-value reported (weight 1)
        if extraction.p_value is not None:
            score += 1.0

        # 6. Has complete CI (weight 0.5)
        if extraction.has_complete_ci:
            score += 0.5

        # 7. (v5.2) Bonus for having BOTH p-value AND CI (weight 1.5)
        # Primary outcomes typically report both; secondary often omit one.
        # Combined p+CI bonus (+3.0 total) can exceed abstract presence (+5.0)
        # when near results heading (+3.0). This is intentional: a fully-reported
        # result is a stronger primary signal than an abstract mention lacking stats.
        if extraction.p_value is not None and extraction.has_complete_ci:
            score += 1.5

        return score

    def _find_abstract_end(self, text: str) -> int:
        """Find the character position where the abstract ends."""
        patterns = [
            r'\n\s*(?:Introduction|Background|Methods?|Materials?\s+and\s+Methods?)\s*\n',
            r'\n\s*INTRODUCTION\s*\n',
            r'\n\s*BACKGROUND\s*\n',
            r'\n\s*METHODS?\s*\n',
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.start()

        # Fallback: first 2000 chars as rough abstract estimate
        return min(2000, len(text) // 4)

    def _find_results_start(self, text: str) -> int:
        """Find where the Results section begins."""
        patterns = [
            r'\n\s*Results?\s*\n',
            r'\n\s*RESULTS?\s*\n',
            r'\n\s*Findings?\s*\n',
            r'\n\s*FINDINGS?\s*\n',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.end()
        return 0
