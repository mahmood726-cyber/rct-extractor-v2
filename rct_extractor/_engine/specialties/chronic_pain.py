"""
Chronic Pain Management Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Chronic-pain RCTs (neuropathic pain, fibromyalgia, osteoarthritis pain, chronic
musculoskeletal pain) report a distinct endpoint vocabulary (pain intensity on
a VAS / NRS, >=30% and >=50% responder rates, physical function / disability,
withdrawal due to adverse events) that the generic effect-size engine does not
recognise on its own.

Subspecialties:
- Pharmacological: opioids, gabapentinoids (pregabalin, gabapentin), SNRI/TCA
  antidepressants (duloxetine, amitriptyline), NSAIDs, topical agents
  (capsaicin, lidocaine), cannabinoids.
- Interventional: peripheral / sympathetic nerve blocks, radiofrequency
  ablation, spinal cord stimulation, epidural / intra-articular steroid
  injection, intrathecal therapy.
- Neuropathic: painful diabetic peripheral neuropathy, postherpetic neuralgia,
  trigeminal neuralgia, central / post-stroke neuropathic pain, sciatica.
- Behavioural / physical: cognitive behavioural therapy, exercise therapy,
  acupuncture, mindfulness, multidisciplinary / physical rehabilitation.

Effect measures follow what these trials report: continuous (pain-intensity
score, function/disability, quality of life) -> mean difference; binary
(>=30% / >=50% pain responder, >=2-point reduction, withdrawal due to adverse
events, treatment response) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# CHRONIC PAIN ENDPOINTS
# ============================================================

CHRONIC_PAIN_ENDPOINTS = {
    'PAIN_INTENSITY': {
        'aliases': ['pain intensity', 'pain score', 'average pain', 'mean pain score',
                    'pain severity', 'visual analogue scale', 'vas pain', 'vas score',
                    'numeric rating scale', 'numerical rating scale', 'nrs pain',
                    'pain at rest', 'worst pain', 'daily pain', 'weekly pain',
                    'brief pain inventory', 'bpi', 'change in pain'],
        'subspecialty': 'pharmacological',
        'measure_types': ['MD']
    },
    'RESPONDER_30': {
        'aliases': ['30% pain reduction', '>=30% reduction', 'at least 30% reduction',
                    '30% responder', 'thirty percent reduction',
                    '30% improvement in pain'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RESPONDER_50': {
        'aliases': ['50% pain reduction', '>=50% reduction', 'at least 50% reduction',
                    '50% responder', 'fifty percent reduction',
                    '50% improvement in pain', 'substantial pain relief',
                    'moderate pain relief'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'PAIN_RELIEF': {
        'aliases': ['pain relief', 'clinically important improvement',
                    'meaningful pain relief', 'treatment response',
                    'much or very much improved', 'global impression of change',
                    'pgic', 'responder'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FUNCTION': {
        'aliases': ['physical function', 'function', 'disability', 'functional status',
                    'oswestry disability index', 'odi', 'roland-morris',
                    'womac function', 'pain disability index', 'functional improvement',
                    'physical functioning'],
        'subspecialty': 'behavioural',
        'measure_types': ['MD']
    },
    'QOL': {
        'aliases': ['quality of life', 'health-related quality of life', 'eq-5d',
                    'sf-36', 'sf-12', 'hrqol', 'wellbeing'],
        'subspecialty': 'behavioural',
        'measure_types': ['MD']
    },
    'SLEEP': {
        'aliases': ['sleep', 'sleep quality', 'sleep interference', 'pain-related sleep',
                    'insomnia'],
        'subspecialty': 'pharmacological',
        'measure_types': ['MD']
    },
    'WITHDRAWAL_AE': {
        'aliases': ['withdrawal due to adverse events', 'discontinuation due to adverse events',
                    'withdrawal due to side effects', 'dropout due to adverse events',
                    'treatment discontinuation', 'withdrawals due to lack of efficacy'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'any adverse event', 'serious adverse events',
                    'treatment-related adverse events', 'somnolence', 'dizziness',
                    'nausea'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'OPIOID_USE': {
        'aliases': ['opioid use', 'opioid consumption', 'rescue medication use',
                    'analgesic consumption', 'opioid dose', 'morphine equivalent'],
        'subspecialty': 'pharmacological',
        'measure_types': ['MD', 'RR']
    },
}


# ============================================================
# PHARMACOLOGICAL PATTERNS
# ============================================================

PHARMACOLOGICAL_PATTERNS = {
    'detection_keywords': [
        r'pregabalin|gabapentin|gabapentinoid', r'duloxetine|milnacipran|venlafaxine|snri',
        r'amitriptyline|nortriptyline|tricyclic\s+antidepressant',
        r'\bopioid\b|oxycodone|tapentadol|tramadol|buprenorphine|morphine',
        r'\bnsaid\b|non[- ]steroidal|naproxen|ibuprofen|celecoxib|diclofenac',
        r'capsaicin|lidocaine\s+patch|topical\s+(?:lidocaine|capsaicin)',
        r'cannabi(?:noid|s)|nabilone|nabiximols|\bthc\b|cannabidiol',
        r'pain\s+intensity|pain\s+score|\bvas\b|\bnrs\b',
    ],
    'endpoint_patterns': [
        (r'(?:>=|at\s+least\s+)?50%\s+(?:pain\s+)?(?:reduction|responder|improvement)|'
         r'substantial\s+pain\s+relief|moderate\s+pain\s+relief', 'RESPONDER_50'),
        (r'(?:>=|at\s+least\s+)?30%\s+(?:pain\s+)?(?:reduction|responder|improvement)',
         'RESPONDER_30'),
        (r'withdrawal\s+due\s+to\s+adverse|discontinuation\s+due\s+to\s+adverse|'
         r'dropout\s+due\s+to\s+adverse', 'WITHDRAWAL_AE'),
        (r'pain\s+(?:intensity|score|severity)|average\s+pain|mean\s+pain|'
         r'visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b|'
         r'brief\s+pain\s+inventory|\bbpi\b', 'PAIN_INTENSITY'),
        (r'pain\s+relief|treatment\s+response|global\s+impression\s+of\s+change|\bpgic\b|'
         r'much\s+or\s+very\s+much\s+improved', 'PAIN_RELIEF'),
        (r'sleep\s+(?:quality|interference)|pain[- ]related\s+sleep|\binsomnia\b', 'SLEEP'),
        (r'(?:rescue\s+medication|opioid|analgesic)\s+(?:use|consumption|dose)', 'OPIOID_USE'),
        (r'serious\s+adverse\s+events?|any\s+adverse\s+event|treatment[- ]related\s+adverse',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'0\s*[-–]\s*10\s+(?:scale|nrs)', r'11[- ]point', r'last\s+observation\s+carried',
    ]
}


# ============================================================
# INTERVENTIONAL PATTERNS
# ============================================================

INTERVENTIONAL_PATTERNS = {
    'detection_keywords': [
        r'nerve\s+block|sympathetic\s+block|stellate\s+ganglion',
        r'radiofrequency\s+(?:ablation|denervation)|\brfa\b|pulsed\s+radiofrequency',
        r'spinal\s+cord\s+stimulation|\bscs\b|dorsal\s+root\s+ganglion\s+stimulation',
        r'epidural\s+steroid\s+injection|\besi\b|transforaminal|intra[- ]articular\s+(?:steroid|injection)',
        r'intrathecal|facet\s+joint\s+injection|genicular',
    ],
    'endpoint_patterns': [
        (r'(?:>=|at\s+least\s+)?50%\s+(?:pain\s+)?(?:reduction|responder|improvement)',
         'RESPONDER_50'),
        (r'(?:>=|at\s+least\s+)?30%\s+(?:pain\s+)?(?:reduction|responder|improvement)',
         'RESPONDER_30'),
        (r'pain\s+(?:intensity|score|severity)|visual\s+analogue|\bvas\b|'
         r'numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_INTENSITY'),
        (r'(?:physical\s+)?function|disability|oswestry|roland[- ]morris|womac', 'FUNCTION'),
        (r'pain\s+relief|treatment\s+response|global\s+impression', 'PAIN_RELIEF'),
    ],
    'context_patterns': [
        r'fluoroscop\w+|ultrasound[- ]guided', r'sham\s+(?:procedure|injection)',
    ]
}


# ============================================================
# NEUROPATHIC PATTERNS
# ============================================================

NEUROPATHIC_PATTERNS = {
    'detection_keywords': [
        r'neuropathic\s+pain|painful\s+(?:diabetic\s+)?(?:peripheral\s+)?neuropathy',
        r'diabetic\s+peripheral\s+neuropathy|\bdpn\b|\bpdpn\b',
        r'post[- ]?herpetic\s+neuralgia|\bphn\b|trigeminal\s+neuralgia',
        r'central\s+(?:neuropathic\s+)?pain|post[- ]stroke\s+pain|sciatica',
        r'radiculopathy|allodynia|hyperalgesia',
    ],
    'endpoint_patterns': [
        (r'(?:>=|at\s+least\s+)?50%\s+(?:pain\s+)?(?:reduction|responder|improvement)',
         'RESPONDER_50'),
        (r'(?:>=|at\s+least\s+)?30%\s+(?:pain\s+)?(?:reduction|responder|improvement)',
         'RESPONDER_30'),
        (r'pain\s+(?:intensity|score|severity)|average\s+(?:daily\s+)?pain|'
         r'visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_INTENSITY'),
        (r'withdrawal\s+due\s+to\s+adverse|discontinuation\s+due\s+to\s+adverse', 'WITHDRAWAL_AE'),
        (r'sleep\s+(?:quality|interference)|pain[- ]related\s+sleep', 'SLEEP'),
        (r'pain\s+relief|treatment\s+response|global\s+impression', 'PAIN_RELIEF'),
    ],
    'context_patterns': [
        r'dn4|leeds\s+assessment', r'11[- ]point\s+nrs',
    ]
}


# ============================================================
# BEHAVIOURAL / PHYSICAL PATTERNS
# ============================================================

BEHAVIOURAL_PATTERNS = {
    'detection_keywords': [
        r'cognitive\s+behavio(?:u)?ral\s+therapy|\bcbt\b|acceptance\s+and\s+commitment',
        r'exercise\s+(?:therapy|program|intervention)|physical\s+therapy|physiotherapy',
        r'acupuncture|dry\s+needling', r'mindfulness|meditation',
        r'multidisciplinary|multimodal\s+rehabilitation|pain\s+management\s+program',
        r'yoga|tai\s+chi',
    ],
    'endpoint_patterns': [
        (r'(?:physical\s+)?function|disability|oswestry|roland[- ]morris|womac|'
         r'functional\s+improvement|physical\s+functioning', 'FUNCTION'),
        (r'pain\s+(?:intensity|score|severity)|visual\s+analogue|\bvas\b|'
         r'numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_INTENSITY'),
        (r'quality\s+of\s+life|eq-5d|sf-36|sf-12|\bhrqol\b', 'QOL'),
        (r'(?:>=|at\s+least\s+)?(?:30|50)%\s+(?:pain\s+)?(?:reduction|responder)', 'PAIN_RELIEF'),
        (r'pain\s+relief|treatment\s+response', 'PAIN_RELIEF'),
    ],
    'context_patterns': [
        r'sessions?\s+over\s+\d+\s+weeks', r'waitlist\s+control|usual\s+care',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_chronic_pain_subspecialty(text: str) -> Tuple[str, float]:
    """Detect chronic-pain trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacological, interventional, neuropathic, behavioural,
    general_pain."""
    text_lower = text.lower()
    scores = {'pharmacological': 0, 'interventional': 0,
              'neuropathic': 0, 'behavioural': 0}
    for kw in PHARMACOLOGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacological'] += 1
    for kw in INTERVENTIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['interventional'] += 1
    for kw in NEUROPATHIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neuropathic'] += 1
    for kw in BEHAVIOURAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['behavioural'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pain', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_chronic_pain_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacological': PHARMACOLOGICAL_PATTERNS['endpoint_patterns'],
        'interventional': INTERVENTIONAL_PATTERNS['endpoint_patterns'],
        'neuropathic': NEUROPATHIC_PATTERNS['endpoint_patterns'],
        'behavioural': BEHAVIOURAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_chronic_pain_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical chronic-pain endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in CHRONIC_PAIN_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
