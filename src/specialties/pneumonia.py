"""
Childhood Pneumonia / Acute Respiratory Infection Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Childhood pneumonia (and acute lower respiratory infection) is
the single largest infectious cause of death in children under five worldwide and
disproportionately African (the WHO African Region carries the highest under-5
pneumonia mortality), so it is a core Africa-priority topic. Pneumonia RCTs report
a distinct endpoint vocabulary the generic effect-size engine does not recognise
on its own.

Subspecialties:
- Treatment (antibiotic therapy): clinical cure / treatment success, treatment
  failure, time to resolution of symptoms (fever, tachypnoea, chest indrawing),
  oxygen saturation recovery, relapse. Drugs: amoxicillin (incl. oral, high-dose,
  3-day vs 5-day), amoxicillin-clavulanate / co-amoxiclav, co-trimoxazole,
  penicillin / ampicillin, benzylpenicillin, ceftriaxone, cefuroxime,
  azithromycin, chloramphenicol, gentamicin.
- Vaccine (prevention, e.g. PCV): radiologically/clinically-confirmed pneumonia
  incidence, vaccine efficacy / effectiveness, invasive pneumococcal disease
  (IPD), vaccine-type nasopharyngeal carriage, serotype-specific immunogenicity
  (anti-pneumococcal IgG GMC / OPA). Vaccines: pneumococcal conjugate vaccine
  (PCV7, PCV10, PCV13, PCV15, PCV20), PPSV23, Hib conjugate vaccine.
- Mortality (severe outcomes): all-cause mortality, pneumonia-specific mortality,
  case fatality.
- Severe (severe disease / hospitalisation): severe / very severe pneumonia,
  hospitalisation / hospital admission, length of hospital stay, ICU / PICU
  admission, mechanical ventilation / respiratory support, empyema / pleural
  effusion / lung abscess.

Effect measures follow what these trials report: binary (cure, failure, relapse,
IPD, carriage, hospitalisation, ICU, ventilation, empyema, death) -> RR/OR/RD;
incidence -> IRR/HR; continuous (time to symptom resolution, oxygen saturation,
hospital stay -> MD/SMD; anti-pneumococcal IgG GMC -> GMR, log-normal).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# PNEUMONIA ENDPOINTS
# ============================================================

PNEUMONIA_ENDPOINTS = {
    # --- Antibiotic treatment efficacy ---
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical success', 'clinical response',
                    'clinical resolution', 'clinical recovery', 'treatment success',
                    'cure rate', 'overall cure', 'favourable clinical outcome',
                    'favorable clinical outcome', 'clinical improvement'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'clinical failure', 'therapeutic failure',
                    'overall treatment failure', 'composite treatment failure',
                    'failure of treatment', 'clinical deterioration',
                    'change of antibiotic'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'TIME_TO_RESOLUTION': {
        'aliases': ['time to resolution', 'time to resolution of symptoms',
                    'time to clinical improvement', 'time to recovery',
                    'time to resolution of fever', 'time to defervescence',
                    'fever clearance time', 'time to resolution of tachypnoea',
                    'time to resolution of tachypnea',
                    'time to cessation of chest indrawing',
                    'duration of fever', 'duration of fast breathing',
                    'duration of illness'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'OXYGEN_SATURATION': {
        'aliases': ['oxygen saturation', 'spo2', 'sao2', 'arterial oxygen saturation',
                    'mean oxygen saturation', 'peripheral oxygen saturation'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse rate', 'clinical relapse', 'recurrence',
                    'recurrent pneumonia', 'reinfection'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Vaccine (prevention) ---
    'PNEUMONIA_INCIDENCE': {
        'aliases': ['radiologically-confirmed pneumonia',
                    'radiologically confirmed pneumonia',
                    'radiographically-confirmed pneumonia',
                    'radiographically confirmed pneumonia',
                    'who-defined pneumonia', 'who defined pneumonia',
                    'clinical pneumonia', 'clinically-defined pneumonia',
                    'first episode of pneumonia', 'pneumonia incidence',
                    'incidence of pneumonia', 'incident pneumonia',
                    'community-acquired pneumonia', 'consolidated pneumonia',
                    'alveolar consolidation'],
        'subspecialty': 'vaccine',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy', 'vaccine effectiveness',
                    'efficacy against pneumonia', 'protection against pneumonia',
                    'efficacy against invasive pneumococcal disease'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'INVASIVE_PNEUMOCOCCAL_DISEASE': {
        'aliases': ['invasive pneumococcal disease', 'vaccine-type ipd',
                    'vaccine type ipd', 'bacteraemic pneumonia',
                    'bacteremic pneumonia', 'pneumococcal bacteraemia',
                    'pneumococcal bacteremia', 'invasive disease'],
        'subspecialty': 'vaccine',
        'measure_types': ['IRR', 'RR', 'HR']
    },
    'NASOPHARYNGEAL_CARRIAGE': {
        'aliases': ['nasopharyngeal carriage', 'vaccine-type carriage',
                    'vaccine type carriage', 'pneumococcal carriage',
                    'nasopharyngeal colonisation', 'nasopharyngeal colonization',
                    'pneumococcal colonisation', 'carriage prevalence'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IMMUNOGENICITY': {
        'aliases': ['anti-pneumococcal igg', 'antipneumococcal igg',
                    'serotype-specific igg', 'serotype specific igg',
                    'pneumococcal igg', 'geometric mean concentration',
                    'geometric mean titre', 'geometric mean titer', 'gmc', 'gmt',
                    'opsonophagocytic activity', 'opa titre', 'opa titer',
                    'immunogenicity', 'igg geometric mean'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Mortality (severe outcomes) ---
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'mortality',
                    'death', 'overall mortality', 'in-hospital mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'PNEUMONIA_MORTALITY': {
        'aliases': ['pneumonia-specific mortality', 'pneumonia specific mortality',
                    'pneumonia mortality', 'pneumonia-related death',
                    'pneumonia related death', 'pneumonia-related mortality',
                    'mortality from pneumonia', 'lrti mortality'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CASE_FATALITY': {
        'aliases': ['case fatality', 'case fatality rate', 'case-fatality rate',
                    'case-fatality ratio', 'fatality rate'],
        'subspecialty': 'mortality',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Severe disease / hospitalisation ---
    'SEVERE_PNEUMONIA': {
        'aliases': ['severe pneumonia', 'very severe pneumonia',
                    'severe disease', 'progression to severe pneumonia',
                    'severe community-acquired pneumonia', 'severe lrti',
                    'severe acute respiratory infection'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITALISATION': {
        'aliases': ['hospitalisation', 'hospitalization', 'hospital admission',
                    'admission to hospital', 'pneumonia hospitalisation',
                    'pneumonia hospitalization', 'hospital admission for pneumonia',
                    'rate of hospitalisation', 'rate of hospitalization'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'HOSPITAL_STAY': {
        'aliases': ['length of hospital stay', 'duration of hospitalisation',
                    'duration of hospitalization', 'length of stay', 'hospital stay',
                    'hospitalisation duration', 'time to discharge'],
        'subspecialty': 'severe',
        'measure_types': ['MD', 'SMD']
    },
    'ICU_ADMISSION': {
        'aliases': ['intensive care admission', 'intensive care unit admission',
                    'icu admission', 'picu admission', 'admission to intensive care',
                    'need for intensive care'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MECHANICAL_VENTILATION': {
        'aliases': ['mechanical ventilation', 'invasive ventilation',
                    'need for mechanical ventilation', 'respiratory support',
                    'assisted ventilation', 'need for ventilation'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'EMPYEMA': {
        'aliases': ['empyema', 'parapneumonic effusion', 'pleural effusion',
                    'lung abscess', 'pleural empyema', 'necrotising pneumonia',
                    'necrotizing pneumonia'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# TREATMENT PATTERNS (antibiotic therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'amoxicillin', r'amoxicillin[- ]clavulanate|co[- ]?amoxiclav',
        r'co[- ]?trimoxazole|trimethoprim', r'benzylpenicillin|penicillin',
        r'ampicillin', r'ceftriaxone', r'cefuroxime', r'cefotaxime',
        r'azithromycin', r'chloramphenicol', r'gentamicin',
        r'clinical\s+(?:cure|success|response)', r'treatment\s+failure',
        r'time\s+to\s+(?:resolution|recovery|clinical\s+improvement)',
        r'oxygen\s+saturation|\bspo2\b', r'fast\s+breathing|tachypn',
        r'chest\s+indrawing', r'(?:3|three)[- ]day|(?:5|five)[- ]day',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:cure|success|response|resolution|recovery|improvement)|'
         r'treatment\s+success|cure\s+rate', 'CLINICAL_CURE'),
        (r'(?:treatment|clinical|therapeutic)\s+failure|failure\s+of\s+treatment|'
         r'clinical\s+deterioration|change\s+of\s+antibiotic', 'TREATMENT_FAILURE'),
        (r'time\s+to\s+(?:resolution|recovery|clinical\s+improvement|defervescence)|'
         r'fever\s+clearance\s+time|'
         r'duration\s+of\s+(?:fever|fast\s+breathing|illness|tachypn(?:oea|ea))|'
         r'time\s+to\s+cessation\s+of\s+chest\s+indrawing', 'TIME_TO_RESOLUTION'),
        (r'oxygen\s+saturation|\bsp[ao]2\b|arterial\s+oxygen\s+saturation', 'OXYGEN_SATURATION'),
        (r'relapse|recurrence|recurrent\s+pneumonia|reinfection', 'RELAPSE'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'who\s+(?:integrated\s+)?guideline',
        r'\bunder[- ]?five|children\s+aged', r'day\s+(?:3|5|14)\s+(?:cure|outcome|failure)',
    ]
}


# ============================================================
# VACCINE PATTERNS (prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'pneumococcal\s+conjugate\s+vaccine|\bpcv\s*\d*\b',
        r'\bppsv\s*\d*\b|polysaccharide\s+vaccine',
        r'\bhib\b|haemophilus\s+influenzae\s+type\s+b',
        r'vaccine\s+(?:efficacy|effectiveness)|protective\s+efficacy',
        r'invasive\s+pneumococcal\s+disease|\bipd\b',
        r'nasopharyngeal\s+(?:carriage|colon[is]ation)',
        r'serotype', r'immunogenicity', r'geometric\s+mean\s+(?:concentration|tit)',
        r'opsonophagocytic', r'radiolog(?:ically|ic)[- ]confirmed',
    ],
    'endpoint_patterns': [
        (r'radiolog(?:ically|raphically)[- ]confirmed\s+pneumonia|'
         r'who[- ]defined\s+pneumonia|clinical(?:ly[- ]defined)?\s+pneumonia|'
         r'pneumonia\s+incidence|incidence\s+of\s+pneumonia|incident\s+pneumonia|'
         r'first\s+episode\s+of\s+pneumonia|alveolar\s+consolidation', 'PNEUMONIA_INCIDENCE'),
        (r'vaccine\s+(?:efficacy|effectiveness)|protective\s+efficacy|'
         r'efficacy\s+against\s+(?:pneumonia|invasive\s+pneumococcal)', 'VACCINE_EFFICACY'),
        (r'invasive\s+pneumococcal\s+disease|vaccine[- ]type\s+ipd|\bipd\b|'
         r'bacterae?mic\s+pneumonia|pneumococcal\s+bacterae?mia', 'INVASIVE_PNEUMOCOCCAL_DISEASE'),
        (r'nasopharyngeal\s+(?:carriage|colon[is]ation)|vaccine[- ]type\s+carriage|'
         r'pneumococcal\s+(?:carriage|colon[is]ation)|carriage\s+prevalence',
         'NASOPHARYNGEAL_CARRIAGE'),
        (r'anti[- ]?pneumococcal\s+igg|serotype[- ]specific\s+igg|pneumococcal\s+igg|'
         r'geometric\s+mean\s+(?:concentration|tit)|\bgmc\b|\bgmt\b|'
         r'opsonophagocytic|opa\s+tit(?:re|er)|immunogenicity', 'IMMUNOGENICITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?(?:person|child)[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'\bmcg/ml\b|\bug/ml\b|µg/ml', r'serotype\s+\d',
    ]
}


# ============================================================
# MORTALITY PATTERNS (severe outcomes)
# ============================================================

MORTALITY_PATTERNS = {
    'detection_keywords': [
        r'(?:all[- ]cause\s+)?mortality', r'\bdeath(?:s)?\b', r'\bdied\b',
        r'case[- ]fatality', r'pneumonia[- ](?:specific|related)\s+(?:mortality|death)',
        r'survival', r'fatal',
    ],
    'endpoint_patterns': [
        (r'pneumonia[- ](?:specific|related)\s+(?:mortality|death)|'
         r'pneumonia\s+mortality|mortality\s+from\s+pneumonia|lrti\s+mortality',
         'PNEUMONIA_MORTALITY'),
        (r'case[- ]fatality(?:\s+(?:rate|ratio))?|fatality\s+rate', 'CASE_FATALITY'),
        (r'(?:all[- ]cause\s+|overall\s+|in[- ]hospital\s+)?mortality|\bdeath\b|\bdied\b',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'\bunder[- ]?five', r'child(?:hood)?\s+(?:mortality|death)', r'follow[- ]up',
    ]
}


# ============================================================
# SEVERE PATTERNS (severe disease / hospitalisation)
# ============================================================

SEVERE_PATTERNS = {
    'detection_keywords': [
        r'severe\s+pneumonia|very\s+severe\s+pneumonia',
        r'hospitali[sz]ation|hospital\s+admission|admission\s+to\s+hospital',
        r'intensive\s+care|\bicu\b|\bpicu\b',
        r'mechanical\s+ventilation|invasive\s+ventilation|respiratory\s+support',
        r'empyema|parapneumonic\s+effusion|pleural\s+effusion|lung\s+abscess',
        r'necroti[sz]ing\s+pneumonia', r'respiratory\s+failure',
    ],
    'endpoint_patterns': [
        (r'(?:very\s+)?severe\s+(?:pneumonia|community[- ]acquired\s+pneumonia|'
         r'lrti|acute\s+respiratory\s+infection|disease)|'
         r'progression\s+to\s+severe\s+pneumonia', 'SEVERE_PNEUMONIA'),
        (r'hospitali[sz]ation|hospital\s+admission|admission\s+to\s+hospital',
         'HOSPITALISATION'),
        (r'length\s+of\s+(?:hospital\s+)?stay|duration\s+of\s+hospitali[sz]ation|'
         r'time\s+to\s+discharge', 'HOSPITAL_STAY'),
        (r'intensive\s+care\s+(?:unit\s+)?admission|\b(?:p)?icu\s+admission|'
         r'admission\s+to\s+intensive\s+care|need\s+for\s+intensive\s+care', 'ICU_ADMISSION'),
        (r'mechanical\s+ventilation|invasive\s+ventilation|assisted\s+ventilation|'
         r'respiratory\s+support|need\s+for\s+ventilation', 'MECHANICAL_VENTILATION'),
        (r'empyema|parapneumonic\s+effusion|pleural\s+effusion|lung\s+abscess|'
         r'necroti[sz]ing\s+pneumonia', 'EMPYEMA'),
    ],
    'context_patterns': [
        r'who\s+(?:severity\s+)?classification', r'danger\s+signs', r'oxygen\s+(?:therapy|requirement)',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_pneumonia_subspecialty(text: str) -> Tuple[str, float]:
    """Detect pneumonia trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, vaccine, mortality, severe, general_pneumonia."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'vaccine': 0, 'mortality': 0, 'severe': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1
    for kw in MORTALITY_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['mortality'] += 1
    for kw in SEVERE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['severe'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_pneumonia', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_pneumonia_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
        'mortality': MORTALITY_PATTERNS['endpoint_patterns'],
        'severe': SEVERE_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_pneumonia_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical pneumonia endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in PNEUMONIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
