"""
Uterine Fibroids (Leiomyoma) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the endometriosis, menopause and
other women's-health profiles. Uterine fibroids are the commonest benign
gynaecological tumour and their RCTs (GnRH antagonists + add-back, ulipristal,
tranexamic acid, uterine artery embolisation vs myomectomy, MRgFUS, radiofrequency
ablation) report a distinct bleeding / volume / procedural endpoint vocabulary the
generic effect-size engine does not recognise on its own.

Subspecialties:
- Bleeding (heavy menstrual bleeding): menstrual blood loss (alkaline-haematin /
  PBAC pictorial score), bleeding-control / amenorrhoea responder, haemoglobin
  change, anaemia correction. Interventions: GnRH antagonists (relugolix
  combination, elagolix + add-back, linzagolix), ulipristal acetate (SPRM),
  tranexamic acid, levonorgestrel intrauterine system.
- Volume (fibroid / uterine size): fibroid (leiomyoma) volume, total uterine
  volume, primary-fibroid diameter.
- Procedural (UAE / myomectomy / MRgFUS / RFA): uterine artery embolisation
  versus myomectomy/hysterectomy; re-intervention / re-operation, symptom-severity
  score (UFS-QoL SSS), procedure complications, length of hospital stay, ovarian
  reserve (AMH).
- Qol (symptom & quality of life): UFS-QoL health-related quality of life, pelvic
  pain / pressure, patient global impression.

Effect measures follow what these trials report: binary (bleeding-control
responder, amenorrhoea, anaemia, re-intervention, hysterectomy, complications) ->
RR/OR/RD; continuous (menstrual blood loss, haemoglobin, fibroid/uterine volume,
symptom-severity and QoL scores, hospital stay) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# UTERINE FIBROIDS ENDPOINTS
# ============================================================

UTERINE_FIBROIDS_ENDPOINTS = {
    # --- Bleeding (heavy menstrual bleeding) ---
    'MENSTRUAL_BLOOD_LOSS': {
        'aliases': ['menstrual blood loss', 'mbl', 'blood loss', 'alkaline haematin',
                    'alkaline hematin', 'pbac score', 'pictorial blood loss',
                    'pictorial blood assessment', 'menstrual blood volume'],
        'subspecialty': 'bleeding',
        'measure_types': ['MD', 'SMD']
    },
    'BLEEDING_CONTROL': {
        'aliases': ['bleeding control', 'menstrual bleeding control',
                    'controlled bleeding', 'responder', 'response rate', 'responders',
                    'reduction in menstrual blood loss', 'treatment response'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'AMENORRHOEA': {
        'aliases': ['amenorrhoea', 'amenorrhea', 'induced amenorrhoea',
                    'induced amenorrhea', 'rate of amenorrhoea'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HAEMOGLOBIN': {
        'aliases': ['haemoglobin', 'hemoglobin', 'haemoglobin concentration',
                    'hemoglobin concentration', 'change in haemoglobin',
                    'haemoglobin level'],
        'subspecialty': 'bleeding',
        'measure_types': ['MD', 'SMD']
    },
    'ANAEMIA': {
        'aliases': ['anaemia', 'anemia', 'iron-deficiency anaemia',
                    'iron deficiency anemia', 'correction of anaemia'],
        'subspecialty': 'bleeding',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Volume (fibroid / uterine size) ---
    'FIBROID_VOLUME': {
        'aliases': ['fibroid volume', 'leiomyoma volume', 'myoma volume',
                    'total fibroid volume', 'primary fibroid volume',
                    'fibroid size', 'leiomyoma size'],
        'subspecialty': 'volume',
        'measure_types': ['MD', 'SMD']
    },
    'UTERINE_VOLUME': {
        'aliases': ['uterine volume', 'total uterine volume', 'uterus volume',
                    'change in uterine volume'],
        'subspecialty': 'volume',
        'measure_types': ['MD', 'SMD']
    },

    # --- Procedural (UAE / myomectomy / MRgFUS / RFA) ---
    'REINTERVENTION': {
        'aliases': ['re-intervention', 'reintervention', 're-operation', 'reoperation',
                    'repeat intervention', 'further intervention', 'repeat procedure',
                    'additional surgery', 'secondary intervention'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HYSTERECTOMY': {
        'aliases': ['hysterectomy', 'subsequent hysterectomy', 'rate of hysterectomy',
                    'conversion to hysterectomy'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SYMPTOM_SEVERITY': {
        'aliases': ['symptom severity score', 'symptom severity', 'ufs-qol',
                    'uterine fibroid symptom', 'sss', 'symptom score'],
        'subspecialty': 'procedural',
        'measure_types': ['MD', 'SMD']
    },
    'PROCEDURE_COMPLICATIONS': {
        'aliases': ['complications', 'procedural complications', 'major complications',
                    'adverse events', 'complication rate', 'periprocedural complications'],
        'subspecialty': 'procedural',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HOSPITAL_STAY': {
        'aliases': ['hospital stay', 'length of stay', 'length of hospital stay',
                    'duration of hospitalisation', 'duration of hospitalization'],
        'subspecialty': 'procedural',
        'measure_types': ['MD', 'SMD']
    },

    # --- Qol (symptom & quality of life) ---
    'QUALITY_OF_LIFE': {
        'aliases': ['quality of life', 'health-related quality of life', 'hrql',
                    'ufs-qol health-related', 'sf-36', 'eq-5d'],
        'subspecialty': 'qol',
        'measure_types': ['MD', 'SMD']
    },
    'PELVIC_PAIN': {
        'aliases': ['pelvic pain', 'pelvic pressure', 'bulk symptoms',
                    'pressure symptoms', 'pain score'],
        'subspecialty': 'qol',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
}


# ============================================================
# BLEEDING PATTERNS
# ============================================================

BLEEDING_PATTERNS = {
    'detection_keywords': [
        r'heavy\s+menstrual\s+bleeding', r'menstrual\s+blood\s+loss',
        r'alkaline\s+h[ae]matin', r'pbac|pictorial\s+blood',
        r'amenorrh(?:oea|ea)', r'bleeding\s+control', r'relugolix|elagolix|linzagolix',
        r'ulipristal', r'tranexamic', r'levonorgestrel', r'menorrhagia',
        r'h[ae]moglobin', r'ana?emia',
    ],
    'endpoint_patterns': [
        (r'menstrual\s+blood\s+loss|\bmbl\b|alkaline\s+h[ae]matin|pbac\s+score|'
         r'pictorial\s+blood(?:\s+(?:loss|assessment))?|menstrual\s+blood\s+volume',
         'MENSTRUAL_BLOOD_LOSS'),
        (r'bleeding\s+control|menstrual\s+bleeding\s+control|controlled\s+bleeding|'
         r'respon(?:se|der)s?(?:\s+rate)?|reduction\s+in\s+menstrual\s+blood\s+loss|'
         r'treatment\s+response', 'BLEEDING_CONTROL'),
        (r'amenorrh(?:oea|ea)', 'AMENORRHOEA'),
        (r'h[ae]moglobin(?:\s+(?:concentration|level))?|change\s+in\s+h[ae]moglobin',
         'HAEMOGLOBIN'),
        (r'(?:iron[- ]deficiency\s+)?ana?emia|correction\s+of\s+ana?emia', 'ANAEMIA'),
    ],
    'context_patterns': [
        r'\bml\b', r'baseline\s+to\s+week\s+\d+', r'change\s+from\s+baseline',
        r'pbac\s*<\s*75',
    ]
}


# ============================================================
# VOLUME PATTERNS
# ============================================================

VOLUME_PATTERNS = {
    'detection_keywords': [
        r'fibroid\s+volume', r'leiomyoma\s+volume', r'myoma\s+volume',
        r'uterine\s+volume', r'fibroid\s+size', r'fibroid\s+diameter',
        r'volume\s+reduction',
    ],
    'endpoint_patterns': [
        (r'(?:fibroid|leiomyoma|myoma|primary\s+fibroid)\s+volume|'
         r'(?:fibroid|leiomyoma)\s+size', 'FIBROID_VOLUME'),
        (r'(?:total\s+)?uterine\s+volume|uterus\s+volume|change\s+in\s+uterine\s+volume',
         'UTERINE_VOLUME'),
    ],
    'context_patterns': [
        r'cm3|cm\^3|cubic\s+cent', r'percentage\s+(?:change|reduction)', r'\bmri\b',
    ]
}


# ============================================================
# PROCEDURAL PATTERNS
# ============================================================

PROCEDURAL_PATTERNS = {
    'detection_keywords': [
        r'uterine\s+artery\s+emboli[sz]ation|\buae\b', r'myomectomy',
        r'hysterectomy', r'focused\s+ultrasound|mrgfus|\bhifu\b',
        r'radiofrequency\s+ablation', r're[- ]?intervention|re[- ]?operation',
        r'symptom\s+severity\s+score|ufs[- ]qol', r'length\s+of\s+(?:hospital\s+)?stay',
        r'ovarian\s+reserve|anti[- ]m(?:u|ü)llerian',
    ],
    'endpoint_patterns': [
        (r're[- ]?intervention|re[- ]?operation|repeat\s+(?:intervention|procedure)|'
         r'further\s+intervention|additional\s+surgery|secondary\s+intervention',
         'REINTERVENTION'),
        (r'hysterectomy|conversion\s+to\s+hysterectomy', 'HYSTERECTOMY'),
        (r'symptom\s+severity(?:\s+score)?|ufs[- ]qol|\bsss\b|uterine\s+fibroid\s+symptom',
         'SYMPTOM_SEVERITY'),
        (r'(?:major\s+|procedural\s+|periprocedural\s+)?complications?(?:\s+rate)?|'
         r'adverse\s+events?', 'PROCEDURE_COMPLICATIONS'),
        (r'length\s+of\s+(?:hospital\s+)?stay|hospital\s+stay|'
         r'duration\s+of\s+hospitali[sz]ation', 'HOSPITAL_STAY'),
    ],
    'context_patterns': [
        r'12[- ]month|24[- ]month|follow[- ]up', r'minimally\s+invasive',
    ]
}


# ============================================================
# QOL PATTERNS
# ============================================================

QOL_PATTERNS = {
    'detection_keywords': [
        r'quality\s+of\s+life', r'ufs[- ]qol', r'hrql', r'health[- ]related\s+quality',
        r'pelvic\s+pain', r'pelvic\s+pressure|bulk\s+symptom', r'\bsf[- ]?36\b|eq[- ]5d',
    ],
    'endpoint_patterns': [
        (r'health[- ]related\s+quality\s+of\s+life|quality\s+of\s+life|\bhrql\b|'
         r'ufs[- ]qol\s+health|\bsf[- ]?36\b|\beq[- ]5d\b', 'QUALITY_OF_LIFE'),
        (r'pelvic\s+pain|pelvic\s+pressure|bulk\s+symptoms?|pressure\s+symptoms?|'
         r'pain\s+score', 'PELVIC_PAIN'),
    ],
    'context_patterns': [
        r'0[- ]to[- ]100\s+scale', r'transformed\s+score', r'change\s+from\s+baseline',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_uterine_fibroids_subspecialty(text: str) -> Tuple[str, float]:
    """Detect uterine-fibroids trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: bleeding, volume, procedural, qol, general_fibroids."""
    text_lower = text.lower()
    scores = {'bleeding': 0, 'volume': 0, 'procedural': 0, 'qol': 0}
    for kw in BLEEDING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['bleeding'] += 1
    for kw in VOLUME_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['volume'] += 1
    for kw in PROCEDURAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['procedural'] += 1
    for kw in QOL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['qol'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_fibroids', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_uterine_fibroids_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'bleeding': BLEEDING_PATTERNS['endpoint_patterns'],
        'volume': VOLUME_PATTERNS['endpoint_patterns'],
        'procedural': PROCEDURAL_PATTERNS['endpoint_patterns'],
        'qol': QOL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_uterine_fibroids_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical uterine-fibroids endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in UTERINE_FIBROIDS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
