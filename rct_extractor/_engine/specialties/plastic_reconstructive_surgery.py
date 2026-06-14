"""
Plastic & Reconstructive Surgery Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Plastic / reconstructive surgery RCTs
(free / pedicled flaps, breast reconstruction, surgical-wound management, scar
management) report a distinct endpoint vocabulary - flap failure / necrosis,
implant loss, capsular contracture, wound dehiscence, hypertrophic scar / keloid -
that is NOT covered by the wound_healing specialty (chronic ulcers: diabetic-foot,
pressure, venous-leg) or orthopaedic surgery.

Subspecialties:
- flap: total / partial flap failure or necrosis, fat necrosis.
- breast: implant loss / reconstruction failure, capsular contracture, BREAST-Q
  satisfaction.
- complications: surgical-site infection, wound dehiscence, haematoma, seroma,
  reoperation.
- scar: hypertrophic scar / keloid, scar quality (POSAS / Vancouver Scar Scale),
  patient satisfaction.

Drug / procedure classes (arm labels): free flap / pedicled flap, DIEP flap,
implant-based vs autologous reconstruction, acellular dermal matrix,
negative-pressure wound therapy, silicone gel / sheet, pressure garment, placebo.

Effect measures: flap / implant / contracture / infection / dehiscence /
haematoma / seroma / scar -> RR/OR/HR; BREAST-Q / scar-scale / satisfaction ->
MD/SMD (continuous, natural scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PLASTIC / RECONSTRUCTIVE ENDPOINTS
# ============================================================

PLASTIC_RECONSTRUCTIVE_SURGERY_ENDPOINTS = {
    # --- flap ---
    'FLAP_FAILURE': {
        'aliases': ['total flap failure', 'total flap loss', 'complete flap loss',
                    'flap failure', 'flap loss', 'flap necrosis', 'flap survival'],
        'subspecialty': 'flap',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PARTIAL_FLAP_NECROSIS': {
        'aliases': ['partial flap necrosis', 'partial flap loss', 'partial necrosis'],
        'subspecialty': 'flap',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'FAT_NECROSIS': {
        'aliases': ['fat necrosis', 'fat necrosis rate'],
        'subspecialty': 'flap',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- breast ---
    'IMPLANT_LOSS': {
        'aliases': ['implant loss', 'implant failure', 'reconstruction failure',
                    'explantation', 'implant explantation', 'prosthesis loss'],
        'subspecialty': 'breast',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CAPSULAR_CONTRACTURE': {
        'aliases': ['capsular contracture', 'baker grade iii-iv', 'baker grade 3-4',
                    'baker grade iii', 'significant capsular contracture'],
        'subspecialty': 'breast',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'BREAST_Q': {
        'aliases': ['breast-q satisfaction with breasts', 'breast-q', 'breast q',
                    'satisfaction with breasts'],
        'subspecialty': 'breast',
        'measure_types': ['MD', 'SMD']
    },

    # --- complications ---
    'SSI': {
        'aliases': ['surgical-site infection', 'surgical site infection', 'wound infection',
                    'ssi', 'surgical-site infections'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DEHISCENCE': {
        'aliases': ['wound dehiscence', 'wound breakdown', 'dehiscence',
                    'incisional dehiscence'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HAEMATOMA': {
        'aliases': ['haematoma', 'hematoma', 'postoperative haematoma', 'postoperative hematoma'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SEROMA': {
        'aliases': ['seroma', 'seroma formation', 'postoperative seroma'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REOPERATION': {
        'aliases': ['reoperation', 're-operation', 'revision surgery', 'revisional surgery',
                    'return to theatre', 'unplanned reoperation'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- scar ---
    'HYPERTROPHIC_SCAR': {
        'aliases': ['hypertrophic scar', 'keloid', 'pathological scar', 'hypertrophic scarring'],
        'subspecialty': 'scar',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SCAR_QUALITY': {
        'aliases': ['patient and observer scar assessment scale', 'posas',
                    'vancouver scar scale', 'vss', 'scar quality', 'scar score'],
        'subspecialty': 'scar',
        'measure_types': ['MD', 'SMD']
    },
    'PATIENT_SATISFACTION': {
        'aliases': ['patient satisfaction score', 'patient satisfaction',
                    'aesthetic satisfaction', 'cosmetic satisfaction'],
        'subspecialty': 'scar',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# FLAP PATTERNS
# ============================================================

FLAP_PATTERNS = {
    'detection_keywords': [
        r'(?:free|pedicled|local|perforator)\s+flap', r'flap\s+(?:failure|loss|necrosis|survival)',
        r'partial\s+flap\s+(?:necrosis|loss)', r'fat\s+necrosis', r'\bdiep\b|\btram\b|microsurg',
    ],
    'endpoint_patterns': [
        (r'partial\s+flap\s+(?:necrosis|loss)|partial\s+necrosis', 'PARTIAL_FLAP_NECROSIS'),
        (r'fat\s+necrosis', 'FAT_NECROSIS'),
        (r'(?:total|complete)\s+flap\s+(?:failure|loss)|flap\s+(?:failure|loss|necrosis|survival)',
         'FLAP_FAILURE'),
    ],
    'context_patterns': [
        r'anastomos', r'venous\s+congestion', r're[- ]exploration',
    ]
}


# ============================================================
# BREAST PATTERNS
# ============================================================

BREAST_PATTERNS = {
    'detection_keywords': [
        r'breast\s+reconstruction', r'implant[- ]based|autologous\s+reconstruction',
        r'capsular\s+contracture', r'implant\s+(?:loss|failure)|explantation',
        r'acellular\s+dermal\s+matrix|\badm\b', r'breast[- ]q',
    ],
    'endpoint_patterns': [
        (r'capsular\s+contracture|baker\s+grade\s+(?:iii|3)', 'CAPSULAR_CONTRACTURE'),
        (r'breast[- ]q(?:\s+satisfaction)?|satisfaction\s+with\s+breasts', 'BREAST_Q'),
        (r'implant\s+(?:loss|failure)|reconstruction\s+failure|explantation|prosthesis\s+loss',
         'IMPLANT_LOSS'),
    ],
    'context_patterns': [
        r'mastectomy', r'prepectoral|subpectoral', r'radiotherapy',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'surgical[- ]site\s+infection|wound\s+infection|\bssi\b',
        r'wound\s+dehiscence|wound\s+breakdown', r'h(?:ae|e)matoma', r'seroma',
        r'reoperation|revision(?:al)?\s+surgery|return\s+to\s+theatre',
    ],
    'endpoint_patterns': [
        (r'surgical[- ]site\s+infection|wound\s+infection|\bssi\b', 'SSI'),
        (r'(?:wound|incisional)\s+dehiscence|wound\s+breakdown', 'DEHISCENCE'),
        (r'(?:postoperative\s+)?h(?:ae|e)matoma', 'HAEMATOMA'),
        (r'(?:postoperative\s+)?seroma(?:\s+formation)?', 'SEROMA'),
        (r'(?:unplanned\s+)?reoperation|re[- ]operation|revision(?:al)?\s+surgery|return\s+to\s+theatre',
         'REOPERATION'),
    ],
    'context_patterns': [
        r'within\s+30\s+days', r'clavien[- ]dindo', r'drain',
    ]
}


# ============================================================
# SCAR PATTERNS
# ============================================================

SCAR_PATTERNS = {
    'detection_keywords': [
        r'hypertrophic\s+scar|keloid', r'scar\s+(?:quality|score|assessment)',
        r'patient\s+and\s+observer\s+scar|posas|vancouver\s+scar\s+scale|\bvss\b',
        r'(?:patient|aesthetic|cosmetic)\s+satisfaction',
    ],
    'endpoint_patterns': [
        (r'patient\s+and\s+observer\s+scar\s+assessment\s+scale|\bposas\b|vancouver\s+scar\s+scale|'
         r'\bvss\b|scar\s+(?:quality|score)', 'SCAR_QUALITY'),
        (r'(?:patient|aesthetic|cosmetic)\s+satisfaction(?:\s+score)?', 'PATIENT_SATISFACTION'),
        (r'hypertrophic\s+scar(?:ring)?|keloid|pathological\s+scar', 'HYPERTROPHIC_SCAR'),
    ],
    'context_patterns': [
        r'silicone', r'months\s+postoperatively', r'\d+\s+points',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_plastic_reconstructive_surgery_subspecialty(text: str) -> Tuple[str, float]:
    """Detect plastic / reconstructive surgery trial subspecialty. Returns
    (subspecialty, confidence). Subspecialties: flap, breast, complications,
    scar, general_plastic."""
    text_lower = text.lower()
    scores = {'flap': 0, 'breast': 0, 'complications': 0, 'scar': 0}
    for kw in FLAP_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['flap'] += 1
    for kw in BREAST_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['breast'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1
    for kw in SCAR_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['scar'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_plastic', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_plastic_reconstructive_surgery_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'flap': FLAP_PATTERNS['endpoint_patterns'],
        'breast': BREAST_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
        'scar': SCAR_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_plastic_reconstructive_surgery_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical plastic-surgery endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PLASTIC_RECONSTRUCTIVE_SURGERY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
