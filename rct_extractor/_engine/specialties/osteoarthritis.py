"""
Osteoarthritis Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. Osteoarthritis (OA) RCTs report a distinct endpoint vocabulary (WOMAC
pain / function / total, pain VAS, OMERACT-OARSI responder, joint space width,
KOOS, total joint replacement) that the generic effect-size engine — and the
rheumatology profile (ra/psa/axspa/gout/sle, no OA) — do not capture.

Subspecialties (mapped onto the registry's generic pattern slots):
- pharmacologic (TREATMENT slot): systemic/topical analgesia — NSAIDs (naproxen,
  celecoxib, diclofenac), paracetamol/acetaminophen, duloxetine, anti-NGF
  (tanezumab). Endpoints: WOMAC pain/function, pain VAS, responder.
- intraarticular (DRUG_RESISTANT slot): intra-articular therapy — corticosteroid
  (triamcinolone), hyaluronic acid/viscosupplementation, platelet-rich plasma,
  injectable agents.
- structural (PREVENTION slot): disease-modifying OA drugs (DMOAD) / structural
  progression — joint space width, cartilage thickness, sprifermin, cathepsin-K.
- nonpharm (LATENT slot): exercise / weight loss / surgery — total knee/hip
  replacement (arthroplasty), physiotherapy, weight reduction.

Effect measures: WOMAC / pain VAS / joint-space-width / KOOS change -> mean
difference; OMERACT-OARSI responder / total joint replacement -> RR/OR/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

OSTEOARTHRITIS_ENDPOINTS = {
    'WOMAC_PAIN': {
        'aliases': ['womac pain', 'womac pain subscale', 'womac pain score',
                    'pain subscale', 'change in womac pain'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },
    'WOMAC_FUNCTION': {
        'aliases': ['womac function', 'womac physical function', 'womac function subscale',
                    'physical function subscale', 'womac disability'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },
    'WOMAC_TOTAL': {
        'aliases': ['womac total', 'womac total score', 'total womac',
                    'western ontario and mcmaster', 'womac global'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },
    'PAIN_VAS': {
        'aliases': ['pain vas', 'visual analogue scale', 'visual analog scale',
                    'pain on a visual analogue', 'vas pain', 'pain intensity',
                    'numeric rating scale', 'nrs pain'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['MD', 'SMD']
    },
    'KOOS': {
        'aliases': ['koos', 'knee injury and osteoarthritis outcome score',
                    'koos pain', 'koos quality of life', 'hoos'],
        'subspecialty': 'nonpharm',
        'measure_types': ['MD']
    },
    'RESPONDER': {
        'aliases': ['omeract-oarsi responder', 'oarsi responder', 'responder',
                    'responder rate', 'omeract responder', 'treatment response',
                    '20% improvement', '50% improvement in pain'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'JOINT_SPACE_WIDTH': {
        'aliases': ['joint space width', 'joint-space width', 'jsw',
                    'joint space narrowing', 'cartilage thickness', 'cartilage volume',
                    'minimum joint space width', 'structural progression'],
        'subspecialty': 'structural',
        'measure_types': ['MD']
    },
    'TJR': {
        'aliases': ['total knee replacement', 'total joint replacement',
                    'total hip replacement', 'knee arthroplasty', 'hip arthroplasty',
                    'joint replacement', 'tkr', 'tka', 'arthroplasty'],
        'subspecialty': 'nonpharm',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RESCUE_MEDICATION': {
        'aliases': ['rescue medication', 'rescue analgesic', 'use of rescue medication',
                    'acetaminophen use', 'paracetamol use'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'MD']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'gastrointestinal adverse',
                    'rapidly progressive osteoarthritis', 'discontinuation due to adverse'],
        'subspecialty': 'pharmacologic',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


TREATMENT_PATTERNS = {  # = pharmacologic
    'detection_keywords': [
        r'osteoarthritis|\boa\b|knee\s+oa|hip\s+oa|degenerative\s+joint',
        r'\bwomac\b|western\s+ontario',
        r'naproxen|celecoxib|diclofenac|ibuprofen|etoricoxib|nsaid',
        r'paracetamol|acetaminophen|duloxetine|tanezumab|anti[- ]ngf|nerve\s+growth\s+factor',
        r'pain\s+(?:vas|score|intensity)|visual\s+analog',
    ],
    'endpoint_patterns': [
        (r'womac\s+pain|pain\s+subscale', 'WOMAC_PAIN'),
        (r'womac\s+(?:physical\s+)?function|function\s+subscale|womac\s+disability',
         'WOMAC_FUNCTION'),
        (r'womac\s+total|total\s+womac|womac\s+global|western\s+ontario', 'WOMAC_TOTAL'),
        (r'pain\s+vas|visual\s+analog(?:ue)?\s+scale|vas\s+pain|pain\s+intensity|'
         r'numeric\s+rating\s+scale|\bnrs\b', 'PAIN_VAS'),
        (r'omeract[- ]oarsi\s+responder|oarsi\s+responder|omeract\s+responder|'
         r'responder\s+rate|\bresponders?\b|20\s*%\s+improvement', 'RESPONDER'),
        (r'rescue\s+(?:medication|analgesic)|acetaminophen\s+use|paracetamol\s+use',
         'RESCUE_MEDICATION'),
        (r'gastrointestinal\s+adverse|serious\s+adverse\s+events?|\badverse\s+events?\b',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'week\s+(?:12|26|52)', r'knee\s+or\s+hip',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = intraarticular
    'detection_keywords': [
        r'intra[- ]?articular|\bia\s+(?:injection|steroid|corticosteroid)',
        r'hyaluron(?:ic|ate)|viscosupplement|hylan',
        r'triamcinolone|methylprednisolone\s+(?:acetate|injection)|corticosteroid\s+injection',
        r'platelet[- ]rich\s+plasma|\bprp\b|mesenchymal\s+stem\s+cell',
        r'genicular|injection\s+(?:into\s+)?the\s+knee',
    ],
    'endpoint_patterns': [
        (r'womac\s+pain|pain\s+subscale', 'WOMAC_PAIN'),
        (r'womac\s+(?:physical\s+)?function', 'WOMAC_FUNCTION'),
        (r'pain\s+vas|visual\s+analog(?:ue)?|vas\s+pain|pain\s+intensity', 'PAIN_VAS'),
        (r'omeract[- ]oarsi\s+responder|oarsi\s+responder|responder\s+rate|\bresponders?\b',
         'RESPONDER'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'single\s+injection|repeat\s+injection', r'ultrasound[- ]guided',
    ]
}


PREVENTION_PATTERNS = {  # = structural / DMOAD
    'detection_keywords': [
        r'disease[- ]modifying\s+osteoarthritis|\bdmoad\b|structural\s+(?:progression|modification)',
        r'joint[- ]space\s+(?:width|narrowing)|\bjsw\b|cartilage\s+(?:thickness|volume|loss)',
        r'sprifermin|cathepsin[- ]k|lorecivivint|\bsm04690\b',
        r'radiographic\s+progression|mri\s+cartilage',
    ],
    'endpoint_patterns': [
        (r'joint[- ]space\s+width|\bjsw\b|joint[- ]space\s+narrowing|cartilage\s+(?:thickness|volume)|'
         r'structural\s+progression|minimum\s+joint\s+space', 'JOINT_SPACE_WIDTH'),
        (r'womac\s+pain', 'WOMAC_PAIN'),
        (r'womac\s+(?:physical\s+)?function', 'WOMAC_FUNCTION'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'radiographic|x[- ]ray', r'over\s+(?:1|2|two)\s+years',
    ]
}


LATENT_PATTERNS = {  # = nonpharm (exercise / weight / surgery)
    'detection_keywords': [
        r'exercise|physiotherapy|physical\s+therapy|strengthening',
        r'weight\s+(?:loss|reduction)|diet',
        r'total\s+(?:knee|hip|joint)\s+(?:replacement|arthroplasty)|\btkr\b|\btka\b|arthroplasty',
        r'\bkoos\b|knee\s+injury\s+and\s+osteoarthritis',
    ],
    'endpoint_patterns': [
        (r'total\s+(?:knee|hip|joint)\s+(?:replacement|arthroplasty)|\btkr\b|\btka\b|'
         r'joint\s+replacement|arthroplasty', 'TJR'),
        (r'\bkoos\b|knee\s+injury\s+and\s+osteoarthritis|\bhoos\b', 'KOOS'),
        (r'womac\s+pain', 'WOMAC_PAIN'),
        (r'womac\s+(?:physical\s+)?function', 'WOMAC_FUNCTION'),
        (r'pain\s+vas|visual\s+analog(?:ue)?', 'PAIN_VAS'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'supervised\s+exercise', r'body\s+mass\s+index|\bbmi\b',
    ]
}


def detect_osteoarthritis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect OA trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pharmacologic, intraarticular, structural, nonpharm, general_oa."""
    text_lower = text.lower()
    scores = {'pharmacologic': 0, 'intraarticular': 0, 'structural': 0, 'nonpharm': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pharmacologic'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['intraarticular'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['structural'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['nonpharm'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_oa', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_osteoarthritis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pharmacologic': TREATMENT_PATTERNS['endpoint_patterns'],
        'intraarticular': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'structural': PREVENTION_PATTERNS['endpoint_patterns'],
        'nonpharm': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_osteoarthritis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical OA endpoint, preferring the LONGEST matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in OSTEOARTHRITIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
