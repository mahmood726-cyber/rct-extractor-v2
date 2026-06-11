"""
COVID-19 Subspecialty Patterns and Endpoints

Built for the same meta-analysis extraction workflow as the malaria / TB / HIV
profiles. COVID-19 RCTs report a distinct endpoint vocabulary (hospitalization-or-
death composite, 28-day mortality, time to sustained recovery, progression to
mechanical ventilation, WHO clinical progression scale, viral clearance, vaccine
efficacy) that the generic `infectious_disease` catch-all does not capture.

Subspecialties (mapped onto the registry's generic pattern slots):
- antiviral (TREATMENT slot): direct-acting antivirals — nirmatrelvir-ritonavir,
  molnupiravir, remdesivir, ensitrelvir. Endpoints: COVID-19-related
  hospitalization or death, time to sustained recovery, viral clearance.
- immunomodulator (DRUG_RESISTANT slot): host-directed anti-inflammatory therapy in
  hospitalized/severe disease — dexamethasone/corticosteroids, tocilizumab/
  sarilumab (IL-6), baricitinib (JAK), anakinra. Endpoints: 28-day mortality,
  progression to mechanical ventilation/ICU, WHO scale.
- prophylaxis_vaccine (PREVENTION slot): vaccines and pre-/post-exposure
  prophylaxis — vaccine efficacy, symptomatic infection, monoclonal-antibody
  prophylaxis.
- severe_supportive (LATENT slot): supportive/critical-care interventions —
  anticoagulation, oxygenation strategy, convalescent plasma, antibody cocktails
  in severe/critical disease.

Effect measures: mortality / hospitalization / progression / symptomatic infection
-> OR/RR/HR; time to recovery / viral clearance -> HR; vaccine efficacy reported as
(1 - RR/HR) percentage handled downstream.
"""
from typing import Dict, List, Tuple, Optional
import re

COVID19_ENDPOINTS = {
    'HOSPITALIZATION_DEATH': {
        'aliases': ['hospitalization or death', 'hospitalisation or death',
                    'covid-19-related hospitalization or death', 'hospitalization or all-cause death',
                    'hospitalization', 'hospital admission', 'covid-19 hospitalization'],
        'subspecialty': 'antiviral',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'MORTALITY': {
        'aliases': ['28-day mortality', '28 day mortality', 'all-cause mortality',
                    'mortality', 'death', '90-day mortality', 'in-hospital mortality',
                    'overall survival', 'covid-19 death'],
        'subspecialty': 'immunomodulator',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RECOVERY': {
        'aliases': ['time to recovery', 'time to sustained recovery', 'sustained recovery',
                    'clinical recovery', 'recovery', 'time to clinical improvement',
                    'clinical improvement', 'rate of recovery'],
        'subspecialty': 'antiviral',
        'measure_types': ['HR', 'RR']
    },
    'PROGRESSION': {
        'aliases': ['mechanical ventilation', 'invasive mechanical ventilation',
                    'progression to mechanical ventilation', 'icu admission',
                    'who clinical progression scale', 'clinical progression',
                    'progression to severe', 'respiratory failure', 'need for oxygen'],
        'subspecialty': 'immunomodulator',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'VIRAL_CLEARANCE': {
        'aliases': ['viral clearance', 'viral load', 'time to viral clearance',
                    'negative pcr', 'rt-pcr negativity', 'viral rna', 'undetectable viral',
                    'change in viral load'],
        'subspecialty': 'antiviral',
        'measure_types': ['HR', 'MD']
    },
    'VACCINE_EFFICACY': {
        'aliases': ['vaccine efficacy', 'vaccine effectiveness', 'efficacy against covid',
                    'protective efficacy', 'efficacy against symptomatic'],
        'subspecialty': 'prophylaxis_vaccine',
        'measure_types': ['RR', 'HR']
    },
    'SYMPTOMATIC_INFECTION': {
        'aliases': ['symptomatic covid-19', 'symptomatic infection', 'symptomatic sars-cov-2',
                    'confirmed covid-19', 'incident infection', 'breakthrough infection',
                    'laboratory-confirmed covid'],
        'subspecialty': 'prophylaxis_vaccine',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'ADVERSE_EVENTS': {
        'aliases': ['adverse events', 'serious adverse events', 'serious adverse event',
                    'treatment-emergent adverse events', 'secondary infection',
                    'discontinuation due to adverse'],
        'subspecialty': 'immunomodulator',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


TREATMENT_PATTERNS = {  # = antiviral
    'detection_keywords': [
        r'nirmatrelvir|ritonavir|paxlovid|molnupiravir|remdesivir|ensitrelvir|'
        r'favipiravir|fluvoxamine',
        r'antiviral|oral\s+antiviral|3cl\s+protease|rna[- ]dependent',
        r'hospitali[sz]ation\s+or\s+death|sustained\s+recovery',
        r'non[- ]hospitali[sz]ed|outpatient|mild[- ]to[- ]moderate\s+covid',
        r'viral\s+(?:load|clearance)|sars[- ]cov[- ]2\s+rna',
    ],
    'endpoint_patterns': [
        (r'(?:covid[- ]?19[- ]related\s+)?hospitali[sz]ation\s+or\s+(?:all[- ]cause\s+)?death|'
         r'hospitali[sz]ation\s+or\s+death', 'HOSPITALIZATION_DEATH'),
        (r'time\s+to\s+(?:sustained\s+)?recovery|sustained\s+recovery|clinical\s+improvement|'
         r'time\s+to\s+clinical\s+improvement|\brecovery\b', 'RECOVERY'),
        (r'viral\s+(?:clearance|load)|time\s+to\s+viral\s+clearance|rt[- ]pcr\s+negativ|'
         r'undetectable\s+viral|negative\s+pcr', 'VIRAL_CLEARANCE'),
        (r'(?:28[- ]day\s+|all[- ]cause\s+)?(?:mortality|(?<!or )death)', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'within\s+5\s+days\s+of\s+symptom', r'high[- ]risk', r'unvaccinated',
    ]
}


DRUG_RESISTANT_PATTERNS = {  # = immunomodulator (hospitalized/severe)
    'detection_keywords': [
        r'dexamethasone|corticosteroid|hydrocortisone|methylprednisolone',
        r'tocilizumab|sarilumab|interleukin[- ]6|\bil[- ]?6\b',
        r'baricitinib|tofacitinib|\bjak\b\s+inhibitor|janus\s+kinase',
        r'anakinra|interleukin[- ]1|canakinumab',
        r'hospitali[sz]ed|severe\s+covid|critically\s+ill|mechanical\s+ventilation',
        r'who\s+clinical\s+(?:progression|ordinal)|ordinal\s+scale',
    ],
    'endpoint_patterns': [
        (r'(?:28[- ]day|90[- ]day|in[- ]hospital|all[- ]cause)\s+(?:mortality|(?<!or )death)|'
         r'\bmortality\b|(?<!or )\bdeath\b', 'MORTALITY'),
        (r'(?:invasive\s+)?mechanical\s+ventilation|progression\s+to\s+(?:mechanical|severe)|'
         r'icu\s+admission|who\s+clinical\s+(?:progression|ordinal)|respiratory\s+failure|'
         r'need\s+for\s+oxygen', 'PROGRESSION'),
        (r'time\s+to\s+(?:clinical\s+)?(?:recovery|improvement)|clinical\s+improvement',
         'RECOVERY'),
        (r'secondary\s+infection|serious\s+adverse\s+events?|\badverse\s+events?\b',
         'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'supplemental\s+oxygen', r'\bicu\b', r'day\s+28',
    ]
}


PREVENTION_PATTERNS = {  # = prophylaxis_vaccine
    'detection_keywords': [
        r'vaccine|vaccination|\bbnt162b2\b|mrna[- ]1273|chadox1|ad26|novavax|sinovac',
        r'vaccine\s+efficacy|vaccine\s+effectiveness',
        r'pre[- ]exposure\s+prophylaxis|post[- ]exposure\s+prophylaxis|prophylaxis',
        r'symptomatic\s+(?:covid|sars[- ]cov|infection)|breakthrough\s+infection',
        r'casirivimab|imdevimab|tixagevimab|cilgavimab|evusheld|sotrovimab',
    ],
    'endpoint_patterns': [
        (r'vaccine\s+efficacy|vaccine\s+effectiveness|efficacy\s+against\s+(?:covid|symptomatic)|'
         r'protective\s+efficacy', 'VACCINE_EFFICACY'),
        (r'symptomatic\s+(?:covid[- ]?19|sars[- ]cov[- ]2|infection)|confirmed\s+covid[- ]?19|'
         r'breakthrough\s+infection|laboratory[- ]confirmed\s+covid|incident\s+infection',
         'SYMPTOMATIC_INFECTION'),
        (r'(?:covid[- ]?19[- ]related\s+)?hospitali[sz]ation', 'HOSPITALIZATION_DEATH'),
        (r'(?:all[- ]cause\s+)?(?:mortality|(?<!or )death)', 'MORTALITY'),
        (r'serious\s+adverse\s+events?|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'two[- ]dose|booster', r'seroconversion|neutralizing\s+antibod',
    ]
}


LATENT_PATTERNS = {  # = severe_supportive
    'detection_keywords': [
        r'convalescent\s+plasma|antibody\s+cocktail|monoclonal\s+antibod',
        r'therapeutic\s+anticoagulation|heparin|enoxaparin|anticoagulation',
        r'high[- ]flow\s+(?:nasal\s+)?oxygen|awake\s+prone|non[- ]invasive\s+ventilation',
        r'critically\s+ill|severe\s+(?:or\s+critical\s+)?covid|acute\s+respiratory\s+distress',
    ],
    'endpoint_patterns': [
        (r'(?:28[- ]day|90[- ]day|in[- ]hospital|all[- ]cause)\s+(?:mortality|(?<!or )death)|'
         r'\bmortality\b|(?<!or )\bdeath\b', 'MORTALITY'),
        (r'(?:invasive\s+)?mechanical\s+ventilation|organ\s+support|icu|respiratory\s+failure|'
         r'progression\s+to\s+(?:mechanical|severe)', 'PROGRESSION'),
        (r'time\s+to\s+(?:clinical\s+)?(?:recovery|improvement)|\brecovery\b', 'RECOVERY'),
        (r'serious\s+adverse\s+events?|major\s+bleeding|\badverse\s+events?\b', 'ADVERSE_EVENTS'),
    ],
    'context_patterns': [
        r'organ\s+support[- ]free\s+days', r'ventilator[- ]free\s+days',
    ]
}


def detect_covid19_subspecialty(text: str) -> Tuple[str, float]:
    """Detect COVID-19 trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: antiviral, immunomodulator, prophylaxis_vaccine,
    severe_supportive, general_covid."""
    text_lower = text.lower()
    scores = {'antiviral': 0, 'immunomodulator': 0, 'prophylaxis_vaccine': 0,
              'severe_supportive': 0}
    for kw in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['antiviral'] += 1
    for kw in DRUG_RESISTANT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['immunomodulator'] += 1
    for kw in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['prophylaxis_vaccine'] += 1
    for kw in LATENT_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['severe_supportive'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_covid', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_covid19_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'antiviral': TREATMENT_PATTERNS['endpoint_patterns'],
        'immunomodulator': DRUG_RESISTANT_PATTERNS['endpoint_patterns'],
        'prophylaxis_vaccine': PREVENTION_PATTERNS['endpoint_patterns'],
        'severe_supportive': LATENT_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_covid19_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical COVID-19 endpoint, preferring the LONGEST alias."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in COVID19_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
