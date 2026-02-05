#!/usr/bin/env python3
"""
RCT Classifier - Detect if a paper is an RCT results publication.
Filters out letters, protocols, reviews, and observational studies.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class StudyType(Enum):
    """Classification of study types"""
    RCT_RESULTS = "rct_results"           # Primary RCT results paper
    RCT_SECONDARY = "rct_secondary"       # Secondary analysis of RCT
    PROTOCOL = "protocol"                  # Trial protocol (no results)
    META_ANALYSIS = "meta_analysis"        # Systematic review / meta-analysis
    OBSERVATIONAL = "observational"        # Cohort, case-control, etc.
    LETTER = "letter"                      # Letter, correspondence, comment
    REVIEW = "review"                      # Narrative review
    OTHER = "other"                        # Unclassified


@dataclass
class ClassificationResult:
    """Result of RCT classification"""
    study_type: StudyType
    is_rct: bool
    has_results: bool
    confidence: float
    signals_found: List[str]
    signals_against: List[str]
    recommendation: str  # "include", "exclude", "review"


class RCTClassifier:
    """
    Classify papers as RCT results vs other study types.

    Based on keyword patterns from medical literature.
    """

    # Positive signals for RCT
    RCT_POSITIVE_PATTERNS = [
        (r'randomi[sz]ed\s+(?:controlled\s+)?(?:trial|study)', 'randomized_trial', 3),
        (r'randomly\s+(?:assigned|allocated)', 'random_assignment', 3),
        (r'double[- ]blind', 'double_blind', 2),
        (r'placebo[- ]controlled', 'placebo_controlled', 2),
        (r'intention[- ]to[- ]treat', 'itt_analysis', 2),
        (r'per[- ]protocol\s+analysis', 'per_protocol', 1),
        (r'CONSORT', 'consort', 2),
        (r'trial\s+registration', 'registered', 1),
        (r'NCT\d{8}', 'nct_id', 2),
        (r'primary\s+(?:end\s*point|outcome)', 'primary_endpoint', 2),
        (r'secondary\s+(?:end\s*point|outcome)', 'secondary_endpoint', 1),
    ]

    # Signals that results are present (not just protocol)
    RESULTS_POSITIVE_PATTERNS = [
        (r'(?:hazard|odds|risk)\s+ratio\s+(?:was|of|for)\s+\d', 'effect_reported', 3),
        (r'(?:HR|OR|RR)\s*[=:]\s*\d+\.\d+', 'effect_abbreviation', 3),
        (r'95%?\s*(?:CI|confidence)', 'confidence_interval', 2),
        (r'p\s*[<>=]\s*0\.\d+', 'p_value', 2),
        (r'we\s+found\s+that', 'findings_stated', 1),
        (r'results\s+show', 'results_show', 1),
        (r'statistically\s+significant', 'stat_significant', 2),
        (r'mean\s+difference\s+(?:was|of)', 'mean_diff_reported', 2),
        (r'number\s+needed\s+to\s+treat', 'nnt_reported', 2),
        (r'kaplan[- ]meier', 'survival_analysis', 1),
        (r'cox\s+(?:proportional|regression)', 'cox_model', 1),
    ]

    # Signals for protocol (no results yet)
    PROTOCOL_PATTERNS = [
        (r'study\s+protocol', 'protocol_title', 5),
        (r'trial\s+protocol', 'protocol_title', 5),
        (r'protocol\s+(?:for|of)\s+a', 'protocol_for', 4),
        (r'will\s+be\s+randomi[sz]ed', 'future_tense', 3),
        (r'planned\s+(?:enrollment|sample)', 'planned', 3),
        (r'we\s+will\s+(?:assess|evaluate|measure)', 'future_methods', 2),
        (r'this\s+(?:protocol|paper)\s+describes', 'describes_protocol', 3),
        (r'recruitment\s+(?:will|is\s+expected\s+to)\s+begin', 'future_recruitment', 3),
    ]

    # Signals for letter/correspondence
    LETTER_PATTERNS = [
        (r'^letter\s*(?:to\s+the\s+editor)?', 'letter_title', 5),
        (r'^correspondence\b', 'correspondence', 5),
        (r'^response\s+to', 'response', 4),
        (r'^comment\s+on', 'comment', 4),
        (r'^reply\s+to', 'reply', 4),
        (r'^editorial\b', 'editorial', 3),
        (r'dear\s+(?:editor|sir|madam)', 'dear_editor', 3),
        (r'in\s+response\s+to\s+the\s+(?:article|paper|letter)', 'in_response', 3),
    ]

    # Signals for meta-analysis/systematic review
    META_ANALYSIS_PATTERNS = [
        (r'systematic\s+review', 'systematic_review', 5),
        (r'meta[- ]analysis', 'meta_analysis', 5),
        (r'pooled\s+(?:analysis|estimate)', 'pooled_analysis', 3),
        (r'we\s+searched\s+(?:PubMed|MEDLINE|Embase|Cochrane)', 'database_search', 4),
        (r'PRISMA', 'prisma', 3),
        (r'(?:forest|funnel)\s+plot', 'ma_plot', 2),
        (r'heterogeneity\s+(?:was|I2)', 'heterogeneity', 2),
        (r'publication\s+bias', 'pub_bias', 2),
        (r'quality\s+assessment', 'quality_assessment', 1),
        (r'risk\s+of\s+bias', 'rob_assessment', 2),
    ]

    # Signals for observational study
    OBSERVATIONAL_PATTERNS = [
        (r'cohort\s+study', 'cohort', 4),
        (r'case[- ]control\s+study', 'case_control', 4),
        (r'cross[- ]sectional\s+study', 'cross_sectional', 4),
        (r'retrospective\s+(?:study|analysis)', 'retrospective', 3),
        (r'prospective\s+(?:cohort|observational)', 'prospective_obs', 3),
        (r'registry\s+(?:study|analysis|data)', 'registry', 2),
        (r'real[- ]world\s+(?:data|evidence)', 'rwd', 2),
        (r'propensity\s+score', 'propensity', 2),
    ]

    def __init__(self):
        """Initialize classifier with compiled patterns"""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns"""
        def compile_list(patterns):
            return [(re.compile(p, re.IGNORECASE | re.MULTILINE), name, weight)
                    for p, name, weight in patterns]

        self.rct_patterns = compile_list(self.RCT_POSITIVE_PATTERNS)
        self.results_patterns = compile_list(self.RESULTS_POSITIVE_PATTERNS)
        self.protocol_patterns = compile_list(self.PROTOCOL_PATTERNS)
        self.letter_patterns = compile_list(self.LETTER_PATTERNS)
        self.meta_patterns = compile_list(self.META_ANALYSIS_PATTERNS)
        self.observational_patterns = compile_list(self.OBSERVATIONAL_PATTERNS)

    def _score_patterns(self, text: str, patterns: list) -> tuple:
        """Score text against pattern list, return (score, signals_found)"""
        score = 0
        signals = []
        for pattern, name, weight in patterns:
            if pattern.search(text):
                score += weight
                signals.append(name)
        return score, signals

    def classify(self, text: str, title: str = "") -> ClassificationResult:
        """
        Classify a paper based on its text content.

        Args:
            text: Full text of paper (or first few pages)
            title: Paper title (optional, helps with letters)

        Returns:
            ClassificationResult with study type and confidence
        """
        # Combine title and text for analysis
        full_text = f"{title}\n{text}" if title else text

        # Use just first ~10000 chars for efficiency
        analysis_text = full_text[:10000]

        # Score against all pattern categories
        rct_score, rct_signals = self._score_patterns(analysis_text, self.rct_patterns)
        results_score, results_signals = self._score_patterns(analysis_text, self.results_patterns)
        protocol_score, protocol_signals = self._score_patterns(analysis_text, self.protocol_patterns)
        letter_score, letter_signals = self._score_patterns(analysis_text, self.letter_patterns)
        meta_score, meta_signals = self._score_patterns(analysis_text, self.meta_patterns)
        obs_score, obs_signals = self._score_patterns(analysis_text, self.observational_patterns)

        # Determine study type based on scores
        all_signals = rct_signals + results_signals
        against_signals = []

        # Check for letter first (usually short, clear signals)
        if letter_score >= 3:
            return ClassificationResult(
                study_type=StudyType.LETTER,
                is_rct=False,
                has_results=False,
                confidence=min(0.95, 0.5 + letter_score * 0.1),
                signals_found=letter_signals,
                signals_against=[],
                recommendation="exclude"
            )

        # Check for protocol
        if protocol_score >= 4 and results_score < 3:
            return ClassificationResult(
                study_type=StudyType.PROTOCOL,
                is_rct=True,
                has_results=False,
                confidence=min(0.95, 0.5 + protocol_score * 0.1),
                signals_found=rct_signals + protocol_signals,
                signals_against=results_signals,
                recommendation="exclude"
            )

        # Check for meta-analysis
        if meta_score >= 4:
            return ClassificationResult(
                study_type=StudyType.META_ANALYSIS,
                is_rct=False,
                has_results=True,
                confidence=min(0.95, 0.5 + meta_score * 0.1),
                signals_found=meta_signals + results_signals,
                signals_against=[],
                recommendation="include"  # Meta-analyses have effects too
            )

        # Check for observational
        if obs_score >= 4 and rct_score < 3:
            return ClassificationResult(
                study_type=StudyType.OBSERVATIONAL,
                is_rct=False,
                has_results=results_score >= 2,
                confidence=min(0.90, 0.5 + obs_score * 0.1),
                signals_found=obs_signals + results_signals,
                signals_against=rct_signals,
                recommendation="include" if results_score >= 2 else "review"
            )

        # Check for RCT with results
        if rct_score >= 3 and results_score >= 3:
            confidence = min(0.98, 0.5 + (rct_score + results_score) * 0.05)
            return ClassificationResult(
                study_type=StudyType.RCT_RESULTS,
                is_rct=True,
                has_results=True,
                confidence=confidence,
                signals_found=all_signals,
                signals_against=protocol_signals,
                recommendation="include"
            )

        # Check for RCT without clear results (might be secondary analysis)
        if rct_score >= 3:
            return ClassificationResult(
                study_type=StudyType.RCT_SECONDARY if results_score >= 1 else StudyType.PROTOCOL,
                is_rct=True,
                has_results=results_score >= 1,
                confidence=min(0.80, 0.4 + rct_score * 0.1),
                signals_found=all_signals,
                signals_against=protocol_signals,
                recommendation="review"
            )

        # Default: unclear
        return ClassificationResult(
            study_type=StudyType.OTHER,
            is_rct=False,
            has_results=results_score >= 2,
            confidence=0.3,
            signals_found=all_signals,
            signals_against=[],
            recommendation="review"
        )


def classify_pdf_text(text: str, title: str = "") -> ClassificationResult:
    """Convenience function to classify PDF text"""
    classifier = RCTClassifier()
    return classifier.classify(text, title)
