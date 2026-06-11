"""
Fracture & Orthopaedic Surgery Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Orthopaedic-trauma and joint-surgery RCTs report a distinct endpoint vocabulary
(reoperation / revision, nonunion, time to union, functional / patient-reported
outcome scores [Harris Hip, Oxford Knee, DASH, Constant], surgical-site
infection, complications, mortality after hip fracture) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Fracture fixation: operative vs nonoperative, intramedullary nailing vs
  plating, open reduction internal fixation (ORIF), external fixation, locking
  plates (distal radius, ankle, tibia, clavicle, proximal humerus).
- Arthroplasty: total hip / knee / shoulder replacement, hemiarthroplasty vs
  fixation for hip fracture, surgical approach, cemented vs uncemented, bearing.
- Healing / biologics: nonunion, delayed union, time to union, bone graft,
  bone morphogenetic protein, teriparatide / vitamin D for fracture healing.
- Functional / rehabilitation: physiotherapy, early weight-bearing, ACL
  reconstruction vs rehabilitation, return to sport / work, PROMs.

Effect measures follow what these trials report: binary (reoperation / revision,
nonunion, infection, complications, mortality, return to activity) -> RR/OR/HR;
count/score outcomes (functional score, time to union, pain, range of motion)
-> mean difference, handled by the shared continuous augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ORTHOPAEDIC ENDPOINTS
# ============================================================

ORTHOPAEDIC_ENDPOINTS = {
    'REOPERATION': {
        'aliases': ['reoperation', 're-operation', 'revision surgery', 'revision',
                    'reintervention', 'unplanned reoperation', 'secondary surgery',
                    'reoperation rate', 'implant removal', 'revision arthroplasty'],
        'subspecialty': 'fracture_fixation',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NONUNION': {
        'aliases': ['nonunion', 'non-union', 'delayed union', 'failure of union',
                    'fracture nonunion', 'malunion', 'failed union', 'ununited fracture'],
        'subspecialty': 'fracture_fixation',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'UNION_TIME': {
        'aliases': ['time to union', 'time to bony union', 'union time',
                    'time to radiographic union', 'time to fracture healing',
                    'time to consolidation', 'healing time'],
        'subspecialty': 'healing',
        'measure_types': ['MD']
    },
    'FUNCTIONAL_SCORE': {
        'aliases': ['functional outcome', 'harris hip score', 'oxford hip score',
                    'oxford knee score', 'knee society score', 'womac', 'dash score',
                    'constant score', 'constant-murley', 'quickdash', 'koos',
                    'patient-reported outcome', 'functional score', 'lysholm',
                    'mayo elbow', 'foot and ankle outcome', 'eq-5d'],
        'subspecialty': 'functional',
        'measure_types': ['MD']
    },
    'PAIN_SCORE': {
        'aliases': ['pain score', 'visual analogue scale', 'vas pain', 'pain intensity',
                    'numeric rating scale', 'nrs pain', 'postoperative pain'],
        'subspecialty': 'functional',
        'measure_types': ['MD']
    },
    'INFECTION': {
        'aliases': ['surgical site infection', 'surgical-site infection', 'ssi',
                    'deep infection', 'periprosthetic joint infection', 'pji',
                    'wound infection', 'superficial infection', 'deep wound infection'],
        'subspecialty': 'arthroplasty',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'COMPLICATIONS': {
        'aliases': ['complications', 'postoperative complications', 'major complications',
                    'overall complications', 'adverse events', 'implant failure',
                    'fixation failure', 'wound complications', 'any complication'],
        'subspecialty': 'fracture_fixation',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', '30-day mortality', '1-year mortality',
                    'one-year mortality', 'all-cause mortality', 'in-hospital mortality',
                    'survival'],
        'subspecialty': 'arthroplasty',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VTE': {
        'aliases': ['venous thromboembolism', 'vte', 'deep vein thrombosis', 'dvt',
                    'pulmonary embolism', 'symptomatic vte'],
        'subspecialty': 'arthroplasty',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RANGE_OF_MOTION': {
        'aliases': ['range of motion', 'rom', 'knee flexion', 'flexion',
                    'joint mobility', 'range of movement'],
        'subspecialty': 'functional',
        'measure_types': ['MD']
    },
    'RETURN_TO_ACTIVITY': {
        'aliases': ['return to sport', 'return to work', 'return to activity',
                    'return to play', 'return to pre-injury level', 'time to return'],
        'subspecialty': 'functional',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'REHOSPITALIZATION': {
        'aliases': ['readmission', 'rehospitalization', 'hospital readmission',
                    '30-day readmission', 'length of stay'],
        'subspecialty': 'arthroplasty',
        'measure_types': ['RR', 'OR', 'MD']
    },
}


# ============================================================
# FRACTURE FIXATION PATTERNS
# ============================================================

FRACTURE_FIXATION_PATTERNS = {
    'detection_keywords': [
        r'(?:internal|external)\s+fixation|open\s+reduction(?:\s+(?:and\s+)?internal\s+fixation)?|\borif\b',
        r'intramedullary\s+nail\w*|\bim\s+nail\b|locking\s+plate|plate\s+fixation|plating',
        r'operative\s+(?:vs\.?\s+)?(?:non[- ]?operative|nonoperative|conservative)',
        r'(?:distal\s+radius|ankle|tibial?|clavicle|proximal\s+humerus|femoral\s+(?:neck|shaft)|hip)\s+fracture',
        r'\bfracture\s+(?:fixation|reduction|management)\b',
        r'nonunion|non[- ]union|time\s+to\s+union',
    ],
    'endpoint_patterns': [
        (r're[- ]?operation|revision(?:\s+surgery)?|reintervention|secondary\s+surgery|'
         r'implant\s+removal', 'REOPERATION'),
        (r'non[- ]?union|delayed\s+union|failure\s+of\s+union|malunion|ununited', 'NONUNION'),
        (r'time\s+to\s+(?:bony\s+|radiographic\s+)?union|union\s+time|time\s+to\s+(?:fracture\s+)?healing|'
         r'time\s+to\s+consolidation|healing\s+time', 'UNION_TIME'),
        (r'(?:implant|fixation)\s+failure|wound\s+complications|major\s+complications|'
         r'postoperative\s+complications|any\s+complication', 'COMPLICATIONS'),
        (r'surgical[- ]site\s+infection|deep\s+infection|wound\s+infection|\bssi\b', 'INFECTION'),
        (r'(?:functional\s+outcome|dash\s+score|quickdash|patient[- ]reported\s+outcome)', 'FUNCTIONAL_SCORE'),
        (r'pain\s+(?:score|intensity)|visual\s+analogue|\bvas\b', 'PAIN_SCORE'),
    ],
    'context_patterns': [
        r'ao/ota|gustilo', r'weight[- ]bearing', r'radiographic\s+union',
    ]
}


# ============================================================
# ARTHROPLASTY PATTERNS
# ============================================================

ARTHROPLASTY_PATTERNS = {
    'detection_keywords': [
        r'(?:total\s+)?(?:hip|knee|shoulder)\s+(?:arthroplasty|replacement)|\btha\b|\btka\b|\btkr\b|\bthr\b',
        r'hemiarthroplasty|unicompartmental|resurfacing',
        r'cemented\s+(?:vs\.?\s+)?(?:un)?cemented|cementless',
        r'(?:anterior|posterior|lateral)\s+approach|surgical\s+approach',
        r'periprosthetic|prosthesis|implant\s+survival',
        r'femoral\s+neck\s+fracture|hip\s+fracture',
    ],
    'endpoint_patterns': [
        (r'periprosthetic\s+joint\s+infection|\bpji\b|deep\s+infection|surgical[- ]site\s+infection|\bssi\b',
         'INFECTION'),
        (r'revision(?:\s+arthroplasty|\s+surgery)?|re[- ]?operation|implant\s+(?:failure|survival)',
         'REOPERATION'),
        (r'venous\s+thromboembolism|\bvte\b|deep\s+vein\s+thrombosis|\bdvt\b|pulmonary\s+embolism',
         'VTE'),
        (r'(?:harris\s+hip|oxford\s+(?:hip|knee)|knee\s+society|womac|koos|constant)\s+score|'
         r'functional\s+outcome|patient[- ]reported\s+outcome', 'FUNCTIONAL_SCORE'),
        (r'range\s+of\s+(?:motion|movement)|\brom\b|knee\s+flexion', 'RANGE_OF_MOTION'),
        (r'readmission|rehospitali[sz]ation|length\s+of\s+stay', 'REHOSPITALIZATION'),
        (r'(?:30[- ]day|1[- ]year|one[- ]year|in[- ]hospital|all[- ]cause)\s+(?:mortality|death)|'
         r'\bmortality\b', 'MORTALITY'),
        (r'(?:postoperative|major|overall)\s+complications|any\s+complication', 'COMPLICATIONS'),
    ],
    'context_patterns': [
        r'national\s+joint\s+registry', r'aseptic\s+loosening', r'10[- ]year\s+survival',
    ]
}


# ============================================================
# HEALING / BIOLOGICS PATTERNS
# ============================================================

HEALING_PATTERNS = {
    'detection_keywords': [
        r'non[- ]?union|delayed\s+union|fracture\s+healing|bony\s+union',
        r'bone\s+graft|autograft|allograft|bone\s+morphogenetic\s+protein|\bbmp\b',
        r'teriparatide|vitamin\s+d\s+(?:for|and)\s+fracture|calcium\s+supplement',
        r'low[- ]intensity\s+(?:pulsed\s+)?ultrasound|\blipus\b|bone\s+stimulat\w+',
        r'time\s+to\s+(?:union|consolidation|healing)',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:bony\s+|radiographic\s+)?union|union\s+time|time\s+to\s+(?:fracture\s+)?healing|'
         r'time\s+to\s+consolidation', 'UNION_TIME'),
        (r'non[- ]?union|delayed\s+union|failure\s+of\s+union|ununited', 'NONUNION'),
        (r're[- ]?operation|revision|secondary\s+(?:surgery|procedure)', 'REOPERATION'),
        (r'(?:functional\s+outcome|dash|patient[- ]reported)\s*(?:score)?', 'FUNCTIONAL_SCORE'),
        (r'pain\s+(?:score|intensity)|visual\s+analogue|\bvas\b', 'PAIN_SCORE'),
    ],
    'context_patterns': [
        r'radius\s+of\s+curvature|callus', r'union\s+rate\s+at\s+\d+\s+(?:weeks|months)',
    ]
}


# ============================================================
# FUNCTIONAL / REHABILITATION PATTERNS
# ============================================================

FUNCTIONAL_PATTERNS = {
    'detection_keywords': [
        r'(?:anterior\s+cruciate\s+ligament|acl)\s+reconstruction|rotator\s+cuff\s+repair',
        r'physiotherapy|rehabilitation|early\s+(?:mobili[sz]ation|weight[- ]bearing)',
        r'return\s+to\s+(?:sport|work|play|activity)',
        r'(?:harris\s+hip|oxford|womac|koos|dash|constant|lysholm)\s+score',
        r'range\s+of\s+motion|patient[- ]reported\s+outcome',
    ],
    'endpoint_patterns': [
        (r'(?:harris\s+hip|oxford\s+(?:hip|knee)|knee\s+society|womac|koos|constant(?:[- ]murley)?|'
         r'dash|quickdash|lysholm|mayo\s+elbow|foot\s+and\s+ankle\s+outcome)\s*(?:score)?|'
         r'functional\s+(?:outcome|score)|patient[- ]reported\s+outcome', 'FUNCTIONAL_SCORE'),
        (r'range\s+of\s+(?:motion|movement)|\brom\b|knee\s+flexion|joint\s+mobility', 'RANGE_OF_MOTION'),
        (r'return\s+to\s+(?:sport|work|play|activity|pre[- ]injury)|time\s+to\s+return', 'RETURN_TO_ACTIVITY'),
        (r'pain\s+(?:score|intensity)|visual\s+analogue|\bvas\b|numeric\s+rating', 'PAIN_SCORE'),
        (r're[- ]?operation|revision|graft\s+failure|re[- ]?rupture', 'REOPERATION'),
    ],
    'context_patterns': [
        r'pivot\s+shift|laxity', r'12[- ]month\s+follow[- ]up',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_orthopaedic_subspecialty(text: str) -> Tuple[str, float]:
    """Detect orthopaedic / fracture-surgery trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: fracture_fixation,
    arthroplasty, healing, functional, general_ortho."""
    text_lower = text.lower()
    scores = {'fracture_fixation': 0, 'arthroplasty': 0, 'healing': 0, 'functional': 0}
    for kw in FRACTURE_FIXATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['fracture_fixation'] += 1
    for kw in ARTHROPLASTY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['arthroplasty'] += 1
    for kw in HEALING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['healing'] += 1
    for kw in FUNCTIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['functional'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_ortho', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_orthopaedic_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'fracture_fixation': FRACTURE_FIXATION_PATTERNS['endpoint_patterns'],
        'arthroplasty': ARTHROPLASTY_PATTERNS['endpoint_patterns'],
        'healing': HEALING_PATTERNS['endpoint_patterns'],
        'functional': FUNCTIONAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_orthopaedic_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical orthopaedic endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ORTHOPAEDIC_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
