"""
Endometriosis Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the cervical-cancer, maternal-neonatal
and other women's-health profiles. Endometriosis is a chronic oestrogen-dependent
disease affecting ~10% of reproductive-age women; its RCTs report a distinct
endpoint vocabulary spanning pain, hormonal/medical suppression, surgery and
fertility that the generic effect-size engine does not recognise on its own.

Subspecialties:
- Pain (symptom outcomes): pelvic pain, dysmenorrhoea, dyspareunia, dyschezia,
  chronic pelvic pain; VAS / NRS pain scores, Biberoglu-Behrman (B&B) score,
  pain responder rate. Interventions: NSAIDs and the hormonal agents below.
- Medical (hormonal suppression): GnRH antagonists (elagolix, relugolix,
  linzagolix), GnRH agonists (leuprolide/leuprorelin, goserelin, triptorelin,
  nafarelin), progestins (dienogest, medroxyprogesterone, norethindrone/
  norethisterone acetate), combined oral contraceptives, danazol, aromatase
  inhibitors (letrozole, anastrozole). Outcomes: amenorrhoea, abnormal uterine
  bleeding, hot flushes (vasomotor AE), bone mineral density loss (AE).
- Surgical: laparoscopic excision vs ablation, cystectomy vs drainage/ablation
  of endometrioma; endometrioma recurrence, symptom/disease recurrence,
  reoperation, rASRM/rAFS stage, adhesion.
- Fertility: clinical pregnancy, live birth, spontaneous/ongoing pregnancy,
  miscarriage in endometriosis-associated infertility.

Effect measures follow what these trials report: binary (recurrence, responder,
amenorrhoea, pregnancy, live birth, hot flushes) -> RR/OR/RD; time-to recurrence
-> HR; continuous (pain VAS, BMD, EHP-30 quality of life, lesion size) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# ENDOMETRIOSIS ENDPOINTS
# ============================================================

ENDOMETRIOSIS_ENDPOINTS = {
    # --- Pain (symptom outcomes) ---
    'PELVIC_PAIN': {
        'aliases': ['pelvic pain', 'chronic pelvic pain', 'overall pelvic pain',
                    'endometriosis-associated pelvic pain', 'non-menstrual pelvic pain',
                    'non-cyclical pelvic pain', 'pelvic pain score'],
        'subspecialty': 'pain',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'DYSMENORRHOEA': {
        'aliases': ['dysmenorrhoea', 'dysmenorrhea', 'menstrual pain',
                    'cyclic pelvic pain', 'cyclical pain', 'painful menstruation',
                    'dysmenorrhoea score'],
        'subspecialty': 'pain',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'DYSPAREUNIA': {
        'aliases': ['dyspareunia', 'painful intercourse', 'deep dyspareunia',
                    'pain during intercourse'],
        'subspecialty': 'pain',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },
    'PAIN_RESPONSE': {
        'aliases': ['pain response', 'pain responder', 'clinically meaningful reduction',
                    'reduction in dysmenorrhoea', 'reduction in dysmenorrhea',
                    'response rate', 'responder rate', 'clinical response',
                    'pain relief'],
        'subspecialty': 'pain',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DYSCHEZIA': {
        'aliases': ['dyschezia', 'painful defecation', 'bowel pain'],
        'subspecialty': 'pain',
        'measure_types': ['MD', 'SMD', 'RR', 'OR']
    },

    # --- Medical (hormonal suppression) ---
    'AMENORRHOEA': {
        'aliases': ['amenorrhoea', 'amenorrhea', 'induced amenorrhoea',
                    'induced amenorrhea', 'rate of amenorrhoea'],
        'subspecialty': 'medical',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ABNORMAL_BLEEDING': {
        'aliases': ['abnormal uterine bleeding', 'uterine bleeding', 'breakthrough bleeding',
                    'irregular bleeding', 'menorrhagia', 'heavy menstrual bleeding',
                    'bleeding profile'],
        'subspecialty': 'medical',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HOT_FLUSHES': {
        'aliases': ['hot flush', 'hot flushes', 'hot flash', 'hot flashes',
                    'vasomotor symptom', 'vasomotor symptoms', 'night sweats'],
        'subspecialty': 'medical',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BMD_LOSS': {
        'aliases': ['bone mineral density', 'bmd', 'bone loss', 'bmd loss',
                    'lumbar spine bmd', 'change in bone mineral density',
                    'bone mineral density loss'],
        'subspecialty': 'medical',
        'measure_types': ['MD', 'SMD']
    },

    # --- Surgical ---
    'DISEASE_RECURRENCE': {
        'aliases': ['recurrence', 'endometrioma recurrence', 'cyst recurrence',
                    'disease recurrence', 'recurrence of endometriosis',
                    'symptom recurrence', 'pain recurrence', 'recurrent endometrioma',
                    'recurrence rate'],
        'subspecialty': 'surgical',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'REOPERATION': {
        'aliases': ['reoperation', 're-operation', 'repeat surgery',
                    'further surgery', 'reintervention', 're-intervention',
                    'repeat laparoscopy'],
        'subspecialty': 'surgical',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'LESION_REDUCTION': {
        'aliases': ['lesion size', 'endometrioma size', 'cyst diameter',
                    'rasrm score', 'rafs score', 'revised american fertility society',
                    'lesion reduction', 'reduction in lesion'],
        'subspecialty': 'surgical',
        'measure_types': ['MD', 'SMD']
    },

    # --- Fertility ---
    'CLINICAL_PREGNANCY': {
        'aliases': ['clinical pregnancy', 'clinical pregnancy rate', 'pregnancy rate',
                    'ongoing pregnancy', 'conception', 'spontaneous pregnancy'],
        'subspecialty': 'fertility',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LIVE_BIRTH': {
        'aliases': ['live birth', 'live birth rate', 'live-birth rate',
                    'cumulative live birth'],
        'subspecialty': 'fertility',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MISCARRIAGE': {
        'aliases': ['miscarriage', 'spontaneous abortion', 'early pregnancy loss',
                    'pregnancy loss', 'miscarriage rate'],
        'subspecialty': 'fertility',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Quality of life (shared) ---
    'QUALITY_OF_LIFE': {
        'aliases': ['quality of life', 'ehp-30', 'ehp-5', 'endometriosis health profile',
                    'sf-36', 'health-related quality of life'],
        'subspecialty': 'pain',
        'measure_types': ['MD', 'SMD']
    },
}


# ============================================================
# PAIN PATTERNS
# ============================================================

PAIN_PATTERNS = {
    'detection_keywords': [
        r'pelvic\s+pain', r'dysmenorrh(?:oea|ea)', r'dyspareunia',
        r'dyschezia', r'chronic\s+pelvic\s+pain', r'pain\s+score',
        r'visual\s+analog(?:ue)?\s+scale|\bvas\b', r'numeric(?:al)?\s+rating\s+scale|\bnrs\b',
        r'biberoglu[- ]behrman|b\s*&\s*b\s+score', r'pain\s+responder',
    ],
    'endpoint_patterns': [
        (r'chronic\s+pelvic\s+pain|non[- ](?:menstrual|cyclical)\s+pelvic\s+pain|'
         r'overall\s+pelvic\s+pain|endometriosis[- ]associated\s+pelvic\s+pain|'
         r'pelvic\s+pain', 'PELVIC_PAIN'),
        (r'dysmenorrh(?:oea|ea)|menstrual\s+pain|cyclic(?:al)?\s+pain|'
         r'painful\s+menstruation', 'DYSMENORRHOEA'),
        (r'dyspareunia|painful\s+intercourse|pain\s+during\s+intercourse', 'DYSPAREUNIA'),
        (r'dyschezia|painful\s+def{1,2}ec?ation|bowel\s+pain', 'DYSCHEZIA'),
        (r'pain\s+respon(?:se|der)|clinical(?:ly\s+meaningful)?\s+respon|'
         r'reduction\s+in\s+dysmenorrh(?:oea|ea)|response\s+rate|responder\s+rate|'
         r'pain\s+relief', 'PAIN_RESPONSE'),
        (r'quality\s+of\s+life|ehp[- ]?30|ehp[- ]?5|endometriosis\s+health\s+profile|'
         r'\bsf[- ]?36\b', 'QUALITY_OF_LIFE'),
    ],
    'context_patterns': [
        r'baseline\s+to\s+(?:week|month)\s+\d+', r'change\s+from\s+baseline',
        r'least[- ]squares\s+mean', r'0[- ]to[- ]10\s+scale|0[- ]10\s+(?:vas|nrs)',
    ]
}


# ============================================================
# MEDICAL (hormonal suppression) PATTERNS
# ============================================================

MEDICAL_PATTERNS = {
    'detection_keywords': [
        r'dienogest', r'elagolix', r'relugolix', r'linzagolix',
        r'gn?rh\s+(?:agonist|antagonist|analog)', r'leuprol(?:ide|in)|leuprorelin',
        r'goserelin', r'triptorelin', r'nafarelin', r'danazol',
        r'progestin|progestogen', r'medroxyprogesterone|norethindrone|norethisterone',
        r'letrozole|anastrozole|aromatase\s+inhibitor', r'add[- ]back\s+therapy',
        r'amenorrh(?:oea|ea)', r'bone\s+mineral\s+density',
    ],
    'endpoint_patterns': [
        (r'amenorrh(?:oea|ea)', 'AMENORRHOEA'),
        (r'abnormal\s+uterine\s+bleeding|uterine\s+bleeding|breakthrough\s+bleeding|'
         r'irregular\s+bleeding|menorrhagia|heavy\s+menstrual\s+bleeding|'
         r'bleeding\s+profile', 'ABNORMAL_BLEEDING'),
        (r'hot\s+flush(?:es)?|hot\s+flash(?:es)?|vasomotor\s+symptom|night\s+sweats',
         'HOT_FLUSHES'),
        (r'bone\s+mineral\s+density|\bbmd\b|bone\s+loss|lumbar\s+spine\s+bmd', 'BMD_LOSS'),
    ],
    'context_patterns': [
        r'add[- ]back', r'estradiol|oestradiol', r'per\s+cent\s+change\s+in\s+bmd',
        r'12[- ]month|24[- ]week|6[- ]month',
    ]
}


# ============================================================
# SURGICAL PATTERNS
# ============================================================

SURGICAL_PATTERNS = {
    'detection_keywords': [
        r'laparoscop(?:y|ic)', r'excision', r'ablation', r'cystectomy',
        r'endometrioma', r'ovarian\s+cyst', r'recurrence', r'reoperation|re[- ]operation',
        r'rasrm|rafs|revised\s+american\s+fertility', r'adhesion',
        r'drainage\s+and\s+(?:coagulation|ablation)',
    ],
    'endpoint_patterns': [
        (r'(?:endometrioma|cyst|disease|symptom|pain)\s+recurrence|'
         r'recurrence\s+of\s+endometri|recurrent\s+endometrioma|recurrence\s+rate|'
         r'\brecurrence\b', 'DISEASE_RECURRENCE'),
        (r're[- ]?operation|repeat\s+surgery|further\s+surgery|re[- ]?intervention|'
         r'repeat\s+laparoscopy', 'REOPERATION'),
        (r'lesion\s+size|endometrioma\s+size|cyst\s+diameter|rasrm\s+score|'
         r'rafs\s+score|reduction\s+in\s+lesion', 'LESION_REDUCTION'),
    ],
    'context_patterns': [
        r'cystectomy\s+versus|excision\s+versus\s+ablation',
        r'\d+[- ]month\s+follow[- ]up', r'ultrasound[- ]confirmed',
    ]
}


# ============================================================
# FERTILITY PATTERNS
# ============================================================

FERTILITY_PATTERNS = {
    'detection_keywords': [
        r'clinical\s+pregnancy', r'live\s+birth', r'pregnancy\s+rate',
        r'fecundity|fecundability', r'conception', r'infertility',
        r'in[- ]vitro\s+fertili[sz]ation|\bivf\b', r'spontaneous\s+pregnancy',
        r'miscarriage|pregnancy\s+loss',
    ],
    'endpoint_patterns': [
        (r'clinical\s+pregnancy|pregnancy\s+rate|ongoing\s+pregnancy|'
         r'spontaneous\s+pregnancy|conception\s+rate', 'CLINICAL_PREGNANCY'),
        (r'live[- ]birth|live\s+birth\s+rate|cumulative\s+live\s+birth', 'LIVE_BIRTH'),
        (r'miscarriage|spontaneous\s+abortion|early\s+pregnancy\s+loss|pregnancy\s+loss',
         'MISCARRIAGE'),
    ],
    'context_patterns': [
        r'per\s+(?:cycle|woman|couple)', r'after\s+surgery', r'within\s+\d+\s+months',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_endometriosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect endometriosis trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: pain, medical, surgical, fertility, general_endometriosis."""
    text_lower = text.lower()
    scores = {'pain': 0, 'medical': 0, 'surgical': 0, 'fertility': 0}
    for kw in PAIN_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pain'] += 1
    for kw in MEDICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['medical'] += 1
    for kw in SURGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['surgical'] += 1
    for kw in FERTILITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['fertility'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_endometriosis', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_endometriosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'pain': PAIN_PATTERNS['endpoint_patterns'],
        'medical': MEDICAL_PATTERNS['endpoint_patterns'],
        'surgical': SURGICAL_PATTERNS['endpoint_patterns'],
        'fertility': FERTILITY_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_endometriosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical endometriosis endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in ENDOMETRIOSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
