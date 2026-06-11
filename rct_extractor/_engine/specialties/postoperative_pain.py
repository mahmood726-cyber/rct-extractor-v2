"""
Postoperative (Acute Surgical) Pain Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Acute postoperative-pain RCTs report a distinct endpoint vocabulary (pain score
at rest and on movement, 24-h cumulative opioid / morphine consumption, time to
first rescue analgesia, proportion needing rescue analgesia, postoperative
nausea and vomiting, chronic post-surgical pain at 3-6 months) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Regional analgesia: peripheral nerve / fascial-plane blocks (TAP, erector
  spinae, interscalene, femoral, pectoral), epidural analgesia, wound / local
  infiltration, intrathecal / spinal opioid.
- Multimodal: paracetamol/acetaminophen, NSAIDs / COX-2, gabapentinoids,
  dexamethasone, ketamine, magnesium, dexmedetomidine, intravenous lidocaine.
- Opioid analgesia: patient-controlled analgesia (PCA morphine), opioid-sparing,
  systemic opioids.
- Chronic post-surgical pain prevention: persistent post-surgical pain at 3 and
  6 months, neuropathic post-surgical pain.

Effect measures follow what these trials report: continuous (pain score, opioid
consumption, time to first analgesia, satisfaction) -> mean difference; binary
(rescue analgesia, PONV, moderate-to-severe pain, chronic post-surgical pain,
block success) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# POSTOPERATIVE PAIN ENDPOINTS
# ============================================================

POSTOPERATIVE_PAIN_ENDPOINTS = {
    'PAIN_SCORE': {
        'aliases': ['pain score', 'postoperative pain', 'pain at rest', 'pain on movement',
                    'pain on coughing', 'pain intensity', 'resting pain', 'dynamic pain',
                    'visual analogue scale', 'vas pain', 'vas score',
                    'numeric rating scale', 'numerical rating scale', 'nrs pain',
                    'pain at 24 hours', 'pain at 24 h', 'worst pain'],
        'subspecialty': 'regional_analgesia',
        'measure_types': ['MD']
    },
    'OPIOID_CONSUMPTION': {
        'aliases': ['opioid consumption', 'morphine consumption',
                    'cumulative opioid consumption', 'cumulative morphine consumption',
                    '24-hour morphine consumption', '24-h opioid consumption',
                    'morphine equivalent', 'total opioid consumption',
                    'postoperative opioid use', 'opioid requirement',
                    'morphine milligram equivalents'],
        'subspecialty': 'opioid',
        'measure_types': ['MD']
    },
    'TIME_TO_RESCUE': {
        'aliases': ['time to first rescue', 'time to first analgesia',
                    'time to first rescue analgesia', 'time to first analgesic request',
                    'duration of analgesia', 'time to rescue analgesia'],
        'subspecialty': 'regional_analgesia',
        'measure_types': ['MD']
    },
    'RESCUE_ANALGESIA': {
        'aliases': ['rescue analgesia', 'need for rescue analgesia', 'rescue analgesic use',
                    'requirement for rescue', 'patients requiring rescue analgesia',
                    'use of rescue analgesia', 'supplemental analgesia'],
        'subspecialty': 'multimodal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PONV': {
        'aliases': ['postoperative nausea and vomiting', 'ponv', 'nausea and vomiting',
                    'postoperative nausea', 'postoperative vomiting', 'nausea', 'vomiting'],
        'subspecialty': 'multimodal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MODERATE_SEVERE_PAIN': {
        'aliases': ['moderate-to-severe pain', 'moderate to severe pain', 'severe pain',
                    'moderate or severe pain', 'clinically significant pain',
                    'inadequate analgesia'],
        'subspecialty': 'multimodal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BLOCK_SUCCESS': {
        'aliases': ['block success', 'successful block', 'sensory block',
                    'analgesic efficacy', 'successful analgesia'],
        'subspecialty': 'regional_analgesia',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CPSP': {
        'aliases': ['chronic post-surgical pain', 'chronic postsurgical pain',
                    'persistent post-surgical pain', 'persistent postsurgical pain',
                    'chronic pain at 3 months', 'chronic pain at 6 months',
                    'persistent pain', 'chronic postoperative pain'],
        'subspecialty': 'chronic_postsurgical',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SATISFACTION': {
        'aliases': ['patient satisfaction', 'satisfaction score',
                    'quality of recovery', 'qor-40', 'qor-15', 'satisfaction with analgesia'],
        'subspecialty': 'multimodal',
        'measure_types': ['MD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'side effects', 'respiratory depression',
                    'sedation', 'pruritus', 'opioid-related adverse events'],
        'subspecialty': 'opioid',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# REGIONAL ANALGESIA PATTERNS
# ============================================================

REGIONAL_ANALGESIA_PATTERNS = {
    'detection_keywords': [
        r'nerve\s+block|fascial\s+plane\s+block|transversus\s+abdominis\s+plane|\btap\s+block\b',
        r'erector\s+spinae|interscalene|femoral\s+(?:nerve\s+)?block|pectoral\s+(?:nerve\s+)?block|\bpecs\b',
        r'epidural\s+analgesia|epidural\s+(?:bupivacaine|ropivacaine)',
        r'wound\s+infiltration|local\s+(?:anaesthetic\s+)?infiltration|surgical\s+site\s+infiltration',
        r'intrathecal\s+(?:morphine|opioid)|spinal\s+(?:morphine|opioid)',
        r'time\s+to\s+first\s+(?:rescue|analgesia)|duration\s+of\s+analgesia',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+first\s+(?:rescue|analgesi\w+|analgesic\s+request)|duration\s+of\s+analgesia',
         'TIME_TO_RESCUE'),
        (r'(?:24[- ]h(?:our)?\s+)?(?:cumulative\s+)?(?:opioid|morphine)\s+consumption|'
         r'morphine\s+equivalent|opioid\s+requirement', 'OPIOID_CONSUMPTION'),
        (r'block\s+success|successful\s+block|sensory\s+block', 'BLOCK_SUCCESS'),
        (r'rescue\s+analgesi\w+|need\s+for\s+rescue|supplemental\s+analgesia', 'RESCUE_ANALGESIA'),
        (r'pain\s+(?:score|at\s+rest|on\s+(?:movement|coughing)|intensity)|resting\s+pain|'
         r'dynamic\s+pain|visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b',
         'PAIN_SCORE'),
        (r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b', 'PONV'),
    ],
    'context_patterns': [
        r'ultrasound[- ]guided', r'ropivacaine|bupivacaine|levobupivacaine', r'0\s*[-–]\s*10\s+nrs',
    ]
}


# ============================================================
# MULTIMODAL PATTERNS
# ============================================================

MULTIMODAL_PATTERNS = {
    'detection_keywords': [
        r'multimodal\s+analgesia|paracetamol|acetaminophen',
        r'\bnsaid\b|non[- ]steroidal|ibuprofen|ketorolac|diclofenac|celecoxib|parecoxib',
        r'gabapentin|pregabalin|gabapentinoid',
        r'dexamethasone|dexmedetomidine|magnesium|intravenous\s+lidocaine|\biv\s+lidocaine\b',
        r'ketamine|opioid[- ]sparing',
        r'rescue\s+analgesia|moderate[- ]to[- ]severe\s+pain',
    ],
    'endpoint_patterns': [
        (r'(?:24[- ]h(?:our)?\s+)?(?:cumulative\s+)?(?:opioid|morphine)\s+consumption|'
         r'morphine\s+equivalent|opioid[- ]sparing|opioid\s+requirement', 'OPIOID_CONSUMPTION'),
        (r'moderate[- ](?:to[- ])?severe\s+pain|severe\s+pain|inadequate\s+analgesia', 'MODERATE_SEVERE_PAIN'),
        (r'rescue\s+analgesi\w+|need\s+for\s+rescue|requirement\s+for\s+rescue|supplemental\s+analgesia',
         'RESCUE_ANALGESIA'),
        (r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b|\bnausea\b|\bvomiting\b', 'PONV'),
        (r'pain\s+(?:score|at\s+rest|on\s+(?:movement|coughing)|intensity)|resting\s+pain|'
         r'dynamic\s+pain|visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b',
         'PAIN_SCORE'),
        (r'patient\s+satisfaction|quality\s+of\s+recovery|qor[- ]?\d+', 'SATISFACTION'),
    ],
    'context_patterns': [
        r'first\s+24\s+hours', r'opioid[- ]free', r'preemptive|pre[- ]emptive',
    ]
}


# ============================================================
# OPIOID ANALGESIA PATTERNS
# ============================================================

OPIOID_PATTERNS = {
    'detection_keywords': [
        r'patient[- ]controlled\s+analgesia|\bpca\b', r'morphine\s+consumption',
        r'opioid[- ]sparing|systemic\s+opioid', r'fentanyl|hydromorphone|oxycodone|sufentanil',
        r'respiratory\s+depression|opioid[- ]related\s+adverse',
    ],
    'endpoint_patterns': [
        (r'(?:24[- ]h(?:our)?\s+)?(?:cumulative\s+)?(?:opioid|morphine|pca)\s+consumption|'
         r'morphine\s+equivalent|opioid\s+requirement', 'OPIOID_CONSUMPTION'),
        (r'respiratory\s+depression|opioid[- ]related\s+adverse|\bsedation\b|pruritus',
         'ADVERSE_EVENTS'),
        (r'pain\s+(?:score|at\s+rest|on\s+movement|intensity)|visual\s+analogue|\bvas\b|'
         r'numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_SCORE'),
        (r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b', 'PONV'),
        (r'rescue\s+analgesi\w+|need\s+for\s+rescue', 'RESCUE_ANALGESIA'),
    ],
    'context_patterns': [
        r'background\s+infusion', r'bolus\s+dose', r'lockout\s+interval',
    ]
}


# ============================================================
# CHRONIC POST-SURGICAL PAIN PATTERNS
# ============================================================

CHRONIC_POSTSURGICAL_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+post[- ]?surgical\s+pain',
        r'persistent\s+post[- ]?surgical\s+pain',
        r'(?:persistent|chronic)\s+pain\s+at\s+(?:3|6|12)\s+months',
        r'(?:post[- ]?surgical|postoperative)\s+pain\s+at\s+(?:3|6|12)\s+months',
        r'chronic\s+postoperative\s+pain|neuropathic\s+post[- ]surgical',
        r'prevention\s+of\s+(?:chronic|persistent)\s+(?:post[- ]?surgical\s+)?pain',
    ],
    'endpoint_patterns': [
        (r'chronic\s+post[- ]?surgical\s+pain|persistent\s+post[- ]?surgical\s+pain|'
         r'persistent\s+pain|chronic\s+pain\s+at\s+(?:3|6)\s+months|chronic\s+postoperative\s+pain',
         'CPSP'),
        (r'pain\s+(?:score|intensity)|visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b',
         'PAIN_SCORE'),
        (r'(?:opioid|morphine)\s+consumption', 'OPIOID_CONSUMPTION'),
    ],
    'context_patterns': [
        r'at\s+(?:3|6|12)\s+months', r'grade\s+\w+\s+pain',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_postoperative_pain_subspecialty(text: str) -> Tuple[str, float]:
    """Detect postoperative-pain trial subspecialty.
    Returns (subspecialty, confidence). Subspecialties: regional_analgesia,
    multimodal, opioid, chronic_postsurgical, general_postop_pain."""
    text_lower = text.lower()
    scores = {'regional_analgesia': 0, 'multimodal': 0,
              'opioid': 0, 'chronic_postsurgical': 0}
    for kw in REGIONAL_ANALGESIA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['regional_analgesia'] += 1
    for kw in MULTIMODAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['multimodal'] += 1
    for kw in OPIOID_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['opioid'] += 1
    for kw in CHRONIC_POSTSURGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['chronic_postsurgical'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_postop_pain', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_postoperative_pain_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'regional_analgesia': REGIONAL_ANALGESIA_PATTERNS['endpoint_patterns'],
        'multimodal': MULTIMODAL_PATTERNS['endpoint_patterns'],
        'opioid': OPIOID_PATTERNS['endpoint_patterns'],
        'chronic_postsurgical': CHRONIC_POSTSURGICAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_postoperative_pain_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical postoperative-pain endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in POSTOPERATIVE_PAIN_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
