"""
Menopause / Hormone-Replacement-Therapy Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the cervical-cancer, endometriosis
and maternal-neonatal women's-health profiles. Menopausal symptom management and
hormone therapy generate a large RCT literature with a distinct endpoint
vocabulary spanning vasomotor symptoms, genitourinary syndrome, bone, and the
WHI-class systemic safety outcomes that the generic effect-size engine does not
recognise on its own.

Subspecialties:
- Vasomotor (VMS): hot flushes / hot flashes, night sweats, vasomotor-symptom
  frequency and severity, VMS responder (>=50% reduction), sleep disturbance.
  Interventions: systemic oestrogen (conjugated equine oestrogens, oestradiol),
  tibolone, NK3-receptor antagonists (fezolinetant, elinzanetant), SSRIs/SNRIs
  (paroxetine, venlafaxine, desvenlafaxine), gabapentin, clonidine.
- Genitourinary (GSM / vulvovaginal atrophy): vaginal dryness, dyspareunia,
  vulvovaginal atrophy, vaginal pH, vaginal maturation index, most-bothersome
  symptom. Interventions: local vaginal oestrogen, ospemifene, intravaginal
  prasterone (DHEA).
- Bone (osteoporosis prevention): bone mineral density, vertebral fracture,
  non-vertebral fracture, hip fracture. Interventions: HRT, raloxifene,
  bazedoxifene/CEE.
- Safety (systemic outcomes): breast cancer, endometrial hyperplasia /
  endometrial cancer, venous thromboembolism, stroke, coronary heart disease.

Effect measures follow what these trials report: binary / time-to-event
(fracture, breast cancer, VTE, stroke, CHD, VMS responder, endometrial
hyperplasia) -> RR/OR/HR; continuous (VMS frequency/severity, BMD %, vaginal pH,
maturation index, quality of life) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# MENOPAUSE / HRT ENDPOINTS
# ============================================================

MENOPAUSE_HRT_ENDPOINTS = {
    # --- Vasomotor (VMS) ---
    'HOT_FLUSHES': {
        'aliases': ['hot flush', 'hot flushes', 'hot flash', 'hot flashes',
                    'vasomotor symptom', 'vasomotor symptoms', 'vms frequency',
                    'moderate to severe vasomotor', 'daily hot flush frequency',
                    'frequency of hot flushes'],
        'subspecialty': 'vasomotor',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'NIGHT_SWEATS': {
        'aliases': ['night sweat', 'night sweats', 'nocturnal sweating'],
        'subspecialty': 'vasomotor',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'VMS_SEVERITY': {
        'aliases': ['vasomotor severity', 'hot flush severity', 'severity score',
                    'vms severity', 'hot flash severity', 'symptom severity'],
        'subspecialty': 'vasomotor',
        'measure_types': ['MD', 'SMD']
    },
    'VMS_RESPONSE': {
        'aliases': ['vms responder', 'hot flush responder', 'response rate',
                    'responder rate', 'clinically meaningful reduction',
                    '50% reduction', 'at least 50% reduction'],
        'subspecialty': 'vasomotor',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SLEEP': {
        'aliases': ['sleep disturbance', 'sleep quality', 'insomnia',
                    'pittsburgh sleep quality', 'psqi', 'sleep score'],
        'subspecialty': 'vasomotor',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },

    # --- Genitourinary (GSM / vulvovaginal atrophy) ---
    'VAGINAL_DRYNESS': {
        'aliases': ['vaginal dryness', 'vulvovaginal dryness', 'dryness severity'],
        'subspecialty': 'genitourinary',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'GSM_DYSPAREUNIA': {
        'aliases': ['dyspareunia', 'painful intercourse', 'moderate to severe dyspareunia',
                    'most bothersome symptom'],
        'subspecialty': 'genitourinary',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'VULVOVAGINAL_ATROPHY': {
        'aliases': ['vulvovaginal atrophy', 'vaginal atrophy', 'genitourinary syndrome',
                    'genitourinary syndrome of menopause', 'atrophic vaginitis'],
        'subspecialty': 'genitourinary',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'VAGINAL_PH': {
        'aliases': ['vaginal ph', 'vaginal maturation index', 'maturation index',
                    'superficial cells', 'parabasal cells', 'vaginal cytology'],
        'subspecialty': 'genitourinary',
        'measure_types': ['MD', 'SMD']
    },

    # --- Bone (osteoporosis prevention) ---
    'BMD': {
        'aliases': ['bone mineral density', 'bmd', 'lumbar spine bmd',
                    'femoral neck bmd', 'total hip bmd', 'change in bmd',
                    'percentage change in bone mineral density'],
        'subspecialty': 'bone',
        'measure_types': ['MD', 'SMD']
    },
    'VERTEBRAL_FRACTURE': {
        'aliases': ['vertebral fracture', 'vertebral fractures',
                    'new vertebral fracture', 'morphometric vertebral fracture',
                    'clinical vertebral fracture'],
        'subspecialty': 'bone',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NONVERTEBRAL_FRACTURE': {
        'aliases': ['non-vertebral fracture', 'nonvertebral fracture',
                    'non vertebral fracture', 'any fracture', 'total fractures',
                    'osteoporotic fracture'],
        'subspecialty': 'bone',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HIP_FRACTURE': {
        'aliases': ['hip fracture', 'hip fractures', 'femoral fracture',
                    'proximal femur fracture'],
        'subspecialty': 'bone',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Safety (systemic outcomes) ---
    'BREAST_CANCER': {
        'aliases': ['breast cancer', 'invasive breast cancer', 'breast carcinoma',
                    'breast cancer incidence', 'breast tumour', 'breast tumor'],
        'subspecialty': 'safety',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ENDOMETRIAL_HYPERPLASIA': {
        'aliases': ['endometrial hyperplasia', 'endometrial cancer',
                    'endometrial carcinoma', 'endometrial neoplasia',
                    'uterine cancer'],
        'subspecialty': 'safety',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VENOUS_THROMBOEMBOLISM': {
        'aliases': ['venous thromboembolism', 'vte', 'deep vein thrombosis',
                    'deep venous thrombosis', 'pulmonary embolism',
                    'thromboembolic event', 'thromboembolism'],
        'subspecialty': 'safety',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'STROKE_EVENT': {
        'aliases': ['stroke', 'ischaemic stroke', 'ischemic stroke',
                    'cerebrovascular event', 'cerebrovascular accident'],
        'subspecialty': 'safety',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CORONARY_HEART_DISEASE': {
        'aliases': ['coronary heart disease', 'chd', 'coronary event',
                    'myocardial infarction', 'cardiovascular disease',
                    'coronary artery disease'],
        'subspecialty': 'safety',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Quality of life (shared) ---
    'QUALITY_OF_LIFE': {
        'aliases': ['quality of life', 'menopause-specific quality of life',
                    'menqol', 'greene climacteric scale', 'health-related quality of life',
                    'climacteric symptoms'],
        'subspecialty': 'vasomotor',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# VASOMOTOR PATTERNS
# ============================================================

VASOMOTOR_PATTERNS = {
    'detection_keywords': [
        r'hot\s+flush(?:es)?', r'hot\s+flash(?:es)?', r'vasomotor\s+symptom',
        r'\bvms\b', r'night\s+sweats?', r'fezolinetant', r'elinzanetant',
        r'nk3\s+receptor|neurokinin[- ]3', r'conjugated\s+equine\s+(?:o?estrogen)',
        r'\bcee\b', r'o?estradiol', r'tibolone', r'paroxetine|venlafaxine|desvenlafaxine',
        r'gabapentin', r'climacteric',
    ],
    'endpoint_patterns': [
        (r'hot\s+flush(?:es)?|hot\s+flash(?:es)?|vasomotor\s+symptom|\bvms\b\s+frequency|'
         r'moderate[- ]to[- ]severe\s+vasomotor|frequency\s+of\s+hot\s+flush', 'HOT_FLUSHES'),
        (r'night\s+sweats?|nocturnal\s+sweating', 'NIGHT_SWEATS'),
        (r'(?:vasomotor|hot\s+flush|hot\s+flash|symptom)\s+severity|severity\s+score|'
         r'\bvms\b\s+severity', 'VMS_SEVERITY'),
        (r'(?:vms|hot\s+flush)\s+responder|response\s+rate|responder\s+rate|'
         r'(?:at\s+least\s+)?50\s*%?\s+reduction|clinically\s+meaningful\s+reduction',
         'VMS_RESPONSE'),
        (r'sleep\s+(?:disturbance|quality|score)|insomnia|pittsburgh\s+sleep|\bpsqi\b',
         'SLEEP'),
        (r'quality\s+of\s+life|menopause[- ]specific\s+quality|\bmenqol\b|'
         r'greene\s+climacteric|climacteric\s+symptoms', 'QUALITY_OF_LIFE'),
    ],
    'context_patterns': [
        r'per\s+(?:day|week)', r'change\s+from\s+baseline', r'week\s+(?:4|12)',
        r'moderate\s+to\s+severe',
    ]
}


# ============================================================
# GENITOURINARY (GSM) PATTERNS
# ============================================================

GENITOURINARY_PATTERNS = {
    'detection_keywords': [
        r'vulvovaginal\s+atrophy', r'vaginal\s+atrophy', r'genitourinary\s+syndrome',
        r'vaginal\s+dryness', r'dyspareunia', r'vaginal\s+ph',
        r'vaginal\s+maturation\s+index', r'ospemifene', r'prasterone|intravaginal\s+dhea',
        r'local\s+(?:vaginal\s+)?o?estrogen', r'atrophic\s+vaginitis',
        r'most\s+bothersome\s+symptom',
    ],
    'endpoint_patterns': [
        (r'vaginal\s+dryness|vulvovaginal\s+dryness|dryness\s+severity', 'VAGINAL_DRYNESS'),
        (r'dyspareunia|painful\s+intercourse|most\s+bothersome\s+symptom', 'GSM_DYSPAREUNIA'),
        (r'vulvovaginal\s+atrophy|vaginal\s+atrophy|genitourinary\s+syndrome|'
         r'atrophic\s+vaginitis', 'VULVOVAGINAL_ATROPHY'),
        (r'vaginal\s+ph|vaginal\s+maturation\s+index|maturation\s+index|'
         r'superficial\s+cells|parabasal\s+cells', 'VAGINAL_PH'),
    ],
    'context_patterns': [
        r'12[- ]week', r'maturation\s+value', r'percentage\s+of\s+(?:superficial|parabasal)',
    ]
}


# ============================================================
# BONE PATTERNS
# ============================================================

BONE_PATTERNS = {
    'detection_keywords': [
        r'bone\s+mineral\s+density', r'\bbmd\b', r'vertebral\s+fracture',
        r'non[- ]?vertebral\s+fracture', r'hip\s+fracture', r'osteoporo(?:sis|tic)',
        r'raloxifene', r'bazedoxifene', r'lumbar\s+spine|femoral\s+neck|total\s+hip',
        r'fracture\s+risk',
    ],
    'endpoint_patterns': [
        (r'vertebral\s+fracture', 'VERTEBRAL_FRACTURE'),
        (r'non[- ]?vertebral\s+fracture|any\s+fracture|osteoporotic\s+fracture|'
         r'total\s+fractures', 'NONVERTEBRAL_FRACTURE'),
        (r'hip\s+fracture|femoral\s+fracture|proximal\s+femur\s+fracture', 'HIP_FRACTURE'),
        (r'bone\s+mineral\s+density|\bbmd\b|lumbar\s+spine\s+bmd|femoral\s+neck\s+bmd|'
         r'total\s+hip\s+bmd|change\s+in\s+bmd', 'BMD'),
    ],
    'context_patterns': [
        r'percentage\s+change', r'dual[- ]energy\s+x[- ]ray|\bdxa\b', r'24[- ]month',
    ]
}


# ============================================================
# SAFETY (systemic outcomes) PATTERNS
# ============================================================

SAFETY_PATTERNS = {
    'detection_keywords': [
        r'breast\s+cancer', r'endometrial\s+(?:hyperplasia|cancer)',
        r'venous\s+thromboembolism|\bvte\b', r'deep\s+vein\s+thrombosis',
        r'pulmonary\s+embolism', r'coronary\s+heart\s+disease|\bchd\b',
        r'myocardial\s+infarction', r'stroke', r'cardiovascular\s+disease',
    ],
    'endpoint_patterns': [
        (r'breast\s+cancer|invasive\s+breast\s+cancer|breast\s+carcinoma|'
         r'breast\s+tumou?r', 'BREAST_CANCER'),
        (r'endometrial\s+hyperplasia|endometrial\s+(?:cancer|carcinoma|neoplasia)|'
         r'uterine\s+cancer', 'ENDOMETRIAL_HYPERPLASIA'),
        (r'venous\s+thromboembolism|\bvte\b|deep\s+ven(?:ous|)\s+thrombosis|'
         r'pulmonary\s+embolism|thromboembolic\s+event', 'VENOUS_THROMBOEMBOLISM'),
        (r'\bstroke\b|isch[ae]mic\s+stroke|cerebrovascular\s+(?:event|accident)',
         'STROKE_EVENT'),
        (r'coronary\s+heart\s+disease|\bchd\b|coronary\s+event|myocardial\s+infarction|'
         r'cardiovascular\s+disease|coronary\s+artery\s+disease', 'CORONARY_HEART_DISEASE'),
    ],
    'context_patterns': [
        r'per\s+10,?000\s+(?:woman|person)[- ]years', r'hazard\s+ratio',
        r'women[- ]years\s+of\s+follow[- ]up',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_menopause_hrt_subspecialty(text: str) -> Tuple[str, float]:
    """Detect menopause/HRT trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: vasomotor, genitourinary, bone, safety, general_menopause."""
    text_lower = text.lower()
    scores = {'vasomotor': 0, 'genitourinary': 0, 'bone': 0, 'safety': 0}
    for kw in VASOMOTOR_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vasomotor'] += 1
    for kw in GENITOURINARY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['genitourinary'] += 1
    for kw in BONE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bone'] += 1
    for kw in SAFETY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['safety'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_menopause', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_menopause_hrt_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'vasomotor': VASOMOTOR_PATTERNS['endpoint_patterns'],
        'genitourinary': GENITOURINARY_PATTERNS['endpoint_patterns'],
        'bone': BONE_PATTERNS['endpoint_patterns'],
        'safety': SAFETY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_menopause_hrt_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical menopause/HRT endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in MENOPAUSE_HRT_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
