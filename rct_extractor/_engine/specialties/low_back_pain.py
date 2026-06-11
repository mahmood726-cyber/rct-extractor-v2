"""
Low Back Pain Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the tuberculosis / ARDS profiles.
Low-back-pain (and sciatica) RCTs report a distinct endpoint vocabulary (pain
intensity on a VAS / NRS, Oswestry / Roland-Morris disability, global perceived
improvement, responder rate, return to work, recurrence) that the generic
effect-size engine does not recognise on its own.

Subspecialties:
- Pharmacological: NSAIDs, paracetamol, opioids, muscle relaxants, antidepressants
  (duloxetine, amitriptyline), gabapentinoids for sciatica.
- Interventional / surgical: epidural steroid injection, radiofrequency / facet
  denervation, discectomy / microdiscectomy, spinal fusion vs non-operative.
- Physical: exercise therapy, physiotherapy, spinal manipulation / manual
  therapy, McKenzie, yoga, motor control / core stability.
- Psychological / multidisciplinary: cognitive behavioural therapy, mindfulness,
  cognitive functional therapy, multidisciplinary biopsychosocial rehabilitation.

Effect measures follow what these trials report: continuous (pain intensity,
disability [ODI / RMDQ], quality of life) -> mean difference; binary
(responders, recovery / recovered, return to work, recurrence, global
improvement) -> RR/OR/RD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# LOW BACK PAIN ENDPOINTS
# ============================================================

LOW_BACK_PAIN_ENDPOINTS = {
    'PAIN_INTENSITY': {
        'aliases': ['pain intensity', 'pain score', 'back pain intensity', 'leg pain',
                    'mean pain', 'average pain', 'visual analogue scale', 'vas pain',
                    'numeric rating scale', 'numerical rating scale', 'nrs pain',
                    'pain severity', 'change in pain', 'low back pain intensity'],
        'subspecialty': 'pharmacological',
        'measure_types': ['MD']
    },
    'DISABILITY': {
        'aliases': ['disability', 'oswestry disability index', 'odi',
                    'roland-morris disability questionnaire', 'roland morris', 'rmdq', 'rdq',
                    'functional disability', 'back-specific function',
                    'disability score', 'quebec back pain disability'],
        'subspecialty': 'physical',
        'measure_types': ['MD']
    },
    'GLOBAL_IMPROVEMENT': {
        'aliases': ['global perceived effect', 'global improvement', 'global impression of change',
                    'patient global impression', 'pgic', 'perceived recovery',
                    'much improved', 'global perceived recovery'],
        'subspecialty': 'physical',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'RESPONDER': {
        'aliases': ['responder', 'responder rate', 'treatment success', 'clinical response',
                    'proportion of responders', '30% pain reduction', '50% pain reduction',
                    'clinically important improvement', 'minimal clinically important'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RECOVERY': {
        'aliases': ['recovery', 'recovered', 'recovery from low back pain',
                    'time to recovery', 'resolution of pain', 'pain-free',
                    'symptom resolution'],
        'subspecialty': 'physical',
        'measure_types': ['RR', 'HR', 'MD']
    },
    'RETURN_TO_WORK': {
        'aliases': ['return to work', 'time to return to work', 'sick leave',
                    'work absence', 'days off work', 'work disability', 'absenteeism'],
        'subspecialty': 'psychological',
        'measure_types': ['RR', 'HR', 'MD']
    },
    'RECURRENCE': {
        'aliases': ['recurrence', 'recurrent low back pain', 'relapse',
                    'recurrence of pain', 'new episode'],
        'subspecialty': 'physical',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'QOL': {
        'aliases': ['quality of life', 'eq-5d', 'sf-36', 'sf-12', 'health-related quality of life',
                    'hrqol'],
        'subspecialty': 'physical',
        'measure_types': ['MD']
    },
    'REOPERATION': {
        'aliases': ['reoperation', 're-operation', 'revision surgery', 'further surgery',
                    'crossover to surgery', 'need for surgery'],
        'subspecialty': 'interventional',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'OPIOID_USE': {
        'aliases': ['opioid use', 'opioid consumption', 'analgesic use',
                    'medication use', 'rescue medication'],
        'subspecialty': 'pharmacological',
        'measure_types': ['MD', 'RR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'treatment-related adverse events',
                    'side effects'],
        'subspecialty': 'pharmacological',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# PHARMACOLOGICAL PATTERNS
# ============================================================

PHARMACOLOGICAL_PATTERNS = {
    'detection_keywords': [
        r'\bnsaid\b|non[- ]steroidal|naproxen|ibuprofen|diclofenac|celecoxib|paracetamol|acetaminophen',
        r'\bopioid\b|oxycodone|tramadol|tapentadol|codeine',
        r'muscle\s+relaxant|cyclobenzaprine|tizanidine|baclofen',
        r'duloxetine|amitriptyline|antidepressant',
        r'pregabalin|gabapentin\s+for\s+sciatica|gabapentinoid',
        r'low\s+back\s+pain|lumbago',
    ],
    'endpoint_patterns': [
        (r'(?:oswestry\s+disability\s+index|\bodi\b|roland[- ]morris|\brmdq\b|\brdq\b|'
         r'quebec\s+back\s+pain)\b|(?:functional\s+)?disability(?:\s+score)?', 'DISABILITY'),
        (r'(?:30|50)%\s+(?:pain\s+)?reduction|responder|treatment\s+success|'
         r'clinically\s+important\s+improvement', 'RESPONDER'),
        (r'(?:back\s+|leg\s+|low\s+back\s+)?pain\s+(?:intensity|score|severity)|average\s+pain|'
         r'mean\s+pain|visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b',
         'PAIN_INTENSITY'),
        (r'(?:opioid|analgesic|medication|rescue\s+medication)\s+(?:use|consumption)', 'OPIOID_USE'),
        (r'global\s+(?:perceived\s+(?:effect|recovery)|impression)|\bpgic\b', 'GLOBAL_IMPROVEMENT'),
        (r'serious\s+adverse|treatment[- ]related\s+adverse|side\s+effects', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'acute\s+low\s+back\s+pain|chronic\s+low\s+back\s+pain', r'0\s*[-–]\s*10\s+scale',
    ]
}


# ============================================================
# INTERVENTIONAL / SURGICAL PATTERNS
# ============================================================

INTERVENTIONAL_PATTERNS = {
    'detection_keywords': [
        r'epidural\s+(?:steroid\s+)?injection|transforaminal|caudal\s+epidural',
        r'radiofrequency\s+(?:ablation|denervation)|facet\s+(?:joint\s+)?(?:injection|denervation)',
        r'discectomy|microdiscectomy|disc\s+herniation|lumbar\s+disc',
        r'spinal\s+fusion|lumbar\s+fusion|decompression\s+surgery|laminectomy',
        r'sciatica|radiculopathy|nerve\s+root',
    ],
    'endpoint_patterns': [
        (r're[- ]?operation|revision\s+surgery|further\s+surgery|crossover\s+to\s+surgery|'
         r'need\s+for\s+surgery', 'REOPERATION'),
        (r'(?:leg\s+|back\s+)?pain\s+(?:intensity|score)|visual\s+analogue|\bvas\b|'
         r'numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_INTENSITY'),
        (r'(?:oswestry\s+disability\s+index|\bodi\b|roland[- ]morris|\brmdq\b)\b|disability(?:\s+score)?',
         'DISABILITY'),
        (r'global\s+(?:perceived|impression)|\bpgic\b|perceived\s+recovery', 'GLOBAL_IMPROVEMENT'),
        (r'recovery|recovered|resolution\s+of\s+(?:pain|symptoms)|pain[- ]free', 'RECOVERY'),
        (r'responder|treatment\s+success', 'RESPONDER'),
    ],
    'context_patterns': [
        r'spine\s+patient\s+outcomes', r'lumbar\s+spinal\s+stenosis',
    ]
}


# ============================================================
# PHYSICAL PATTERNS
# ============================================================

PHYSICAL_PATTERNS = {
    'detection_keywords': [
        r'exercise\s+(?:therapy|program|intervention)|physiotherapy|physical\s+therapy',
        r'spinal\s+manipulation|manual\s+therapy|mckenzie|mobili[sz]ation',
        r'motor\s+control|core\s+stability|stabili[sz]ation\s+exercise',
        r'yoga|pilates|tai\s+chi', r'graded\s+activity',
        r'oswestry|roland[- ]morris',
    ],
    'endpoint_patterns': [
        (r'(?:oswestry\s+disability\s+index|\bodi\b|roland[- ]morris(?:\s+disability)?|\brmdq\b|\brdq\b|'
         r'quebec\s+back\s+pain)\b|(?:functional\s+)?disability(?:\s+score)?', 'DISABILITY'),
        (r'(?:back\s+|low\s+back\s+)?pain\s+(?:intensity|score|severity)|average\s+pain|'
         r'visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating\s+scale|\bnrs\b', 'PAIN_INTENSITY'),
        (r'global\s+(?:perceived\s+(?:effect|recovery)|impression)|\bpgic\b|much\s+improved',
         'GLOBAL_IMPROVEMENT'),
        (r'recovery|recovered|time\s+to\s+recovery|pain[- ]free', 'RECOVERY'),
        (r'recurrence|recurrent\s+(?:low\s+back\s+pain|episode)|relapse', 'RECURRENCE'),
        (r'quality\s+of\s+life|eq-5d|sf-36|sf-12', 'QOL'),
        (r'return\s+to\s+work|sick\s+leave|work\s+absence|days\s+off\s+work', 'RETURN_TO_WORK'),
    ],
    'context_patterns': [
        r'supervised\s+exercise', r'home\s+exercise\s+program',
    ]
}


# ============================================================
# PSYCHOLOGICAL / MULTIDISCIPLINARY PATTERNS
# ============================================================

PSYCHOLOGICAL_PATTERNS = {
    'detection_keywords': [
        r'cognitive\s+behavio(?:u)?ral\s+therapy|\bcbt\b|cognitive\s+functional\s+therapy|\bcft\b',
        r'mindfulness|acceptance\s+and\s+commitment|pain\s+neuroscience\s+education',
        r'multidisciplinary|biopsychosocial|interdisciplinary\s+rehabilitation',
        r'fear[- ]avoidance|psychologically\s+informed',
        r'return\s+to\s+work|work[- ]focused',
    ],
    'endpoint_patterns': [
        (r'return\s+to\s+work|time\s+to\s+return\s+to\s+work|sick\s+leave|work\s+absence|'
         r'days\s+off\s+work|absenteeism', 'RETURN_TO_WORK'),
        (r'(?:oswestry\s+disability\s+index|\bodi\b|roland[- ]morris|\brmdq\b)\b|disability(?:\s+score)?',
         'DISABILITY'),
        (r'(?:back\s+)?pain\s+(?:intensity|score)|visual\s+analogue|\bvas\b|numeric(?:al)?\s+rating',
         'PAIN_INTENSITY'),
        (r'global\s+(?:perceived|impression)|\bpgic\b', 'GLOBAL_IMPROVEMENT'),
        (r'quality\s+of\s+life|eq-5d|sf-36', 'QOL'),
        (r'recovery|recovered', 'RECOVERY'),
    ],
    'context_patterns': [
        r'fear[- ]avoidance\s+beliefs', r'catastrophi[sz]ing',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_low_back_pain_subspecialty(text: str) -> Tuple[str, float]:
    """Detect low-back-pain trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacological, interventional, physical, psychological,
    general_lbp."""
    text_lower = text.lower()
    scores = {'pharmacological': 0, 'interventional': 0,
              'physical': 0, 'psychological': 0}
    for kw in PHARMACOLOGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacological'] += 1
    for kw in INTERVENTIONAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['interventional'] += 1
    for kw in PHYSICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['physical'] += 1
    for kw in PSYCHOLOGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['psychological'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_lbp', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_low_back_pain_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacological': PHARMACOLOGICAL_PATTERNS['endpoint_patterns'],
        'interventional': INTERVENTIONAL_PATTERNS['endpoint_patterns'],
        'physical': PHYSICAL_PATTERNS['endpoint_patterns'],
        'psychological': PSYCHOLOGICAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_low_back_pain_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical low-back-pain endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in LOW_BACK_PAIN_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
