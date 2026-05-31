"""
Malaria Subspecialty Patterns and Endpoints

Built for African student meta-analysis workflows (treatment, prevention,
severe malaria, transmission-blocking trials). Antimalarial RCTs report a
distinct endpoint vocabulary that the generic effect-size engine does not
recognise on its own:

Subspecialties:
- Treatment (uncomplicated P. falciparum / P. vivax ACT efficacy):
  ACPR, treatment failure (ETF/LCF/LPF), parasite/fever clearance,
  recrudescence vs reinfection, parasitaemia, Hb recovery.
- Prevention (SMC, IPTp/IPTi, chemoprophylaxis, vaccines):
  clinical malaria incidence, protective/vaccine efficacy, prevalence.
- Severe malaria (cerebral / severe falciparum):
  mortality, coma recovery, neurological sequelae, hospitalisation.
- Transmission (gametocyte carriage, MDA, mosquito infectivity).

WHO antimalarial-efficacy terminology (WHO 2009 protocol) is the anchor for the
treatment endpoints. Effect measures follow what these trials actually report:
binary outcomes -> RR/OR/ARD, incidence -> IRR/HR (protective efficacy =
1 - RR/HR), continuous (parasitaemia, Hb) -> MD/SMD/GMR.
"""

from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# MALARIA ENDPOINTS
# ============================================================

MALARIA_ENDPOINTS = {
    # --- Treatment efficacy (WHO therapeutic-efficacy outcomes) ---
    'ACPR': {
        'aliases': ['adequate clinical and parasitological response',
                    'adequate clinical and parasitologic response',
                    'acpr', 'pcr-corrected acpr', 'pcr-adjusted acpr',
                    'pcr corrected cure rate', 'parasitological cure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'TREATMENT_FAILURE': {
        'aliases': ['treatment failure', 'total treatment failure',
                    'therapeutic failure', 'clinical failure',
                    'parasitological failure', 'failure rate'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'HR', 'OR']
    },
    'EARLY_TREATMENT_FAILURE': {
        'aliases': ['early treatment failure', 'etf'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'LATE_CLINICAL_FAILURE': {
        'aliases': ['late clinical failure', 'lcf'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'LATE_PARASITOLOGICAL_FAILURE': {
        'aliases': ['late parasitological failure',
                    'late parasitologic failure', 'lpf'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'RECRUDESCENCE': {
        'aliases': ['recrudescence', 'pcr-confirmed recrudescence',
                    'recrudescent infection', 'pcr-corrected failure'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'REINFECTION': {
        'aliases': ['reinfection', 're-infection', 'new infection',
                    'pcr-confirmed reinfection'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },
    'PARASITE_CLEARANCE_TIME': {
        'aliases': ['parasite clearance time', 'pct',
                    'parasite clearance half-life', 'clearance half-life',
                    'time to parasite clearance'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'HR']
    },
    'DAY3_POSITIVITY': {
        'aliases': ['day 3 parasitaemia', 'day-3 parasitaemia',
                    'day 3 positivity', 'day 3 parasite positivity',
                    'proportion positive on day 3', 'day 3 positive'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'RD', 'OR']
    },
    'FEVER_CLEARANCE_TIME': {
        'aliases': ['fever clearance time', 'fct',
                    'time to fever clearance'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'HR']
    },
    'PARASITAEMIA': {
        'aliases': ['parasitaemia', 'parasitemia', 'parasite density',
                    'asexual parasitaemia', 'geometric mean parasite density'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD', 'GMR']
    },
    'GAMETOCYTE_CARRIAGE': {
        'aliases': ['gametocyte carriage', 'gametocytaemia', 'gametocytemia',
                    'gametocyte prevalence', 'gametocyte positivity'],
        'subspecialty': 'transmission',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'HAEMOGLOBIN': {
        'aliases': ['haemoglobin', 'hemoglobin', 'hb concentration',
                    'haemoglobin recovery', 'change in haemoglobin'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'SMD']
    },
    'ANAEMIA': {
        'aliases': ['anaemia', 'anemia', 'severe anaemia', 'moderate anaemia'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Prevention / vaccine / chemoprevention ---
    'CLINICAL_MALARIA': {
        'aliases': ['clinical malaria', 'clinical malaria episodes',
                    'symptomatic malaria', 'uncomplicated malaria',
                    'malaria incidence', 'incidence of malaria',
                    'first or only episode of clinical malaria'],
        'subspecialty': 'prevention',
        'measure_types': ['IRR', 'HR', 'RR']
    },
    'MALARIA_INFECTION': {
        'aliases': ['malaria infection', 'asymptomatic parasitaemia',
                    'incident malaria infection', 'incident infection',
                    'time to first infection'],
        'subspecialty': 'prevention',
        'measure_types': ['IRR', 'HR', 'RR', 'OR']
    },
    'PROTECTIVE_EFFICACY': {
        'aliases': ['protective efficacy', 'vaccine efficacy',
                    'efficacy against clinical malaria',
                    'efficacy against severe malaria', 'malaria efficacy'],
        'subspecialty': 'prevention',
        'measure_types': ['HR', 'IRR', 'RR']
    },
    'PREVALENCE': {
        'aliases': ['parasite prevalence', 'malaria prevalence',
                    'prevalence of parasitaemia', 'pcr prevalence'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Severe malaria ---
    'MORTALITY': {
        'aliases': ['mortality', 'death', 'all-cause mortality',
                    'malaria mortality', 'case fatality', 'in-hospital mortality',
                    'malaria-attributable mortality'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'SEVERE_MALARIA': {
        'aliases': ['severe malaria', 'severe and complicated malaria',
                    'progression to severe malaria'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'CEREBRAL_MALARIA': {
        'aliases': ['cerebral malaria', 'coma', 'coma recovery time',
                    'neurological sequelae'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR', 'MD']
    },
    'HOSPITALISATION': {
        'aliases': ['hospitalisation', 'hospitalization', 'hospital admission',
                    'admission for malaria', 'malaria hospitalisation'],
        'subspecialty': 'severe',
        'measure_types': ['IRR', 'HR', 'RR']
    },

    # --- P. vivax radical cure (relapse is distinct from recrudescence/reinfection) ---
    'RELAPSE': {
        'aliases': ['relapse', 'vivax relapse', 'p. vivax recurrence',
                    'recurrent vivax', 'recurrence-free efficacy',
                    'first recurrence', 'time to first recurrence',
                    'freedom from recurrence', 'radical cure'],
        'subspecialty': 'treatment',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RECURRENT_PARASITAEMIA': {
        'aliases': ['recurrent parasitaemia', 'recurrent parasitemia',
                    'pcr-uncorrected recurrence', 'any recurrence',
                    'recurrent infection (uncorrected)'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'HR', 'OR']
    },

    # --- Molecular / pharmacodynamic (resistance surveillance) ---
    'MOLECULAR_MARKER': {
        'aliases': ['kelch13', 'k13', 'pfkelch13', 'pfk13',
                    'artemisinin partial resistance', 'validated marker',
                    'pfcrt', 'pfmdr1', 'pfpm2', 'plasmepsin', 'copy number'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR']
    },
    'PARASITE_REDUCTION_RATIO': {
        'aliases': ['parasite reduction ratio', 'prr', 'prr48', 'prr24',
                    'log10 parasite reduction', 'parasite clearance estimator'],
        'subspecialty': 'treatment',
        'measure_types': ['MD', 'GMR']
    },
    'HAEMOLYSIS': {
        'aliases': ['haemolysis', 'hemolysis', 'acute haemolytic anaemia',
                    'haemoglobin drop', 'haemoglobinuria', 'g6pd deficiency'],
        'subspecialty': 'treatment',
        'measure_types': ['RR', 'OR', 'MD']
    },

    # --- IPTp / maternal malaria outcomes ---
    'PLACENTAL_MALARIA': {
        'aliases': ['placental malaria', 'placental parasitaemia',
                    'placental infection'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LOW_BIRTH_WEIGHT': {
        'aliases': ['low birth weight', 'low birthweight', 'lbw',
                    'birth weight', 'birthweight'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR', 'MD']
    },
    'MATERNAL_ANAEMIA': {
        'aliases': ['maternal anaemia', 'maternal anemia',
                    'third-trimester anaemia', 'anaemia at delivery'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR']
    },
    'PRETERM_BIRTH': {
        'aliases': ['preterm birth', 'prematurity', 'preterm delivery',
                    'small for gestational age', 'stillbirth'],
        'subspecialty': 'prevention',
        'measure_types': ['RR', 'OR']
    },

    # --- Severe-malaria component outcomes ---
    'ACIDOSIS': {
        'aliases': ['metabolic acidosis', 'base deficit', 'hyperlactataemia',
                    'respiratory distress', 'acidosis'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR']
    },
    'HYPOGLYCAEMIA': {
        'aliases': ['hypoglycaemia', 'hypoglycemia'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR']
    },
    'ACUTE_KIDNEY_INJURY': {
        'aliases': ['acute kidney injury', 'aki', 'renal failure',
                    'blackwater fever'],
        'subspecialty': 'severe',
        'measure_types': ['RR', 'OR', 'HR']
    },
}


# ============================================================
# TREATMENT PATTERNS (uncomplicated falciparum / vivax)
# ============================================================

TREATMENT_PATTERNS = {
    'detection_keywords': [
        r'uncomplicated\s+(?:falciparum\s+|vivax\s+|plasmodium\s+)?malaria',
        r'antimalarial\s+(?:drug\s+)?efficacy',
        r'therapeutic\s+efficacy',
        r'\bacpr\b',
        r'adequate\s+clinical\s+and\s+parasitolog',
        r'parasite\s+clearance',
        r'recrudescen',
        r'artemisinin[- ]based\s+combination',
        r'\bact\b',
        r'artemether[- ]?lumefantrine|coartem',
        r'artesunate[- ]?amodiaquine',
        r'dihydroartemisinin[- ]?piperaquine|dha[- ]?ppq|\bdp\b',
        r'artesunate[- ]?(?:mefloquine|pyronaridine)',
        r'chloroquine|amodiaquine',
        r'sulfadoxine[- ]?pyrimethamine|\bsp\b',
        r'primaquine|tafenoquine',
        r'p(?:lasmodium)?\.?\s*falciparum',
        r'p(?:lasmodium)?\.?\s*vivax',
    ],
    'endpoint_patterns': [
        (r'adequate\s+clinical\s+and\s+parasitolog\w+\s+response', 'ACPR'),
        (r'\bacpr\b', 'ACPR'),
        (r'pcr[- ]?(?:corrected|adjusted)\s+(?:cure|acpr)', 'ACPR'),
        (r'(?:parasitological\s+|day[- ]?\d+\s+)?cure\s+rate', 'ACPR'),
        (r'early\s+treatment\s+failure|\betf\b', 'EARLY_TREATMENT_FAILURE'),
        (r'late\s+clinical\s+failure|\blcf\b', 'LATE_CLINICAL_FAILURE'),
        (r'late\s+parasitolog\w+\s+failure|\blpf\b', 'LATE_PARASITOLOGICAL_FAILURE'),
        (r'(?:total\s+|therapeutic\s+)?treatment\s+failure', 'TREATMENT_FAILURE'),
        # vivax relapse / radical-cure recurrence -- BEFORE recrudescence/reinfection
        (r'recurrence[- ]free|radical\s+cure|vivax\s+(?:relapse|recurrence)|'
         r'recurrent\s+vivax|time\s+to\s+first\s+recurrence', 'RELAPSE'),
        (r'\brelapse', 'RELAPSE'),
        (r'recrudescen\w+', 'RECRUDESCENCE'),
        (r're[- ]?infection|new\s+infection', 'REINFECTION'),
        # PCR-UNCORRECTED recurrent parasitaemia != treatment failure (failure is
        # the PCR-corrected recrudescent fraction). Map to the neutral endpoint.
        (r'recurrent\s+parasit', 'RECURRENT_PARASITAEMIA'),
        (r'parasite\s+reduction\s+ratio|\bprr(?:48|24)?\b|'
         r'log10?\s+parasite\s+reduction', 'PARASITE_REDUCTION_RATIO'),
        (r'parasite\s+clearance\s+(?:time|half[- ]?life)|\bpct\b', 'PARASITE_CLEARANCE_TIME'),
        (r'day[- ]?3\s+(?:parasit|positiv)', 'DAY3_POSITIVITY'),
        (r'fever\s+clearance\s+time|\bfct\b', 'FEVER_CLEARANCE_TIME'),
        (r'kelch\s?13|pfk(?:elch)?13|\bk13\b|artemisinin\s+partial\s+resistance',
         'MOLECULAR_MARKER'),
        (r'h[ae]molysis|haemoglobinuria|g6pd\s+deficien', 'HAEMOLYSIS'),
        (r'parasite\s+density|parasit[ae]emia', 'PARASITAEMIA'),
        (r'gametocyt', 'GAMETOCYTE_CARRIAGE'),
        (r'h[ae]moglobin|\bhb\b', 'HAEMOGLOBIN'),
        (r'an[ae]emia', 'ANAEMIA'),
    ],
    'context_patterns': [
        r'day\s+(?:28|42|63)\s+(?:acpr|cure|efficacy)',
        r'pcr[- ]?(?:corrected|adjusted|uncorrected)',
        r'who\s+(?:2009\s+)?(?:protocol|antimalarial)',
        r'parasites?\s*/\s*[µu]?l',
    ]
}


# ============================================================
# PREVENTION PATTERNS (SMC, IPT, chemoprophylaxis, vaccines)
# ============================================================

PREVENTION_PATTERNS = {
    'detection_keywords': [
        r'seasonal\s+malaria\s+chemoprevention|\bsmc\b',
        r'intermittent\s+preventive\s+treatment|\bipt[pi]?\b',
        r'chemoprophylaxis|chemoprevention',
        r'malaria\s+vaccine',
        r'rts,?\s?s|as01',
        r'r21|matrix[- ]?m',
        r'protective\s+efficacy|vaccine\s+efficacy',
        r'incidence\s+of\s+(?:clinical\s+)?malaria',
        r'insecticide[- ]?treated\s+net|\bitn\b|\bllin\b',
        r'indoor\s+residual\s+spray',
        r'mass\s+drug\s+administration|\bmda\b',
    ],
    'endpoint_patterns': [
        (r'clinical\s+malaria|symptomatic\s+malaria|uncomplicated\s+malaria', 'CLINICAL_MALARIA'),
        (r'incidence\s+of\s+(?:clinical\s+)?malaria|malaria\s+incidence', 'CLINICAL_MALARIA'),
        (r'(?:vaccine|protective)\s+efficacy|efficacy\s+against', 'PROTECTIVE_EFFICACY'),
        (r'placental\s+malaria|placental\s+(?:parasit|infection)', 'PLACENTAL_MALARIA'),
        (r'low\s+birth\s*weight|\blbw\b|birth\s*weight', 'LOW_BIRTH_WEIGHT'),
        (r'maternal\s+an[ae]emia|an[ae]emia\s+at\s+delivery', 'MATERNAL_ANAEMIA'),
        (r'preterm\s+(?:birth|delivery)|prematurity|small\s+for\s+gestational|stillbirth',
         'PRETERM_BIRTH'),
        (r'(?:malaria|parasite|p\.?\s*falciparum)\s+infection', 'MALARIA_INFECTION'),
        (r'(?:parasite|malaria)\s+prevalence', 'PREVALENCE'),
        (r'asymptomatic\s+parasit', 'MALARIA_INFECTION'),
    ],
    'context_patterns': [
        r'per\s+(?:person[- ]?year|child[- ]?year|1000\s+(?:person|child)[- ]?years)',
        r'incidence\s+rate\s+ratio|\birr\b',
        r'1\s*[-−]\s*(?:hazard\s+ratio|hr|rr|risk\s+ratio)',
        r'transmission\s+season',
    ]
}


# ============================================================
# SEVERE MALARIA PATTERNS
# ============================================================

SEVERE_PATTERNS = {
    'detection_keywords': [
        r'severe\s+(?:and\s+complicated\s+)?malaria',
        r'cerebral\s+malaria',
        r'severe\s+falciparum\s+malaria',
        r'intravenous\s+artesunate|iv\s+artesunate',
        r'parenteral\s+(?:artesunate|quinine)',
        r'coma|blantyre\s+coma|glasgow\s+coma',
        r'case\s+fatality',
        r'\bquinine\b',
    ],
    'endpoint_patterns': [
        (r'(?:in[- ]?hospital\s+|case\s+)?(?:mortality|fatality|death)', 'MORTALITY'),
        (r'severe\s+malaria|progression\s+to\s+severe', 'SEVERE_MALARIA'),
        (r'cerebral\s+malaria|coma|neurological\s+sequelae', 'CEREBRAL_MALARIA'),
        (r'metabolic\s+acidosis|base\s+deficit|hyperlactat|respiratory\s+distress',
         'ACIDOSIS'),
        (r'hypoglyc[ae]emia', 'HYPOGLYCAEMIA'),
        (r'acute\s+kidney\s+injury|\baki\b|renal\s+failure|blackwater', 'ACUTE_KIDNEY_INJURY'),
        (r'hospital(?:isation|ization|\s+admission)', 'HOSPITALISATION'),
    ],
    'context_patterns': [
        r'blantyre\s+coma\s+score',
        r'parenteral|intravenous|intramuscular',
        r'lactate|acidosis|hypoglyc[ae]emia',
    ]
}


# ============================================================
# TRANSMISSION PATTERNS
# ============================================================

TRANSMISSION_PATTERNS = {
    'detection_keywords': [
        r'gametocyt',
        r'transmission[- ]?blocking',
        r'mosquito\s+infectivity',
        r'membrane\s+feeding',
        r'single[- ]?(?:low[- ]?)?dose\s+primaquine|\bsldp\b',
        r'infectious\s+to\s+mosquito',
    ],
    'endpoint_patterns': [
        (r'gametocyte\s+(?:carriage|prevalence|positivity|density)', 'GAMETOCYTE_CARRIAGE'),
        (r'gametocyt[ae]emia', 'GAMETOCYTE_CARRIAGE'),
        (r'mosquito\s+infectivity|membrane\s+feeding', 'GAMETOCYTE_CARRIAGE'),
    ],
    'context_patterns': [
        r'day\s+(?:7|14)\s+gametocyte',
        r'g6pd|glucose[- ]?6[- ]?phosphate',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_malaria_subspecialty(text: str) -> Tuple[str, float]:
    """
    Detect malaria trial subspecialty from text.

    Returns:
        Tuple of (subspecialty, confidence)
        Subspecialties: 'treatment', 'prevention', 'severe', 'transmission',
        'general_malaria'
    """
    text_lower = text.lower()

    scores = {
        'treatment': 0,
        'prevention': 0,
        'severe': 0,
        'transmission': 0,
    }

    for keyword in TREATMENT_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['treatment'] += 1
    for keyword in PREVENTION_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['prevention'] += 1
    for keyword in SEVERE_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['severe'] += 1
    for keyword in TRANSMISSION_PATTERNS['detection_keywords']:
        if re.search(keyword, text_lower):
            scores['transmission'] += 1

    best_subspecialty = max(scores, key=scores.get)
    best_score = scores[best_subspecialty]
    total = sum(scores.values())

    if best_score == 0:
        return ('general_malaria', 0.5)

    confidence = best_score / total if total > 0 else 0.5
    return (best_subspecialty, confidence)


def get_malaria_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    """Get endpoint patterns for a specific malaria subspecialty."""
    patterns_map = {
        'treatment': TREATMENT_PATTERNS['endpoint_patterns'],
        'prevention': PREVENTION_PATTERNS['endpoint_patterns'],
        'severe': SEVERE_PATTERNS['endpoint_patterns'],
        'transmission': TRANSMISSION_PATTERNS['endpoint_patterns'],
    }
    return patterns_map.get(subspecialty, [])


def normalize_malaria_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize endpoint name to canonical malaria form.

    Prefers the LONGEST matching alias so specific endpoints win over generic
    substrings (e.g. "maternal anaemia" -> MATERNAL_ANAEMIA, not ANAEMIA;
    "recurrent parasitaemia" -> RECURRENT_PARASITAEMIA, not PARASITAEMIA).
    """
    endpoint_lower = endpoint.lower()

    best, best_len = None, 0
    for canonical, info in MALARIA_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    if best:
        return best

    return endpoint.upper()
