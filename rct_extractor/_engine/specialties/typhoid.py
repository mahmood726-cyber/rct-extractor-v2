"""
Typhoid (enteric fever) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria and HIV
profiles. Typhoid / paratyphoid (enteric fever) RCTs report a distinct endpoint
vocabulary the generic effect-size engine does not recognise on its own.

Subspecialties:
- Treatment (antibiotic therapy): clinical cure, microbiological/bacteriological
  cure, fever clearance time, treatment failure, relapse, faecal carriage,
  hospital stay, mortality. Drugs: fluoroquinolones (ciprofloxacin, ofloxacin,
  gatifloxacin), azithromycin, ceftriaxone/cefixime, chloramphenicol, amoxicillin,
  co-trimoxazole.
- Vaccine (prevention): blood-culture-confirmed typhoid incidence, vaccine
  efficacy, seroconversion, anti-Vi immunogenicity (GMT/GMC). Vaccines: typhoid
  conjugate vaccine (TCV, Vi-TT, Vi-DT), Ty21a, Vi polysaccharide.
- Resistance (cross-cutting): MDR typhoid, fluoroquinolone non-susceptibility /
  nalidixic-acid resistance, XDR / ceftriaxone resistance.
- Complications (severe): intestinal perforation, GI bleeding, encephalopathy,
  severe/complicated typhoid.

Effect measures follow what these trials report: binary (cure, failure, relapse,
carriage, perforation) -> RR/OR/RD; incidence -> IRR/HR; continuous (fever
clearance time, hospital stay -> MD/SMD; anti-Vi titres -> GMR, log-normal).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# TYPHOID ENDPOINTS
# ============================================================

TYPHOID_ENDPOINTS = {
    # --- Antibiotic treatment efficacy ---
    'CLINICAL_CURE': {
        'aliases': ['clinical cure', 'clinical success', 'clinical response',
                    'clinical resolution', 'overall cure', 'cure rate',
                    'favourable clinical outcome', 'favorable clinical outcome'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'MICROBIOLOGICAL_CURE': {
        'aliases': ['microbiological cure', 'bacteriological cure',
                    'microbiological clearance', 'bacteriological clearance',
                    'culture conversion', 'blood culture clearance',
                    'bacteriological success', 'microbiological eradication'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FEVER_CLEARANCE_TIME': {
        'aliases': ['fever clearance time', 'time to fever clearance',
                    'time to defervescence', 'defervescence time',
                    'fever resolution time', 'time to fever resolution',
                    'fever subsidence time'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'clinical failure', 'microbiological failure',
                    'therapeutic failure', 'overall treatment failure',
                    'composite treatment failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'relapse rate', 'clinical relapse',
                    'microbiological relapse', 'recurrence', 'recrudescence'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FECAL_CARRIAGE': {
        'aliases': ['faecal carriage', 'fecal carriage', 'stool carriage',
                    'chronic carriage', 'convalescent carriage', 'chronic carrier',
                    'chronic faecal carriage', 'chronic fecal carriage',
                    'persistent carriage'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HOSPITAL_STAY': {
        'aliases': ['length of hospital stay', 'duration of hospitalization',
                    'duration of hospitalisation', 'length of stay', 'hospital stay',
                    'hospitalization duration', 'time to discharge'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'case fatality',
                    'case fatality rate', 'typhoid-related death', 'in-hospital mortality'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Vaccine (prevention) ---
    'TYPHOID_INCIDENCE': {
        'aliases': ['typhoid fever', 'blood culture-confirmed typhoid',
                    'blood-culture-confirmed typhoid', 'culture-confirmed typhoid',
                    'confirmed typhoid fever', 'typhoid incidence', 'incident typhoid',
                    'enteric fever', 'incidence of typhoid', 'first episode of typhoid'],
        'subspecialty': 'vaccine',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against typhoid', 'efficacy against typhoid fever',
                    'relative risk reduction in typhoid'],
        'subspecialty': 'vaccine',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'SEROCONVERSION': {
        'aliases': ['seroconversion', 'seroconversion rate', 'anti-vi seroconversion',
                    'four-fold rise', 'fourfold rise', 'seroresponse',
                    'sero-response rate'],
        'subspecialty': 'vaccine',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'IMMUNOGENICITY': {
        'aliases': ['anti-vi igg', 'anti-vi antibody', 'vi igg', 'geometric mean titer',
                    'geometric mean titre', 'gmt', 'geometric mean concentration', 'gmc',
                    'anti-vi geometric mean', 'immunogenicity', 'vi antibody titre'],
        'subspecialty': 'vaccine',
        'measure_types': ['GMR', 'MD', 'SMD']
    },

    # --- Resistance (cross-cutting) ---
    'MDR_TYPHOID': {
        'aliases': ['multidrug-resistant typhoid', 'multidrug resistance',
                    'mdr typhoid', 'mdr salmonella', 'multidrug-resistant salmonella',
                    'multidrug-resistant s. typhi'],
        'subspecialty': 'resistance',
        'measure_types': ['RR', 'OR']
    },
    'FLUOROQUINOLONE_RESISTANCE': {
        'aliases': ['fluoroquinolone resistance', 'fluoroquinolone non-susceptibility',
                    'nalidixic acid resistance', 'nalidixic-acid resistance',
                    'ciprofloxacin resistance', 'decreased ciprofloxacin susceptibility',
                    'reduced fluoroquinolone susceptibility'],
        'subspecialty': 'resistance',
        'measure_types': ['RR', 'OR']
    },
    'XDR_TYPHOID': {
        'aliases': ['extensively drug-resistant typhoid', 'xdr typhoid',
                    'xdr salmonella', 'extensively drug-resistant salmonella',
                    'ceftriaxone resistance', 'ceftriaxone-resistant',
                    'cephalosporin resistance'],
        'subspecialty': 'resistance',
        'measure_types': ['RR', 'OR']
    },

    # --- Complications (severe) ---
    'INTESTINAL_PERFORATION': {
        'aliases': ['intestinal perforation', 'ileal perforation', 'bowel perforation',
                    'gastrointestinal perforation', 'typhoid intestinal perforation',
                    'enteric perforation'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GI_BLEEDING': {
        'aliases': ['gastrointestinal bleeding', 'intestinal haemorrhage',
                    'intestinal hemorrhage', 'gastrointestinal haemorrhage',
                    'gastrointestinal hemorrhage', 'intestinal bleeding',
                    'gi bleeding'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'ENCEPHALOPATHY': {
        'aliases': ['typhoid encephalopathy', 'encephalopathy', 'altered consciousness',
                    'altered mental status', 'neuropsychiatric complication'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR']
    },
    'SEVERE_TYPHOID': {
        'aliases': ['severe typhoid', 'complicated typhoid', 'severe enteric fever',
                    'complicated enteric fever', 'severe typhoid fever',
                    'serious complication'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# TREATMENT PATTERNS (antibiotic therapy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'azithromycin', r'ciprofloxacin', r'ofloxacin', r'gatifloxacin',
        r'levofloxacin', r'norfloxacin', r'pefloxacin', r'fluoroquinolone',
        r'ceftriaxone', r'cefixime', r'cefotaxime', r'chloramphenicol',
        r'amoxicillin', r'ampicillin', r'co[- ]?trimoxazole|trimethoprim',
        r'fever\s+clearance', r'defervescence', r'clinical\s+cure',
        r'(?:micro)?biological\s+(?:cure|clearance)', r'treatment\s+failure',
        r'fa?ecal\s+carriage', r'time\s+to\s+defervescence',
    ],
    'endpoint_patterns': [
        (r'clinical\s+(?:cure|success|response|resolution)|cure\s+rate', 'CLINICAL_CURE'),
        (r'(?:micro)?biological\s+(?:cure|clearance|success|eradication)|'
         r'culture\s+conversion|blood\s+culture\s+clearance', 'MICROBIOLOGICAL_CURE'),
        (r'fever\s+clearance\s+time|time\s+to\s+(?:defervescence|fever\s+clearance)|'
         r'defervescence\s+time', 'FEVER_CLEARANCE_TIME'),
        (r'(?:treatment|clinical|microbiological|therapeutic)\s+failure', 'TREATMENT_FAILURE'),
        (r'relapse|recurrence|recrudescence', 'RELAPSE'),
        (r'fa?ecal\s+carriage|stool\s+carriage|chronic\s+(?:carriage|carrier)|'
         r'convalescent\s+carriage', 'FECAL_CARRIAGE'),
        (r'length\s+of\s+(?:hospital\s+)?stay|duration\s+of\s+hospitali[sz]ation|'
         r'time\s+to\s+discharge', 'HOSPITAL_STAY'),
        (r'(?:all[- ]cause\s+)?mortality|case\s+fatality|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'per[- ]protocol|intention[- ]to[- ]treat', r'day\s+(?:7|10|14)\s+(?:cure|outcome)',
        r'culture[- ]confirmed', r'\bMIC\b|minimum\s+inhibitory',
    ]
}


# ============================================================
# VACCINE PATTERNS (prevention)
# ============================================================

VACCINE_PATTERNS = {
    'detection_keywords': [
        r'typhoid\s+conjugate\s+vaccine|\btcv\b', r'\bvi[- ]tt\b|\bvi[- ]dt\b',
        r'vi\s+polysaccharide|\bvi[- ]ps\b|\bvips\b', r'vi[- ]rep?a?',
        r'\bty21a\b', r'typbar', r'typhim', r'live\s+oral\s+vaccine',
        r'vaccine\s+efficacy|protective\s+efficacy', r'seroconversion',
        r'anti[- ]vi', r'immunogenicity', r'geometric\s+mean\s+tit',
    ],
    'endpoint_patterns': [
        (r'blood[- ]culture[- ]confirmed\s+typhoid|culture[- ]confirmed\s+typhoid|'
         r'confirmed\s+typhoid\s+fever|typhoid\s+incidence|incident\s+typhoid|'
         r'incidence\s+of\s+typhoid|enteric\s+fever', 'TYPHOID_INCIDENCE'),
        (r'vaccine\s+efficacy|protective\s+efficacy|efficacy\s+against\s+typhoid',
         'VACCINE_EFFICACY'),
        (r'seroconversion|four[- ]?fold\s+rise|seroresponse', 'SEROCONVERSION'),
        (r'anti[- ]vi\s+(?:igg|antibody|geometric)|geometric\s+mean\s+(?:tit|concentration)|'
         r'\bgmt\b|\bgmc\b|immunogenicity', 'IMMUNOGENICITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100,?000\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'eu\/ml|elisa\s+unit', r'cases\s+per\s+\d',
    ]
}


# ============================================================
# RESISTANCE PATTERNS (cross-cutting)
# ============================================================

RESISTANCE_PATTERNS = {
    'detection_keywords': [
        r'multidrug[- ]resistant|\bmdr\b', r'extensively\s+drug[- ]resistant|\bxdr\b',
        r'fluoroquinolone\s+(?:resistance|non[- ]susceptibility)',
        r'nalidixic\s+acid', r'ciprofloxacin\s+resistance',
        r'ceftriaxone\s+resistance|ceftriaxone[- ]resistant',
        r'azithromycin\s+resistance', r'\bh58\b|haplotype\s+58', r'\bblaCTX\b',
    ],
    'endpoint_patterns': [
        (r'multidrug[- ]resistant|\bmdr\b\s+(?:typhoid|salmonella|s\.?\s*typhi)|'
         r'multidrug\s+resistance', 'MDR_TYPHOID'),
        (r'fluoroquinolone\s+(?:resistance|non[- ]susceptibility)|nalidixic[- ]acid\s+resistance|'
         r'nalidixic\s+acid\s+resistance|ciprofloxacin\s+resistance|'
         r'decreased\s+ciprofloxacin\s+susceptibility', 'FLUOROQUINOLONE_RESISTANCE'),
        (r'extensively\s+drug[- ]resistant|\bxdr\b|ceftriaxone\s+resistance|'
         r'ceftriaxone[- ]resistant|cephalosporin\s+resistance', 'XDR_TYPHOID'),
    ],
    'context_patterns': [
        r'antimicrobial\s+susceptibility', r'\bMIC\b', r'breakpoint',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS (severe disease)
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'intestinal\s+perforation|ileal\s+perforation|bowel\s+perforation',
        r'gastrointestinal\s+(?:bleeding|ha?emorrhage)|intestinal\s+(?:bleeding|ha?emorrhage)',
        r'encephalopathy', r'severe\s+typhoid|complicated\s+(?:typhoid|enteric)',
        r'peritonitis', r'altered\s+(?:consciousness|mental\s+status)',
    ],
    'endpoint_patterns': [
        (r'(?:intestinal|ileal|bowel|gastrointestinal|enteric)\s+perforation',
         'INTESTINAL_PERFORATION'),
        (r'(?:gastrointestinal|intestinal)\s+(?:bleeding|ha?emorrhage)|\bgi\s+bleeding',
         'GI_BLEEDING'),
        (r'encephalopathy|altered\s+(?:consciousness|mental\s+status)', 'ENCEPHALOPATHY'),
        (r'severe\s+(?:typhoid|enteric\s+fever)|complicated\s+(?:typhoid|enteric\s+fever)',
         'SEVERE_TYPHOID'),
    ],
    'context_patterns': [
        r'surgical\s+intervention', r'laparotomy', r'intensive\s+care',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_typhoid_subspecialty(text: str) -> Tuple[str, float]:
    """Detect typhoid trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, vaccine, resistance, complications, general_typhoid."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'vaccine': 0, 'resistance': 0, 'complications': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in VACCINE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['vaccine'] += 1
    for kw in RESISTANCE_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['resistance'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_typhoid', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_typhoid_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'vaccine': VACCINE_PATTERNS['endpoint_patterns'],
        'resistance': RESISTANCE_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_typhoid_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical typhoid endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in TYPHOID_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
