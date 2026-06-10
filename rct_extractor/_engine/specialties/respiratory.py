"""
Respiratory (chronic airways + interstitial lung disease) Subspecialty Patterns
and Endpoints.

Built for the same meta-analysis workflow as the malaria / HIV / hepatitis
profiles. Chronic-respiratory RCTs report an endpoint vocabulary the generic
effect-size engine does not recognise on its own (exacerbation rates, lung
function, symptom/quality-of-life scores).

Subspecialties:
- COPD (chronic obstructive pulmonary disease):
    exacerbations (moderate/severe AECOPD; rate -> IRR/RR, time-to-first -> HR),
    trough FEV1 (mL), rate of FEV1 decline (mL/year), SGRQ / CAT (symptom-QoL),
    TDI dyspnea, 6-minute walk distance, COPD hospitalisation, mortality.
- Asthma:
    severe exacerbation rate (IRR/RR), ACQ / ACT / AQLQ control & QoL scores,
    pre/post-bronchodilator FEV1, peak expiratory flow (PEF), FeNO, blood
    eosinophils (log-normal), oral-corticosteroid (OCS) dose reduction /
    OCS-sparing, rescue-medication use.
- ILD (interstitial lung disease / idiopathic pulmonary fibrosis):
    forced vital capacity (FVC, mL), rate of FVC decline (mL/year), DLCO,
    disease progression, acute exacerbation of IPF, 6-minute walk, mortality.

Effect measures follow what these trials report: binary (exacerbation occurrence,
hospitalisation, response, mortality) -> RR/OR/RD; event rates over follow-up
(exacerbation rate, time-to-first) -> IRR/HR; continuous (FEV1, FVC, SGRQ, ACQ,
PEF, 6MWD) -> MD/SMD. FeNO and blood eosinophils are log-normal (pool on the log
scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# RESPIRATORY ENDPOINTS
# ============================================================

RESPIRATORY_ENDPOINTS = {
    # --- COPD ---
    'COPD_EXACERBATION': {
        'aliases': ['copd exacerbation', 'acute exacerbation of copd', 'aecopd',
                    'moderate or severe exacerbation', 'moderate-to-severe exacerbation',
                    'severe exacerbation', 'exacerbation rate', 'annual exacerbation rate',
                    'rate of moderate or severe exacerbations', 'acute exacerbation'],
        'subspecialty': 'copd',
        'measure_types': ['IRR', 'RR', 'HR', 'OR']
    },
    'TROUGH_FEV1': {
        'aliases': ['trough fev1', 'trough fev-1', 'pre-dose fev1', 'pre-bronchodilator fev1',
                    'post-bronchodilator fev1', 'change in trough fev1', 'fev1', 'fev-1',
                    'forced expiratory volume in 1 second', 'forced expiratory volume in one second'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'FEV1_DECLINE': {
        'aliases': ['rate of fev1 decline', 'fev1 decline', 'annual fev1 decline',
                    'rate of decline in fev1', 'decline in lung function'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'SGRQ': {
        'aliases': ["st george's respiratory questionnaire", 'sgrq', 'sgrq total score',
                    'sgrq-c', 'st georges respiratory questionnaire'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'CAT_SCORE': {
        'aliases': ['copd assessment test', 'cat score', 'cat total score'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'DYSPNEA_TDI': {
        'aliases': ['transition dyspnea index', 'tdi', 'tdi focal score', 'mmrc',
                    'modified medical research council', 'baseline dyspnea index', 'bdi',
                    'dyspnea score'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'RESCUE_MEDICATION': {
        'aliases': ['rescue medication use', 'rescue medication', 'rescue inhaler use',
                    'use of rescue medication', 'reliever use', 'puffs per day'],
        'subspecialty': 'copd',
        'measure_types': ['MD', 'SMD']
    },
    'COPD_HOSPITALIZATION': {
        'aliases': ['copd hospitalization', 'copd hospitalisation', 'hospitalization for copd',
                    'hospitalisation for exacerbation', 'exacerbation-related hospitalization',
                    'respiratory hospitalization'],
        'subspecialty': 'copd',
        'measure_types': ['RR', 'HR', 'IRR', 'OR']
    },

    # --- Asthma ---
    'ASTHMA_EXACERBATION': {
        'aliases': ['severe asthma exacerbation', 'asthma exacerbation', 'clinically significant exacerbation',
                    'annualized exacerbation rate', 'annualised exacerbation rate',
                    'rate of severe exacerbations', 'asthma exacerbation rate'],
        'subspecialty': 'asthma',
        'measure_types': ['IRR', 'RR', 'HR', 'OR']
    },
    'ACQ': {
        'aliases': ['asthma control questionnaire', 'acq', 'acq-5', 'acq-6', 'acq-7',
                    'asthma control questionnaire score'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD']
    },
    'ACT': {
        'aliases': ['asthma control test', 'act score', 'act total score', 'childhood asthma control test',
                    'c-act'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD']
    },
    'AQLQ': {
        'aliases': ['asthma quality of life questionnaire', 'aqlq', 'aqlq score',
                    'mini asthma quality of life questionnaire', 'miniaqlq'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD']
    },
    'PEF': {
        'aliases': ['peak expiratory flow', 'pef', 'morning pef', 'evening pef',
                    'peak flow', 'am pef'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD']
    },
    'FENO': {
        'aliases': ['fractional exhaled nitric oxide', 'feno', 'exhaled nitric oxide',
                    'fe-no', 'fractional concentration of exhaled nitric oxide'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'BLOOD_EOSINOPHILS': {
        'aliases': ['blood eosinophil count', 'blood eosinophils', 'eosinophil count',
                    'peripheral eosinophils', 'sputum eosinophils'],
        'subspecialty': 'asthma',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'OCS_REDUCTION': {
        'aliases': ['oral corticosteroid dose reduction', 'ocs dose reduction', 'ocs reduction',
                    'oral glucocorticoid reduction', 'reduction in oral corticosteroid dose',
                    'corticosteroid-sparing', 'oral steroid reduction', 'maintenance ocs dose'],
        'subspecialty': 'asthma',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- ILD / IPF ---
    'FVC': {
        'aliases': ['forced vital capacity', 'fvc', 'change in fvc', 'absolute change in fvc',
                    'fvc % predicted', 'fvc percent predicted'],
        'subspecialty': 'ild',
        'measure_types': ['MD', 'SMD']
    },
    'FVC_DECLINE': {
        'aliases': ['rate of fvc decline', 'annual rate of decline in fvc', 'fvc decline',
                    'annual fvc decline', 'rate of decline in fvc', 'decline in fvc'],
        'subspecialty': 'ild',
        'measure_types': ['MD', 'SMD']
    },
    'DLCO': {
        'aliases': ['dlco', 'diffusing capacity', 'diffusion capacity', 'tlco',
                    'carbon monoxide diffusing capacity'],
        'subspecialty': 'ild',
        'measure_types': ['MD', 'SMD']
    },
    'ILD_PROGRESSION': {
        'aliases': ['disease progression', 'progression-free survival', 'time to progression',
                    'progression of pulmonary fibrosis', 'ild progression'],
        'subspecialty': 'ild',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'ACUTE_EXACERBATION_IPF': {
        'aliases': ['acute exacerbation of ipf', 'acute exacerbation of idiopathic pulmonary fibrosis',
                    'acute exacerbation', 'ipf exacerbation'],
        'subspecialty': 'ild',
        'measure_types': ['HR', 'RR', 'OR']
    },

    # --- Cross-cutting respiratory outcomes ---
    'SIX_MIN_WALK': {
        'aliases': ['6-minute walk distance', 'six-minute walk distance', '6mwd', '6-minute walk test',
                    'six minute walk distance', 'six-minute walking distance', '6 min walk distance'],
        'subspecialty': 'general_respiratory',
        'measure_types': ['MD', 'SMD']
    },
    'MORTALITY': {
        'aliases': ['all-cause mortality', 'all-cause death', 'respiratory mortality',
                    'respiratory death', 'overall survival', 'mortality', 'death'],
        'subspecialty': 'general_respiratory',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'SERIOUS_AE': {
        'aliases': ['serious adverse event', 'serious adverse events', 'sae', 'saes'],
        'subspecialty': 'general_respiratory',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# COPD PATTERNS
# ============================================================

COPD_PATTERNS = {
    'detection_keywords': [
        r'chronic\s+obstructive\s+pulmonary\s+disease', r'\bcopd\b', r'\baecopd\b',
        r'emphysema', r'chronic\s+bronchitis',
        r'trough\s+fev1?', r'st\s+george', r'\bsgrq\b', r'copd\s+assessment\s+test|\bcat\b',
        r'tiotropium|umeclidinium|glycopyrr?onium|aclidinium', r'\blama\b|\blaba\b|\bics\b',
        r'roflumilast', r'triple\s+therapy', r'exacerbation',
    ],
    'endpoint_patterns': [
        (r'copd\s+exacerbation|acute\s+exacerbation\s+of\s+copd|\baecopd\b|'
         r'moderate(?:[- ]to[- ]|\s+or\s+)severe\s+exacerbation|exacerbation\s+rate|'
         r'rate\s+of\s+(?:moderate\s+or\s+severe\s+)?exacerbations?', 'COPD_EXACERBATION'),
        (r'rate\s+of\s+(?:decline\s+in\s+)?fev1?\s+decline|fev1?\s+decline|'
         r'annual\s+fev1?\s+decline|rate\s+of\s+decline\s+in\s+fev1?', 'FEV1_DECLINE'),
        (r'trough\s+fev1?|pre[- ](?:dose|bronchodilator)\s+fev1?|post[- ]bronchodilator\s+fev1?|'
         r'change\s+in\s+trough\s+fev1?|\bfev1?\b|forced\s+expiratory\s+volume', 'TROUGH_FEV1'),
        (r"st\s+george'?s?\s+respiratory\s+questionnaire|\bsgrq(?:-c)?\b", 'SGRQ'),
        (r'copd\s+assessment\s+test|\bcat\s+(?:score|total)', 'CAT_SCORE'),
        (r'transition\s+dyspnea\s+index|\btdi\b|\bmmrc\b|baseline\s+dyspnea\s+index|\bbdi\b|'
         r'dyspnea\s+score', 'DYSPNEA_TDI'),
        (r'rescue\s+medication\s+use|rescue\s+medication|reliever\s+use|puffs\s+per\s+day',
         'RESCUE_MEDICATION'),
        (r'copd\s+hospitali[sz]ation|hospitali[sz]ation\s+for\s+copd|'
         r'exacerbation[- ]related\s+hospitali[sz]ation|respiratory\s+hospitali[sz]ation',
         'COPD_HOSPITALIZATION'),
    ],
    'context_patterns': [
        r'gold\s+(?:stage|[1-4abcd])', r'post[- ]bronchodilator', r'former\s+smoker',
        r'eosinophil',
    ]
}


# ============================================================
# ASTHMA PATTERNS
# ============================================================

ASTHMA_PATTERNS = {
    'detection_keywords': [
        r'\basthma\b', r'asthmatic', r'severe\s+(?:eosinophilic\s+)?asthma',
        r'asthma\s+control', r'\bacq(?:-?[567])?\b', r'asthma\s+control\s+test|\bact\b',
        r'\baqlq\b', r'biologic', r'mepolizumab|benralizumab|reslizumab|dupilumab|omalizumab|tezepelumab',
        r'eosinophil', r'\bfeno\b|exhaled\s+nitric\s+oxide',
        r'oral\s+corticosteroid|\bocs\b', r'inhaled\s+cortico?steroid',
    ],
    'endpoint_patterns': [
        (r'severe\s+asthma\s+exacerbation|asthma\s+exacerbation|clinically\s+significant\s+exacerbation|'
         r'annuali[sz]ed\s+exacerbation\s+rate|rate\s+of\s+severe\s+exacerbations?', 'ASTHMA_EXACERBATION'),
        (r'asthma\s+control\s+questionnaire|\bacq(?:-?[567])?\b', 'ACQ'),
        (r'asthma\s+control\s+test|\bc?-?act\s+(?:score|total)|\bact\s+score\b', 'ACT'),
        (r'(?:mini\s+)?asthma\s+quality\s+of\s+life\s+questionnaire|\bmini[- ]?aqlq\b|\baqlq\b', 'AQLQ'),
        (r'peak\s+expiratory\s+flow|\bpef\b|morning\s+pef|evening\s+pef|peak\s+flow', 'PEF'),
        (r'fractional\s+exhaled\s+nitric\s+oxide|\bfeno\b|exhaled\s+nitric\s+oxide', 'FENO'),
        (r'blood\s+eosinophil\s+count|blood\s+eosinophils|eosinophil\s+count|'
         r'peripheral\s+eosinophils|sputum\s+eosinophils', 'BLOOD_EOSINOPHILS'),
        (r'oral\s+cortico?steroid\s+(?:dose\s+)?reduction|\bocs\s+(?:dose\s+)?reduction|'
         r'cortico?steroid[- ]sparing|reduction\s+in\s+oral\s+cortico?steroid|'
         r'maintenance\s+ocs\s+dose|oral\s+steroid\s+reduction', 'OCS_REDUCTION'),
    ],
    'context_patterns': [
        r'eosinophilic', r'type\s*2\s+inflammation', r'add[- ]on\s+therapy',
        r'maintenance\s+(?:and\s+reliever\s+)?therapy',
    ]
}


# ============================================================
# ILD / IPF PATTERNS
# ============================================================

ILD_PATTERNS = {
    'detection_keywords': [
        r'idiopathic\s+pulmonary\s+fibrosis', r'\bipf\b', r'interstitial\s+lung\s+disease',
        r'\bild\b', r'pulmonary\s+fibrosis', r'progressive\s+fibrosing',
        r'nintedanib|pirfenidone', r'forced\s+vital\s+capacity|\bfvc\b',
        r'\bdlco\b|diffusing\s+capacity', r'fibrotic',
    ],
    'endpoint_patterns': [
        (r'rate\s+of\s+(?:decline\s+in\s+)?fvc\s+decline|annual\s+(?:rate\s+of\s+)?(?:decline\s+in\s+)?fvc|'
         r'fvc\s+decline|rate\s+of\s+decline\s+in\s+fvc|decline\s+in\s+fvc', 'FVC_DECLINE'),
        (r'forced\s+vital\s+capacity|\bfvc\b|change\s+in\s+fvc|fvc\s+(?:%|percent)\s+predicted',
         'FVC'),
        (r'\bdlco\b|\btlco\b|diffusing\s+capacity|diffusion\s+capacity', 'DLCO'),
        (r'acute\s+exacerbation\s+of\s+(?:ipf|idiopathic\s+pulmonary\s+fibrosis)|ipf\s+exacerbation',
         'ACUTE_EXACERBATION_IPF'),
        (r'disease\s+progression|progression[- ]free\s+survival|time\s+to\s+progression|'
         r'progression\s+of\s+pulmonary\s+fibrosis|ild\s+progression', 'ILD_PROGRESSION'),
    ],
    'context_patterns': [
        r'high[- ]resolution\s+ct|hrct', r'usual\s+interstitial\s+pneumonia|\buip\b',
        r'%\s*predicted',
    ]
}


# ============================================================
# GENERAL RESPIRATORY (cross-cutting outcomes)
# ============================================================

GENERAL_PATTERNS = {
    'detection_keywords': [
        r'6[- ]minute\s+walk|six[- ]minute\s+walk|\b6mwd\b',
        r'all[- ]cause\s+mortality', r'respiratory\s+(?:death|mortality)',
    ],
    'endpoint_patterns': [
        (r'6[- ]minute\s+walk\s+(?:distance|test)|six[- ]minute\s+walk\w*|\b6\s*mwd\b|'
         r'6\s*min\s+walk\s+distance', 'SIX_MIN_WALK'),
        (r'serious\s+adverse\s+events?|\bsaes?\b', 'SERIOUS_AE'),
        # Generic mortality (respiratory or all-cause).
        (r'(?:all[- ]cause\s+|respiratory\s+)?(?:mortality|death)\b|overall\s+survival', 'MORTALITY'),
    ],
    'context_patterns': [
        r'per\s+(?:100\s+)?person[- ]years', r'kaplan[- ]meier',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_respiratory_subspecialty(text: str) -> Tuple[str, float]:
    """Detect respiratory trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: copd, asthma, ild, general_respiratory."""
    text_lower = text.lower()
    scores = {'copd': 0, 'asthma': 0, 'ild': 0}
    for kw in COPD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['copd'] += 1
    for kw in ASTHMA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['asthma'] += 1
    for kw in ILD_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['ild'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_respiratory', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_respiratory_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'copd': COPD_PATTERNS['endpoint_patterns'],
        'asthma': ASTHMA_PATTERNS['endpoint_patterns'],
        'ild': ILD_PATTERNS['endpoint_patterns'],
        'general_respiratory': GENERAL_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_respiratory_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical respiratory endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in RESPIRATORY_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
