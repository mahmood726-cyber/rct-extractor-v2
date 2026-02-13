"""
Main RCT Extractor - Orchestrates the extraction pipeline.
Integrates PDF parsing, table extraction, endpoint matching, and validation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import re
import yaml
import logging
import time
from datetime import datetime

from rapidfuzz import fuzz, process

from .models import (
    ExtractionOutput, ExtractionRecord, PaperMetadata, Arm,
    BinaryOutcome, HazardRatioCI, OddsRatioCI, RiskRatioCI, MeanDifference,
    Provenance, BoundingBox, Timepoint, EndpointType, AnalysisPopulation,
    ExtractionConfidence, TableType, ReviewQueueItem, ReviewSeverity
)
from ..pdf.pdf_parser import PDFParser, PDFContent, PageContent, BBox
from ..tables.table_extractor import TableExtractor, TableStructure
from ..validators.validators import Validator, ValidationReport

logger = logging.getLogger(__name__)


# ============================================================
# NUMERIC PARSERS
# ============================================================

class NumericParser:
    """
    Parse numeric values from text with provenance.

    Patterns are derived from battle-tested RCTExtractor_v4_8_AI.js
    which achieved 100% accuracy on 40 real-world NEJM/Lancet/JAMA publications.
    """

    # Patterns for different numeric formats
    # COMPREHENSIVE: Integrates all patterns from RCTExtractor_v4_8_AI.js
    HR_PATTERNS = [
        # PRIORITY 1: Most common NEJM/Lancet/JAMA patterns
        # Pattern: "hazard ratio for X was VALUE (95% CI, A to B)" - THE MOST COMMON
        r'hazard\s*ratio\s+for\s+[^)]+?\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)\s*%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # Pattern: "hazard ratio for disease progression or death was VALUE (95% CI, A to B)"
        r'hazard\s*ratio\s+for\s+(?:disease\s+)?(?:progression|death|hospitalization)[\w\s]*was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # Pattern: "hazard ratio for X with Y was VALUE (95% CI, A to B)"
        r'hazard\s*ratio\s+for\s+\w+(?:\s+with\s+[\w\s]+)?\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # Pattern: "hazard ratio was VALUE (95% CI, A to B)"
        r'hazard\s*ratio\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',

        # Patterns with "99.5% CI" or other confidence levels
        r'hazard\s*ratio\s+for\s+[^)]+?\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)\s*%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',

        # REAL-WORLD PATTERNS from NEJM/Lancet/JAMA publications
        # Pattern: "hazard ratio in the X group, VALUE; 95% CI, A to B"
        r'hazard\s*ratio\s+in\s+the\s+[\w\-]+\s+group[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio with X, VALUE; 95% CI, A to B" (multi-word treatments)
        r'hazard\s*ratio\s+with\s+[\w\-]+(?:\s+[\w\-]+)?[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*(?:confidence\s+interval\s+\[?CI\]?|CI)[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio for X, as compared with Z, was VALUE"
        r'hazard\s*ratio\s+for\s+[\w\-]+(?:\s+in\s+the\s+[\w\-]+\s+group)?(?:[^,]*,\s*as\s+compared\s+with[^,]*,)?\s*was\s*(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: JAMA bracket format "hazard ratio, VALUE [95% CI, A-B]"
        r'hazard\s*ratio[,;:\s]*(\d+[·.]?\d*)\s*\[(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*[-–to]+\s*(\d+[·.]?\d*)\]',
        # Pattern: Lancet format with middle dots "hazard ratio VALUE, 95% CI A–B"
        r'hazard\s*ratio\s+(\d+[·.]?\d*)[,;]\s*(\d+[·.]?\d*)%?\s*CI\s*(\d+[·.]?\d*)\s*[-–to]+\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio for the X dose vs. Y, VALUE; 95% CI"
        r'hazard\s*ratio\s+for\s+(?:the\s+)?[\w\-]+(?:\s+dose)?\s+vs\.?\s+\w+[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratios...were VALUE (95% CI, A to B)"
        r'hazard\s*ratios?\s+(?:for\s+)?[^0-9]+?(?:were|was)\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)\)',
        # Pattern: "Hazard ratio for [any text] was VALUE (95% CI, A-B)"
        r'hazard\s*ratio\s+for\s+.+?\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio was VALUE (95% CI, A-B)"
        r'hazard\s*ratio\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*[-–]\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio was VALUE (95% confidence interval [CI], A to B)" - full CI name
        r'hazard\s*ratio\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*confidence\s+interval\s+\[?CI\]?[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "HR VALUE (95% confidence interval LOW-HIGH" - abbreviation with full "confidence interval"
        r'(?:HR)\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*confidence\s+interval\s*(\d+[·.]?\d*)\s*[-–]\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio of VALUE (95% CI, LOW to HIGH" - "of" before value
        r'hazard\s*ratio\s+of\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "hazard ratio in the X group was VALUE (95% confidence interval [CI], LOW to HIGH"
        r'hazard\s*ratio\s+in\s+the\s+[\w\-]+\s+group\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*confidence\s+interval\s+\[?CI\]?[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # HR bracket format: "HR = 0.75 [95% CI: 0.62-0.90]"
        r'(?:HR|hazard\s*ratio)[,;:\s=]*(\d+\.?\d*)\s*\[(\d+\.?\d*)%?\s*CI[,:\s]*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)\]',
        # Standard formats
        r'(?:HR|hazard\s*ratio)[,;:\s=]*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:hazard\s*ratio)[,;:\s]*(\d+\.?\d*)[;,]\s*(\d+\.?\d*)%?\s*confidence\s*interval\s*\[?CI\]?[,:\s]*(\d+\.?\d*)\s*(?:to|-|–)\s*(\d+\.?\d*)',
        # Oncology format - "hazard ratio for death, X.XX; 95% CI X.XX to X.XX"
        r'(?:hazard\s*ratio)\s+(?:for\s+)?(?:death|progression|disease|survival)[^,]*,\s*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        # Simple HR patterns (value only)
        r'(?:HR|hazard\s*ratio)[,;:\s=]+(\d+\.?\d*)',
        r'(?:hazard\s+ratio\s+(?:of|was|=))\s*(\d+\.?\d*)',
    ]

    OR_PATTERNS = [
        # PRIORITY 1: Common patterns with "to"
        # "odds ratio for X was VALUE (95% CI, A to B)"
        r'odds\s*ratio\s+for\s+[^)]+?was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # "odds ratio for X was VALUE (95% CI A-B)" - without comma
        r'odds\s*ratio\s+for\s+[^)]+?was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI\s+(\d+[·.]?\d*)\s*[-–]\s*(\d+[·.]?\d*)',
        # Pattern: "Odds ratio for X was VALUE (95% CI, A-B)"
        r'odds\s*ratio\s+for\s+\w+\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*[-–]\s*(\d+[·.]?\d*)',
        # Pattern: "odds ratio with X therapy, VALUE; 95% CI, A to B"
        r'odds\s*ratio\s+with\s+[\w\-]+(?:\s+therapy|\s+treatment)?[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Pattern: "adjusted odds ratio, VALUE; 95% CI, A to B"
        r'adjusted\s*odds\s*ratio[,;:\s]*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Standard OR patterns
        r'(?:OR|odds\s*ratio)[,;:\s=]*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:adjusted\s+)?(?:odds\s*ratio)[,;:\s=]*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:common\s+)?(?:odds\s*ratio)[,;:\s]+(?:was|of|=)?\s*(\d+\.?\d*)\s*\(?(\d+\.?\d*)%?\s*CI[,:\s]*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:odds\s*ratio)(?:\s+\w+)*\s+(?:was|of|=)\s*(\d+\.?\d*)',
        r'(?:odds\s*ratio|OR)[,;:\s=]+(\d+\.?\d*)',
    ]

    RR_PATTERNS = [
        # PRIORITY 1: Most common patterns
        # "rate ratio vs X, VALUE; 95% CI, A to B" - IMPACT pattern
        r'rate\s*ratio\s+vs\s+[\w\-]+[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # "rate ratio for death with X was VALUE (95% CI, A to B)"
        r'rate\s*ratio\s+for\s+[^)]+?was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # "relative risk of X was VALUE (95% CI, A to B)"
        r'relative\s*risk\s+of\s+[^)]+?was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # "relative risk of hospitalization was VALUE (95% BCI, A to B)" - Bayesian CI
        r'relative\s*risk\s+of\s+[^)]+?was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*BCI[,:\s]*(\d+[·.]?\d*)\s+to\s+(\d+[·.]?\d*)',
        # "rate ratio for X was VALUE (95% CI, A to B)"
        r'rate\s*ratio\s+for\s+\w+\s+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # "relative risk of X was VALUE (95% CI, A to B)"
        r'relative\s*risk\s+(?:of\s+)?[\w\s]+was\s+(\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # "rate ratio vs X, VALUE; 95% CI, A to B"
        r'rate\s*ratio(?:\s+vs\.?\s+\w+)?[,;]\s*(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # "rate ratio, VALUE; 95% CI, A to B"
        r'rate\s*ratio[,;:\s]+(\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*(\d+[·.]?\d*)\s*(?:to|[-–])\s*(\d+[·.]?\d*)',
        # Standard RR patterns
        r'(?:RR|relative\s*risk)[,;:\s=]*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:RR|relative\s*risk)\s+(?:was|of|=)\s*(\d+\.?\d*)',
        r'(?:relative\s*risk)[,;:\s=]+(\d+\.?\d*)',
        r'(?:age-adjusted\s+)?(?:rate\s*ratio)[,;:\s=]*(\d+\.?\d*)\s*[;,]?\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
        r'(?:rate\s*ratio)[,;:\s]+(?:for\s+\w+[,;:\s]+)?(\d+\.?\d*)[;,]\s*(\d+\.?\d*)%?\s*CI[,:\s]*(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d*)',
    ]

    RD_PATTERNS = [
        # PRIORITY 1: Common patterns with "to"
        # "difference in X was VALUE% (95% CI, A% to B%)"
        r'difference\s+in\s+[^)]+?was\s+([−\-]?\d+[·.]?\d*)\s*%?\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*%?\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference, VALUE percentage points; 95% CI, A to B"
        r'difference[,;:\s]+([−\-]?\d+[·.]?\d*)\s*percentage\s*points[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        # "difference was VALUE percentage points (95% CI, A to B)"
        r'difference\s+(?:was\s+)?([−\-]?\d+[·.]?\d*)\s*percentage\s*points\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        # Risk difference with unicode minus and middle dots
        r'adjusted\s*risk\s*difference\s*([−\-]?\d+[·.]?\d*)%?\s*\[?(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)\]?',
        r'risk\s*difference\s*([−\-]?\d+[·.]?\d*)%?\s*\((\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)\)',
        r'(?:risk\s*difference|RD|ARR|absolute\s*risk\s*reduction)[,;:\s=]*(-?\d+\.?\d*)\s*%?\s*(?:percentage\s*points)?',
    ]

    MD_PATTERNS = [
        # PRIORITY 1: Weight loss / metabolic patterns (STEP, SURMOUNT trials)
        # "estimated treatment difference was VALUE percentage points (95% CI, A to B)" - STEP-4 pattern
        r'(?:estimated\s+)?treatment\s+difference\s+was\s+([−\-]?\d+[·.]?\d*)\s*percentage\s*points\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "treatment difference in body weight was VALUE percentage points (95% CI, A to B)"
        r'(?:estimated\s+)?treatment\s+difference\s+in\s+[^)]+?was\s+([−\-]?\d+[·.]?\d*)\s*percentage\s*points\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference in weight change was VALUE percentage points (95% CI, A to B)"
        r'difference\s+in\s+[^)]+?was\s+([−\-]?\d+[·.]?\d*)\s*percentage\s*points\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference in HbA1c was VALUE percentage points (95% CI, A to B)"
        r'difference\s+in\s+[\w\-]+\s+was\s+([−\-]?\d+[·.]?\d*)\s*percentage\s*points\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference in [multi-word phrase] was VALUE ml (95% CI, A to B)" - INBUILD pattern
        r'difference\s+in\s+[^)]+?was\s+([−\-]?\d+[·.]?\d*)\s*(?:ml|mL)?\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference in X score change was VALUE (95% CI, A-B)" - TRAILBLAZER pattern (with dash)
        r'difference\s+in\s+[^)]+?was\s+([−\-]?\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*[-–]\s*([−\-]?\d+[·.]?\d*)',
        # "estimated treatment difference, VALUE percentage points; 95% CI, A to B"
        r'(?:estimated\s+)?treatment\s+difference[,;:\s]+([−\-]?\d+[·.]?\d*)\s*percentage\s*points[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "difference, VALUE percentage points; 95% CI, A to B"
        r'difference[,;:\s]+([−\-]?\d+[·.]?\d*)\s*percentage\s*points[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s+to\s+([−\-]?\d+[·.]?\d*)',
        # "mean change was VALUE percentage points (95% CI, A to B)"
        r'mean\s+change\s+was\s+([−\-]?\d+[·.]?\d*)\s*(?:percentage\s+points)?\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        # "difference in X was VALUE (95% CI, A to B)"
        r'difference\s+in\s+[\w\-]+\s+was\s+([−\-]?\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        # "difference was VALUE (95% CI, A to B)"
        r'difference\s+was\s+([−\-]?\d+[·.]?\d*)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        # Mean/treatment difference with unicode minus
        r'difference[,;:\s]+([−\-]?\d+[·.]?\d*)\s*[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        r'(?:estimated\s+)?treatment\s+difference[^,]*,\s*([−\-]?\d+[·.]?\d*)\s*(?:percentage\s*points)?[;,]\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*(?:to|[-–])\s*([−\-]?\d+[·.]?\d*)',
        r'difference\s+([−\-]?\d+[·.]?\d*)\s*(?:mL|ml|L|liters?)\s*\(\s*(\d+[·.]?\d*)%?\s*CI[,:\s]*([−\-]?\d+[·.]?\d*)\s*[-–]\s*([−\-]?\d+[·.]?\d*)',
        r'\(?difference\s+(-?\d+\.?\d*)\s*(?:ml\/year|ml\/min|mm\s*Hg|kg|g|%|points?)?[;,]\s*(\d+\.?\d*)%?\s*CI\s*(-?\d+\.?\d*)\s*[-–to]+\s*(-?\d+\.?\d*)',
        r'(?:MD|mean\s*difference)[,;:\s=]+(-?\d+\.?\d*)\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(-?\d+\.?\d*)?\s*(?:to|-|–)?\s*(-?\d+\.?\d*)?',
    ]

    EVENTS_PATTERNS = [
        # 100/500 (20%)
        r'(\d+)\s*/\s*(\d+)\s*\((\d+\.?\d*)%?\)',
        # "187 deaths (7.5%)" or "100 events (20%)"
        r'(\d+)\s+\w+\s*\((\d+\.?\d*)%\)',
        # 100 (20%) or 100 of 500
        r'(\d+)\s*(?:\((\d+\.?\d*)%\)|\s+of\s+(\d+))',
        # n=100, events=20
        r'(?:events?|n)[=:\s]*(\d+)',
    ]

    PVALUE_PATTERNS = [
        r'[pP]\s*[=<>]\s*([\d.]+)',
        r'[pP]\s*-?\s*value[:\s]*[=<>]?\s*([\d.]+|<\s*[\d.]+)',
    ]

    NNT_PATTERNS = [
        r'(?:NNT|number\s*needed\s*to\s*treat)[,;:\s=]*(\d+\.?\d*)\s*(?:\(?(\d+\.?\d*)%?\s*CI[,:\s]*)?(\d+\.?\d*)?\s*[-–to]*\s*(\d+\.?\d*)?',
        r'(?:The\s+)?NNT\s+(?:to\s+prevent\s+one\s+)?(?:\w+\s+)*(?:event\s+)?was\s+(\d+)\s*\((\d+\.?\d*)%?\s*CI[,:\s]*(\d+)\s*[-–to]+\s*(\d+)\)',
        r'NNT\s+(?:for\s+)?(?:\w+\s+)*(?:\w+)?\s*[:=]?\s*(\d+)\s*\((\d+\.?\d*)%?\s*CI[,:\s]*(\d+)\s*[-–to]+\s*(\d+)\)',
    ]

    @classmethod
    def parse_hazard_ratio(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract HR and CI from text"""
        text = cls._normalize_text(text)

        for pattern in cls.HR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    hr = float(groups[0])
                    ci_level = float(groups[1]) / 100 if len(groups) > 1 and groups[1] else 0.95
                    ci_low = float(groups[2]) if len(groups) > 2 else None
                    ci_high = float(groups[3]) if len(groups) > 3 else None

                    if hr > 0 and ci_low and ci_high and ci_low < ci_high:
                        return {
                            'hr': hr,
                            'ci_low': ci_low,
                            'ci_high': ci_high,
                            'ci_level': ci_level,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                except (ValueError, IndexError):
                    continue

        return None

    @classmethod
    def parse_odds_ratio(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract OR and CI from text"""
        text = cls._normalize_text(text)

        for pattern in cls.OR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    return {
                        'or': float(groups[0]),
                        'ci_low': float(groups[2]) if len(groups) > 2 else None,
                        'ci_high': float(groups[3]) if len(groups) > 3 else None,
                        'raw_match': match.group(0),
                        'span': (match.start(), match.end())
                    }
                except (ValueError, IndexError):
                    continue

        return None

    @classmethod
    def parse_events_n(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract events/n from text"""
        for pattern in cls.EVENTS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    if '/' in match.group(0):
                        # Pattern: events/total (percentage)
                        events = int(groups[0])
                        n = int(groups[1])
                        pct = float(groups[2]) if len(groups) > 2 and groups[2] else (events / n * 100)
                        return {
                            'events': events,
                            'n': n,
                            'percentage': pct,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                    elif '%' in match.group(0) and len(groups) >= 2 and groups[1]:
                        # Pattern: "187 deaths (7.5%)" — events + percentage, no total
                        events = int(groups[0])
                        pct = float(groups[1])
                        return {
                            'events': events,
                            'n': None,
                            'percentage': pct,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                    elif 'of' in match.group(0).lower() and len(groups) >= 3 and groups[2]:
                        # Pattern: "100 of 500"
                        events = int(groups[0])
                        n = int(groups[2])
                        return {
                            'events': events,
                            'n': n,
                            'percentage': events / n * 100,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                except (ValueError, IndexError, ZeroDivisionError):
                    continue

        return None

    @classmethod
    def parse_p_value(cls, text: str) -> Optional[Tuple[float, str]]:
        """Extract p-value from text"""
        for pattern in cls.PVALUE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                if '<' in raw:
                    # p < 0.001
                    num = re.search(r'[\d.]+', raw)
                    if num:
                        return (float(num.group()), raw)
                else:
                    try:
                        return (float(raw), raw)
                    except ValueError:
                        pass
        return None

    @classmethod
    def parse_relative_risk(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract RR and CI from text"""
        text = cls._normalize_text(text)

        for pattern in cls.RR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    rr = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    if rr > 0:
                        return {
                            'rr': rr,
                            'ci_low': ci_low,
                            'ci_high': ci_high,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                except (ValueError, IndexError):
                    continue
        return None

    @classmethod
    def parse_risk_difference(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract risk difference and CI from text"""
        text = cls._normalize_text(text)

        for pattern in cls.RD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    rd = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    return {
                        'rd': rd,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'raw_match': match.group(0),
                        'span': (match.start(), match.end())
                    }
                except (ValueError, IndexError):
                    continue
        return None

    # Patterns that indicate false positive (SD, IQR, SE, not CI)
    MD_REJECTION_PATTERNS = [
        r'\(SD\s',           # (SD 4.2) - standard deviation
        r'\(SE\s',           # (SE 0.5) - standard error
        r'\(IQR\s',          # (IQR 1.8-4.6) - interquartile range
        r'\(SEM\s',          # (SEM 0.3) - standard error of mean
        r'SD\s*[=:]\s*\d',   # SD = 4.2 or SD: 4.2
        r'\bSD\s+\d',        # SD 4.2
    ]

    @classmethod
    def parse_mean_difference(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract mean difference and CI from text"""
        text = cls._normalize_text(text)

        # Reject if text contains SD/SE/IQR instead of CI (false positive check)
        for reject_pattern in cls.MD_REJECTION_PATTERNS:
            if re.search(reject_pattern, text, re.IGNORECASE):
                return None

        for pattern in cls.MD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    md = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    return {
                        'md': md,
                        'ci_low': ci_low,
                        'ci_high': ci_high,
                        'raw_match': match.group(0),
                        'span': (match.start(), match.end())
                    }
                except (ValueError, IndexError):
                    continue
        return None

    @classmethod
    def parse_nnt(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract NNT and CI from text"""
        text = cls._normalize_text(text)

        for pattern in cls.NNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    nnt = float(groups[0])
                    ci_low = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    ci_high = float(groups[3]) if len(groups) > 3 and groups[3] else None

                    if nnt > 0:
                        return {
                            'nnt': nnt,
                            'ci_low': ci_low,
                            'ci_high': ci_high,
                            'raw_match': match.group(0),
                            'span': (match.start(), match.end())
                        }
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for pattern matching (handle Unicode chars)"""
        return text.replace('−', '-').replace('–', '-').replace('·', '.').replace('—', '-')


# ============================================================
# ENDPOINT MATCHER
# ============================================================

class EndpointMatcher:
    """Match extracted text to canonical endpoints"""

    def __init__(self, vocabulary_path: str):
        self.vocabulary = self._load_vocabulary(vocabulary_path)
        self.endpoint_index = self._build_index()

    def _load_vocabulary(self, path: str) -> Dict:
        """Load endpoint vocabulary from YAML"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_index(self) -> Dict[str, str]:
        """Build synonym -> canonical mapping"""
        index = {}
        for endpoint_id, endpoint_data in self.vocabulary.get('endpoints', {}).items():
            canonical = endpoint_data['canonical']
            for synonym in endpoint_data.get('synonyms', []):
                index[synonym.lower()] = canonical
            # Also add canonical itself
            index[canonical.lower()] = canonical
        return index

    def match(self, text: str, threshold: float = 70) -> Optional[Tuple[str, float]]:
        """Match text to canonical endpoint"""
        text_lower = text.lower().strip()

        # Exact match first
        if text_lower in self.endpoint_index:
            return (self.endpoint_index[text_lower], 100.0)

        # Fuzzy match
        best_match = process.extractOne(
            text_lower,
            self.endpoint_index.keys(),
            scorer=fuzz.token_set_ratio
        )

        if best_match and best_match[1] >= threshold:
            return (self.endpoint_index[best_match[0]], best_match[1])

        return None

    def get_endpoint_type(self, canonical: str) -> EndpointType:
        """Get endpoint type from vocabulary"""
        for endpoint_id, data in self.vocabulary.get('endpoints', {}).items():
            if data['canonical'] == canonical:
                type_str = data.get('type', 'unknown')
                return EndpointType(type_str)
        return EndpointType.UNKNOWN


# ============================================================
# MAIN EXTRACTOR
# ============================================================

class RCTExtractor:
    """
    Main extraction orchestrator.
    Implements the hybrid two-pass pipeline.
    """

    def __init__(
        self,
        vocabulary_path: str,
        use_ml_tables: bool = True,
        output_crops: bool = True
    ):
        self.pdf_parser = PDFParser(output_images=output_crops)
        self.table_extractor = TableExtractor(use_ml=use_ml_tables)
        self.endpoint_matcher = EndpointMatcher(vocabulary_path)
        self.validator = Validator()
        self.output_crops = output_crops

    def extract(self, pdf_path: str, output_dir: str = None) -> ExtractionOutput:
        """
        Main extraction method.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files (crops, etc.)

        Returns:
            ExtractionOutput with all extracted data
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize output
        output = ExtractionOutput(
            source_pdf=str(pdf_path),
            paper=PaperMetadata(),
            arms=[],
            extractions=[],
            overall_confidence=ExtractionConfidence.REVIEW_REQUIRED,
            review_queue=[],
            pages_processed=0,
            tables_found=0,
            extraction_time_seconds=0
        )

        try:
            # ========================================
            # PASS A: Structure-First Extraction
            # ========================================
            logger.info(f"PASS A: Parsing PDF {pdf_path}")

            # 1. Parse PDF
            pdf_content = self.pdf_parser.parse(str(pdf_path))
            output.pages_processed = pdf_content.num_pages

            # 2. Extract metadata
            output.paper = self._extract_metadata(pdf_content)

            # 3. Find and extract tables
            all_tables = []
            for page in pdf_content.pages:
                tables = self.table_extractor.extract_tables(str(pdf_path), page)
                all_tables.extend(tables)

            output.tables_found = len(all_tables)
            logger.info(f"Found {len(all_tables)} tables")

            # 4. Extract arms from baseline tables
            baseline_tables = [t for t in all_tables if t.table_type == TableType.BASELINE]
            output.arms = self._extract_arms(baseline_tables, pdf_content)

            # 5. Extract outcomes from outcome tables
            outcomes_tables = [t for t in all_tables if t.table_type == TableType.OUTCOMES]
            pass_a_extractions = self._extract_outcomes(outcomes_tables, output.arms, str(pdf_path))

            # 6. Also extract from full text (for inline results)
            text_extractions = self._extract_from_text(pdf_content, output.arms, str(pdf_path))

            # Merge extractions
            all_extractions = self._merge_extractions(pass_a_extractions, text_extractions)

            # ========================================
            # PASS B: Semantic Cross-Check
            # ========================================
            logger.info("PASS B: Semantic cross-check")

            # For each extraction, re-verify using region crops
            for extraction in all_extractions:
                pass_b_value = self._cross_check_extraction(extraction, pdf_content, str(pdf_path))
                if pass_b_value:
                    extraction.pass_b_value = str(pass_b_value)
                    extraction.passes_agree = (extraction.pass_a_value == extraction.pass_b_value)

            # ========================================
            # VALIDATION
            # ========================================
            logger.info("Validating extractions")

            validation_reports = self.validator.validate_all(all_extractions, output.arms)

            # Update confidence based on validation
            for i, report in enumerate(validation_reports):
                if i < len(all_extractions):
                    all_extractions[i].confidence = report.confidence
                    all_extractions[i].flags = [issue.code for issue in report.issues]

            # Generate review queue
            output.review_queue = self.validator.generate_review_queue(
                validation_reports, str(pdf_path)
            )

            output.extractions = all_extractions

            # Overall confidence
            if all(e.confidence == ExtractionConfidence.HIGH for e in all_extractions):
                output.overall_confidence = ExtractionConfidence.HIGH
            elif any(e.confidence == ExtractionConfidence.REVIEW_REQUIRED for e in all_extractions):
                output.overall_confidence = ExtractionConfidence.REVIEW_REQUIRED
            else:
                output.overall_confidence = ExtractionConfidence.MEDIUM

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            output.review_queue.append(ReviewQueueItem(
                record_id="EXTRACTION_FAILED",
                pdf_file=str(pdf_path),
                page_number=0,
                severity=ReviewSeverity.ERROR,
                reason_code="EXTRACTION_FAILED",
                reason_text=str(e),
                suggested_action="manual_extraction"
            ))

        output.extraction_time_seconds = time.time() - start_time
        return output

    def _extract_metadata(self, pdf_content: PDFContent) -> PaperMetadata:
        """Extract paper metadata from PDF"""
        metadata = PaperMetadata()

        # Try to find title (usually first large text on first page)
        if pdf_content.pages:
            first_page = pdf_content.pages[0]
            # Find largest font on first page
            max_font_size = 0
            title_text = ""
            for block in first_page.text_blocks[:20]:  # Check first 20 blocks
                if block.font_size and block.font_size > max_font_size:
                    max_font_size = block.font_size
                    title_text = block.text

            if title_text:
                metadata.title = title_text.strip()

        # Find NCT ID
        full_text = " ".join(p.full_text for p in pdf_content.pages)
        nct_match = re.search(r'NCT\d{8}', full_text)
        if nct_match:
            metadata.nct_id = nct_match.group(0)

        # Find year
        year_match = re.search(r'\b(19|20)\d{2}\b', full_text[:5000])
        if year_match:
            metadata.year = int(year_match.group(0))

        return metadata

    def _extract_arms(self, tables: List[TableStructure], pdf_content: PDFContent) -> List[Arm]:
        """Extract treatment arms from baseline tables"""
        arms = []
        seen_names = set()

        for table in tables:
            headers = table.get_headers()
            if not headers:
                continue

            # Look for arm names in headers
            for col_idx, header in enumerate(headers[0]):
                header_clean = header.strip()
                if not header_clean or header_clean.lower() in ['characteristic', 'variable', 'n', '%']:
                    continue

                if header_clean not in seen_names:
                    # Try to determine arm type
                    arm_type = "unknown"
                    header_lower = header_clean.lower()
                    if any(kw in header_lower for kw in ['placebo', 'control', 'usual care']):
                        arm_type = "placebo"
                    elif any(kw in header_lower for kw in ['treatment', 'active', 'intervention']):
                        arm_type = "treatment"

                    arm = Arm(
                        arm_id=f"arm_{len(arms)}",
                        arm_name=header_clean,
                        arm_type=arm_type
                    )

                    # Try to find n randomized
                    # Look in first data row for N value
                    first_row = table.get_row(1) if table.num_rows > 1 else []
                    if col_idx < len(first_row):
                        n_match = re.search(r'n\s*=?\s*(\d+)', first_row[col_idx].text, re.IGNORECASE)
                        if n_match:
                            arm.n_randomized = int(n_match.group(1))

                    arms.append(arm)
                    seen_names.add(header_clean)

        return arms

    def _extract_outcomes(
        self,
        tables: List[TableStructure],
        arms: List[Arm],
        pdf_path: str
    ) -> List[ExtractionRecord]:
        """Extract outcomes from outcome tables"""
        extractions = []

        for table in tables:
            # Find relevant columns
            arm_cols = {}
            hr_col = None
            ci_col = None

            headers = table.get_headers()
            if headers:
                for col_idx, header in enumerate(headers[0]):
                    header_lower = header.lower()

                    # Match to arms
                    for arm in arms:
                        if arm.arm_name.lower() in header_lower:
                            arm_cols[arm.arm_id] = col_idx
                            break

                    # Find HR/CI columns
                    if any(kw in header_lower for kw in ['hazard', 'hr', 'ratio']):
                        hr_col = col_idx
                    if any(kw in header_lower for kw in ['ci', 'confidence', 'interval']):
                        ci_col = col_idx

            # Process data rows
            for row_idx in range(table.header_rows, table.num_rows):
                row = table.get_row(row_idx)
                if not row:
                    continue

                # First cell is usually endpoint name
                endpoint_text = row[0].text if row else ""
                if not endpoint_text:
                    continue

                # Match to canonical endpoint
                match_result = self.endpoint_matcher.match(endpoint_text)
                if not match_result:
                    continue

                canonical, confidence = match_result
                endpoint_type = self.endpoint_matcher.get_endpoint_type(canonical)

                # Create provenance
                provenance = Provenance(
                    pdf_file=pdf_path,
                    page_number=table.page_num,
                    bbox=BoundingBox(
                        x1=table.bbox.x0,
                        y1=table.bbox.y0,
                        x2=table.bbox.x1,
                        y2=table.bbox.y1
                    ) if table.bbox else None,
                    raw_text=endpoint_text,
                    extraction_method="table_extraction"
                )

                extraction = ExtractionRecord(
                    endpoint_canonical=canonical,
                    endpoint_raw=endpoint_text,
                    endpoint_type=endpoint_type,
                    timepoint=Timepoint(raw_text=""),
                    confidence=ExtractionConfidence.MEDIUM,
                    confidence_score=confidence / 100
                )

                # Extract HR if available
                if hr_col is not None and hr_col < len(row):
                    hr_text = row[hr_col].text
                    hr_data = NumericParser.parse_hazard_ratio(hr_text)
                    if hr_data:
                        extraction.effect_estimate = HazardRatioCI(
                            hr=hr_data['hr'],
                            ci_low=hr_data['ci_low'],
                            ci_high=hr_data['ci_high'],
                            provenance=provenance
                        )
                        extraction.pass_a_value = f"HR={hr_data['hr']}"

                # Extract binary outcomes if available
                binary_outcomes = []
                for arm_id, col_idx in arm_cols.items():
                    if col_idx < len(row):
                        cell_text = row[col_idx].text
                        events_data = NumericParser.parse_events_n(cell_text)
                        if events_data:
                            binary_outcomes.append(BinaryOutcome(
                                arm_id=arm_id,
                                events=events_data['events'],
                                n=events_data['n'],
                                percentage=events_data.get('percentage'),
                                provenance=provenance
                            ))

                if binary_outcomes:
                    extraction.binary_outcomes = binary_outcomes
                    extraction.endpoint_type = EndpointType.BINARY

                if extraction.effect_estimate or extraction.binary_outcomes:
                    extractions.append(extraction)

        return extractions

    def _extract_from_text(
        self,
        pdf_content: PDFContent,
        arms: List[Arm],
        pdf_path: str
    ) -> List[ExtractionRecord]:
        """Extract outcomes from inline text (not in tables)"""
        extractions = []

        for page in pdf_content.pages:
            # Split into sentences
            sentences = re.split(r'[.!?]\s+', page.full_text)

            for sentence in sentences:
                # Look for HR patterns
                hr_data = NumericParser.parse_hazard_ratio(sentence)
                if hr_data:
                    # Try to identify endpoint from sentence
                    match_result = self.endpoint_matcher.match(sentence[:100])
                    canonical = match_result[0] if match_result else "UNKNOWN_ENDPOINT"

                    provenance = Provenance(
                        pdf_file=pdf_path,
                        page_number=page.page_num,
                        raw_text=sentence,
                        extraction_method="text_extraction"
                    )

                    extraction = ExtractionRecord(
                        endpoint_canonical=canonical,
                        endpoint_raw=sentence[:100],
                        endpoint_type=EndpointType.TIME_TO_EVENT,
                        timepoint=Timepoint(raw_text=""),
                        effect_estimate=HazardRatioCI(
                            hr=hr_data['hr'],
                            ci_low=hr_data['ci_low'],
                            ci_high=hr_data['ci_high'],
                            provenance=provenance
                        ),
                        pass_a_value=f"HR={hr_data['hr']}"
                    )
                    extractions.append(extraction)

        return extractions

    def _merge_extractions(
        self,
        table_extractions: List[ExtractionRecord],
        text_extractions: List[ExtractionRecord]
    ) -> List[ExtractionRecord]:
        """Merge extractions from different sources, preferring table data"""
        merged = table_extractions.copy()

        for text_ext in text_extractions:
            # Check if we already have this endpoint from tables
            is_duplicate = False
            for table_ext in table_extractions:
                if table_ext.endpoint_canonical == text_ext.endpoint_canonical:
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged.append(text_ext)

        return merged

    def _cross_check_extraction(
        self,
        extraction: ExtractionRecord,
        pdf_content: PDFContent,
        pdf_path: str
    ) -> Optional[str]:
        """
        PASS B: Re-extract value using different method.
        Returns the re-extracted value for comparison.
        """
        # If we have a bbox, try OCR on that region
        if extraction.effect_estimate and hasattr(extraction.effect_estimate, 'provenance'):
            prov = extraction.effect_estimate.provenance
            if prov.bbox and prov.page_number:
                # For now, just re-parse the raw text
                # In production, would OCR the cropped region
                raw_text = prov.raw_text

                hr_data = NumericParser.parse_hazard_ratio(raw_text)
                if hr_data:
                    return f"HR={hr_data['hr']}"

        return None
