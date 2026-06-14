"""
Neonatology (NICU) Subspecialty Patterns and Endpoints

Built on the same meta-analysis workflow. Neonatal-intensive-care RCTs (preterm /
VLBW infants; surfactant, CPAP, caffeine, inhaled nitric oxide, therapeutic
hypothermia, probiotics, PDA pharmacotherapy) report a distinct endpoint
vocabulary - bronchopulmonary dysplasia, necrotising enterocolitis,
intraventricular haemorrhage, retinopathy of prematurity, patent ductus
arteriosus, periventricular leukomalacia, late-onset sepsis - that is NOT covered
by the maternal_neonatal profile (an obstetric/birth-outcome profile: preterm
birth, stillbirth, birth weight, Apgar, pre-eclampsia).

Subspecialties:
- respiratory: bronchopulmonary dysplasia / chronic lung disease, respiratory
  distress syndrome.
- gastrointestinal: necrotising enterocolitis, spontaneous intestinal perforation.
- neurological: intraventricular haemorrhage, periventricular leukomalacia,
  neurodevelopmental impairment / cerebral palsy.
- complications: retinopathy of prematurity, patent ductus arteriosus,
  late-onset sepsis, neonatal mortality.

Drug / intervention classes (arm labels): surfactant (poractant / beractant /
calfactant), CPAP, caffeine, inhaled nitric oxide, indomethacin / ibuprofen /
paracetamol (PDA), probiotics, erythropoietin, hydrocortisone / dexamethasone,
therapeutic hypothermia, placebo.

Effect measures: all neonatal morbidity / mortality endpoints -> RR/OR/HR.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# NEONATOLOGY ENDPOINTS
# ============================================================

NEONATOLOGY_ENDPOINTS = {
    # --- respiratory ---
    'BRONCHOPULMONARY_DYSPLASIA': {
        'aliases': ['bronchopulmonary dysplasia', 'bpd', 'chronic lung disease',
                    'chronic lung disease of prematurity', 'oxygen at 36 weeks',
                    'oxygen dependency at 36 weeks'],
        'subspecialty': 'respiratory',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'RESPIRATORY_DISTRESS_SYNDROME': {
        'aliases': ['respiratory distress syndrome', 'neonatal respiratory distress syndrome',
                    'hyaline membrane disease', 'rds', 'surfactant deficiency'],
        'subspecialty': 'respiratory',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- gastrointestinal ---
    'NECROTISING_ENTEROCOLITIS': {
        'aliases': ['necrotising enterocolitis', 'necrotizing enterocolitis', 'nec',
                    'nec stage ii', 'nec stage 2', 'surgical nec', 'confirmed nec'],
        'subspecialty': 'gastrointestinal',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'INTESTINAL_PERFORATION': {
        'aliases': ['spontaneous intestinal perforation', 'intestinal perforation',
                    'focal intestinal perforation', 'sip'],
        'subspecialty': 'gastrointestinal',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- neurological ---
    'INTRAVENTRICULAR_HAEMORRHAGE': {
        'aliases': ['intraventricular haemorrhage', 'intraventricular hemorrhage',
                    'severe intraventricular haemorrhage', 'severe intraventricular hemorrhage',
                    'germinal matrix haemorrhage', 'germinal matrix hemorrhage',
                    'grade iii-iv ivh', 'grade 3-4 ivh', 'ivh'],
        'subspecialty': 'neurological',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PERIVENTRICULAR_LEUKOMALACIA': {
        'aliases': ['periventricular leukomalacia', 'periventricular leucomalacia', 'pvl',
                    'cystic periventricular leukomalacia'],
        'subspecialty': 'neurological',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NEURODEVELOPMENTAL_IMPAIRMENT': {
        'aliases': ['neurodevelopmental impairment', 'neurodevelopmental disability',
                    'cerebral palsy', 'death or neurodevelopmental impairment',
                    'death or disability', 'major disability'],
        'subspecialty': 'neurological',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- complications ---
    'RETINOPATHY_OF_PREMATURITY': {
        'aliases': ['retinopathy of prematurity', 'rop', 'severe retinopathy of prematurity',
                    'treatment for retinopathy of prematurity', 'stage 3 rop',
                    'threshold rop'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PATENT_DUCTUS_ARTERIOSUS': {
        'aliases': ['patent ductus arteriosus', 'pda', 'haemodynamically significant pda',
                    'hemodynamically significant pda', 'pda requiring treatment',
                    'pda ligation'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'LATE_ONSET_SEPSIS': {
        'aliases': ['late-onset sepsis', 'late onset sepsis', 'culture-proven sepsis',
                    'culture proven sepsis', 'neonatal sepsis', 'nosocomial infection',
                    'blood-culture-positive sepsis'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NEONATAL_MORTALITY': {
        'aliases': ['neonatal mortality', 'neonatal death', 'death before discharge',
                    'mortality before discharge', 'all-cause mortality', 'all cause mortality',
                    'in-hospital mortality', 'death'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# RESPIRATORY PATTERNS
# ============================================================

RESPIRATORY_PATTERNS = {
    'detection_keywords': [
        r'bronchopulmonary\s+dysplasia|\bbpd\b', r'chronic\s+lung\s+disease',
        r'respiratory\s+distress\s+syndrome|\brds\b|hyaline\s+membrane',
        r'oxygen\s+at\s+36\s+weeks|surfactant',
    ],
    'endpoint_patterns': [
        (r'bronchopulmonary\s+dysplasia|\bbpd\b|chronic\s+lung\s+disease(?:\s+of\s+prematurity)?|'
         r'oxygen\s+(?:dependency\s+)?at\s+36\s+weeks', 'BRONCHOPULMONARY_DYSPLASIA'),
        (r'(?:neonatal\s+)?respiratory\s+distress\s+syndrome|\brds\b|hyaline\s+membrane\s+disease|'
         r'surfactant\s+deficiency', 'RESPIRATORY_DISTRESS_SYNDROME'),
    ],
    'context_patterns': [
        r'postmenstrual\s+age', r'mechanical\s+ventilation', r'preterm',
    ]
}


# ============================================================
# GASTROINTESTINAL PATTERNS
# ============================================================

GASTROINTESTINAL_PATTERNS = {
    'detection_keywords': [
        r'necroti[sz]ing\s+enterocolitis|\bnec\b',
        r'(?:spontaneous|focal)\s+intestinal\s+perforation|\bsip\b',
        r'feeding\s+intolerance', r'enteral\s+(?:feed|nutrition)',
    ],
    'endpoint_patterns': [
        (r'(?:spontaneous|focal)\s+intestinal\s+perforation|\bsip\b', 'INTESTINAL_PERFORATION'),
        (r'necroti[sz]ing\s+enterocolitis|\bnec\b(?:\s+stage\s+(?:ii?|[23]))?', 'NECROTISING_ENTEROCOLITIS'),
    ],
    'context_patterns': [
        r'bell\s+stage', r'\d+\s*ml/kg', r'breast\s+milk|formula',
    ]
}


# ============================================================
# NEUROLOGICAL PATTERNS
# ============================================================

NEUROLOGICAL_PATTERNS = {
    'detection_keywords': [
        r'intraventricular\s+h[ae]morrhage|\bivh\b|germinal\s+matrix\s+h[ae]morrhage',
        r'periventricular\s+leu[ck]omalacia|\bpvl\b',
        r'neurodevelopmental\s+(?:impairment|disability)|cerebral\s+palsy',
        r'hypoxic[- ]isch[ae]mic\s+encephalopathy|\bhie\b|therapeutic\s+hypothermia',
    ],
    'endpoint_patterns': [
        (r'periventricular\s+leu[ck]omalacia|\bpvl\b', 'PERIVENTRICULAR_LEUKOMALACIA'),
        (r'(?:severe\s+|grade\s+(?:iii?[- ]iv|[34]))?intraventricular\s+h[ae]morrhage|\bivh\b|'
         r'germinal\s+matrix\s+h[ae]morrhage', 'INTRAVENTRICULAR_HAEMORRHAGE'),
        (r'(?:death\s+or\s+)?neurodevelopmental\s+(?:impairment|disability)|cerebral\s+palsy|'
         r'death\s+or\s+disability|major\s+disability', 'NEURODEVELOPMENTAL_IMPAIRMENT'),
    ],
    'context_patterns': [
        r'cranial\s+ultrasound', r'bayley', r'corrected\s+age',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'retinopathy\s+of\s+prematurity|\brop\b',
        r'patent\s+ductus\s+arteriosus|\bpda\b',
        r'late[- ]onset\s+sepsis|culture[- ]proven\s+sepsis|neonatal\s+sepsis',
        r'neonatal\s+(?:mortality|death)|death\s+before\s+discharge',
    ],
    'endpoint_patterns': [
        (r'retinopathy\s+of\s+prematurity|\brop\b(?:\s+stage\s+\d)?|threshold\s+rop',
         'RETINOPATHY_OF_PREMATURITY'),
        (r'patent\s+ductus\s+arteriosus|\bpda\b|h[ae]modynamically\s+significant\s+pda',
         'PATENT_DUCTUS_ARTERIOSUS'),
        (r'late[- ]onset\s+sepsis|culture[- ]proven\s+sepsis|(?:neonatal\s+)?nosocomial\s+infection|'
         r'blood[- ]culture[- ]positive\s+sepsis|neonatal\s+sepsis', 'LATE_ONSET_SEPSIS'),
        (r'neonatal\s+(?:mortality|death)|death\s+before\s+discharge|'
         r'mortality\s+before\s+discharge|in[- ]hospital\s+mortality|all[- ]cause\s+(?:mortality|death)',
         'NEONATAL_MORTALITY'),
    ],
    'context_patterns': [
        r'corrected\s+gestational\s+age', r'\d+\s*weeks', r'\d+[- ]day\s+mortality',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_neonatology_subspecialty(text: str) -> Tuple[str, float]:
    """Detect neonatology trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: respiratory, gastrointestinal, neurological, complications,
    general_neonatal."""
    text_lower = text.lower()
    scores = {'respiratory': 0, 'gastrointestinal': 0, 'neurological': 0, 'complications': 0}
    for kw in RESPIRATORY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['respiratory'] += 1
    for kw in GASTROINTESTINAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['gastrointestinal'] += 1
    for kw in NEUROLOGICAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neurological'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_neonatal', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_neonatology_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'respiratory': RESPIRATORY_PATTERNS['endpoint_patterns'],
        'gastrointestinal': GASTROINTESTINAL_PATTERNS['endpoint_patterns'],
        'neurological': NEUROLOGICAL_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_neonatology_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical neonatology endpoint, preferring the LONGEST
    matching alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in NEONATOLOGY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
