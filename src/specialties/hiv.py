"""
HIV Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria profile.
HIV RCTs report a distinct endpoint vocabulary the generic effect-size engine
does not recognise on its own.

Subspecialties:
- Treatment (ART efficacy): viral suppression (FDA snapshot <50/<200 copies),
  virologic failure, CD4 recovery, mortality, AIDS progression, discontinuation,
  treatment-emergent drug resistance.
- Prevention (PrEP / vaccine / VMMC): HIV acquisition / incidence, seroconversion,
  PrEP efficacy.
- PMTCT (prevention of mother-to-child transmission): vertical transmission,
  infant HIV infection.
- Co-infection (TB/HIV, HCV/HIV): TB incidence, IRIS, mortality.

Effect measures follow what these trials report: binary (suppression, failure,
acquisition, MTCT) -> RR/OR/RD; incidence -> IRR/HR; continuous (CD4 change, log
HIV-RNA) -> MD/SMD (HIV-RNA is log-scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# HIV ENDPOINTS
# ============================================================

HIV_ENDPOINTS = {
    # --- ART treatment efficacy ---
    'VIRAL_SUPPRESSION': {
        'aliases': ['viral suppression', 'virologic suppression', 'virological suppression',
                    'viral load suppression', 'undetectable viral load', 'undetectable',
                    'hiv-1 rna <50', 'hiv rna less than 50', 'plasma viral load <50',
                    'snapshot', 'virologic success', 'hiv-rna <50 copies'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'VIROLOGIC_FAILURE': {
        'aliases': ['virologic failure', 'virological failure', 'confirmed virologic failure',
                    'viral rebound', 'virologic non-response', 'treatment failure',
                    'protocol-defined virologic failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'CD4_COUNT': {
        'aliases': ['cd4 count', 'cd4 cell count', 'cd4+ count', 'cd4 recovery',
                    'change in cd4', 'cd4 increase', 'cd4 cell recovery', 'cd4 t-cell count'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'HIV_RNA': {
        'aliases': ['hiv rna', 'hiv-1 rna', 'plasma hiv rna', 'viral load',
                    'log10 copies', 'change in viral load', 'log viral load reduction'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'AIDS_PROGRESSION': {
        'aliases': ['aids progression', 'progression to aids', 'aids-defining illness',
                    'aids-defining event', 'clinical progression', 'disease progression',
                    'who stage 3 or 4', 'aids or death'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'aids-related death',
                    'aids-related mortality', 'overall survival', 'all-cause death'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'TREATMENT_DISCONTINUATION': {
        'aliases': ['discontinuation', 'treatment discontinuation', 'treatment-limiting',
                    'discontinuation due to adverse events', 'drug discontinuation',
                    'regimen switch', 'treatment modification'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'DRUG_RESISTANCE': {
        'aliases': ['treatment-emergent resistance', 'drug resistance', 'resistance mutation',
                    'resistance-associated mutation', 'm184v', 'k65r', 'integrase resistance',
                    'emergent resistance'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'WEIGHT_GAIN': {
        'aliases': ['weight gain', 'change in body weight', 'weight increase',
                    'clinically significant weight gain'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'RR', 'OR']
    },

    # --- Prevention (PrEP / vaccine / VMMC) ---
    'HIV_ACQUISITION': {
        'aliases': ['hiv acquisition', 'hiv infection', 'incident hiv infection',
                    'hiv incidence', 'incidence of hiv', 'seroconversion', 'hiv seroconversion',
                    'new hiv infection', 'hiv-1 acquisition'],
        'subspecialty': 'prevention',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'PREP_EFFICACY': {
        'aliases': ['prep efficacy', 'pre-exposure prophylaxis efficacy',
                    'efficacy against hiv acquisition', 'protective efficacy',
                    'relative risk reduction in hiv'],
        'subspecialty': 'prevention',
        'measure_types': ['HR', 'IRR', 'RR']
    },

    # --- PMTCT ---
    'MTCT': {
        'aliases': ['mother-to-child transmission', 'mtct', 'vertical transmission',
                    'perinatal transmission', 'infant hiv infection', 'infant infection',
                    'early infant diagnosis', 'transmission to infant', 'in utero transmission'],
        'subspecialty': 'pmtct',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Co-infection ---
    'TB_INCIDENCE': {
        'aliases': ['tuberculosis incidence', 'incident tuberculosis', 'tb incidence',
                    'active tuberculosis', 'incident tb'],
        'subspecialty': 'coinfection',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'IRIS': {
        'aliases': ['immune reconstitution inflammatory syndrome', 'iris',
                    'immune reconstitution'],
        'subspecialty': 'coinfection',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Care cascade (cross-cutting) ---
    'RETENTION': {
        'aliases': ['retention in care', 'retention', 'loss to follow-up',
                    'lost to follow-up', 'ltfu', 'attrition', 'disengagement from care'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADHERENCE': {
        'aliases': ['art adherence', 'adherence', 'medication adherence',
                    'optimal adherence', 'adherence >=95%'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'MD']
    },
}


# ============================================================
# TREATMENT PATTERNS (ART efficacy)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'antiretroviral\s+therapy|\bart\b|\bhaart\b',
        r'viral\s+(?:load\s+)?suppression', r'virologic\w*\s+(?:failure|suppression|response)',
        r'undetectable', r'hiv[- ]?1?\s*rna', r'\bcd4\b', r'<\s*50\s*copies',
        r'fda\s+snapshot|snapshot\s+algorithm',
        r'dolutegravir|bictegravir|raltegravir|elvitegravir|cabotegravir',
        r'efavirenz|nevirapine|rilpivirine|doravirine',
        r'tenofovir|emtricitabine|lamivudine|abacavir|zidovudine',
        r'lopinavir|darunavir|atazanavir|ritonavir',
        r'\bDTG\b|\bBIC\b|\bRAL\b|\bEFV\b|\bTDF\b|\bTAF\b|\bFTC\b|\b3TC\b|\bABC\b|\bAZT\b',
    ],
    'endpoint_patterns': [
        (r'viral\s+(?:load\s+)?suppression|virologic\w*\s+suppression|'
         r'undetectable|hiv[- ]?1?\s*rna\s*<\s*50|snapshot', 'VIRAL_SUPPRESSION'),
        (r'virologic\w*\s+(?:failure|non-response)|viral\s+rebound', 'VIROLOGIC_FAILURE'),
        (r'treatment[- ]emergent\s+resistance|resistance[- ]associated\s+mutation|'
         r'\bm184v\b|\bk65r\b', 'DRUG_RESISTANCE'),
        (r'cd4\+?\s*(?:cell\s+)?count|cd4\s+(?:recovery|increase)|change\s+in\s+cd4', 'CD4_COUNT'),
        (r'hiv[- ]?1?\s*rna|viral\s+load|log10?\s+copies', 'HIV_RNA'),
        (r'progression\s+to\s+aids|aids[- ]defining|clinical\s+progression|aids\s+or\s+death',
         'AIDS_PROGRESSION'),
        (r'discontinuation|treatment[- ]limiting|regimen\s+switch', 'TREATMENT_DISCONTINUATION'),
        (r'weight\s+gain|change\s+in\s+(?:body\s+)?weight', 'WEIGHT_GAIN'),
        (r'retention\s+in\s+care|loss\s+to\s+follow|\bltfu\b|attrition', 'RETENTION'),
        (r'art\s+adherence|medication\s+adherence|optimal\s+adherence', 'ADHERENCE'),
        (r'(?:all[- ]cause|aids[- ]related)\s+(?:mortality|death)|\bmortality\b|\bdeath\b',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'week\s+48\s+(?:snapshot|suppression)', r'<\s*(?:50|200|400)\s*copies',
        r'intention[- ]to[- ]treat|per[- ]protocol', r'fda\s+snapshot',
    ]
}


# ============================================================
# PREVENTION PATTERNS (PrEP / vaccine / VMMC)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'pre[- ]?exposure\s+prophylaxis|\bprep\b',
        r'cabotegravir|\bCAB[- ]?LA\b|long[- ]acting\s+cabotegravir',
        r'dapivirine\s+ring|vaginal\s+ring', r'lenacapavir',
        r'voluntary\s+medical\s+male\s+circumcision|\bvmmc\b',
        r'hiv\s+vaccine|\bmosaic\b', r'seroconversion',
        r'hiv\s+(?:acquisition|incidence)',
    ],
    'endpoint_patterns': [
        (r'hiv\s+(?:acquisition|incidence)|incident\s+hiv|seroconversion|new\s+hiv\s+infection',
         'HIV_ACQUISITION'),
        (r'prep\s+efficacy|protective\s+efficacy|efficacy\s+against\s+hiv', 'PREP_EFFICACY'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'1\s*[-−]\s*(?:hazard\s+ratio|hr)', r'breakthrough\s+infection',
    ]
}


# ============================================================
# PMTCT PATTERNS
# ============================================================

PMTCT_PATTERNS = {
    'detection_keywords': [
        r'mother[- ]to[- ]child\s+transmission|\bmtct\b|\bpmtct\b',
        r'vertical\s+transmission', r'perinatal\s+transmission',
        r'early\s+infant\s+diagnosis|\beid\b', r'infant\s+hiv',
        r'pregnant\s+women\s+living\s+with\s+hiv', r'breastfeeding',
    ],
    'endpoint_patterns': [
        (r'mother[- ]to[- ]child\s+transmission|\bmtct\b|vertical\s+transmission|'
         r'perinatal\s+transmission|infant\s+hiv\s+infection|in\s+utero\s+transmission', 'MTCT'),
    ],
    'context_patterns': [
        r'at\s+(?:6|4|12)\s+weeks', r'breastfeeding|in\s+utero|intrapartum',
    ]
}


# ============================================================
# CO-INFECTION PATTERNS (TB/HIV, HCV/HIV)
# ============================================================

COINFECTION_PATTERNS = {
    'detection_keywords': [
        r'hiv[/ -]?tb|tb[/ -]?hiv|tuberculosis', r'isoniazid\s+preventive',
        r'immune\s+reconstitution|\biris\b', r'hepatitis\s+c|\bhcv\b',
        r'cryptococcal', r'opportunistic\s+infection',
    ],
    'endpoint_patterns': [
        (r'(?:incident|active)\s+tuberculosis|tb\s+incidence|incident\s+tb', 'TB_INCIDENCE'),
        (r'immune\s+reconstitution\s+inflammatory|\biris\b', 'IRIS'),
    ],
    'context_patterns': [
        r'isoniazid|rifampic?in', r'sputum\s+culture', r'cd4\s*<\s*(?:50|100|200)',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_hiv_subspecialty(text: str) -> Tuple[str, float]:
    """Detect HIV trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, prevention, pmtct, coinfection, general_hiv."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'prevention': 0, 'pmtct': 0, 'coinfection': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in PMTCT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['pmtct'] += 1
    for kw in COINFECTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['coinfection'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_hiv', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_hiv_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'pmtct': PMTCT_PATTERNS['endpoint_patterns'],
        'coinfection': COINFECTION_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_hiv_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical HIV endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in HIV_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
