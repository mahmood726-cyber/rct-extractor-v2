"""
Immune Thrombocytopenia (ITP) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
ITP RCTs report a distinct endpoint vocabulary (platelet response >=30 or
>=50 x10^9/L, complete response, durable / sustained response, bleeding events,
time to response, rescue therapy, relapse) that the generic effect-size engine
does not recognise on its own.

Subspecialties:
- First-line: corticosteroids (prednisone / prednisolone, high-dose
  dexamethasone), intravenous immunoglobulin (IVIG), anti-D immunoglobulin.
- TPO-RA (thrombopoietin receptor agonists): eltrombopag, romiplostim,
  avatrombopag, hetrombopag.
- Second-line / immunomodulatory: rituximab, fostamatinib (Syk inhibitor),
  splenectomy, mycophenolate, FcRn inhibitors (efgartigimod, rozanolixizumab).
- Paediatric / chronic ITP management.

Effect measures follow what these trials report: binary (platelet response,
complete response, durable response, bleeding, rescue therapy, relapse) ->
RR/OR/RD; count/time outcomes (platelet count, time to response, duration of
response) -> mean difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ITP ENDPOINTS
# ============================================================

ITP_ENDPOINTS = {
    'PLATELET_RESPONSE': {
        'aliases': ['platelet response', 'overall response', 'response rate',
                    'haemostatic response', 'hemostatic response',
                    'platelet count response', 'initial response',
                    'platelet count >=30', 'platelet count of at least 30',
                    'platelet count >=50', 'response (platelet count'],
        'subspecialty': 'first_line',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'COMPLETE_RESPONSE': {
        'aliases': ['complete response', 'complete remission', 'cr',
                    'platelet count >=100', 'complete platelet response'],
        'subspecialty': 'first_line',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DURABLE_RESPONSE': {
        'aliases': ['durable response', 'sustained response', 'sustained platelet response',
                    'durable platelet response', 'persistent response',
                    'sustained remission', 'lasting response',
                    'durable haemostatic response', 'maintained response'],
        'subspecialty': 'tpo_ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PLATELET_COUNT': {
        'aliases': ['platelet count', 'mean platelet count', 'median platelet count',
                    'change in platelet count', 'platelet level'],
        'subspecialty': 'tpo_ra',
        'measure_types': ['MD']
    },
    'BLEEDING': {
        'aliases': ['bleeding', 'bleeding events', 'haemorrhage', 'hemorrhage',
                    'clinically significant bleeding', 'bleeding episodes',
                    'who bleeding', 'bleeding score', 'major bleeding',
                    'significant bleeding'],
        'subspecialty': 'first_line',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TIME_TO_RESPONSE': {
        'aliases': ['time to response', 'time to platelet response',
                    'time to first response', 'median time to response'],
        'subspecialty': 'first_line',
        'measure_types': ['MD']
    },
    'RESCUE_THERAPY': {
        'aliases': ['rescue therapy', 'rescue medication', 'need for rescue therapy',
                    'use of rescue', 'rescue treatment'],
        'subspecialty': 'tpo_ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'recurrence', 'loss of response', 'relapse-free',
                    'sustained off-treatment response', 'remission off treatment'],
        'subspecialty': 'second_line',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SPLENECTOMY_AVOIDANCE': {
        'aliases': ['splenectomy', 'avoidance of splenectomy', 'splenectomy-free',
                    'need for splenectomy'],
        'subspecialty': 'second_line',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'thromboembolic events',
                    'thrombosis', 'headache', 'treatment-related adverse events',
                    'infusion reactions'],
        'subspecialty': 'tpo_ra',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# FIRST-LINE PATTERNS
# ============================================================

FIRST_LINE_PATTERNS = {
    'detection_keywords': [
        r'corticosteroid|prednis(?:on|olon)e|high[- ]dose\s+dexamethasone|\bdexamethasone\b',
        r'intravenous\s+immunoglobulin|\bivig\b|\bivIg\b',
        r'anti[- ]d\s+immunoglobulin|anti[- ]d\b',
        r'newly\s+diagnosed\s+(?:itp|immune\s+thrombocytopenia)|first[- ]line',
        r'platelet\s+response|complete\s+response',
    ],
    'endpoint_patterns': [
        (r'durable\s+(?:platelet\s+|h(?:ae|e)mostatic\s+)?response|sustained\s+(?:platelet\s+)?response|'
         r'sustained\s+remission', 'DURABLE_RESPONSE'),
        (r'complete\s+(?:platelet\s+)?response|complete\s+remission', 'COMPLETE_RESPONSE'),
        (r'(?:overall\s+|initial\s+|platelet\s+|h(?:ae|e)mostatic\s+)?response\s*(?:rate)?|'
         r'response\s*\(platelet|platelet\s+count\s+(?:>=|of\s+at\s+least)\s*\d+', 'PLATELET_RESPONSE'),
        (r'time\s+to\s+(?:platelet\s+|first\s+)?response', 'TIME_TO_RESPONSE'),
        (r'(?:clinically\s+significant\s+|major\s+|who\s+)?bleeding|h(?:ae|e)morrhage|bleeding\s+score',
         'BLEEDING'),
        (r'(?:mean\s+|median\s+|change\s+in\s+)?platelet\s+count', 'PLATELET_COUNT'),
        (r'rescue\s+(?:therapy|medication|treatment)|need\s+for\s+rescue', 'RESCUE_THERAPY'),
    ],
    'context_patterns': [
        r'x\s*10\s*\^?\s*9\s*/\s*l|×\s*10\s*9\s*/\s*l|10\^9/l', r'day\s+7|day\s+14',
    ]
}


# ============================================================
# TPO-RA PATTERNS
# ============================================================

TPO_RA_PATTERNS = {
    'detection_keywords': [
        r'thrombopoietin\s+receptor\s+agonist|\btpo[- ]?ra\b|tpo\s+receptor',
        r'eltrombopag|romiplostim|avatrombopag|hetrombopag|lusutrombopag',
        r'durable\s+(?:platelet\s+)?response|sustained\s+(?:platelet\s+)?response',
        r'chronic\s+(?:itp|immune\s+thrombocytopenia)|persistent\s+itp',
    ],
    'endpoint_patterns': [
        (r'durable\s+(?:platelet\s+|h(?:ae|e)mostatic\s+)?response|sustained\s+(?:platelet\s+)?response|'
         r'maintained\s+response|lasting\s+response', 'DURABLE_RESPONSE'),
        (r'complete\s+(?:platelet\s+)?response', 'COMPLETE_RESPONSE'),
        (r'(?:overall\s+|platelet\s+)?response\s*(?:rate)?|platelet\s+count\s+(?:>=|of\s+at\s+least)\s*\d+',
         'PLATELET_RESPONSE'),
        (r'rescue\s+(?:therapy|medication|treatment)|need\s+for\s+rescue', 'RESCUE_THERAPY'),
        (r'(?:mean\s+|median\s+|change\s+in\s+)?platelet\s+count', 'PLATELET_COUNT'),
        (r'(?:clinically\s+significant\s+|who\s+)?bleeding|h(?:ae|e)morrhage', 'BLEEDING'),
        (r'thromboembolic|thrombosis|serious\s+adverse', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'weeks?\s+\d+\s+(?:to|through)\s+\d+', r'>=6\s+of\s+8\s+weeks|6\s+of\s+the\s+8',
    ]
}


# ============================================================
# SECOND-LINE PATTERNS
# ============================================================

SECOND_LINE_PATTERNS = {
    'detection_keywords': [
        r'rituximab|fostamatinib|\bsyk\s+inhibitor\b',
        r'splenectomy', r'mycophenolate|azathioprine|cyclosporin',
        r'efgartigimod|rozanolixizumab|fcrn|neonatal\s+fc\s+receptor',
        r'relapsed\s+(?:itp|immune\s+thrombocytopenia)|refractory\s+itp',
    ],
    'endpoint_patterns': [
        (r'relapse|recurrence|loss\s+of\s+response', 'RELAPSE'),
        (r'splenectomy[- ]free|avoidance\s+of\s+splenectomy|need\s+for\s+splenectomy', 'SPLENECTOMY_AVOIDANCE'),
        (r'durable\s+(?:platelet\s+)?response|sustained\s+(?:platelet\s+)?response', 'DURABLE_RESPONSE'),
        (r'complete\s+(?:platelet\s+)?response|complete\s+remission', 'COMPLETE_RESPONSE'),
        (r'(?:overall\s+|platelet\s+)?response\s*(?:rate)?', 'PLATELET_RESPONSE'),
        (r'(?:clinically\s+significant\s+|who\s+)?bleeding|h(?:ae|e)morrhage', 'BLEEDING'),
        (r'(?:mean\s+|median\s+)?platelet\s+count', 'PLATELET_COUNT'),
    ],
    'context_patterns': [
        r'375\s*mg/m2', r'off[- ]treatment\s+response',
    ]
}


# ============================================================
# PAEDIATRIC PATTERNS
# ============================================================

PAEDIATRIC_PATTERNS = {
    'detection_keywords': [
        r'(?:childhood|paediatric|pediatric)\s+(?:itp|immune\s+thrombocytopenia)',
        r'children\s+with\s+(?:itp|immune\s+thrombocytopenia)',
        r'acute\s+(?:childhood\s+)?itp',
    ],
    'endpoint_patterns': [
        (r'(?:overall\s+|platelet\s+)?response\s*(?:rate)?|platelet\s+count\s+(?:>=|of\s+at\s+least)\s*\d+',
         'PLATELET_RESPONSE'),
        (r'complete\s+(?:platelet\s+)?response', 'COMPLETE_RESPONSE'),
        (r'(?:clinically\s+significant\s+|who\s+)?bleeding|h(?:ae|e)morrhage|bleeding\s+score', 'BLEEDING'),
        (r'time\s+to\s+(?:platelet\s+)?response', 'TIME_TO_RESPONSE'),
        (r'(?:mean\s+|median\s+)?platelet\s+count', 'PLATELET_COUNT'),
        (r'relapse|recurrence|chronic\s+itp', 'RELAPSE'),
    ],
    'context_patterns': [
        r'resolution\s+within\s+\d+\s+months', r'progression\s+to\s+chronic',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_itp_subspecialty(text: str) -> Tuple[str, float]:
    """Detect ITP trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: first_line, tpo_ra, second_line, paediatric, general_itp."""
    text_lower = text.lower()
    scores = {'first_line': 0, 'tpo_ra': 0, 'second_line': 0, 'paediatric': 0}
    for kw in FIRST_LINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['first_line'] += 1
    for kw in TPO_RA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['tpo_ra'] += 1
    for kw in SECOND_LINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['second_line'] += 1
    for kw in PAEDIATRIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['paediatric'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_itp', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_itp_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'first_line': FIRST_LINE_PATTERNS['endpoint_patterns'],
        'tpo_ra': TPO_RA_PATTERNS['endpoint_patterns'],
        'second_line': SECOND_LINE_PATTERNS['endpoint_patterns'],
        'paediatric': PAEDIATRIC_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_itp_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical ITP endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ITP_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
