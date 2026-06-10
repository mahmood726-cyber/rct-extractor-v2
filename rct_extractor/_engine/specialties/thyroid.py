"""
Thyroid Disorders Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow as the diabetes / obesity profiles.
Thyroid RCTs (levothyroxine for hypothyroidism, antithyroid drugs / radioiodine
for hyperthyroidism, subclinical thyroid disease in pregnancy) report a distinct
endpoint vocabulary (TSH / free T4 / free T3 levels, TSH normalisation,
hyperthyroid remission and relapse, thyroid quality-of-life) that the generic
effect-size engine does not recognise.

Subspecialties:
- hypothyroidism: TSH normalisation / control, thyroid symptom & quality-of-life
  scores (levothyroxine, combination LT4/LT3, desiccated thyroid).
- hyperthyroidism: euthyroidism restoration, remission, relapse / recurrence,
  Graves' orbitopathy response (antithyroid drugs, radioiodine, thyroidectomy).
- thyroid_function (continuous): TSH, free T4 (FT4), free T3 (FT3), total T4/T3,
  thyroid-peroxidase antibody (TPOAb) levels.
- outcomes: pregnancy loss / preterm birth in (subclinical) thyroid disease,
  cardiovascular events / mortality, treatment adverse events (agranulocytosis,
  hepatotoxicity).

Effect measures: lab levels and symptom/QoL scores -> MD/SMD (continuous);
TSH normalisation, euthyroidism, remission, relapse, pregnancy / CV outcomes and
adverse events -> RR/OR/HR (binary / time-to-event).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# THYROID ENDPOINTS
# ============================================================

THYROID_ENDPOINTS = {
    # --- thyroid_function (continuous) ---
    'TSH_LEVEL': {
        'aliases': ['thyroid-stimulating hormone', 'thyroid stimulating hormone',
                    'serum tsh', 'tsh level', 'tsh concentration', 'change in tsh', 'tsh'],
        'subspecialty': 'thyroid_function',
        'measure_types': ['MD', 'SMD']
    },
    'FT4_LEVEL': {
        'aliases': ['free thyroxine', 'free t4', 'ft4', 'free thyroxine level',
                    'serum free thyroxine', 'ft4 level'],
        'subspecialty': 'thyroid_function',
        'measure_types': ['MD', 'SMD']
    },
    'FT3_LEVEL': {
        'aliases': ['free triiodothyronine', 'free t3', 'ft3', 'free triiodothyronine level',
                    'ft3 level'],
        'subspecialty': 'thyroid_function',
        'measure_types': ['MD', 'SMD']
    },
    'T4_LEVEL': {
        'aliases': ['total thyroxine', 'total t4', 'serum thyroxine', 'thyroxine level'],
        'subspecialty': 'thyroid_function',
        'measure_types': ['MD', 'SMD']
    },
    'TPO_ANTIBODY': {
        'aliases': ['thyroid peroxidase antibody', 'thyroid-peroxidase antibody', 'tpo antibody',
                    'tpoab', 'anti-tpo antibody', 'thyroid antibody titre', 'thyroid antibodies'],
        'subspecialty': 'thyroid_function',
        'measure_types': ['MD', 'SMD']
    },
    'THYROID_QOL': {
        'aliases': ['thyroid-related quality of life', 'thypro score', 'thyroid symptom score',
                    'hypothyroid symptoms', 'quality of life score', 'thyroid quality of life'],
        'subspecialty': 'hypothyroidism',
        'measure_types': ['MD', 'SMD']
    },

    # --- hypothyroidism (binary) ---
    'TSH_NORMALIZATION': {
        'aliases': ['tsh normalization', 'tsh normalisation', 'normalization of tsh',
                    'normalisation of tsh', 'tsh within reference range', 'tsh target achieved',
                    'achieved target tsh', 'euthyroid tsh', 'tsh control'],
        'subspecialty': 'hypothyroidism',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- hyperthyroidism ---
    'EUTHYROIDISM': {
        'aliases': ['euthyroidism', 'restoration of euthyroidism', 'euthyroid state',
                    'biochemical euthyroidism', 'achieved euthyroidism'],
        'subspecialty': 'hyperthyroidism',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REMISSION': {
        'aliases': ['remission', 'disease remission', 'sustained remission',
                    'biochemical remission', 'graves remission'],
        'subspecialty': 'hyperthyroidism',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'recurrence', 'hyperthyroidism relapse', 'relapse of hyperthyroidism',
                    'recurrence of hyperthyroidism', 'disease recurrence'],
        'subspecialty': 'hyperthyroidism',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ORBITOPATHY_RESPONSE': {
        'aliases': ["graves' orbitopathy", 'graves orbitopathy', 'thyroid eye disease',
                    'thyroid-associated ophthalmopathy', 'orbitopathy response',
                    'ophthalmopathy improvement', 'proptosis response'],
        'subspecialty': 'hyperthyroidism',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- outcomes ---
    'PREGNANCY_LOSS': {
        'aliases': ['pregnancy loss', 'miscarriage', 'spontaneous abortion', 'fetal loss',
                    'pregnancy loss rate'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PRETERM_BIRTH': {
        'aliases': ['preterm birth', 'preterm delivery', 'premature birth', 'preterm labor',
                    'preterm labour'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['agranulocytosis', 'hepatotoxicity', 'adverse events', 'adverse drug reactions',
                    'cutaneous reactions', 'treatment-related adverse events'],
        'subspecialty': 'outcomes',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# HYPOTHYROIDISM PATTERNS
# ============================================================

HYPOTHYROIDISM_PATTERNS = {
    'detection_keywords': [
        r'hypothyroid(?:ism)?', r'levothyroxine|thyroxine|\blt4\b', r'liothyronine|\blt3\b',
        r'desiccated\s+thyroid', r'subclinical\s+hypothyroidism', r'tsh\s+normali[sz]ation',
        r'thyroid[- ]related\s+quality\s+of\s+life|thypro', r'thyroid\s+symptom',
        r'combination\s+(?:lt4|levothyroxine).{0,10}(?:lt3|liothyronine)',
    ],
    'endpoint_patterns': [
        (r'tsh\s+normali[sz]ation|normali[sz]ation\s+of\s+tsh|tsh\s+within\s+reference|'
         r'tsh\s+target\s+achieved|tsh\s+control', 'TSH_NORMALIZATION'),
        (r'thyroid[- ]related\s+quality\s+of\s+life|thypro\s+score|thyroid\s+symptom\s+score|'
         r'hypothyroid\s+symptoms', 'THYROID_QOL'),
    ],
    'context_patterns': [
        r'reference\s+range', r'\bmiu/l\b|\bmu/l\b', r'weight[- ]based\s+dose',
    ]
}


# ============================================================
# HYPERTHYROIDISM PATTERNS
# ============================================================

HYPERTHYROIDISM_PATTERNS = {
    'detection_keywords': [
        r'hyperthyroid(?:ism)?', r'graves[’\']?\s+disease|graves\s+disease',
        r'methimazole|carbimazole|thiamazole|propylthiouracil|\bptu\b', r'antithyroid',
        r'radioactive\s+iodine|radioiodine|\bi[- ]?131\b|\b131i\b', r'thyroidectomy',
        r'thyrotoxicosis', r'remission|relapse|recurrence', r'euthyroid',
        r'orbitopathy|ophthalmopathy|thyroid\s+eye\s+disease',
    ],
    'endpoint_patterns': [
        (r"graves[’']?\s+orbitopathy|graves\s+orbitopathy|thyroid\s+eye\s+disease|"
         r'thyroid[- ]associated\s+ophthalmopathy|orbitopathy\s+response|'
         r'ophthalmopathy\s+improvement|proptosis\s+response', 'ORBITOPATHY_RESPONSE'),
        (r'restoration\s+of\s+euthyroidism|euthyroidism|euthyroid\s+state|'
         r'biochemical\s+euthyroidism', 'EUTHYROIDISM'),
        (r'(?:hyperthyroidism\s+|disease\s+)?relapse|recurrence(?:\s+of\s+hyperthyroidism)?',
         'RELAPSE'),
        (r'(?:sustained\s+|biochemical\s+|disease\s+|graves\s+)?remission', 'REMISSION'),
    ],
    'context_patterns': [
        r'\d+\s*months?\s+(?:of\s+)?(?:treatment|follow[- ]up)', r'block[- ]and[- ]replace',
        r'titration\s+regimen',
    ]
}


# ============================================================
# THYROID-FUNCTION PATTERNS (continuous)
# ============================================================

THYROID_FUNCTION_PATTERNS = {
    'detection_keywords': [
        r'thyroid[- ]stimulating\s+hormone|\btsh\b', r'free\s+(?:thyroxine|t4)|\bft4\b',
        r'free\s+(?:triiodothyronine|t3)|\bft3\b', r'total\s+(?:thyroxine|t4|t3)',
        r'thyroid\s+peroxidase\s+antibody|\btpoab?\b|anti[- ]tpo', r'thyroid\s+function\s+test',
    ],
    'endpoint_patterns': [
        (r'thyroid[- ]peroxidase\s+antibody|anti[- ]tpo\s+antibod|\btpoab\b|'
         r'thyroid\s+antibod(?:y|ies)', 'TPO_ANTIBODY'),
        (r'free\s+thyroxine|free\s+t4\b|\bft4\b', 'FT4_LEVEL'),
        (r'free\s+triiodothyronine|free\s+t3\b|\bft3\b', 'FT3_LEVEL'),
        (r'total\s+thyroxine|total\s+t4\b|serum\s+thyroxine', 'T4_LEVEL'),
        (r'(?:serum\s+|change\s+in\s+)?thyroid[- ]stimulating\s+hormone|'
         r'(?:serum\s+|change\s+in\s+)?\btsh\b(?:\s+(?:level|concentration))?', 'TSH_LEVEL'),
    ],
    'context_patterns': [
        r'\bmiu/l\b|\bmu/l\b|pmol/l|ng/dl', r'baseline\s+to\s+(?:week|month)',
    ]
}


# ============================================================
# OUTCOMES PATTERNS
# ============================================================

OUTCOMES_PATTERNS = {
    'detection_keywords': [
        r'miscarriage|pregnancy\s+loss|spontaneous\s+abortion', r'preterm\s+(?:birth|delivery)',
        r'agranulocytosis|hepatotoxicity', r'cardiovascular\s+(?:events|death|mortality)',
        r'live\s+birth', r'adverse\s+events',
    ],
    'endpoint_patterns': [
        (r'pregnancy\s+loss|miscarriage|spontaneous\s+abortion|fetal\s+loss', 'PREGNANCY_LOSS'),
        (r'preterm\s+(?:birth|delivery|labou?r)|premature\s+birth', 'PRETERM_BIRTH'),
        (r'agranulocytosis|hepatotoxicity|cutaneous\s+reactions|treatment[- ]related\s+adverse\s+events|'
         r'adverse\s+drug\s+reactions', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'subclinical', r'first\s+trimester', r'thyroid\s+autoimmunity',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_thyroid_subspecialty(text: str) -> Tuple[str, float]:
    """Detect thyroid trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: hypothyroidism, hyperthyroidism, thyroid_function, outcomes,
    general_thyroid."""
    text_lower = text.lower()
    scores = {'hypothyroidism': 0, 'hyperthyroidism': 0, 'thyroid_function': 0, 'outcomes': 0}
    for kw in HYPOTHYROIDISM_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hypothyroidism'] += 1
    for kw in HYPERTHYROIDISM_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hyperthyroidism'] += 1
    for kw in THYROID_FUNCTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['thyroid_function'] += 1
    for kw in OUTCOMES_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['outcomes'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_thyroid', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_thyroid_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'hypothyroidism': HYPOTHYROIDISM_PATTERNS['endpoint_patterns'],
        'hyperthyroidism': HYPERTHYROIDISM_PATTERNS['endpoint_patterns'],
        'thyroid_function': THYROID_FUNCTION_PATTERNS['endpoint_patterns'],
        'outcomes': OUTCOMES_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_thyroid_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical thyroid endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in THYROID_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
