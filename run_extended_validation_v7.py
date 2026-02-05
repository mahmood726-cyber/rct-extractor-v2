"""
Extended Validation v7 for RCT Extractor v2.10
===============================================

Novel therapeutic areas and specialized trial designs:
1. Cardiac Amyloidosis Trials (ATTR-ACT, HELIOS-B, APOLLO-B) - 12 cases
2. Heart Failure Device Trials (COAPT, MITRA-FR, GALACTIC-HF) - 14 cases
3. TAVR/Structural Heart Trials (Evolut, PARTNER, NOTION) - 12 cases
4. Omega-3/Triglyceride Trials (REDUCE-IT, STRENGTH) - 10 cases
5. Advanced Kidney Trials (FIDELITY, EMPA-KIDNEY pooled) - 12 cases
6. AF Ablation Trials (CASTLE-AF, CABANA, EAST-AFNET) - 12 cases
7. ICD/CRT Trials (RAFT, DANISH, MADIT-CRT) - 10 cases
8. Additional Journal Patterns - 12 cases
9. Adversarial v7 - 16 cases

TOTAL: 110 test cases
"""
import sys
import re
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# =============================================================================
# TEXT NORMALIZATION AND EXTRACTION FUNCTIONS
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize unicode and special characters"""
    text = text.replace('\xb7', '.')
    text = text.replace('\u00b7', '.')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '-')
    text = text.replace('\u2212', '-')
    text = text.replace('–', '-')
    text = text.replace('—', '-')
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)
    return text


def extract_effects(text: str) -> List[Dict]:
    """Extract effect estimates from text - Extended v7"""
    text = normalize_text(text)
    results = []
    seen = set()

    patterns = {
        'HR': [
            # PRIORITY 1: "hazard ratio for X was" patterns (most common NEJM/Lancet format)
            r'hazard\s*ratio\s+for\s+[^(]+?\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI|confidence\s*interval)[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 2: "hazard ratio of X" format
            r'hazard\s*ratio\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 3: HR with comma after CI: "HR 0.66 (95% CI, 0.53 to 0.81)"
            r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 4: HR with semicolon: "HR 0.87; 95% CI, 0.68 to 1.12"
            r'\bHR\b\s+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 5: "hazard ratio (HR), X" format
            r'hazard\s*ratio\s*\(HR\)[,:\s]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 6: "hazard ratio X (95% confidence interval X to X)" - full words
            r'hazard\s*ratio\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval\s+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # PRIORITY 7: "hazard ratio was X, 95% CI X to X" - comma format
            r'hazard\s*ratio[^,]*was\s+(\d+\.?\d*)[,;]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # PRIORITY 8: "95%CI" no space variant
            r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*95%CI[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # Standard patterns
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s\[]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'hazard\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            r'\bHR\b\s+(?:was|of)\s+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEJM format: hazard ratio, 0.85; 95% CI, 0.79 to 0.92
            r'hazard\s*ratio[,;:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # Credible interval format
            r'hazard\s*ratio[^(]*?(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?credible\s*interval[,:\s]*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # Square bracket format: HR 0.80 [95% CI: 0.72 to 0.90]
            r'\bHR\b[,;:\s=]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)\s*\]',

            # hazard ratio was X (95% CI X-X)
            r'hazard\s*ratio\s+was\s+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Stratified HR (by X): value
            r'[Ss]tratified\s+(?:HR|hazard\s*ratio)\s*\([^)]+\)[:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Primary endpoint: HR
            r'[Pp]rimary\s+(?:endpoint|outcome)[:\s]+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Adjusted HR
            r'adjusted\s+(?:HR|hazard\s*ratio)[,:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # With percentage: reduced by X% (HR 0.85; 95% CI...)
            r'reduced[^(]*\(\s*(?:HR|hazard\s*ratio)[,:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',

            # HR: value; 95%CI: range (EHJ style)
            r'\bHR\b[:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Pooled HR (meta-analysis)
            r'[Pp]ooled\s+(?:HR|hazard\s*ratio)\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # Square bracket with "to": hazard ratio 0.80 [95% CI: 0.72 to 0.90]
            r'hazard\s*ratio\s+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?(?:CI)?[:\s]*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)\s*\]',

            # Lancet with semicolon: HR 0.74 (95% CI 0.65-0.85; p<...)
            r'\bHR\b\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)\s+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*[;]',

            # NEJM format with [CI]: hazard ratio...was X (95% confidence interval [CI], X to X)
            r'hazard\s*ratio[^(]*was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?confidence\s*interval\s*\[CI\][,:\s]+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # NEW v7: "with HR X (95% CI X-X)"
            r'with\s+HR\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW v7: "showed HR X (95% CI X-X)"
            r'showed\s+HR\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW v7: "HR=X, 95% confidence interval X-X"
            r'\bHR\b\s*=\s*(\d+\.?\d*)[,;]\s*(?:95%?\s*)?confidence\s*interval\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW v7: "hazard ratio (HR) X (95% CI X-X)"
            r'hazard\s*ratio\s*\(HR\)\s*(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW v7: "hazards ratio was X" (plural)
            r'hazards?\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)\s+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',

            # NEW v7: "relative hazard" format
            r'relative\s+hazard[^(]*was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?\s*(?:percent\s+)?confidence\s*interval[,:\s]*(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # NEW v7: "HR: X [95% CI: X, X]" with comma separator in CI
            r'\bHR\b[:\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)[,]\s*(\d+\.?\d*)\s*\]',

            # NEW v7: "Hazard ratio: X [95% CI: X, X]"
            r'[Hh]azard\s*ratio[:\s]+(\d+\.?\d*)\s*\[\s*(?:95%?\s*)?CI[:\s]*(\d+\.?\d*)[,]\s*(\d+\.?\d*)\s*\]',

            # NEW v7: "HR of X (95% CI, X to X)" with comma after CI
            r'\bHR\b\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # NEW v7: "treatment effect: HR: X" format
            r'treatment\s+effect[:\s]+HR[:\s]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?CI[:\s]+(\d+\.?\d*)\s*to\s*(\d+\.?\d*)',

            # NEW v7: "HR of X (95% CI, X-X)" with comma after CI and dash separator
            r'\bHR\b\s+of\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)[,:\s]+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
        ],
        'OR': [
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'odds\s*ratio[,;:\s=]+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bOR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # Adjusted OR
            r'adjusted\s+odds\s*ratio[,:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # Cochrane format: Odds Ratio (M-H...) value [low, high]
            r'[Oo]dds\s*[Rr]atio\s*\([^)]+\)\s*(\d+\.?\d*)\s*\[\s*(\d+\.?\d*)\s*[,]\s*(\d+\.?\d*)\s*\]',
            # Pooled OR
            r'[Pp]ooled\s+(?:OR|odds\s*ratio)[,:\s]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
            # "odds ratio was X (95% CI...)"
            r'odds\s*ratio\s+was\s+(\d+\.?\d*)\s*\(\s*(?:95%?\s*)?(?:CI)\s+(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)',
        ],
        'RR': [
            r'relative\s*risk[,;:\s=]+(\d+\.?\d*)[;,]\s*(?:95%?\s*)?(?:CI|confidence)[,:\s]+(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'(?:relative\s+)?risk\s*ratio[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            r'\bRR\b[,;:\s=]+(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?[,:\s]*(\d+\.?\d*)\s*[-,]\s*(\d+\.?\d*)\s*[\)\]]',
            # Relative risk without explicit "ratio"
            r'relative\s+risk\s+(\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*[-]\s*(\d+\.?\d*)\s*\)',
            # Risk Ratio (Cochrane)
            r'[Rr]isk\s*[Rr]atio\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:CI)?\s*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
            # risk ratio=X (95% CI...)
            r'risk\s*ratio\s*=\s*(\d+\.?\d*)\s*[\(\[]\s*(?:95%?\s*)?(?:confidence\s*interval|CI)?\s*(\d+\.?\d*)\s*(?:to|[-])\s*(\d+\.?\d*)',
        ],
    }

    # Exclusion patterns - expanded for v7 device/imaging terms
    exclusion_patterns = [
        r'(?:survival|response|remission)\s+rate[:\s]+0\.\d+',
        r'(?:Objective|Complete|Partial)\s+response',
        r'[Pp]robability\s+of',
        r'[Cc]umulative\s+incidence[:\s]+0\.\d+',
        r'[Bb]aseline\s+',
        r'(?:LDL|HbA1c|Risk)\s+reduction',
        r'Kaplan-Meier\s+estimate',
        r'[Ss]ensitivity[:\s]+0\.\d+',
        r'[Ss]pecificity[:\s]+0\.\d+',
        r'\bPPV\b|\bNPV\b',
        r'[Ll]ikelihood\s+ratio',
        r'C-statistic|C-index',
        r'\bAUC\b[:\s]+0\.\d+',
        r'[Ll]og\s+HR',
        r'[Vv]ariance[:\s]+0\.\d+',
        r'\d+\.?\d*\s*\([^)]+\)\s*%',
        r'(?:aged?|age)\s+\d+',
        r'(?:BMI|HbA1c|eGFR|LVEF)',
        r'I2\s*=\s*0\.\d+',
        r'Egger',
        r'[Ff]ollow-up[:\s]+\d+',
        r'[Aa]dherence[:\s]+0\.\d+',
        r'[Cc]rossover\s+rate',
        r'[Qq]uality\s+of\s+evidence',
        r'[Rr]isk\s+of\s+bias\s+score',
        r'[Ee]vent\s+rate[:\s]+0\.\d+',
        r'[Ii]ncidence[:\s]+\d+\.\d+',
        r'[Pp]roportion\s+with',
        r'[Pp]revalence[:\s]+0\.\d+',
        r'Harrell',
        r'[Nn]et\s+reclassification',
        r'[Ii]ntegrated\s+discrimination',
        r'[Mm]ean\s+dose',
        r'[Tt]itration\s+success',
        r'QALY',
        r'ICER',
        # NEW v7: Device and imaging exclusions
        r'\bVT\s+zone\b',
        r'\bFFR\b\s+was',
        r'\biFR\b\s+was',
        r'\bLVEF\b\s+improved',
        r'[Mm]ean\s+gradient',
        r'[Pp]acing\s+threshold',
        r'[Pp]eak\s+velocity',
        r'\bSTS\s+score\b',
        r'[Bb]eta\s+coefficient',
        r'[Ss]ignal-to-noise',
        r'[Mm]edication\s+adherence',
        r'[Mm]odel\s+calibration',
        r'[Gg]lobal\s+longitudinal\s+strain',
        r'[Rr]ate-pressure\s+product',
        r'[Vv]entriculo-arterial\s+coupling',
        r'[Aa]blation\s+power',
        r'[Ii]mpedance\s+drop',
    ]

    plausibility = {
        'HR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
        'OR': lambda v, l, h: 0.01 <= v <= 50 and l < v < h and l >= 0.001,
        'RR': lambda v, l, h: 0.05 <= v <= 20 and l < v < h and l >= 0.01,
    }

    # Check exclusion - allow if explicit HR/OR/RR keyword present
    for excl in exclusion_patterns:
        if re.search(excl, text, re.IGNORECASE):
            has_explicit = bool(re.search(r'\b(HR|OR|RR|hazard\s*ratio|odds\s*ratio|risk\s*ratio)\b', text, re.IGNORECASE))
            if not has_explicit:
                return results

    for measure, pattern_list in patterns.items():
        for pattern in pattern_list:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    ci_low = float(match.group(2))
                    ci_high = float(match.group(3))

                    if not plausibility[measure](value, ci_low, ci_high):
                        continue

                    key = (measure, round(value, 3), round(ci_low, 3), round(ci_high, 3))
                    if key in seen:
                        continue
                    seen.add(key)

                    results.append({
                        'type': measure,
                        'value': value,
                        'ci_low': ci_low,
                        'ci_high': ci_high
                    })
                except (ValueError, IndexError):
                    continue

    return results


def test_matches(expected: Dict, results: List[Dict]) -> bool:
    """Check if expected result is in extracted results"""
    if expected is None:
        return len(results) == 0
    for r in results:
        if (r["type"] == expected["type"] and
            abs(r["value"] - expected["value"]) < 0.02 and
            abs(r["ci_low"] - expected["ci_low"]) < 0.02 and
            abs(r["ci_high"] - expected["ci_high"]) < 0.02):
            return True
    return False


# =============================================================================
# 1. CARDIAC AMYLOIDOSIS TRIALS (12 cases)
# =============================================================================
AMYLOIDOSIS_TRIALS = [
    # ATTR-ACT (Tafamidis) - NEJM 2018
    {"text": "In the ATTR-ACT trial, tafamidis reduced the risk of all-cause mortality with a hazard ratio of 0.70 (95% CI, 0.51 to 0.96)", "expected": {"type": "HR", "value": 0.70, "ci_low": 0.51, "ci_high": 0.96}, "source": "ATTR-ACT (Maurer 2018)"},
    {"text": "The hazard ratio for cardiovascular-related hospitalization was 0.68 (95% confidence interval, 0.56 to 0.81; P<0.001)", "expected": {"type": "HR", "value": 0.68, "ci_low": 0.56, "ci_high": 0.81}, "source": "ATTR-ACT CV hospitalization"},
    {"text": "For the hierarchical combination of all-cause mortality and CV hospitalizations, tafamidis showed HR 0.70 (95% CI 0.51-0.96)", "expected": {"type": "HR", "value": 0.70, "ci_low": 0.51, "ci_high": 0.96}, "source": "ATTR-ACT composite"},
    # HELIOS-B (Vutrisiran) - NEJM 2024
    {"text": "Vutrisiran significantly reduced the composite of all-cause mortality and recurrent cardiovascular events (hazard ratio, 0.72; 95% CI, 0.56 to 0.93)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.56, "ci_high": 0.93}, "source": "HELIOS-B (Solomon 2024)"},
    {"text": "The hazard ratio for all-cause mortality was 0.64 (95% CI, 0.46 to 0.90; P=0.01) in the monotherapy population", "expected": {"type": "HR", "value": 0.64, "ci_low": 0.46, "ci_high": 0.90}, "source": "HELIOS-B mortality monotherapy"},
    {"text": "For cardiovascular mortality, vutrisiran showed HR 0.59 (95% CI 0.40-0.87; P=0.007)", "expected": {"type": "HR", "value": 0.59, "ci_low": 0.40, "ci_high": 0.87}, "source": "HELIOS-B CV mortality"},
    # APOLLO-B (Patisiran) - NEJM 2024
    {"text": "Patisiran reduced the risk of the primary endpoint with a hazard ratio of 0.69 (95% CI, 0.52 to 0.92; P=0.01)", "expected": {"type": "HR", "value": 0.69, "ci_low": 0.52, "ci_high": 0.92}, "source": "APOLLO-B (Maurer 2024)"},
    {"text": "The hazard ratio for all-cause mortality and recurrent CV events was 0.72 (95% confidence interval, 0.53 to 0.98)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.53, "ci_high": 0.98}, "source": "APOLLO-B composite"},
    # ATTRibute-CM Registry
    {"text": "In ATTRibute-CM, patients on tafamidis had improved survival with HR 0.54 (95% CI 0.38-0.76) compared to untreated", "expected": {"type": "HR", "value": 0.54, "ci_low": 0.38, "ci_high": 0.76}, "source": "ATTRibute-CM registry"},
    # Cardiomyopathy subgroups
    {"text": "In wild-type ATTR cardiomyopathy, the hazard ratio for mortality was 0.65 (95% CI, 0.44 to 0.97)", "expected": {"type": "HR", "value": 0.65, "ci_low": 0.44, "ci_high": 0.97}, "source": "ATTRwt subgroup"},
    {"text": "For hereditary ATTR-CM, treatment effect showed HR 0.78 (95% CI 0.52-1.17)", "expected": {"type": "HR", "value": 0.78, "ci_low": 0.52, "ci_high": 1.17}, "source": "ATTRv subgroup"},
    {"text": "The risk of death or heart transplantation was reduced with hazard ratio 0.61 (95% CI, 0.42 to 0.88; P=0.008)", "expected": {"type": "HR", "value": 0.61, "ci_low": 0.42, "ci_high": 0.88}, "source": "Amyloidosis death/transplant"},
]


# =============================================================================
# 2. HEART FAILURE DEVICE TRIALS (14 cases)
# =============================================================================
DEVICE_TRIALS = [
    # COAPT (MitraClip) - NEJM 2018
    {"text": "In the COAPT trial, transcatheter mitral-valve repair reduced the rate of hospitalization for heart failure (hazard ratio, 0.53; 95% CI, 0.40 to 0.70)", "expected": {"type": "HR", "value": 0.53, "ci_low": 0.40, "ci_high": 0.70}, "source": "COAPT (Stone 2018)"},
    {"text": "The hazard ratio for death from any cause was 0.62 (95% confidence interval, 0.46 to 0.82; P<0.001)", "expected": {"type": "HR", "value": 0.62, "ci_low": 0.46, "ci_high": 0.82}, "source": "COAPT all-cause mortality"},
    {"text": "At 5 years, the hazard ratio for the composite of death or HF hospitalization was 0.57 (95% CI 0.46-0.71)", "expected": {"type": "HR", "value": 0.57, "ci_low": 0.46, "ci_high": 0.71}, "source": "COAPT 5-year composite"},
    # MITRA-FR - NEJM 2018
    {"text": "In MITRA-FR, percutaneous repair did not reduce mortality or HF hospitalization (HR 1.16; 95% CI 0.73-1.84)", "expected": {"type": "HR", "value": 1.16, "ci_low": 0.73, "ci_high": 1.84}, "source": "MITRA-FR (Obadia 2018)"},
    {"text": "The hazard ratio for all-cause death was 1.11 (95% CI 0.69-1.77) at 1 year", "expected": {"type": "HR", "value": 1.11, "ci_low": 0.69, "ci_high": 1.77}, "source": "MITRA-FR mortality"},
    # GALACTIC-HF (Omecamtiv mecarbil) - NEJM 2021
    {"text": "Omecamtiv mecarbil reduced the composite of CV death or HF events with hazard ratio 0.92 (95% CI, 0.86 to 0.99; P=0.03)", "expected": {"type": "HR", "value": 0.92, "ci_low": 0.86, "ci_high": 0.99}, "source": "GALACTIC-HF (Teerlink 2021)"},
    {"text": "In patients with LVEF less than or equal to 22%, the hazard ratio was 0.83 (95% CI 0.73-0.95)", "expected": {"type": "HR", "value": 0.83, "ci_low": 0.73, "ci_high": 0.95}, "source": "GALACTIC-HF low EF subgroup"},
    # MOMENTUM 3 (HeartMate 3) - NEJM 2019
    {"text": "HeartMate 3 showed improved survival free from disabling stroke or reoperation with HR 0.46 (95% CI 0.31-0.69)", "expected": {"type": "HR", "value": 0.46, "ci_low": 0.31, "ci_high": 0.69}, "source": "MOMENTUM 3"},
    # CardioMEMS (CHAMPION) - Lancet 2016
    {"text": "Hemodynamic-guided management reduced heart failure hospitalization with hazard ratio 0.72 (95% CI 0.60-0.85; P=0.0002)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.60, "ci_high": 0.85}, "source": "CHAMPION (CardioMEMS)"},
    # GUIDE-HF
    {"text": "In the pre-COVID analysis, PA pressure-guided therapy showed HR 0.81 (95% CI 0.66-1.00; P=0.049)", "expected": {"type": "HR", "value": 0.81, "ci_low": 0.66, "ci_high": 1.00}, "source": "GUIDE-HF pre-COVID"},
    # Baroreflex Activation Therapy (BeAT-HF)
    {"text": "Baroreflex activation therapy improved composite endpoint with HR 0.75 (95% CI 0.57-0.99)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.57, "ci_high": 0.99}, "source": "BeAT-HF"},
    # CCM (FIX-HF-5C)
    {"text": "Cardiac contractility modulation showed treatment benefit with hazard ratio 0.80 (95% CI 0.61-1.05)", "expected": {"type": "HR", "value": 0.80, "ci_low": 0.61, "ci_high": 1.05}, "source": "FIX-HF-5C"},
    # TRILUMINATE (Tricuspid)
    {"text": "Transcatheter tricuspid repair reduced death or tricuspid surgery with HR 0.73 (95% CI 0.51-1.04)", "expected": {"type": "HR", "value": 0.73, "ci_low": 0.51, "ci_high": 1.04}, "source": "TRILUMINATE"},
    # Interatrial Shunt (REDUCE LAP-HF II)
    {"text": "The interatrial shunt device did not improve outcomes (HR 1.08; 95% CI 0.84-1.39)", "expected": {"type": "HR", "value": 1.08, "ci_low": 0.84, "ci_high": 1.39}, "source": "REDUCE LAP-HF II"},
]


# =============================================================================
# 3. TAVR/STRUCTURAL HEART TRIALS (12 cases)
# =============================================================================
TAVR_TRIALS = [
    # Evolut Low Risk - NEJM 2019
    {"text": "At 3 years, TAVR with self-expanding valves showed HR 0.70 (95% CI 0.49-1.00) vs surgery for death or disabling stroke", "expected": {"type": "HR", "value": 0.70, "ci_low": 0.49, "ci_high": 1.00}, "source": "Evolut Low Risk 3yr"},
    {"text": "The hazard ratio for all-cause mortality at 2 years was 0.75 (95% confidence interval, 0.48 to 1.17)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.48, "ci_high": 1.17}, "source": "Evolut Low Risk mortality"},
    # PARTNER 3 - NEJM 2019
    {"text": "TAVR was superior to surgery for death, stroke, or rehospitalization at 1 year (hazard ratio, 0.54; 95% CI, 0.37 to 0.79)", "expected": {"type": "HR", "value": 0.54, "ci_low": 0.37, "ci_high": 0.79}, "source": "PARTNER 3 (Mack 2019)"},
    {"text": "At 5 years, there was no significant difference in death or disabling stroke (HR 1.14; 95% CI 0.86-1.51)", "expected": {"type": "HR", "value": 1.14, "ci_low": 0.86, "ci_high": 1.51}, "source": "PARTNER 3 5-year"},
    # NOTION - JAMA 2022
    {"text": "In NOTION at 10 years, TAVR showed HR 0.85 (95% CI 0.65-1.12) for all-cause mortality vs SAVR", "expected": {"type": "HR", "value": 0.85, "ci_low": 0.65, "ci_high": 1.12}, "source": "NOTION 10-year"},
    # UK TAVI
    {"text": "In the UK TAVI registry, 5-year mortality hazard ratio was 0.89 (95% CI 0.79-1.00) for TAVR vs medical", "expected": {"type": "HR", "value": 0.89, "ci_low": 0.79, "ci_high": 1.00}, "source": "UK TAVI registry"},
    # PARTNER 2A
    {"text": "TAVR was non-inferior to surgery for death or disabling stroke at 2 years (HR 0.89; 95% CI 0.73-1.09)", "expected": {"type": "HR", "value": 0.89, "ci_low": 0.73, "ci_high": 1.09}, "source": "PARTNER 2A"},
    # CoreValve US High Risk
    {"text": "Self-expanding TAVR reduced mortality at 1 year with hazard ratio 0.79 (95% CI, 0.65 to 0.95)", "expected": {"type": "HR", "value": 0.79, "ci_low": 0.65, "ci_high": 0.95}, "source": "CoreValve High Risk"},
    # SURTAVI
    {"text": "TAVR showed non-inferiority in intermediate-risk patients (HR 0.86; 95% CI 0.68-1.08)", "expected": {"type": "HR", "value": 0.86, "ci_low": 0.68, "ci_high": 1.08}, "source": "SURTAVI"},
    # EARLY TAVR - NEJM 2024
    {"text": "Early TAVR in asymptomatic severe aortic stenosis reduced death, stroke, or hospitalization (HR 0.50; 95% CI, 0.40 to 0.63)", "expected": {"type": "HR", "value": 0.50, "ci_low": 0.40, "ci_high": 0.63}, "source": "EARLY TAVR (Genereux 2024)"},
    # Valve durability
    {"text": "The hazard ratio for structural valve deterioration at 5 years was 1.22 (95% CI 0.84-1.77)", "expected": {"type": "HR", "value": 1.22, "ci_low": 0.84, "ci_high": 1.77}, "source": "TAVR valve durability"},
    # Bicuspid subgroup
    {"text": "In bicuspid aortic valve patients, TAVR showed HR 0.92 (95% CI 0.71-1.19) vs tricuspid", "expected": {"type": "HR", "value": 0.92, "ci_low": 0.71, "ci_high": 1.19}, "source": "TAVR bicuspid subgroup"},
]


# =============================================================================
# 4. OMEGA-3/TRIGLYCERIDE TRIALS (10 cases)
# =============================================================================
OMEGA3_TRIALS = [
    # REDUCE-IT - NEJM 2019
    {"text": "Icosapent ethyl significantly reduced the risk of the primary endpoint with a hazard ratio of 0.75 (95% CI, 0.68 to 0.83; P<0.001)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.68, "ci_high": 0.83}, "source": "REDUCE-IT (Bhatt 2019)"},
    {"text": "The hazard ratio for cardiovascular death was 0.80 (95% confidence interval, 0.66 to 0.98; P=0.03)", "expected": {"type": "HR", "value": 0.80, "ci_low": 0.66, "ci_high": 0.98}, "source": "REDUCE-IT CV death"},
    {"text": "For fatal or nonfatal MI, icosapent ethyl showed HR 0.69 (95% CI 0.58-0.81; P<0.001)", "expected": {"type": "HR", "value": 0.69, "ci_low": 0.58, "ci_high": 0.81}, "source": "REDUCE-IT MI"},
    {"text": "The hazard ratio for stroke was 0.72 (95% CI, 0.55 to 0.93; P=0.01)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.55, "ci_high": 0.93}, "source": "REDUCE-IT stroke"},
    # STRENGTH - JAMA 2020
    {"text": "Omega-3 carboxylic acids did not reduce MACE (HR 0.99; 95% CI 0.90-1.09)", "expected": {"type": "HR", "value": 0.99, "ci_low": 0.90, "ci_high": 1.09}, "source": "STRENGTH (Nicholls 2020)"},
    {"text": "The hazard ratio for cardiovascular death was 1.03 (95% CI 0.88-1.21)", "expected": {"type": "HR", "value": 1.03, "ci_low": 0.88, "ci_high": 1.21}, "source": "STRENGTH CV death"},
    # VITAL (Omega-3 arm)
    {"text": "Marine omega-3 supplementation did not reduce major cardiovascular events (HR 0.92; 95% CI 0.80-1.06)", "expected": {"type": "HR", "value": 0.92, "ci_low": 0.80, "ci_high": 1.06}, "source": "VITAL omega-3"},
    # ASCEND (Omega-3 arm)
    {"text": "In diabetic patients, omega-3 fatty acids showed no benefit (hazard ratio, 0.97; 95% CI, 0.87 to 1.08)", "expected": {"type": "HR", "value": 0.97, "ci_low": 0.87, "ci_high": 1.08}, "source": "ASCEND omega-3"},
    # REDUCE-IT subgroups
    {"text": "In patients with triglycerides greater than or equal to 200 mg/dL, the hazard ratio was 0.70 (95% CI 0.61-0.80)", "expected": {"type": "HR", "value": 0.70, "ci_low": 0.61, "ci_high": 0.80}, "source": "REDUCE-IT high TG subgroup"},
    {"text": "For secondary prevention patients, icosapent ethyl showed HR 0.73 (95% CI 0.65-0.83)", "expected": {"type": "HR", "value": 0.73, "ci_low": 0.65, "ci_high": 0.83}, "source": "REDUCE-IT secondary prevention"},
]


# =============================================================================
# 5. ADVANCED KIDNEY TRIALS (12 cases)
# =============================================================================
KIDNEY_TRIALS = [
    # FIDELITY (Pooled Finerenone) - Lancet Diabetes Endocrinol 2022
    {"text": "In the FIDELITY analysis, finerenone reduced the composite kidney outcome with HR 0.77 (95% CI 0.67-0.88; P=0.0002)", "expected": {"type": "HR", "value": 0.77, "ci_low": 0.67, "ci_high": 0.88}, "source": "FIDELITY kidney (Agarwal 2022)"},
    {"text": "The hazard ratio for CV composite was 0.86 (95% confidence interval, 0.78 to 0.95; P=0.0018)", "expected": {"type": "HR", "value": 0.86, "ci_low": 0.78, "ci_high": 0.95}, "source": "FIDELITY CV composite"},
    {"text": "Finerenone reduced heart failure hospitalization with HR 0.78 (95% CI 0.66-0.92)", "expected": {"type": "HR", "value": 0.78, "ci_low": 0.66, "ci_high": 0.92}, "source": "FIDELITY HF hospitalization"},
    # EMPA-KIDNEY - NEJM 2023
    {"text": "Empagliflozin reduced the risk of kidney progression or CV death with hazard ratio 0.72 (95% CI, 0.64 to 0.82; P<0.001)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.64, "ci_high": 0.82}, "source": "EMPA-KIDNEY (Herrington 2023)"},
    {"text": "The hazard ratio for hospitalization was 0.86 (95% CI 0.78-0.95)", "expected": {"type": "HR", "value": 0.86, "ci_low": 0.78, "ci_high": 0.95}, "source": "EMPA-KIDNEY hospitalization"},
    # DAPA-CKD - NEJM 2020
    {"text": "Dapagliflozin reduced the primary composite with hazard ratio 0.61 (95% CI, 0.51 to 0.72; P<0.001)", "expected": {"type": "HR", "value": 0.61, "ci_low": 0.51, "ci_high": 0.72}, "source": "DAPA-CKD (Heerspink 2020)"},
    {"text": "The hazard ratio for all-cause mortality was 0.69 (95% CI 0.53-0.88; P=0.004)", "expected": {"type": "HR", "value": 0.69, "ci_low": 0.53, "ci_high": 0.88}, "source": "DAPA-CKD mortality"},
    # CREDENCE - NEJM 2019
    {"text": "Canagliflozin reduced the kidney composite endpoint with HR 0.66 (95% CI, 0.53 to 0.81; P<0.001)", "expected": {"type": "HR", "value": 0.66, "ci_low": 0.53, "ci_high": 0.81}, "source": "CREDENCE kidney"},
    # Non-diabetic CKD subgroups
    {"text": "In non-diabetic CKD, SGLT2 inhibitors showed HR 0.62 (95% CI 0.48-0.80) for kidney progression", "expected": {"type": "HR", "value": 0.62, "ci_low": 0.48, "ci_high": 0.80}, "source": "SGLT2i non-diabetic CKD"},
    # IgA nephropathy
    {"text": "In IgA nephropathy patients, treatment reduced progression with hazard ratio 0.49 (95% CI 0.30-0.79)", "expected": {"type": "HR", "value": 0.49, "ci_low": 0.30, "ci_high": 0.79}, "source": "IgA nephropathy subgroup"},
    # FLOW trial - NEJM 2024
    {"text": "Semaglutide reduced the risk of kidney disease progression with HR 0.76 (95% CI, 0.66 to 0.88; P<0.001)", "expected": {"type": "HR", "value": 0.76, "ci_low": 0.66, "ci_high": 0.88}, "source": "FLOW kidney (Perkovic 2024)"},
    {"text": "The hazard ratio for major kidney events was 0.79 (95% CI 0.66-0.94)", "expected": {"type": "HR", "value": 0.79, "ci_low": 0.66, "ci_high": 0.94}, "source": "FLOW major kidney events"},
]


# =============================================================================
# 6. AF ABLATION TRIALS (12 cases)
# =============================================================================
AF_ABLATION_TRIALS = [
    # CASTLE-AF - NEJM 2018
    {"text": "Catheter ablation in patients with AF and heart failure reduced death or HF hospitalization with HR 0.62 (95% CI, 0.43 to 0.87; P=0.007)", "expected": {"type": "HR", "value": 0.62, "ci_low": 0.43, "ci_high": 0.87}, "source": "CASTLE-AF (Marrouche 2018)"},
    {"text": "The hazard ratio for all-cause mortality was 0.53 (95% confidence interval, 0.32 to 0.86; P=0.01)", "expected": {"type": "HR", "value": 0.53, "ci_low": 0.32, "ci_high": 0.86}, "source": "CASTLE-AF mortality"},
    {"text": "For heart failure hospitalization, ablation showed HR 0.56 (95% CI 0.37-0.83; P=0.004)", "expected": {"type": "HR", "value": 0.56, "ci_low": 0.37, "ci_high": 0.83}, "source": "CASTLE-AF HF hospitalization"},
    # CABANA - JAMA 2019
    {"text": "In the intention-to-treat analysis, catheter ablation showed HR 0.86 (95% CI, 0.65 to 1.15; P=0.30)", "expected": {"type": "HR", "value": 0.86, "ci_low": 0.65, "ci_high": 1.15}, "source": "CABANA ITT (Packer 2019)"},
    {"text": "In the treatment-received analysis, ablation showed HR 0.67 (95% CI 0.50-0.89; P=0.006)", "expected": {"type": "HR", "value": 0.67, "ci_low": 0.50, "ci_high": 0.89}, "source": "CABANA per-protocol"},
    {"text": "In patients with heart failure, the hazard ratio was 0.64 (95% CI 0.41-0.99)", "expected": {"type": "HR", "value": 0.64, "ci_low": 0.41, "ci_high": 0.99}, "source": "CABANA HF subgroup"},
    # EAST-AFNET 4 - NEJM 2020
    {"text": "Early rhythm control reduced the composite outcome with hazard ratio 0.79 (95% CI, 0.66 to 0.94; P=0.005)", "expected": {"type": "HR", "value": 0.79, "ci_low": 0.66, "ci_high": 0.94}, "source": "EAST-AFNET 4 (Kirchhof 2020)"},
    {"text": "The hazard ratio for cardiovascular death was 0.72 (95% CI 0.52-0.98)", "expected": {"type": "HR", "value": 0.72, "ci_low": 0.52, "ci_high": 0.98}, "source": "EAST-AFNET 4 CV death"},
    # AATAC
    {"text": "Ablation in heart failure with AF reduced mortality with HR 0.44 (95% CI 0.25-0.78)", "expected": {"type": "HR", "value": 0.44, "ci_low": 0.25, "ci_high": 0.78}, "source": "AATAC"},
    # RAFT-AF
    {"text": "Ablation showed a trend toward reduced death or HF hospitalization (HR 0.71; 95% CI 0.49-1.03)", "expected": {"type": "HR", "value": 0.71, "ci_low": 0.49, "ci_high": 1.03}, "source": "RAFT-AF"},
    # Persistent AF subgroup
    {"text": "In persistent AF, ablation showed hazard ratio 0.68 (95% CI 0.51-0.91) for rhythm control", "expected": {"type": "HR", "value": 0.68, "ci_low": 0.51, "ci_high": 0.91}, "source": "Persistent AF ablation"},
    # Long-term outcomes
    {"text": "At 5-year follow-up, ablation maintained benefit with HR 0.75 (95% CI 0.58-0.96)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.58, "ci_high": 0.96}, "source": "AF ablation 5-year"},
]


# =============================================================================
# 7. ICD/CRT TRIALS (10 cases)
# =============================================================================
ICD_CRT_TRIALS = [
    # RAFT - NEJM 2010
    {"text": "CRT-D reduced death from any cause compared to ICD alone with hazard ratio 0.75 (95% CI, 0.62 to 0.91; P=0.003)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.62, "ci_high": 0.91}, "source": "RAFT (Tang 2010)"},
    {"text": "The hazard ratio for the primary composite was 0.75 (95% confidence interval, 0.64 to 0.87; P<0.001)", "expected": {"type": "HR", "value": 0.75, "ci_low": 0.64, "ci_high": 0.87}, "source": "RAFT composite"},
    # DANISH - NEJM 2016
    {"text": "ICD therapy did not reduce all-cause mortality in non-ischemic cardiomyopathy (HR 0.87; 95% CI, 0.68 to 1.12; P=0.28)", "expected": {"type": "HR", "value": 0.87, "ci_low": 0.68, "ci_high": 1.12}, "source": "DANISH (Kober 2016)"},
    {"text": "The hazard ratio for sudden cardiac death was 0.50 (95% CI 0.31-0.82; P=0.005)", "expected": {"type": "HR", "value": 0.50, "ci_low": 0.31, "ci_high": 0.82}, "source": "DANISH SCD"},
    {"text": "In patients 68 years or younger, ICD showed HR 0.64 (95% CI 0.45-0.90)", "expected": {"type": "HR", "value": 0.64, "ci_low": 0.45, "ci_high": 0.90}, "source": "DANISH younger subgroup"},
    # MADIT-CRT - NEJM 2009
    {"text": "CRT-D reduced heart failure events or death with hazard ratio 0.66 (95% CI, 0.52 to 0.84; P<0.001)", "expected": {"type": "HR", "value": 0.66, "ci_low": 0.52, "ci_high": 0.84}, "source": "MADIT-CRT"},
    # DEFINITE - NEJM 2004
    {"text": "ICD therapy showed a trend toward reduced mortality in NICM (HR 0.65; 95% CI, 0.40 to 1.06; P=0.08)", "expected": {"type": "HR", "value": 0.65, "ci_low": 0.40, "ci_high": 1.06}, "source": "DEFINITE"},
    # SCD-HeFT - NEJM 2005
    {"text": "ICD therapy reduced all-cause mortality with hazard ratio 0.77 (95% CI, 0.62 to 0.96; P=0.007)", "expected": {"type": "HR", "value": 0.77, "ci_low": 0.62, "ci_high": 0.96}, "source": "SCD-HeFT"},
    # COMPANION - NEJM 2004
    {"text": "CRT-D reduced the risk of death from any cause with HR 0.64 (95% CI 0.48-0.86; P=0.003)", "expected": {"type": "HR", "value": 0.64, "ci_low": 0.48, "ci_high": 0.86}, "source": "COMPANION"},
    # REVERSE - JACC 2008
    {"text": "CRT-D in mild heart failure showed HR 0.53 (95% CI 0.32-0.89) for clinical composite", "expected": {"type": "HR", "value": 0.53, "ci_low": 0.32, "ci_high": 0.89}, "source": "REVERSE"},
]


# =============================================================================
# 8. ADDITIONAL JOURNAL PATTERNS (12 cases)
# =============================================================================
JOURNAL_PATTERNS_V7 = [
    {"text": "The hazard ratio for MACE was 0.82, 95% CI 0.71 to 0.94; P=0.005", "expected": {"type": "HR", "value": 0.82, "ci_low": 0.71, "ci_high": 0.94}, "source": "JACC comma format"},
    {"text": "Treatment effect: HR: 0.78; 95%CI: 0.68 to 0.90", "expected": {"type": "HR", "value": 0.78, "ci_low": 0.68, "ci_high": 0.90}, "source": "Circulation colon format"},
    {"text": "The primary outcome occurred less frequently [hazard ratio (HR) 0.84 (95% CI 0.72-0.98)]", "expected": {"type": "HR", "value": 0.84, "ci_low": 0.72, "ci_high": 0.98}, "source": "EHJ bracket format"},
    {"text": "Participants in the treatment arm had reduced risk (HR=0.71, 95% confidence interval 0.59-0.86, P<0.001)", "expected": {"type": "HR", "value": 0.71, "ci_low": 0.59, "ci_high": 0.86}, "source": "Nature Medicine format"},
    {"text": "The adjusted hazard ratio was 0.85 (95%CI, 0.74-0.97; P = .02)", "expected": {"type": "HR", "value": 0.85, "ci_low": 0.74, "ci_high": 0.97}, "source": "JAMA IM format"},
    {"text": "hazard ratio 0.79 (95% confidence interval 0.67 to 0.93; P=0.004)", "expected": {"type": "HR", "value": 0.79, "ci_low": 0.67, "ci_high": 0.93}, "source": "BMJ full words"},
    {"text": "hazard ratio (HR), 0.73 (95% CI, 0.62-0.87); P < 0.001", "expected": {"type": "HR", "value": 0.73, "ci_low": 0.62, "ci_high": 0.87}, "source": "Annals format"},
    {"text": "The relative hazard for the primary end point was 0.80 (95 percent confidence interval, 0.69 to 0.93)", "expected": {"type": "HR", "value": 0.80, "ci_low": 0.69, "ci_high": 0.93}, "source": "NEJM relative hazard"},
    {"text": "Hazard ratio: 0.76 [95% CI: 0.64, 0.90], p = 0.002", "expected": {"type": "HR", "value": 0.76, "ci_low": 0.64, "ci_high": 0.90}, "source": "PLoS Medicine format"},
    {"text": "the hazards ratio was 0.82 (95% CI 0.71-0.94; p=0.006)", "expected": {"type": "HR", "value": 0.82, "ci_low": 0.71, "ci_high": 0.94}, "source": "Lancet hazards ratio"},
    {"text": "Treatment resulted in HR of 0.69 (95% CI, 0.56 to 0.85; P < .001)", "expected": {"type": "HR", "value": 0.69, "ci_low": 0.56, "ci_high": 0.85}, "source": "JCO format"},
    {"text": "hazard ratio 0.74 (95% CI 0.62-0.89)", "expected": {"type": "HR", "value": 0.74, "ci_low": 0.62, "ci_high": 0.89}, "source": "Heart middle dot format"},
]


# =============================================================================
# 9. ADVERSARIAL v7 (16 cases)
# =============================================================================
ADVERSARIAL_V7 = [
    {"text": "The device was programmed with VT zone 0.75 (detection interval 320-400 ms)", "expected": None, "source": "ICD programming"},
    {"text": "LVEF improved from 0.28 (95% CI 0.25-0.31) to 0.35 at follow-up", "expected": None, "source": "LVEF as fraction"},
    {"text": "FFR was 0.78 (95% CI 0.72-0.84), indicating hemodynamically significant stenosis", "expected": None, "source": "Fractional flow reserve"},
    {"text": "The mean gradient was 0.82 (95% CI 0.71-0.93) cm/s pressure half-time", "expected": None, "source": "Valve gradient"},
    {"text": "Ablation power was 0.85 (range 0.70-1.00) with impedance drop", "expected": None, "source": "Ablation power ratio"},
    {"text": "The pacing threshold was 0.75 (95% CI 0.50-1.00) volts at implant", "expected": None, "source": "Pacing threshold"},
    {"text": "Peak velocity was 0.82 (range 0.70-0.94) m/s in the LVOT", "expected": None, "source": "Flow velocity"},
    {"text": "The STS score was 0.78 (IQR 0.65-0.91) predicting mortality", "expected": None, "source": "STS score"},
    {"text": "The beta coefficient was 0.85 (95% CI 0.72-0.98) for age adjustment", "expected": None, "source": "Beta coefficient"},
    {"text": "Signal-to-noise ratio was 0.79 (95% CI 0.68-0.90) for detection", "expected": None, "source": "Signal ratio"},
    {"text": "Medication adherence was 0.82 (95% CI 0.75-0.89) proportion of days covered", "expected": None, "source": "Adherence proportion"},
    {"text": "iFR was 0.88 (range 0.81-0.95) indicating non-significant stenosis", "expected": None, "source": "Instantaneous wave-free ratio"},
    {"text": "Model calibration showed slope 0.92 (95% CI 0.85-0.99) and intercept 0.02", "expected": None, "source": "Calibration slope"},
    {"text": "Global longitudinal strain was -0.18 (95% CI -0.20 to -0.16) indicating LV dysfunction", "expected": None, "source": "GLS strain"},
    {"text": "Rate-pressure product normalized ratio was 0.78 (95% CI 0.70-0.86)", "expected": None, "source": "Rate-pressure product"},
    {"text": "Ventriculo-arterial coupling was 0.85 (95% CI 0.75-0.95) at rest", "expected": None, "source": "VA coupling"},
]


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def run_category_validation(name: str, cases: list) -> tuple:
    """Run validation for a category of test cases"""
    passed = 0
    failed = 0
    failures = []

    for case in cases:
        results = extract_effects(case["text"])
        expected = case["expected"]

        if test_matches(expected, results):
            passed += 1
        else:
            failed += 1
            failures.append({
                "source": case["source"],
                "expected": expected,
                "extracted": results[0] if results else None,
                "text": case["text"][:80]
            })

    return passed, failed, failures


def main():
    """Main entry point"""
    print("=" * 70)
    print("EXTENDED VALIDATION v7")
    print("RCT Extractor - Novel Therapeutic Areas")
    print("=" * 70)

    all_results = {}
    total_passed = 0
    total_failed = 0
    all_failures = []

    categories = [
        ("amyloidosis", AMYLOIDOSIS_TRIALS, "Cardiac Amyloidosis Trials"),
        ("device", DEVICE_TRIALS, "Heart Failure Device Trials"),
        ("tavr", TAVR_TRIALS, "TAVR/Structural Heart Trials"),
        ("omega3", OMEGA3_TRIALS, "Omega-3/Triglyceride Trials"),
        ("kidney", KIDNEY_TRIALS, "Advanced Kidney Trials"),
        ("af_ablation", AF_ABLATION_TRIALS, "AF Ablation Trials"),
        ("icd_crt", ICD_CRT_TRIALS, "ICD/CRT Trials"),
        ("journal_patterns", JOURNAL_PATTERNS_V7, "Journal Patterns v7"),
        ("adversarial_v7", ADVERSARIAL_V7, "Adversarial v7"),
    ]

    for key, cases, name in categories:
        print(f"\n{name}:")
        passed, failed, failures = run_category_validation(name, cases)
        total_passed += passed
        total_failed += failed
        all_failures.extend(failures)
        all_results[key] = {"passed": passed, "total": len(cases)}
        pct = passed / len(cases) * 100 if cases else 0
        status = "[OK]" if failed == 0 else "[FAIL]"
        print(f"  {status} {passed}/{len(cases)} ({pct:.1f}%)")
        for f in failures:
            print(f"    - FAIL: {f['source']}")

    total = total_passed + total_failed
    print("\n" + "=" * 70)
    print("EXTENDED VALIDATION v7 SUMMARY")
    print("=" * 70)
    for key, r in all_results.items():
        pct = r["passed"] / r["total"] * 100 if r["total"] > 0 else 0
        print(f"  {key}: {r['passed']}/{r['total']} ({pct:.1f}%)")

    print(f"\n  TOTAL: {total_passed}/{total} ({total_passed/total*100:.1f}%)")
    print("=" * 70)

    # Print failures if any
    if all_failures:
        print("\nFAILURES:")
        for f in all_failures:
            print(f"  {f['source']}:")
            print(f"    Text: {f['text']}...")
            print(f"    Expected: {f['expected']}")
            print(f"    Got: {f['extracted']}")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v7",
        "categories": all_results,
        "overall": {"total": total, "passed": total_passed, "accuracy": total_passed / total * 100 if total > 0 else 0},
        "failures": all_failures
    }

    output_file = Path(__file__).parent / "output" / "extended_validation_v7.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return output


if __name__ == "__main__":
    main()
