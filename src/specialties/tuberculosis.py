"""
Tuberculosis Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria and HIV
profiles. TB RCTs report a distinct endpoint vocabulary (sputum culture
conversion, treatment success / unfavourable outcome, relapse, drug resistance,
TB-preventive-therapy completion, vaccine efficacy) that the generic effect-size
engine does not recognise on its own.

Subspecialties:
- Treatment (drug-susceptible active TB): sputum culture conversion (2-month /
  8-week), time to culture conversion, smear conversion, treatment success /
  cure, treatment failure, relapse / recurrence, mortality, hepatotoxicity.
- Drug-resistant (MDR / RR / pre-XDR / XDR TB): favourable / unfavourable
  outcome, culture conversion, acquired drug resistance, death, QT prolongation
  and other serious adverse events (bedaquiline / delamanid / linezolid).
- Prevention (vaccine / prevention of infection or disease): incident
  tuberculosis, TB infection (IGRA / QFT conversion), vaccine efficacy
  (BCG, M72/AS01E).
- Latent (LTBI / TB preventive therapy): TPT completion, treatment completion,
  hepatotoxicity, conversion.

Effect measures follow what these trials report: binary (culture conversion,
treatment success, relapse, completion) -> RR/OR/RD; incidence / time-to-event
(incident TB, time to culture conversion, mortality) -> IRR/HR; vaccine and
preventive efficacy are reported as efficacy % (1 - HR/RR), handled by the
shared effects augmenter.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# TUBERCULOSIS ENDPOINTS
# ============================================================

TUBERCULOSIS_ENDPOINTS = {
    # --- Drug-susceptible treatment efficacy ---
    'CULTURE_CONVERSION': {
        'aliases': ['culture conversion', 'sputum culture conversion',
                    '2-month culture conversion', 'two-month culture conversion',
                    '8-week culture conversion', 'month 2 culture conversion',
                    'culture negativity', 'culture-negative status',
                    'sputum culture negativity', 'stable culture conversion'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'TIME_TO_CULTURE_CONVERSION': {
        'aliases': ['time to culture conversion', 'time to stable culture conversion',
                    'time to sputum culture conversion', 'time to culture negativity'],
        'subspecialty': 'treatment',
        'measure_types': ['HR']
    },
    'SMEAR_CONVERSION': {
        'aliases': ['sputum smear conversion', 'smear conversion',
                    'smear negativity', 'sputum smear negativity'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'TREATMENT_SUCCESS': {
        'aliases': ['treatment success', 'cure', 'cured', 'favourable outcome',
                    'favorable outcome', 'favourable status', 'favorable status',
                    'successful treatment outcome', 'sustained cure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'UNFAVORABLE_OUTCOME': {
        'aliases': ['unfavourable outcome', 'unfavorable outcome',
                    'unfavourable status', 'unfavorable status',
                    'composite unfavourable outcome', 'composite unfavorable outcome',
                    'poor outcome', 'treatment failure or relapse'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'bacteriological failure',
                    'microbiological failure', 'failure of treatment'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'RELAPSE': {
        'aliases': ['relapse', 'recurrence', 'recurrent tuberculosis',
                    'recurrent tb', 'tb recurrence', 'disease recurrence',
                    'bacteriological relapse', 'retreatment'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality', 'tb mortality',
                    'tuberculosis mortality', 'tb-related death', 'overall survival',
                    'all-cause death'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'HEPATOTOXICITY': {
        'aliases': ['hepatotoxicity', 'drug-induced liver injury',
                    'hepatic adverse event', 'alt elevation',
                    'aminotransferase elevation', 'grade 3 hepatotoxicity',
                    'liver enzyme elevation', 'hepatitis'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Drug-resistant TB ---
    'ACQUIRED_RESISTANCE': {
        'aliases': ['acquired drug resistance', 'acquired resistance',
                    'emergence of resistance', 'amplified resistance',
                    'treatment-emergent resistance', 'resistance amplification'],
        'subspecialty': 'drug_resistant',
        'measure_types': ['RR', 'OR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['serious adverse events', 'serious adverse event',
                    'grade 3 or 4 adverse events', 'grade 3-4 adverse events',
                    'qt prolongation', 'qtcf prolongation', 'qtc prolongation',
                    'treatment-emergent adverse events'],
        'subspecialty': 'drug_resistant',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Prevention (vaccine / prevention of infection or disease) ---
    'TB_INCIDENCE': {
        'aliases': ['incident tuberculosis', 'incident tb', 'tb incidence',
                    'tuberculosis incidence', 'incidence of tuberculosis',
                    'active tuberculosis', 'active tb', 'tb disease',
                    'progression to active tb', 'incident active tuberculosis'],
        'subspecialty': 'prevention',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'TB_INFECTION': {
        'aliases': ['tb infection', 'tuberculosis infection',
                    'm. tuberculosis infection', 'mycobacterium tuberculosis infection',
                    'igra conversion', 'qft conversion', 'quantiferon conversion',
                    'sustained qft conversion', 'tst conversion',
                    'sustained infection', 'initial infection'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'protective efficacy',
                    'efficacy against tuberculosis', 'efficacy against tb disease',
                    'prevention of tb disease', 'vaccine effectiveness'],
        'subspecialty': 'prevention',
        'measure_types': ['HR', 'RR', 'IRR']
    },

    # --- Latent TB / TB preventive therapy ---
    'TPT_COMPLETION': {
        'aliases': ['treatment completion', 'tpt completion',
                    'preventive therapy completion', 'completion of preventive therapy',
                    'completion of tb preventive treatment', 'regimen completion',
                    'completed treatment', 'adherence to preventive therapy'],
        'subspecialty': 'latent',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# TREATMENT PATTERNS (drug-susceptible active TB)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'pulmonary\s+tuberculosis|active\s+tuberculosis|drug[- ]susceptible\s+tuberculosis',
        r'sputum\s+culture|culture\s+conversion|smear[- ]positive|smear\s+conversion',
        r'\bhrze\b|2hrze|standard\s+(?:tb\s+)?regimen|6[- ]month\s+regimen',
        r'4[- ]month\s+regimen|treatment[- ]shortening',
        r'isoniazid|rifampic?in|rifapentine|pyrazinamide|ethambutol',
        r'moxifloxacin|rifabutin',
        r'time\s+to\s+culture\s+conversion|relapse|recurrence',
    ],
    'endpoint_patterns': [
        (r'time\s+to\s+(?:stable\s+)?(?:sputum\s+)?culture\s+(?:conversion|negativity)',
         'TIME_TO_CULTURE_CONVERSION'),
        (r'(?:sputum\s+)?culture\s+(?:conversion|negativity)|culture[- ]negative|'
         r'2[- ]month\s+culture\s+conversion|8[- ]week\s+culture\s+conversion',
         'CULTURE_CONVERSION'),
        (r'(?:sputum\s+)?smear\s+(?:conversion|negativity)', 'SMEAR_CONVERSION'),
        (r'unfavou?rable\s+(?:outcome|status)|poor\s+outcome|'
         r'treatment\s+failure\s+or\s+relapse', 'UNFAVORABLE_OUTCOME'),
        (r'treatment\s+success|favou?rable\s+(?:outcome|status)|\bcured?\b|'
         r'successful\s+treatment\s+outcome', 'TREATMENT_SUCCESS'),
        (r'(?:bacteriolog\w+|microbiolog\w+)?\s*treatment\s+failure|failure\s+of\s+treatment',
         'TREATMENT_FAILURE'),
        (r'relapse|recurrence|recurrent\s+(?:tuberculosis|tb)|retreatment', 'RELAPSE'),
        (r'hepatotoxicity|drug[- ]induced\s+liver\s+injury|alt\s+elevation|'
         r'aminotransferase\s+elevation', 'HEPATOTOXICITY'),
        (r'(?:all[- ]cause|tb[- ]related|tuberculosis)\s+(?:mortality|death)|'
         r'\bmortality\b|\bdeath\b', 'MORTALITY'),
    ],
    'context_patterns': [
        r'(?:week|month)\s+(?:8|2)\s+culture', r'per[- ]protocol|modified\s+intention',
        r'liquid\s+culture|\bmgit\b|solid\s+culture', r'rifampic?in[- ]susceptible',
    ]
}


# ============================================================
# DRUG-RESISTANT PATTERNS (MDR / RR / pre-XDR / XDR-TB)
# ============================================================

DRUG_RESISTANT_PATTERNS = {
    'detection_keywords': [
        r'multidrug[- ]resistant|\bmdr[- ]?tb\b|rifampic?in[- ]resistant|\brr[- ]?tb\b',
        r'pre[- ]?xdr|\bxdr[- ]?tb\b|extensively\s+drug[- ]resistant',
        r'fluoroquinolone[- ]resistant',
        r'bedaquiline|delamanid|pretomanid|linezolid|clofazimine|cycloserine',
        r'\bbpal\b|\bbpalm\b|\bbdq\b|\bdlm\b',
        r'amikacin|kanamycin|capreomycin|ethionamide|short\w*\s+regimen',
    ],
    'endpoint_patterns': [
        (r'acquired\s+(?:drug\s+)?resistance|emergence\s+of\s+resistance|'
         r'amplified\s+resistance|resistance\s+amplification', 'ACQUIRED_RESISTANCE'),
        (r'serious\s+adverse\s+events?|grade\s+3(?:\s*[-/]\s*4|\s+or\s+4)?\s+adverse|'
         r'qtc?f?\s+prolongation', 'ADVERSE_EVENTS'),
        (r'unfavou?rable\s+(?:outcome|status)|poor\s+outcome', 'UNFAVORABLE_OUTCOME'),
        (r'favou?rable\s+(?:outcome|status)|treatment\s+success|\bcured?\b',
         'TREATMENT_SUCCESS'),
        (r'(?:sputum\s+)?culture\s+(?:conversion|negativity)', 'CULTURE_CONVERSION'),
        (r'relapse|recurrence|recurrent\s+(?:tuberculosis|tb)', 'RELAPSE'),
        (r'(?:all[- ]cause|tb[- ]related)\s+(?:mortality|death)|\bmortality\b|\bdeath\b',
         'MORTALITY'),
    ],
    'context_patterns': [
        r'6[- ]month\s+(?:all[- ]oral\s+)?regimen', r'all[- ]oral\s+regimen',
        r'\bbpalm?\b', r'second[- ]line', r'\bdst\b|drug[- ]susceptibility\s+testing',
    ]
}


# ============================================================
# PREVENTION PATTERNS (vaccine / prevention of infection or disease)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'tb\s+vaccine|tuberculosis\s+vaccine|\bm72\b|as01e|\bbcg\b',
        r'revaccination|vaccine\s+efficacy|protective\s+efficacy',
        r'prevention\s+of\s+(?:tb|tuberculosis)\s+disease',
        r'incident\s+tuberculosis|tb\s+incidence|progression\s+to\s+(?:active\s+)?tb',
        r'igra\s+conversion|quantiferon|qft\s+conversion|sustained\s+conversion',
    ],
    'endpoint_patterns': [
        (r'vaccine\s+efficacy|protective\s+efficacy|efficacy\s+against\s+(?:tb|tuberculosis)|'
         r'prevention\s+of\s+tb\s+disease|vaccine\s+effectiveness', 'VACCINE_EFFICACY'),
        (r'(?:incident|active)\s+tuberculosis|tb\s+incidence|incident\s+tb|'
         r'progression\s+to\s+(?:active\s+)?tb|tb\s+disease', 'TB_INCIDENCE'),
        (r'(?:tb|tuberculosis|m\.?\s*tuberculosis|mycobacterium\s+tuberculosis)\s+infection|'
         r'(?:igra|qft|quantiferon|tst)\s+conversion|sustained\s+conversion', 'TB_INFECTION'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'incidence\s+rate\s+ratio|\birr\b',
        r'1\s*[-−]\s*(?:hazard\s+ratio|hr)', r'sustained\s+qft\s+conversion',
    ]
}


# ============================================================
# LATENT PATTERNS (LTBI / TB preventive therapy)
# ============================================================

LATENT_PATTERNS = {
    'detection_keywords': [
        r'latent\s+(?:tb|tuberculosis)\s+infection|\bltbi\b',
        r'tb\s+preventive\s+(?:therapy|treatment)|\btpt\b|preventive\s+therapy',
        r'isoniazid\s+preventive\s+therapy|\bipt\b',
        r'\b3hp\b|\b1hp\b|\b6h\b|\b9h\b|\b4r\b|weekly\s+rifapentine',
        r'household\s+contacts?|tb\s+contacts?',
    ],
    'endpoint_patterns': [
        (r'(?:tpt|treatment|regimen|preventive\s+therapy)\s+completion|'
         r'completion\s+of\s+(?:preventive\s+therapy|tb\s+preventive\s+treatment)|'
         r'completed\s+treatment|adherence\s+to\s+preventive', 'TPT_COMPLETION'),
        (r'(?:incident|active)\s+tuberculosis|tb\s+incidence|incident\s+tb|'
         r'progression\s+to\s+(?:active\s+)?tb', 'TB_INCIDENCE'),
        (r'hepatotoxicity|drug[- ]induced\s+liver\s+injury|alt\s+elevation', 'HEPATOTOXICITY'),
        (r'(?:tb|tuberculosis)\s+infection|(?:igra|qft|tst)\s+conversion', 'TB_INFECTION'),
    ],
    'context_patterns': [
        r'weekly\s+(?:dose|isoniazid|rifapentine)', r'12\s+(?:weekly\s+)?doses',
        r'self[- ]administered|directly\s+observed', r'tuberculin\s+skin\s+test',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_tuberculosis_subspecialty(text: str) -> Tuple[str, float]:
    """Detect TB trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: treatment, drug_resistant, prevention, latent, general_tb."""
    text_lower = text.lower()
    scores = {'treatment': 0, 'drug_resistant': 0, 'prevention': 0, 'latent': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['treatment'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['drug_resistant'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prevention'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['latent'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_tb', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_tuberculosis_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'drug_resistant': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'latent': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_tuberculosis_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical TB endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in TUBERCULOSIS_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
