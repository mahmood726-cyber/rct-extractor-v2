"""
Infertility / IVF / Assisted-Reproduction Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the cervical-cancer, endometriosis
and menopause women's-health profiles. Assisted-reproduction RCTs are abundant
and report a distinct endpoint vocabulary spanning ovarian stimulation, the
embryology lab, embryo transfer and pregnancy outcomes that the generic
effect-size engine does not recognise on its own.

This profile folds in the "ovarian stimulation / IVF outcomes" area as the
`stimulation` subspecialty (oocyte yield, OHSS, cancellation) rather than a
separate top-level specialty.

Subspecialties:
- Stimulation (controlled ovarian stimulation / IVF outcomes): number of oocytes
  retrieved, mature (MII) oocytes, ovarian hyperstimulation syndrome (OHSS),
  cycle cancellation, oestradiol on trigger day, total gonadotrophin dose,
  endometrial thickness. Protocols: GnRH antagonist vs long agonist, rFSH /
  follitropin, HMG/HP-hMG, corifollitropin, letrozole/clomiphene co-treatment,
  hCG vs GnRH-agonist trigger, progestin-primed (PPOS).
- Lab (embryology): fertilisation rate, blastocyst formation/utilisation,
  good-quality embryos, ICSI vs conventional IVF.
- Transfer (embryo transfer & pregnancy): clinical pregnancy, live birth,
  ongoing pregnancy, implantation rate, miscarriage, multiple pregnancy,
  biochemical pregnancy, cumulative live birth. Fresh vs frozen (FET), single vs
  double embryo transfer, blastocyst vs cleavage-stage.
- Ovulation (ovulation induction & IUI): ovulation rate, clinical pregnancy with
  clomiphene / letrozole / gonadotrophins, intrauterine insemination outcomes.

Effect measures follow what these trials report: binary (clinical pregnancy,
live birth, ongoing pregnancy, miscarriage, OHSS, multiple pregnancy, ovulation,
cancellation) -> RR/OR/RD; continuous (oocytes retrieved, MII oocytes, oestradiol,
gonadotrophin dose, endometrial thickness, fertilisation/implantation rate as a
proportion) -> MD/SMD or RR/OR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# INFERTILITY / IVF ENDPOINTS
# ============================================================

INFERTILITY_IVF_ENDPOINTS = {
    # --- Stimulation (controlled ovarian stimulation / IVF outcomes) ---
    'OOCYTES_RETRIEVED': {
        'aliases': ['oocytes retrieved', 'number of oocytes', 'oocyte yield',
                    'retrieved oocytes', 'cumulus-oocyte complexes', 'oocytes collected',
                    'mean number of oocytes', 'total oocytes'],
        'subspecialty': 'stimulation',
        'measure_types': ['MD', 'SMD']
    },
    'MATURE_OOCYTES': {
        'aliases': ['mature oocytes', 'mii oocytes', 'metaphase ii oocytes',
                    'number of mature oocytes', 'mature metaphase ii'],
        'subspecialty': 'stimulation',
        'measure_types': ['MD', 'SMD']
    },
    'OHSS': {
        'aliases': ['ovarian hyperstimulation syndrome', 'ohss',
                    'moderate to severe ohss', 'severe ohss', 'moderate ohss',
                    'ohss incidence', 'early ohss', 'late ohss'],
        'subspecialty': 'stimulation',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CYCLE_CANCELLATION': {
        'aliases': ['cycle cancellation', 'cancellation rate', 'cancelled cycle',
                    'cancelled cycles', 'cancellation of the cycle',
                    'poor response cancellation'],
        'subspecialty': 'stimulation',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ESTRADIOL_TRIGGER': {
        'aliases': ['oestradiol on trigger', 'estradiol on trigger',
                    'peak oestradiol', 'peak estradiol', 'serum oestradiol',
                    'serum estradiol', 'e2 on the day of', 'oestradiol level'],
        'subspecialty': 'stimulation',
        'measure_types': ['MD', 'SMD']
    },
    'GONADOTROPHIN_DOSE': {
        'aliases': ['gonadotrophin dose', 'gonadotropin dose', 'total gonadotrophin',
                    'total gonadotropin', 'total fsh dose', 'duration of stimulation',
                    'days of stimulation', 'total dose of'],
        'subspecialty': 'stimulation',
        'measure_types': ['MD', 'SMD']
    },
    'ENDOMETRIAL_THICKNESS': {
        'aliases': ['endometrial thickness', 'endometrial lining',
                    'endometrium thickness', 'triple-line endometrium'],
        'subspecialty': 'stimulation',
        'measure_types': ['MD', 'SMD']
    },

    # --- Lab (embryology) ---
    'FERTILIZATION_RATE': {
        'aliases': ['fertilization rate', 'fertilisation rate', 'normal fertilization',
                    'normal fertilisation', '2pn rate', 'two-pronuclear',
                    'fertilization', 'fertilisation'],
        'subspecialty': 'lab',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'BLASTOCYST_RATE': {
        'aliases': ['blastocyst formation', 'blastocyst rate', 'blastocyst formation rate',
                    'blastulation rate', 'good-quality blastocyst', 'usable blastocyst',
                    'blastocyst utilization', 'blastocyst utilisation'],
        'subspecialty': 'lab',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'GOOD_QUALITY_EMBRYO': {
        'aliases': ['good-quality embryo', 'good quality embryo', 'top-quality embryo',
                    'high-quality embryo', 'number of good-quality embryos',
                    'good-quality embryos'],
        'subspecialty': 'lab',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- Transfer (embryo transfer & pregnancy) ---
    'CLINICAL_PREGNANCY': {
        'aliases': ['clinical pregnancy', 'clinical pregnancy rate',
                    'clinical pregnancy per', 'pregnancy rate', 'clinical pregnancies'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LIVE_BIRTH': {
        'aliases': ['live birth', 'live birth rate', 'live-birth rate',
                    'live birth per', 'cumulative live birth', 'cumulative live-birth rate',
                    'live births'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ONGOING_PREGNANCY': {
        'aliases': ['ongoing pregnancy', 'ongoing pregnancy rate',
                    'ongoing pregnancies', 'continuing pregnancy'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IMPLANTATION_RATE': {
        'aliases': ['implantation rate', 'implantation', 'embryo implantation',
                    'implantation per embryo'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'MISCARRIAGE': {
        'aliases': ['miscarriage', 'miscarriage rate', 'spontaneous abortion',
                    'early pregnancy loss', 'pregnancy loss', 'spontaneous miscarriage'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MULTIPLE_PREGNANCY': {
        'aliases': ['multiple pregnancy', 'multiple pregnancy rate', 'twin pregnancy',
                    'multiple gestation', 'multiple birth', 'twin birth rate'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BIOCHEMICAL_PREGNANCY': {
        'aliases': ['biochemical pregnancy', 'positive pregnancy test',
                    'positive hcg', 'biochemical pregnancy rate'],
        'subspecialty': 'transfer',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Ovulation (ovulation induction & IUI) ---
    'OVULATION': {
        'aliases': ['ovulation rate', 'ovulation', 'ovulatory response',
                    'mono-ovulation', 'ovulation per cycle'],
        'subspecialty': 'ovulation',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# STIMULATION PATTERNS
# ============================================================

STIMULATION_PATTERNS = {
    'detection_keywords': [
        r'controlled\s+ovarian\s+(?:stimulation|hyperstimulation)',
        r'ovarian\s+stimulation', r'gn?rh\s+antagonist|gn?rh\s+agonist',
        r'follitropin|rec(?:ombinant\s+)?fsh|\brfsh\b', r'\bhmg\b|menotrophin|menotropin',
        r'corifollitropin', r'oocytes?\s+retrieved', r'ovarian\s+hyperstimulation\s+syndrome',
        r'\bohss\b', r'gonadotro?ph?in', r'progestin[- ]primed|\bppos\b',
        r'cycle\s+cancellation', r'trigger', r'antral\s+follicle',
    ],
    'endpoint_patterns': [
        (r'oocytes?\s+retrieved|number\s+of\s+oocytes|oocyte\s+yield|oocytes?\s+collected|'
         r'cumulus[- ]oocyte', 'OOCYTES_RETRIEVED'),
        (r'mature\s+oocytes|mii\s+oocytes|metaphase\s+ii\s+oocytes', 'MATURE_OOCYTES'),
        (r'ovarian\s+hyperstimulation\s+syndrome|\bohss\b', 'OHSS'),
        (r'cycle\s+cancellation|cancellation\s+rate|cancelled\s+cycles?', 'CYCLE_CANCELLATION'),
        (r'(?:peak|serum)\s+o?estradiol|o?estradiol\s+on\s+(?:the\s+)?(?:trigger|day)|'
         r'e2\s+on\s+the\s+day', 'ESTRADIOL_TRIGGER'),
        (r'(?:total\s+)?gonadotro?ph?in\s+dose|total\s+fsh\s+dose|duration\s+of\s+stimulation|'
         r'days\s+of\s+stimulation', 'GONADOTROPHIN_DOSE'),
        (r'endometrial\s+thickness|endometrial\s+lining|endometrium\s+thickness',
         'ENDOMETRIAL_THICKNESS'),
    ],
    'context_patterns': [
        r'day\s+of\s+(?:hcg|trigger|ovulation)', r'per\s+(?:cycle|stimulation)',
        r'antagonist\s+protocol|long\s+agonist\s+protocol',
    ]
}


# ============================================================
# LAB (embryology) PATTERNS
# ============================================================

LAB_PATTERNS = {
    'detection_keywords': [
        r'fertili[sz]ation\s+rate', r'2pn|two[- ]pronuclear',
        r'blastocyst\s+(?:formation|rate|utili[sz]ation)', r'blastulation',
        r'good[- ]quality\s+embryo|top[- ]quality\s+embryo', r'intracytoplasmic\s+sperm\s+injection',
        r'\bicsi\b', r'conventional\s+ivf', r'embryo\s+grade',
    ],
    'endpoint_patterns': [
        (r'fertili[sz]ation\s+rate|normal\s+fertili[sz]ation|2pn\s+rate|'
         r'two[- ]pronuclear', 'FERTILIZATION_RATE'),
        (r'blastocyst\s+(?:formation|rate|utili[sz]ation)|blastulation\s+rate|'
         r'usable\s+blastocyst|good[- ]quality\s+blastocyst', 'BLASTOCYST_RATE'),
        (r'good[- ]quality\s+embryos?|top[- ]quality\s+embryos?|high[- ]quality\s+embryos?',
         'GOOD_QUALITY_EMBRYO'),
    ],
    'context_patterns': [
        r'per\s+(?:oocyte|2pn|injected)', r'day\s+(?:3|5)\s+embryo',
    ]
}


# ============================================================
# TRANSFER (embryo transfer & pregnancy) PATTERNS
# ============================================================

TRANSFER_PATTERNS = {
    'detection_keywords': [
        r'embryo\s+transfer', r'clinical\s+pregnancy', r'live\s+birth',
        r'ongoing\s+pregnancy', r'implantation\s+rate', r'frozen[- ]thawed|frozen\s+embryo|\bfet\b',
        r'fresh\s+(?:embryo\s+)?transfer', r'single\s+embryo\s+transfer|\bset\b|elective\s+single',
        r'blastocyst[- ]stage|cleavage[- ]stage', r'miscarriage', r'multiple\s+pregnancy',
        r'cumulative\s+live\s+birth',
    ],
    'endpoint_patterns': [
        (r'clinical\s+pregnancy(?:\s+rate)?|clinical\s+pregnancies', 'CLINICAL_PREGNANCY'),
        (r'live[- ]birth|cumulative\s+live[- ]birth|live\s+births?', 'LIVE_BIRTH'),
        (r'ongoing\s+pregnanc(?:y|ies)|continuing\s+pregnancy', 'ONGOING_PREGNANCY'),
        (r'implantation\s+rate|embryo\s+implantation', 'IMPLANTATION_RATE'),
        (r'miscarriage|spontaneous\s+abortion|early\s+pregnancy\s+loss|pregnancy\s+loss',
         'MISCARRIAGE'),
        (r'multiple\s+pregnancy|twin\s+pregnancy|multiple\s+gestation|multiple\s+birth',
         'MULTIPLE_PREGNANCY'),
        (r'biochemical\s+pregnancy|positive\s+(?:pregnancy\s+test|hcg)', 'BIOCHEMICAL_PREGNANCY'),
    ],
    'context_patterns': [
        r'per\s+(?:transfer|cycle|woman|embryo)', r'fresh\s+versus\s+frozen',
        r'cumulative', r'after\s+(?:the\s+)?first\s+transfer',
    ]
}


# ============================================================
# OVULATION (induction & IUI) PATTERNS
# ============================================================

OVULATION_PATTERNS = {
    'detection_keywords': [
        r'ovulation\s+induction', r'ovulation\s+rate', r'clomiphene|clomifene',
        r'letrozole', r'intrauterine\s+insemination|\biui\b', r'anovulat',
        r'unexplained\s+infertility', r'timed\s+intercourse',
    ],
    'endpoint_patterns': [
        (r'ovulation\s+rate|ovulatory\s+response|ovulation\s+per\s+cycle|\bovulation\b',
         'OVULATION'),
        (r'clinical\s+pregnancy(?:\s+rate)?', 'CLINICAL_PREGNANCY'),
        (r'live[- ]birth', 'LIVE_BIRTH'),
        (r'multiple\s+pregnancy', 'MULTIPLE_PREGNANCY'),
    ],
    'context_patterns': [
        r'per\s+(?:cycle|ovulation|couple)', r'cumulative\s+over\s+\d+\s+cycles',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_infertility_ivf_subspecialty(text: str) -> Tuple[str, float]:
    """Detect infertility/IVF trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: stimulation, lab, transfer, ovulation, general_infertility."""
    text_lower = text.lower()
    scores = {'stimulation': 0, 'lab': 0, 'transfer': 0, 'ovulation': 0}
    for kw in STIMULATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['stimulation'] += 1
    for kw in LAB_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['lab'] += 1
    for kw in TRANSFER_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['transfer'] += 1
    for kw in OVULATION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ovulation'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_infertility', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_infertility_ivf_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'stimulation': STIMULATION_PATTERNS['endpoint_patterns'],
        'lab': LAB_PATTERNS['endpoint_patterns'],
        'transfer': TRANSFER_PATTERNS['endpoint_patterns'],
        'ovulation': OVULATION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_infertility_ivf_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical infertility/IVF endpoint, preferring the LONGEST
    matching alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in INFERTILITY_IVF_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
